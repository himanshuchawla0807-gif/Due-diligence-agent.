"""Durable local jobs with atomic claims, cancellation, and bounded execution."""
import asyncio
import json
import time
import uuid

from .persistence import validate_id

LEASE_SECONDS = 600

class JobManager:
    def __init__(self, database, runner, concurrency=3, *, on_result=None):
        self.database, self.runner = database, runner
        self.on_result = on_result
        self.tasks = {}
        self.limit = asyncio.Semaphore(max(1, min(concurrency, 7)))
        with database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            columns = {row[1] for row in connection.execute("PRAGMA table_info(jobs)")}
            if "lease_until" not in columns:
                connection.execute("ALTER TABLE jobs ADD COLUMN lease_until REAL NOT NULL DEFAULT 0")
            if "lease_token" not in columns:
                connection.execute("ALTER TABLE jobs ADD COLUMN lease_token TEXT")
            connection.execute("CREATE TABLE IF NOT EXISTS job_events(sequence INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL, state TEXT NOT NULL, timestamp REAL NOT NULL)")

    def _state(self, job_id, lease_token, state, result=None, error=None):
        with self.database.connect() as connection:
            now = time.time()
            claimed = connection.execute(
                "UPDATE jobs SET state=?,result=?,error=?,updated=?,lease_until=0,lease_token=NULL "
                "WHERE id=? AND state='running' AND lease_token=? RETURNING session_id",
                (state, json.dumps(result) if result is not None else None, error, now, job_id, lease_token),
            ).fetchone()
            if claimed:
                if result is not None and self.on_result:
                    self.on_result(connection, claimed[0], result)
                connection.execute("INSERT INTO job_events(job_id,state,timestamp) VALUES (?,?,?)", (job_id, state, now))

    def submit(self, session_id, payload, idempotency_key=None):
        validate_id(session_id)
        # Idempotency IDs are scoped to this tenant database, and payloads must match.
        job_id = uuid.uuid5(uuid.NAMESPACE_URL, session_id+":"+idempotency_key).hex if idempotency_key else uuid.uuid4().hex
        encoded = json.dumps(payload, sort_keys=True)
        with self.database.connect() as connection:
            connection.execute("INSERT OR IGNORE INTO jobs(id,session_id,state,payload,updated) VALUES (?,?,'queued',?,?)", (job_id, session_id, encoded, time.time()))
            if connection.execute("SELECT payload FROM jobs WHERE id=?", (job_id,)).fetchone()[0] != encoded:
                raise ValueError("Idempotency key already used with a different request")
        self.recover()
        return job_id

    def recover(self):
        with self.database.connect() as connection:
            rows = connection.execute("SELECT id FROM jobs WHERE state='queued' OR (state='running' AND lease_until<?)", (time.time(),)).fetchall()
        for (job_id,) in rows:
            if job_id not in self.tasks:
                task = asyncio.create_task(self._run(job_id))
                self.tasks[job_id] = task
                task.add_done_callback(lambda _, key=job_id: self.tasks.pop(key, None))

    async def _run(self, job_id):
        async with self.limit:
            with self.database.connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute("SELECT session_id,payload,cancelled FROM jobs WHERE id=? AND (state='queued' OR (state='running' AND lease_until<?))", (job_id, time.time())).fetchone()
                if not row:
                    return
                if row[2]:
                    connection.execute("UPDATE jobs SET state='cancelled' WHERE id=?", (job_id,))
                    return
                lease_token = uuid.uuid4().hex
                now = time.time()
                connection.execute(
                    "UPDATE jobs SET state='running',lease_until=?,lease_token=?,updated=? WHERE id=?",
                    (now + LEASE_SECONDS, lease_token, now, job_id),
                )
                connection.execute("INSERT INTO job_events(job_id,state,timestamp) VALUES (?,'running',?)", (job_id, time.time()))
            renewal = asyncio.create_task(self._renew_lease(job_id, lease_token))
            try:
                result = await self.runner(row[0], json.loads(row[1]))
                self._state(job_id, lease_token, result.get("status", "completed"), result=result)
            except asyncio.CancelledError:
                # Explicit cancellation already cleared the token and marked the
                # job terminal. Worker shutdown only requeues its own attempt.
                self._state(job_id, lease_token, "queued")
            except Exception as exc:
                self._state(job_id, lease_token, "error", error=str(exc))
            finally:
                renewal.cancel()
                await asyncio.gather(renewal, return_exceptions=True)

    async def _renew_lease(self, job_id, lease_token):
        while True:
            await asyncio.sleep(LEASE_SECONDS / 3)
            with self.database.connect() as connection:
                updated = connection.execute(
                    "UPDATE jobs SET lease_until=? WHERE id=? AND state='running' AND lease_token=?",
                    (time.time() + LEASE_SECONDS, job_id, lease_token),
                )
                if not updated.rowcount:
                    return

    def get(self, job_id):
        with self.database.connect() as connection:
            row = connection.execute("SELECT session_id,state,result,error,cancelled FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            return None
        return {"job_id": job_id, "session_id": row[0], "status": row[1], "result": json.loads(row[2]) if row[2] else None, "error": row[3], "cancel_requested": bool(row[4])}

    def cancel_session(self, session_id):
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            now = time.time()
            ids = [row[0] for row in connection.execute(
                "UPDATE jobs SET cancelled=1,state='cancelled',result=NULL,error=NULL,updated=?,lease_until=0,lease_token=NULL "
                "WHERE session_id=? AND state IN ('queued','running') RETURNING id",
                (now, session_id),
            )]
            connection.executemany(
                "INSERT INTO job_events(job_id,state,timestamp) VALUES (?,'cancelled',?)",
                [(job_id, now) for job_id in ids],
            )
        for job_id in ids:
            task = self.tasks.get(job_id)
            if task:
                task.cancel()
        return len(ids)

    async def wait(self, job_id):
        if job_id in self.tasks:
            await asyncio.gather(asyncio.shield(self.tasks[job_id]), return_exceptions=True)
        result = self.get(job_id)
        if not result or result["status"] in {"error", "cancelled", "queued", "running"}:
            raise ValueError((result or {}).get("error") or "Analysis cancelled")
        return result["result"]

    async def close(self):
        tasks = list(self.tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

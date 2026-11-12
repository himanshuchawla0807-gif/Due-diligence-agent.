import asyncio

import pytest

from backend.jobs import JobManager
from backend.persistence import Database


@pytest.mark.asyncio
async def test_live_job_renews_lease_before_another_worker_recovers(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.jobs.LEASE_SECONDS", 0.15, raising=False)
    clock = [1000.0]
    monkeypatch.setattr("backend.jobs.time.time", lambda: clock[0])
    started = asyncio.Event()
    release = asyncio.Event()
    attempts = []

    async def runner(session, payload):
        attempts.append(session)
        started.set()
        await release.wait()
        return {"status": "completed"}

    database = Database(tmp_path / "jobs.sqlite3")
    first = JobManager(database, runner)
    second = JobManager(database, runner)
    job_id = first.submit("case", {})
    try:
        await asyncio.wait_for(started.wait(), 1)
        clock[0] += 601
        await asyncio.sleep(0.1)
        second.recover()
        await asyncio.sleep(0.05)
        assert attempts == ["case"]
        release.set()
        assert (await first.wait(job_id))["status"] == "completed"
    finally:
        await first.close()
        await second.close()

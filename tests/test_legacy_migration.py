import json

import pytest

from backend.config import Settings
from backend.storage import SessionStore


def test_corrupt_legacy_store_can_be_repaired_and_retried(tmp_path):
    path = tmp_path / "sessions.json"
    path.write_text("{broken", encoding="utf-8")
    settings = Settings(local_storage_dir=tmp_path / "storage", session_store=path)

    with pytest.raises(ValueError, match="corrupt"):
        SessionStore(settings)

    path.write_text(json.dumps({"case": {"findings": [{"finding": "Revenue risk"}]}}), encoding="utf-8")
    assert SessionStore(settings).get_or_create("case")["findings"] == [{"finding": "Revenue risk"}]


def test_invalid_legacy_record_does_not_partially_migrate(tmp_path):
    path = tmp_path / "sessions.json"
    path.write_text(json.dumps({"case": {"findings": ["first"]}, "bad/id": {"findings": []}}), encoding="utf-8")
    settings = Settings(local_storage_dir=tmp_path / "storage", session_store=path)

    with pytest.raises(ValueError):
        SessionStore(settings)

    path.write_text(json.dumps({"case": {"findings": ["first"]}, "other": {"findings": ["second"]}}), encoding="utf-8")
    store = SessionStore(settings)
    assert store.get_or_create("case")["findings"] == ["first"]
    assert store.get_or_create("other")["findings"] == ["second"]


def test_interrupted_migration_rolls_back_and_retries(tmp_path, monkeypatch):
    from backend.persistence import Database

    path = tmp_path / "sessions.json"
    path.write_text(json.dumps({"case": {"findings": ["first"]}, "other": {"findings": ["second"]}}), encoding="utf-8")
    settings = Settings(local_storage_dir=tmp_path / "storage", session_store=path)
    original = Database.update_session_in_transaction

    def interrupt(connection, session_id, change):
        if session_id == "other":
            raise RuntimeError("interrupted")
        return original(connection, session_id, change)

    with monkeypatch.context() as context:
        context.setattr(Database, "update_session_in_transaction", staticmethod(interrupt))
        with pytest.raises(RuntimeError, match="interrupted"):
            SessionStore(settings)

    store = SessionStore(settings)
    assert store.get_or_create("case")["findings"] == ["first"]
    assert store.get_or_create("other")["findings"] == ["second"]

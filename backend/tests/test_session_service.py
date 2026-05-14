import shutil
import time
from pathlib import Path

from app.services.session_service import SessionService, _registry


def _make_service(tmp_path: Path) -> SessionService:
    _registry.clear()
    return SessionService(generated_agents_dir=str(tmp_path))


def test_create_session(tmp_path):
    svc = _make_service(tmp_path)
    sid = svc.create_session()
    assert isinstance(sid, str)
    assert len(sid) == 36  # UUID v4 format
    assert (tmp_path / sid).is_dir()


def test_get_session(tmp_path):
    svc = _make_service(tmp_path)
    sid = svc.create_session()
    session = svc.get_session(sid)
    assert session is not None
    assert session["session_id"] == sid
    assert session["stage"] == "idle"
    assert session["chat_ws"] is None
    assert session["status_ws"] is None


def test_get_session_unknown(tmp_path):
    svc = _make_service(tmp_path)
    assert svc.get_session("nonexistent") is None


def test_session_exists(tmp_path):
    svc = _make_service(tmp_path)
    sid = svc.create_session()
    assert svc.session_exists(sid) is True
    assert svc.session_exists("fake") is False


def test_set_and_clear_chat_ws(tmp_path):
    svc = _make_service(tmp_path)
    sid = svc.create_session()
    svc.set_chat_ws(sid, "mock_ws")
    assert _registry[sid]["chat_ws"] == "mock_ws"
    svc.clear_chat_ws(sid)
    assert _registry[sid]["chat_ws"] is None


def test_set_and_clear_status_ws(tmp_path):
    svc = _make_service(tmp_path)
    sid = svc.create_session()
    svc.set_status_ws(sid, "mock_ws")
    assert _registry[sid]["status_ws"] == "mock_ws"
    svc.clear_status_ws(sid)
    assert _registry[sid]["status_ws"] is None


def test_update_stage(tmp_path):
    svc = _make_service(tmp_path)
    sid = svc.create_session()
    svc.update_stage(sid, "elicitor")
    assert _registry[sid]["stage"] == "elicitor"


def test_get_session_dir(tmp_path):
    svc = _make_service(tmp_path)
    sid = svc.create_session()
    assert svc.get_session_dir(sid) == tmp_path / sid


def test_cleanup_old_sessions(tmp_path):
    svc = _make_service(tmp_path)
    old_dir = tmp_path / "old-session"
    old_dir.mkdir()
    # Backdate mtime to 2 days ago
    old_time = time.time() - (48 * 3600)
    import os
    os.utime(old_dir, (old_time, old_time))

    new_sid = svc.create_session()  # fresh session

    deleted = svc.cleanup_old_sessions(max_age_hours=24)
    assert deleted == 1
    assert not old_dir.exists()
    assert (tmp_path / new_sid).exists()


def test_cleanup_no_dir(tmp_path):
    nonexistent = tmp_path / "nope"
    svc = SessionService(generated_agents_dir=str(nonexistent))
    _registry.clear()
    assert svc.cleanup_old_sessions() == 0

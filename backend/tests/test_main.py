import pytest
from httpx import ASGITransport, AsyncClient
from fastapi.testclient import TestClient

from app.main import app
from app.services.session_service import _registry


@pytest.fixture(autouse=True)
def clear_registry():
    _registry.clear()
    yield
    _registry.clear()


# ── REST Tests ───────────────────────────────────────────────────────


def test_health():
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


def test_create_session():
    with TestClient(app) as client:
        resp = client.post("/sessions")
        assert resp.status_code == 201
        data = resp.json()
        assert "session_id" in data
        sid = data["session_id"]
        assert len(sid) == 36


def test_cors_headers():
    with TestClient(app) as client:
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


# ── WebSocket Tests ──────────────────────────────────────────────────


def test_ws_chat_welcome():
    with TestClient(app) as client:
        sid = client.post("/sessions").json()["session_id"]
        with client.websocket_connect(f"/ws/chat/{sid}") as ws:
            data = ws.receive_json()
            assert data["type"] == "chat.message"
            assert "text" in data["payload"]
            assert data["session_id"] == sid


def test_ws_chat_unknown_session():
    with TestClient(app) as client:
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/chat/bad-session-id") as ws:
                ws.receive_json()


def test_ws_status_initial_stage():
    with TestClient(app) as client:
        sid = client.post("/sessions").json()["session_id"]
        with client.websocket_connect(f"/ws/status/{sid}") as ws:
            data = ws.receive_json()
            assert data["type"] == "status.stage_update"
            assert data["payload"]["stage"] == "idle"
            assert data["payload"]["description"] == "Waiting for prompt"
            assert data["session_id"] == sid


def test_ws_status_unknown_session():
    with TestClient(app) as client:
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/status/bad-session-id") as ws:
                ws.receive_json()


def test_ws_chat_stub_response():
    with TestClient(app) as client:
        sid = client.post("/sessions").json()["session_id"]
        with client.websocket_connect(f"/ws/chat/{sid}") as ws:
            ws.receive_json()  # welcome
            ws.send_json({"type": "control.user_input", "payload": {"text": "test"}})
            resp = ws.receive_json()
            assert resp["type"] == "error.pipeline_failure"
            assert "not yet connected" in resp["payload"]["message"].lower() or "not yet" in resp["payload"]["message"].lower()

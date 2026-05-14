import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.models.messages import (
    BaseMessage,
    ChatMessage,
    ErrorMessage,
    StageUpdateMessage,
)
from app.services.session_service import SessionService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

session_service = SessionService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    base_dir = Path(settings.generated_agents_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    deleted = session_service.cleanup_old_sessions()
    logger.info("Startup complete. Cleaned %d old session(s).", deleted)
    yield


app = FastAPI(title="Frankenstein", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


async def send_message(ws: WebSocket, msg: BaseMessage) -> None:
    try:
        await ws.send_json(msg.model_dump(mode="json"))
    except Exception as e:
        logger.warning("Failed to send WS message: %s", e)


# ── REST Endpoints ───────────────────────────────────────────────────


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/sessions", status_code=201)
async def create_session():
    try:
        session_id = session_service.create_session()
        return {"session_id": session_id}
    except OSError as e:
        logger.error("Failed to create session directory: %s", e)
        return JSONResponse(
            content={"detail": "Failed to create session directory"},
            status_code=500,
        )


# ── WebSocket Endpoints ─────────────────────────────────────────────


@app.websocket("/ws/chat/{session_id}")
async def ws_chat(websocket: WebSocket, session_id: str):
    await websocket.accept()

    if not session_service.session_exists(session_id):
        await websocket.close(code=4004, reason="unknown session")
        return

    session_service.set_chat_ws(session_id, websocket)

    welcome = ChatMessage(
        payload={"text": "Frankenstein is ready. Describe the agent you want to build."},
        session_id=session_id,
    )
    await send_message(websocket, welcome)

    try:
        while True:
            data = await websocket.receive_json()
            logger.info("Chat message from %s: %s", session_id, data.get("type"))
            err = ErrorMessage(
                type="error.pipeline_failure",
                payload={
                    "stage": "idle",
                    "message": "Pipeline not yet connected. This will be wired in Story 1.3.",
                    "recoverable": False,
                },
                session_id=session_id,
            )
            await send_message(websocket, err)
    except WebSocketDisconnect:
        logger.info("Chat WS disconnected: %s", session_id)
    finally:
        session_service.clear_chat_ws(session_id)


@app.websocket("/ws/status/{session_id}")
async def ws_status(websocket: WebSocket, session_id: str):
    await websocket.accept()

    if not session_service.session_exists(session_id):
        await websocket.close(code=4004, reason="unknown session")
        return

    session_service.set_status_ws(session_id, websocket)

    stage_msg = StageUpdateMessage(
        payload={"stage": "idle", "description": "Waiting for prompt"},
        session_id=session_id,
    )
    await send_message(websocket, stage_msg)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("Status WS disconnected: %s", session_id)
    finally:
        session_service.clear_status_ws(session_id)

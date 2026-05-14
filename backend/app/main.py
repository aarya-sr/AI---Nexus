import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langgraph.types import Command
from pydantic import BaseModel

from app.config import settings
from app.models.messages import (
    BaseMessage,
    ChatMessage,
    CheckpointMessage,
    ErrorMessage,
    StageUpdateMessage,
)
from app.pipeline.graph import compiled_graph
from app.services.session_service import SessionService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

session_service = SessionService()

# In-memory pipeline run tracking (NFR16: no persistence)
_pipeline_runs: dict[str, asyncio.Task] = {}


# ── Request/Response Models ──────────────────────────────────────────


class ApproveRequest(BaseModel):
    checkpoint: Literal["requirements", "spec"]
    approved: bool
    feedback: str | None = None


class ApproveResponse(BaseModel):
    status: Literal["resumed", "revision_requested"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.chroma_service import ChromaService

    base_dir = Path(settings.generated_agents_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    chroma = ChromaService(persist_dir=settings.chroma_persist_dir)
    tool_dir = Path(__file__).parent / "tool_library"
    count = chroma.seed_tools(tool_dir)
    logger.info("Seeded %d tools into Chroma.", count)
    app.state.chroma = chroma

    deleted = session_service.cleanup_old_sessions()
    logger.info("Startup complete. Cleaned %d old session(s).", deleted)
    yield


app = FastAPI(title="Frankenstein", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


async def send_message(ws: WebSocket, msg: BaseMessage) -> None:
    try:
        await ws.send_json(msg.model_dump(mode="json"))
    except WebSocketDisconnect:
        raise
    except Exception as e:
        logger.error("Failed to send WS message: %s", e)
        raise


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


@app.post("/sessions/{session_id}/approve", response_model=ApproveResponse)
async def approve_checkpoint(session_id: str, body: ApproveRequest):
    """Resume pipeline after human checkpoint approval or send corrections."""
    if not session_service.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    thread_id = session_id
    config = {"configurable": {"thread_id": thread_id}}
    is_spec = body.checkpoint == "spec"

    if body.approved:
        await asyncio.to_thread(
            compiled_graph.invoke,
            Command(resume={"approved": True}),
            config,
        )

        session = session_service.get_session(session_id)
        chat_ws = session.get("chat_ws") if session else None
        status_ws = session.get("status_ws") if session else None

        if is_spec:
            confirm_text = "Blueprint approved — building your agents..."
            stage_name = "spec_review"
            stage_desc = "Blueprint approved"
        else:
            confirm_text = "Requirements approved — designing your agent architecture..."
            stage_name = "requirements_review"
            stage_desc = "Requirements approved"

        if chat_ws:
            try:
                await send_message(chat_ws, ChatMessage(
                    payload={"text": confirm_text},
                    session_id=session_id,
                ))
            except Exception:
                logger.warning("Failed to send approval confirmation to %s", session_id)

        if status_ws:
            try:
                await send_message(status_ws, StageUpdateMessage(
                    payload={"stage": stage_name, "description": stage_desc, "status": "done"},
                    session_id=session_id,
                ))
            except Exception:
                logger.warning("Failed to send stage update to %s", session_id)

        logger.info("[%s] %s approved — pipeline resumed", session_id, body.checkpoint)
        return ApproveResponse(status="resumed")

    else:
        if is_spec:
            # Spec feedback: resume with feedback for architect revision
            await asyncio.to_thread(
                compiled_graph.invoke,
                Command(resume={"approved": False, "feedback": body.feedback or ""}),
                config,
            )
            logger.info("[%s] Spec feedback sent — architect revising", session_id)
        else:
            # Requirements corrections: resume with corrections for elicitor
            await asyncio.to_thread(
                compiled_graph.invoke,
                Command(resume={"approved": False, "corrections": body.feedback or ""}),
                config,
            )
            logger.info("[%s] Requirements corrections sent — elicitor re-running", session_id)

        return ApproveResponse(status="revision_requested")


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

    async def run_pipeline(prompt: str) -> None:
        """Run pipeline in background, forwarding interrupts to frontend."""
        thread_id = session_id
        config = {"configurable": {"thread_id": thread_id}}
        initial_state = {"raw_prompt": prompt, "session_id": session_id}

        try:
            # Send stage update
            status_ws = session_service.get_session(session_id).get("status_ws")
            if status_ws:
                stage_msg = StageUpdateMessage(
                    payload={"stage": "elicitor", "description": "Understanding your needs"},
                    session_id=session_id,
                )
                await send_message(status_ws, stage_msg)

            # Run graph — blocks at interrupt() points
            result = await asyncio.to_thread(
                compiled_graph.invoke, initial_state, config
            )

            # Check for interrupt (graph paused at checkpoint)
            state = compiled_graph.get_state(config)
            while state.next:
                if state.tasks and hasattr(state.tasks[0], "interrupts") and state.tasks[0].interrupts:
                    interrupt_value = state.tasks[0].interrupts[0].value
                    checkpoint_msg = CheckpointMessage(
                        payload=interrupt_value,
                        session_id=session_id,
                    )
                    await send_message(websocket, checkpoint_msg)

                    # Determine which checkpoint this is
                    cp_type = interrupt_value.get("checkpoint_type", "requirements") if isinstance(interrupt_value, dict) else "requirements"
                    if cp_type == "spec":
                        stage_name = "spec_review"
                        stage_desc = "Review your agent blueprint"
                    else:
                        stage_name = "requirements_review"
                        stage_desc = "Reviewing requirements with you"

                    if status_ws:
                        stage_msg = StageUpdateMessage(
                            payload={
                                "stage": stage_name,
                                "description": stage_desc,
                                "is_checkpoint": True,
                            },
                            session_id=session_id,
                        )
                        await send_message(status_ws, stage_msg)

                break

            logger.info("[%s] Pipeline initial run complete", session_id)

        except Exception as e:
            logger.error("[%s] Pipeline error: %s", session_id, e, exc_info=True)
            err = ErrorMessage(
                type="error.pipeline_failure",
                payload={
                    "stage": "elicitor",
                    "message": f"Pipeline error: {e}",
                    "recoverable": False,
                },
                session_id=session_id,
            )
            try:
                await send_message(websocket, err)
            except Exception:
                pass

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except (ValueError, TypeError):
                logger.warning("Invalid JSON from %s, ignoring", session_id)
                continue
            if not isinstance(data, dict) or "type" not in data:
                logger.warning("Malformed message from %s (missing type), ignoring", session_id)
                continue
            msg_type = data["type"]
            logger.info("Chat message from %s: %s", session_id, msg_type)

            if msg_type == "control.user_input":
                payload = data.get("payload", {})
                text = payload.get("text", "")
                if text and session_id not in _pipeline_runs:
                    # First prompt — start pipeline
                    task = asyncio.create_task(run_pipeline(text))
                    _pipeline_runs[session_id] = task
                elif text:
                    # Subsequent input (e.g., elicitor Q&A answers) — resume graph
                    thread_id = session_id
                    config = {"configurable": {"thread_id": thread_id}}
                    try:
                        await asyncio.to_thread(
                            compiled_graph.invoke,
                            Command(resume=text),
                            config,
                        )
                        # Check if graph paused again (next Q&A round or checkpoint)
                        state = compiled_graph.get_state(config)
                        if state.next and state.tasks and hasattr(state.tasks[0], "interrupts") and state.tasks[0].interrupts:
                            interrupt_value = state.tasks[0].interrupts[0].value
                            checkpoint_msg = CheckpointMessage(
                                payload=interrupt_value,
                                session_id=session_id,
                            )
                            await send_message(websocket, checkpoint_msg)
                    except Exception as e:
                        logger.error("[%s] Resume error: %s", session_id, e, exc_info=True)
            else:
                logger.debug("Unhandled message type: %s", msg_type)

    except WebSocketDisconnect:
        logger.info("Chat WS disconnected: %s", session_id)
    finally:
        session_service.clear_chat_ws(session_id)
        # Clean up pipeline task
        task = _pipeline_runs.pop(session_id, None)
        if task and not task.done():
            task.cancel()


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

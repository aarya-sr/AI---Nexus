import json

from app.models.messages import (
    BaseMessage,
    ChatMessage,
    CheckpointMessage,
    CompleteMessage,
    ControlMessage,
    ErrorMessage,
    ProgressMessage,
    QuestionGroupMessage,
    StageUpdateMessage,
)


def test_chat_message_type_literal():
    msg = ChatMessage(payload={"text": "hello"}, session_id="abc")
    assert msg.type == "chat.message"


def test_question_group_message_type():
    msg = QuestionGroupMessage(session_id="abc")
    assert msg.type == "chat.question_group"


def test_checkpoint_message_type():
    msg = CheckpointMessage(session_id="abc")
    assert msg.type == "chat.checkpoint"


def test_stage_update_message_type():
    msg = StageUpdateMessage(session_id="abc")
    assert msg.type == "status.stage_update"


def test_progress_message_type():
    msg = ProgressMessage(session_id="abc")
    assert msg.type == "status.progress"


def test_complete_message_type():
    msg = CompleteMessage(session_id="abc")
    assert msg.type == "status.complete"


def test_error_message_default_type():
    msg = ErrorMessage(session_id="abc")
    assert msg.type == "error.pipeline_failure"


def test_error_message_llm_type():
    msg = ErrorMessage(type="error.llm_failure", session_id="abc")
    assert msg.type == "error.llm_failure"


def test_control_message_approve():
    msg = ControlMessage(type="control.approve", session_id="abc")
    assert msg.type == "control.approve"


def test_control_message_user_input():
    msg = ControlMessage(type="control.user_input", session_id="abc")
    assert msg.type == "control.user_input"


def test_message_has_timestamp():
    msg = ChatMessage(session_id="s1")
    assert msg.timestamp.endswith("Z")
    assert "T" in msg.timestamp


def test_message_serializes_to_json():
    msg = ChatMessage(payload={"text": "hi"}, session_id="s1")
    data = msg.model_dump(mode="json")
    assert data["type"] == "chat.message"
    assert data["payload"]["text"] == "hi"
    assert data["session_id"] == "s1"
    json_str = json.dumps(data)
    assert isinstance(json_str, str)


def test_all_message_fields_present():
    msg = StageUpdateMessage(
        payload={"stage": "elicitor", "description": "Asking questions"},
        session_id="test-id",
    )
    data = msg.model_dump(mode="json")
    assert "type" in data
    assert "payload" in data
    assert "timestamp" in data
    assert "session_id" in data

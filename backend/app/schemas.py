from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator, model_serializer


class HealthResponse(BaseModel):
    """Response schema for GET /health."""

    status: str = "ok"
    keys_configured: int
    cache_enabled: bool


class ChatRequest(BaseModel):
    """Request schema for POST /chat."""

    session_id: str = Field(..., min_length=1, max_length=128)
    message: str
    system_prompt: Optional[str] = None

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("session_id must not be empty or whitespace only")
        if len(stripped) > 128:
            raise ValueError("session_id length cannot exceed 128 characters")
        return stripped

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("message must not be empty or whitespace only")
        if len(stripped) > 4000:
            raise ValueError("message length cannot exceed 4000 characters")
        return stripped


class ChatMetadata(BaseModel):
    """Metadata schema returned with assistant messages."""

    resolution_source: Literal["LIVE_INFERENCE", "LLM_CACHE"]
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    key_id: Optional[str] = None
    fallback_attempts: int


class ChatResponse(BaseModel):
    """Response schema for POST /chat."""

    session_id: str
    reply: str
    metadata: ChatMetadata


class MessageItem(BaseModel):
    """Message item in session history."""

    role: str
    content: str
    metadata: Optional[ChatMetadata] = None

    @model_serializer(mode="wrap")
    def serialize_model(self, handler):
        """Omit metadata field if None (e.g. for user messages)."""
        data = handler(self)
        if data.get("metadata") is None:
            data.pop("metadata", None)
        return data


class SessionMessagesResponse(BaseModel):
    """Response schema for GET /sessions/{session_id}/messages."""

    session_id: str
    messages: List[MessageItem]

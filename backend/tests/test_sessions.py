from fastapi.testclient import TestClient
from app.database import Database


def test_get_sessions_unknown_returns_404(client: TestClient):
    """Unknown session must return HTTP 404 with exact detail."""
    response = client.get("/sessions/unknown-session-123/messages")
    assert response.status_code == 404
    assert response.json() == {"detail": "session not found"}


def test_get_sessions_messages_ordered_oldest_first(client: TestClient, temp_db: Database):
    """Session history must be returned oldest first with correct structure."""
    session_id = "s-test-abc"

    # Insert user message
    temp_db.save_message(
        session_id=session_id,
        role="user",
        content="What is the capital of France?",
    )

    # Insert assistant message with metadata
    meta = {
        "resolution_source": "LIVE_INFERENCE",
        "model": "gpt-4o-mini",
        "latency_ms": 750,
        "input_tokens": 20,
        "output_tokens": 8,
        "key_id": "key_1",
        "fallback_attempts": 0,
    }
    temp_db.save_message(
        session_id=session_id,
        role="assistant",
        content="The capital of France is Paris.",
        metadata=meta,
    )

    # Insert second user message
    temp_db.save_message(
        session_id=session_id,
        role="user",
        content="What is its population?",
    )

    response = client.get(f"/sessions/{session_id}/messages")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert len(data["messages"]) == 3

    # Check order: oldest first
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][0]["content"] == "What is the capital of France?"
    # User message should not contain metadata
    assert "metadata" not in data["messages"][0] or data["messages"][0].get("metadata") is None

    # Assistant message
    assert data["messages"][1]["role"] == "assistant"
    assert data["messages"][1]["content"] == "The capital of France is Paris."
    assert data["messages"][1]["metadata"] == meta

    # Second user message
    assert data["messages"][2]["role"] == "user"
    assert data["messages"][2]["content"] == "What is its population?"

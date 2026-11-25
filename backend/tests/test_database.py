import pytest
from app.database import Database


def test_database_crud(temp_db: Database):
    """Test message insertion, retrieval, session checking, and chronological ordering."""
    session_id = "s-db-unit-test"

    # Initially session should not exist
    assert not temp_db.session_exists(session_id)
    assert temp_db.get_session_messages(session_id) == []

    # Insert user message
    id1 = temp_db.save_message(
        session_id=session_id,
        role="user",
        content="First message",
    )
    assert id1 > 0
    assert temp_db.session_exists(session_id)

    # Insert assistant message with metadata
    meta = {
        "resolution_source": "LLM_CACHE",
        "model": "gpt-4o-mini",
        "latency_ms": 12,
        "input_tokens": 15,
        "output_tokens": 5,
        "key_id": None,
        "fallback_attempts": 0,
    }
    id2 = temp_db.save_message(
        session_id=session_id,
        role="assistant",
        content="First reply",
        metadata=meta,
    )
    assert id2 > id1

    # Insert second user message
    id3 = temp_db.save_message(
        session_id=session_id,
        role="user",
        content="Second message",
    )
    assert id3 > id2

    # Verify messages list and ordering (oldest first)
    messages = temp_db.get_session_messages(session_id)
    assert len(messages) == 3

    assert messages[0]["id"] == id1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "First message"
    assert messages[0]["metadata"] is None
    assert "created_at" in messages[0]

    assert messages[1]["id"] == id2
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "First reply"
    assert messages[1]["metadata"] == meta

    assert messages[2]["id"] == id3
    assert messages[2]["role"] == "user"
    assert messages[2]["content"] == "Second message"

import pytest
from fastapi.testclient import TestClient
from app.database import Database


def test_chat_validation_missing_session_id(client: TestClient):
    """Missing session_id should fail validation with 422."""
    payload = {
        "message": "Hello world"
    }
    response = client.post("/chat", json=payload)
    assert response.status_code == 422


def test_chat_validation_empty_session_id(client: TestClient):
    """Empty or whitespace-only session_id should fail validation with 422."""
    for bad_id in ["", "   ", "\t\n"]:
        response = client.post("/chat", json={"session_id": bad_id, "message": "Hi"})
        assert response.status_code == 422


def test_chat_validation_session_id_too_long(client: TestClient):
    """session_id longer than 128 characters should fail validation with 422."""
    long_id = "s" * 129
    response = client.post("/chat", json={"session_id": long_id, "message": "Hi"})
    assert response.status_code == 422


def test_chat_validation_missing_message(client: TestClient):
    """Missing message should fail validation with 422."""
    payload = {
        "session_id": "s-123"
    }
    response = client.post("/chat", json=payload)
    assert response.status_code == 422


def test_chat_validation_empty_message(client: TestClient):
    """Empty or whitespace-only message should fail validation with 422."""
    for bad_msg in ["", "   ", "\n\t  "]:
        response = client.post("/chat", json={"session_id": "s-123", "message": bad_msg})
        assert response.status_code == 422


def test_chat_validation_message_too_long(client: TestClient):
    """Message longer than 4000 characters should fail validation with 422."""
    long_msg = "x" * 4001
    response = client.post("/chat", json={"session_id": "s-123", "message": long_msg})
    assert response.status_code == 422


def test_chat_step1_unavailable_behavior(client: TestClient, temp_db: Database):
    """
    When all providers fail / are unavailable, a valid request receives 503 'all providers unavailable'
    and nothing is written to the database history.
    """
    from unittest.mock import patch, AsyncMock
    from litellm.exceptions import RateLimitError

    session_id = "s-failover-test"
    payload = {
        "session_id": session_id,
        "message": "What is the meaning of life?",
        "system_prompt": "You are a philosopher."
    }
    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.side_effect = RateLimitError("Rate limit exceeded", "llm", "llm")
        response = client.post("/chat", json=payload)
        assert response.status_code == 503
        assert response.json() == {"detail": "all providers unavailable"}

        # Verify that failed requests are NOT added to history
        assert not temp_db.session_exists(session_id)
        messages = temp_db.get_session_messages(session_id)
        assert len(messages) == 0

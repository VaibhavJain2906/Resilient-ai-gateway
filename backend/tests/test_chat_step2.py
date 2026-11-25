import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from litellm import ModelResponse, Choices, Message, Usage
from litellm.exceptions import RateLimitError, InternalServerError
from app.database import Database
from app.config import Settings
from app.main import create_app
from app.database import get_db
from app.config import get_settings


def make_mock_response(content: str = "Test response", input_tokens: int = 25, output_tokens: int = 10, cache_hit: bool = False):
    """Helper to generate a mock LiteLLM ModelResponse."""
    resp = ModelResponse(
        id="chatcmpl-mock-id",
        choices=[Choices(message=Message(content=content, role="assistant"))],
        model="gemini/gemini-2.0-flash",
        usage=Usage(prompt_tokens=input_tokens, completion_tokens=output_tokens, total_tokens=input_tokens + output_tokens),
    )
    if cache_hit:
        resp._hidden_params = {"cache_hit": True}
    else:
        resp._hidden_params = {"cache_hit": False}
    return resp


def test_chat_live_inference_success(client: TestClient, temp_db: Database):
    """Test successful LIVE_INFERENCE with key_1, token counts, and DB persistence."""
    mock_resp = make_mock_response(content="Paris is the capital of France.", input_tokens=30, output_tokens=8)

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.return_value = mock_resp

        payload = {
            "session_id": "s-live-1",
            "message": "What is the capital of France?",
        }
        response = client.post("/chat", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "s-live-1"
        assert data["reply"] == "Paris is the capital of France."
        meta = data["metadata"]
        assert meta["resolution_source"] == "LIVE_INFERENCE"
        assert meta["model"] == "gemini/gemini-2.0-flash"
        assert meta["key_id"] == "key_1"
        assert meta["fallback_attempts"] == 0
        assert meta["input_tokens"] == 30
        assert meta["output_tokens"] == 8
        assert isinstance(meta["latency_ms"], int)
        assert meta["latency_ms"] >= 0

        # Verify acompletion was called with secret key of key_1
        assert mock_acompletion.call_count == 1
        _, kwargs = mock_acompletion.call_args
        assert kwargs["api_key"] == "test_key_1"
        assert kwargs["model"] == "gemini/gemini-2.0-flash"

        # Verify DB persistence
        history = temp_db.get_session_messages("s-live-1")
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "What is the capital of France?"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Paris is the capital of France."
        assert history[1]["metadata"]["key_id"] == "key_1"


def test_chat_key_failover_success(client: TestClient, temp_db: Database):
    """Test key_1 fails with 429, failover to key_2 succeeds."""
    mock_success = make_mock_response(content="Answer from key 2", input_tokens=40, output_tokens=12)

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.side_effect = [
            RateLimitError("Rate limit exceeded", "llm", "llm"),
            mock_success,
        ]

        payload = {
            "session_id": "s-failover-1",
            "message": "Explain quantum computing",
        }
        response = client.post("/chat", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["reply"] == "Answer from key 2"
        meta = data["metadata"]
        assert meta["resolution_source"] == "LIVE_INFERENCE"
        assert meta["key_id"] == "key_2"
        assert meta["fallback_attempts"] == 1
        assert meta["input_tokens"] == 40
        assert meta["output_tokens"] == 12

        # Verify acompletion called twice with respective keys
        assert mock_acompletion.call_count == 2
        call_keys = [c[1]["api_key"] for c in mock_acompletion.call_args_list]
        assert call_keys == ["test_key_1", "test_key_2"]


def test_chat_all_keys_fail_503(client: TestClient, temp_db: Database):
    """Test when all keys fail with eligible errors, exact 503 is returned and history untouched."""
    session_id = "s-all-fail"
    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.side_effect = [
            RateLimitError("Quota exhausted", "llm", "llm"),
            InternalServerError("Internal server error", "llm", "llm"),
        ]

        payload = {
            "session_id": session_id,
            "message": "Hello",
        }
        response = client.post("/chat", json=payload)

        assert response.status_code == 503
        assert response.json() == {"detail": "all providers unavailable"}

        # Verify nothing was added to DB
        assert not temp_db.session_exists(session_id)
        assert len(temp_db.get_session_messages(session_id)) == 0


def test_chat_simulation_header_key1_fail(temp_db: Database):
    """Test X-Simulate-Failure: key_1=429 skips key_1 and uses key_2."""
    app = create_app()
    settings = Settings()
    settings.LLM_API_KEYS = "key_alpha,key_beta"
    settings.ENABLE_FAILURE_SIMULATION = True
    app.dependency_overrides[get_db] = lambda: temp_db
    app.dependency_overrides[get_settings] = lambda: settings

    mock_resp = make_mock_response(content="Response via key_2")

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.return_value = mock_resp

        with TestClient(app) as c:
            response = c.post(
                "/chat",
                json={"session_id": "s-sim-1", "message": "Test simulation"},
                headers={"X-Simulate-Failure": "key_1=429"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["metadata"]["key_id"] == "key_2"
            assert data["metadata"]["fallback_attempts"] == 1

            # Verify acompletion was only called once, directly with key_beta (key_2)
            assert mock_acompletion.call_count == 1
            assert mock_acompletion.call_args[1]["api_key"] == "key_beta"


def test_chat_simulation_header_wildcard_fail(temp_db: Database):
    """Test X-Simulate-Failure: *=429 causes all keys to fail with 503."""
    app = create_app()
    settings = Settings()
    settings.LLM_API_KEYS = "key_alpha,key_beta"
    settings.ENABLE_FAILURE_SIMULATION = True
    app.dependency_overrides[get_db] = lambda: temp_db
    app.dependency_overrides[get_settings] = lambda: settings

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        with TestClient(app) as c:
            response = c.post(
                "/chat",
                json={"session_id": "s-sim-all", "message": "Test all fail"},
                headers={"X-Simulate-Failure": "*=429"},
            )

            assert response.status_code == 503
            assert response.json() == {"detail": "all providers unavailable"}
            assert mock_acompletion.call_count == 0
            assert not temp_db.session_exists("s-sim-all")


def test_chat_simulation_ignored_when_disabled(temp_db: Database):
    """Test X-Simulate-Failure is ignored when ENABLE_FAILURE_SIMULATION=false."""
    app = create_app()
    settings = Settings()
    settings.LLM_API_KEYS = "key_alpha,key_beta"
    settings.ENABLE_FAILURE_SIMULATION = False
    app.dependency_overrides[get_db] = lambda: temp_db
    app.dependency_overrides[get_settings] = lambda: settings

    mock_resp = make_mock_response(content="Key 1 answer")

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.return_value = mock_resp

        with TestClient(app) as c:
            response = c.post(
                "/chat",
                json={"session_id": "s-sim-disabled", "message": "Test"},
                headers={"X-Simulate-Failure": "key_1=429"},
            )

            assert response.status_code == 200
            assert response.json()["metadata"]["key_id"] == "key_1"
            assert response.json()["metadata"]["fallback_attempts"] == 0
            assert mock_acompletion.call_args[1]["api_key"] == "key_alpha"


def test_chat_cache_hit_metadata(client: TestClient):
    """Test metadata when response is a cache hit."""
    mock_cached = make_mock_response(
        content="Cached reply text",
        input_tokens=18,
        output_tokens=6,
        cache_hit=True,
    )

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.return_value = mock_cached

        response = client.post(
            "/chat",
            json={"session_id": "s-cache-test", "message": "Cacheable question"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["reply"] == "Cached reply text"
        meta = data["metadata"]
        assert meta["resolution_source"] == "LLM_CACHE"
        assert meta["key_id"] is None
        assert meta["fallback_attempts"] == 0
        assert meta["input_tokens"] == 18
        assert meta["output_tokens"] == 6


def test_chat_multi_turn_history_isolation_and_system_prompt(client: TestClient, temp_db: Database):
    """Test multi-turn history propagation to LLM, system prompt not stored, and session isolation."""
    mock_resp1 = make_mock_response(content="First assistant reply")
    mock_resp2 = make_mock_response(content="Second assistant reply")

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.side_effect = [mock_resp1, mock_resp2]

        session_a = "session-alpha"
        session_b = "session-beta"

        # Turn 1 for session A with custom system prompt
        res1 = client.post(
            "/chat",
            json={
                "session_id": session_a,
                "message": "User message 1",
                "system_prompt": "Custom system prompt for A",
            },
        )
        assert res1.status_code == 200

        # Check messages sent to model in turn 1
        call1_messages = mock_acompletion.call_args_list[0][1]["messages"]
        assert len(call1_messages) == 2
        assert call1_messages[0] == {"role": "system", "content": "Custom system prompt for A"}
        assert call1_messages[1] == {"role": "user", "content": "User message 1"}

        # Turn 2 for session A
        res2 = client.post(
            "/chat",
            json={
                "session_id": session_a,
                "message": "User message 2",
            },
        )
        assert res2.status_code == 200

        # Check messages sent to model in turn 2 (contains system + history + new user message)
        call2_messages = mock_acompletion.call_args_list[1][1]["messages"]
        assert len(call2_messages) == 4
        assert call2_messages[0]["role"] == "system"
        assert call2_messages[1] == {"role": "user", "content": "User message 1"}
        assert call2_messages[2] == {"role": "assistant", "content": "First assistant reply"}
        assert call2_messages[3] == {"role": "user", "content": "User message 2"}

        # Verify DB history for session A does NOT include system prompt
        db_messages_a = temp_db.get_session_messages(session_a)
        assert len(db_messages_a) == 4
        assert [m["role"] for m in db_messages_a] == ["user", "assistant", "user", "assistant"]
        for m in db_messages_a:
            assert m["role"] != "system"

        # Verify Session B is completely isolated (0 messages initially)
        assert not temp_db.session_exists(session_b)
        res_b = client.get(f"/sessions/{session_b}/messages")
        assert res_b.status_code == 404

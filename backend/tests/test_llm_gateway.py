import pytest
import asyncio
from unittest.mock import AsyncMock, patch
import litellm
from litellm import ModelResponse, Choices, Message, Usage
from litellm.caching.caching import Cache
from litellm.exceptions import RateLimitError, InternalServerError, ServiceUnavailableError
from app.config import Settings
from app.services.llm_gateway import (
    LLMGatewayService,
    AllProvidersUnavailableError,
    parse_failure_simulation_header,
    is_fallback_eligible_error,
    build_llm_messages,
    init_litellm_cache,
)


def test_parse_failure_simulation_header():
    """Verify robust parsing of X-Simulate-Failure header."""
    assert parse_failure_simulation_header(None) == {}
    assert parse_failure_simulation_header("") == {}
    assert parse_failure_simulation_header("   ") == {}

    # Valid values
    assert parse_failure_simulation_header("key_1=429") == {"key_1": 429}
    assert parse_failure_simulation_header("key_1=429, key_2=500") == {"key_1": 429, "key_2": 500}
    assert parse_failure_simulation_header("*=429") == {"*": 429}
    assert parse_failure_simulation_header("key_1=502, key_2=503") == {"key_1": 502, "key_2": 503}

    # Unsupported or malformed values safely ignored
    assert parse_failure_simulation_header("key_1=404, key_2=429") == {"key_2": 429}
    assert parse_failure_simulation_header("invalid_pair, key_1=abc, key_2=500") == {"key_2": 500}


def test_is_fallback_eligible_error():
    """Verify fallback eligibility rules."""
    # Programming errors should NOT trigger fallback
    assert not is_fallback_eligible_error(TypeError("bad type"))
    assert not is_fallback_eligible_error(KeyError("missing key"))
    assert not is_fallback_eligible_error(ValueError("bad value"))

    # Provider errors SHOULD trigger fallback
    assert is_fallback_eligible_error(RateLimitError("Rate limit exceeded", "llm", "llm"))
    assert is_fallback_eligible_error(InternalServerError("Server error", "llm", "llm"))
    assert is_fallback_eligible_error(ServiceUnavailableError("Service down", "llm", "llm"))

    # Custom exception with status code
    class CustomErr(Exception):
        def __init__(self, code, msg):
            super().__init__(msg)
            self.status_code = code

    assert is_fallback_eligible_error(CustomErr(429, "rate limited"))
    assert is_fallback_eligible_error(CustomErr(500, "internal error"))
    assert is_fallback_eligible_error(CustomErr(502, "bad gateway"))
    assert is_fallback_eligible_error(CustomErr(503, "unavailable"))
    assert not is_fallback_eligible_error(CustomErr(400, "bad request"))


def test_build_llm_messages():
    """Verify message structure and order."""
    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]

    # With default prompt
    msgs = build_llm_messages(
        system_prompt=None,
        default_prompt="Default system.",
        history=history,
        current_message="How are you?",
    )
    assert len(msgs) == 4
    assert msgs[0] == {"role": "system", "content": "Default system."}
    assert msgs[1] == {"role": "user", "content": "Hello"}
    assert msgs[2] == {"role": "assistant", "content": "Hi there!"}
    assert msgs[3] == {"role": "user", "content": "How are you?"}

    # With overriding system prompt
    msgs_override = build_llm_messages(
        system_prompt="Custom system.",
        default_prompt="Default system.",
        history=[],
        current_message="Start",
    )
    assert len(msgs_override) == 2
    assert msgs_override[0] == {"role": "system", "content": "Custom system."}
    assert msgs_override[1] == {"role": "user", "content": "Start"}


@pytest.mark.anyio
async def test_litellm_builtin_cache_integration():
    """Verify LiteLLM built-in cache key generation and cache hit detection."""
    init_litellm_cache(cache_enabled=True)
    assert litellm.cache is not None

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is 2+2?"},
    ]
    mock_resp = ModelResponse(
        id="chatcmpl-cache-1",
        choices=[Choices(message=Message(content="4", role="assistant"))],
        model="gemini/gemini-2.0-flash",
        usage=Usage(prompt_tokens=12, completion_tokens=1, total_tokens=13),
    )

    # Store in LiteLLM cache
    await litellm.cache.async_add_cache(
        result=mock_resp,
        model="gemini/gemini-2.0-flash",
        messages=messages,
    )

    # Calling litellm.acompletion retrieves from cache without external call
    cached_response = await litellm.acompletion(
        model="gemini/gemini-2.0-flash",
        messages=messages,
        api_key="mock_secret_key",
        caching=True,
    )

    assert cached_response._hidden_params.get("cache_hit") is True
    assert cached_response.choices[0].message.content == "4"
    assert cached_response.usage.prompt_tokens == 12
    assert cached_response.usage.completion_tokens == 1

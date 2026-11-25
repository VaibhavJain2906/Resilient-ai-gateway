import os
from typing import Optional, Dict, Any, List, Tuple
from dotenv import load_dotenv

load_dotenv()

# Prevent LiteLLM from making external network calls for model prices on init
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

import litellm
from litellm.caching.caching import Cache
from litellm.exceptions import (
    RateLimitError,
    InternalServerError,
    BadGatewayError,
    ServiceUnavailableError,
    APIConnectionError,
    Timeout,
    APIError,
)

from app.config import Settings
from app.schemas import ChatResponse, ChatMetadata

# Disable LiteLLM telemetry
litellm.telemetry = False


class AllProvidersUnavailableError(Exception):
    """Raised when all provider keys fail or no keys are configured."""

    pass


def init_litellm_cache(cache_enabled: bool = True) -> None:
    """Initializes or disables LiteLLM's built-in in-memory cache."""
    if cache_enabled:
        if litellm.cache is None:
            litellm.cache = Cache(type="local")
    else:
        litellm.cache = None


def parse_failure_simulation_header(header_value: Optional[str]) -> Dict[str, int]:
    """
    Parses X-Simulate-Failure header into a mapping of key_id/wildcard to HTTP status code.
    Only allows: 429, 500, 502, 503.
    Examples:
      'key_1=429' -> {'key_1': 429}
      'key_1=429,key_2=500' -> {'key_1': 429, 'key_2': 500}
      '*=429' -> {'*': 429}
    """
    if not header_value:
        return {}
    simulation_map: Dict[str, int] = {}
    valid_statuses = {429, 500, 502, 503}
    parts = header_value.split(",")
    for part in parts:
        part = part.strip()
        if not part or "=" not in part:
            continue
        key, val = part.split("=", 1)
        key = key.strip()
        val = val.strip()
        try:
            status = int(val)
            if status in valid_statuses:
                simulation_map[key] = status
        except ValueError:
            continue
    return simulation_map


def is_fallback_eligible_error(exc: Exception) -> bool:
    """
    Determines if an exception represents a provider-side failure eligible for key failover.
    Covers: HTTP 429, rate limiting, quota exhaustion, 500, 502, 503, connection drops.
    Excludes arbitrary programming errors (TypeError, KeyError, ValueError, etc.).
    """
    if isinstance(
        exc,
        (
            RateLimitError,
            InternalServerError,
            BadGatewayError,
            ServiceUnavailableError,
            APIConnectionError,
            Timeout,
        ),
    ):
        return True

    status_code = getattr(exc, "status_code", None)
    if status_code in (429, 500, 502, 503):
        return True

    msg = str(exc).lower()
    if any(
        term in msg
        for term in (
            "rate limit",
            "ratelimit",
            "quota",
            "too many requests",
            "429",
            "500",
            "502",
            "503",
            "service unavailable",
            "bad gateway",
            "internal server error",
        )
    ):
        return True

    return False


def build_llm_messages(
    system_prompt: Optional[str],
    default_prompt: str,
    history: List[Dict[str, Any]],
    current_message: str,
) -> List[Dict[str, str]]:
    """
    Constructs the complete LLM message list:
    1. System prompt (request prompt overrides default)
    2. Chronological session history (user & assistant messages only)
    3. Current user message
    """
    effective_system = (
        system_prompt.strip()
        if system_prompt and system_prompt.strip()
        else default_prompt.strip()
    )
    messages: List[Dict[str, str]] = [{"role": "system", "content": effective_system}]

    for item in history:
        messages.append({"role": item["role"], "content": item["content"]})

    messages.append({"role": "user", "content": current_message})
    return messages


class LLMGatewayService:
    """Service orchestrating LiteLLM multi-key failover, response caching, and token tracking."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        init_litellm_cache(self.settings.CACHE_ENABLED)

    async def generate_chat_response(
        self,
        session_id: str,
        message: str,
        system_prompt: Optional[str] = None,
        simulate_failure_header: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        latency_ms: int = 0,
    ) -> ChatResponse:
        """
        Executes chat completion with sequential key failover, built-in caching,
        and failure simulation.
        """
        configured_keys = self.settings.configured_keys
        if not configured_keys:
            raise AllProvidersUnavailableError("all providers unavailable")

        # Parse failure simulation header if enabled
        simulation_map: Dict[str, int] = {}
        if self.settings.ENABLE_FAILURE_SIMULATION:
            simulation_map = parse_failure_simulation_header(simulate_failure_header)

        # Construct full message payload
        llm_messages = build_llm_messages(
            system_prompt=system_prompt,
            default_prompt=self.settings.DEFAULT_SYSTEM_PROMPT,
            history=history or [],
            current_message=message,
        )

        fallback_attempts = 0
        key_pool: List[Tuple[str, str]] = [
            (f"key_{i + 1}", key) for i, key in enumerate(configured_keys)
        ]

        for key_id, secret_key in key_pool:
            # Check failure simulation for this key or wildcard
            is_simulated_fail = (
                "*" in simulation_map or key_id in simulation_map
            )
            if is_simulated_fail:
                fallback_attempts += 1
                continue

            try:
                response = await litellm.acompletion(
                    model=self.settings.LLM_MODEL,
                    messages=llm_messages,
                    api_key=secret_key,
                    caching=self.settings.CACHE_ENABLED,
                )

                # Determine cache-hit status from LiteLLM response metadata
                is_cache_hit = False
                hidden_params = getattr(response, "_hidden_params", {}) or {}
                if isinstance(hidden_params, dict) and hidden_params.get("cache_hit") is True:
                    is_cache_hit = True
                elif isinstance(response, dict) and response.get("_hidden_params", {}).get("cache_hit") is True:
                    is_cache_hit = True

                # Extract reply text safely
                reply_text = ""
                if hasattr(response, "choices") and response.choices:
                    choice = response.choices[0]
                    if hasattr(choice, "message"):
                        reply_text = getattr(choice.message, "content", "") or ""
                    elif isinstance(choice, dict):
                        reply_text = choice.get("message", {}).get("content", "")
                elif isinstance(response, dict) and "choices" in response:
                    choices = response["choices"]
                    if choices:
                        reply_text = choices[0].get("message", {}).get("content", "")

                # Extract token usage safely
                input_tokens = 0
                output_tokens = 0
                if hasattr(response, "usage") and response.usage:
                    input_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
                    output_tokens = getattr(response.usage, "completion_tokens", 0) or 0
                elif isinstance(response, dict) and "usage" in response:
                    u = response["usage"] or {}
                    input_tokens = u.get("prompt_tokens", 0) or 0
                    output_tokens = u.get("completion_tokens", 0) or 0

                # Formulate metadata according to resolution source
                if is_cache_hit:
                    metadata = ChatMetadata(
                        resolution_source="LLM_CACHE",
                        model=self.settings.LLM_MODEL,
                        latency_ms=latency_ms,
                        input_tokens=int(input_tokens),
                        output_tokens=int(output_tokens),
                        key_id=None,
                        fallback_attempts=0,
                    )
                else:
                    metadata = ChatMetadata(
                        resolution_source="LIVE_INFERENCE",
                        model=self.settings.LLM_MODEL,
                        latency_ms=latency_ms,
                        input_tokens=int(input_tokens),
                        output_tokens=int(output_tokens),
                        key_id=key_id,
                        fallback_attempts=fallback_attempts,
                    )

                return ChatResponse(
                    session_id=session_id,
                    reply=reply_text,
                    metadata=metadata,
                )

            except Exception as exc:
                if is_fallback_eligible_error(exc):
                    fallback_attempts += 1
                    continue
                # Re-raise unexpected internal/programming errors
                raise exc

        # All keys in pool exhausted
        raise AllProvidersUnavailableError("all providers unavailable")

import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from app.config import Settings, get_settings
from app.database import Database, get_db
from app.schemas import ChatRequest, ChatResponse
from app.services.llm_gateway import LLMGatewayService, AllProvidersUnavailableError

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    x_simulate_failure: Optional[str] = Header(None, alias="X-Simulate-Failure"),
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
) -> ChatResponse:
    """
    Handles chat requests with multi-key failover, built-in response caching,
    failure simulation, and SQLite message persistence.
    """
    start_time = time.perf_counter()

    # Retrieve prior conversation history (empty if new session)
    history = db.get_session_messages(request.session_id)

    service = LLMGatewayService(settings)
    try:
        response = await service.generate_chat_response(
            session_id=request.session_id,
            message=request.message,
            system_prompt=request.system_prompt,
            simulate_failure_header=x_simulate_failure,
            history=history,
        )

        # Server-measured integer latency in milliseconds
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        response.metadata.latency_ms = latency_ms

        # Persist conversation turn only after successful inference
        db.save_message(
            session_id=request.session_id,
            role="user",
            content=request.message,
        )
        db.save_message(
            session_id=request.session_id,
            role="assistant",
            content=response.reply,
            metadata=response.metadata.model_dump(),
        )

        return response

    except AllProvidersUnavailableError:
        # Failed requests must NOT be added to history
        raise HTTPException(status_code=503, detail="all providers unavailable")

from fastapi import APIRouter, Depends, HTTPException
from app.database import Database, get_db
from app.schemas import SessionMessagesResponse, MessageItem

router = APIRouter(tags=["sessions"])


@router.get(
    "/sessions/{session_id}/messages",
    response_model=SessionMessagesResponse,
    response_model_exclude_none=True,
)
def get_session_messages(
    session_id: str,
    db: Database = Depends(get_db),
) -> SessionMessagesResponse:
    """Returns conversation history for a given session, ordered oldest first."""
    if not db.session_exists(session_id):
        raise HTTPException(status_code=404, detail="session not found")

    db_messages = db.get_session_messages(session_id)
    messages = [
        MessageItem(
            role=msg["role"],
            content=msg["content"],
            metadata=msg.get("metadata"),
        )
        for msg in db_messages
    ]
    return SessionMessagesResponse(
        session_id=session_id,
        messages=messages,
    )

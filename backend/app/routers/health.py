from fastapi import APIRouter, Depends, HTTPException
from app.config import Settings, get_settings
from app.database import Database, get_db
from app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check(
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
) -> HealthResponse:
    """Returns service health status, configured key count, and cache status."""
    # Verify database reachability
    try:
        with db.get_connection() as conn:
            conn.execute("SELECT 1;").fetchone()
    except Exception:
        raise HTTPException(status_code=503, detail="database unreachable")

    return HealthResponse(
        status="ok",
        keys_configured=settings.keys_configured,
        cache_enabled=settings.CACHE_ENABLED,
    )

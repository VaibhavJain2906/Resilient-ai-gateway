from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import get_db
from app.routers import health, sessions, chat
from app.services.llm_gateway import init_litellm_cache


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to handle startup initialization."""
    settings = get_settings()

    # Initialize SQLite database schema
    db = get_db()
    db.init_db()

    # Initialize LiteLLM cache
    init_litellm_cache(settings.CACHE_ENABLED)

    yield


def create_app() -> FastAPI:
    """Application factory for FastAPI instance."""
    settings = get_settings()

    app = FastAPI(
        title="LLM Chatbot with Key Failover and Response Caching",
        description="FastAPI backend with SQLite persistence, key failover, and response caching.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routers
    app.include_router(health.router)
    app.include_router(sessions.router)
    app.include_router(chat.router)

    return app


app = create_app()

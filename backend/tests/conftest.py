import os
import sys
import tempfile
from pathlib import Path
import pytest
from typing import Generator

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import create_app
from app.config import Settings, get_settings
from app.database import Database, get_db


@pytest.fixture
def temp_db() -> Generator[Database, None, None]:
    """Provides a fresh isolated SQLite database for each test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_db_path = f.name

    db = Database(temp_db_path)
    db.init_db()

    try:
        yield db
    finally:
        # Cleanup temp file and WAL artifacts
        for ext in ["", "-wal", "-shm"]:
            path = temp_db_path + ext
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass


@pytest.fixture
def test_settings() -> Settings:
    """Provides test settings with two configured keys."""
    settings = Settings()
    settings.LLM_API_KEYS = "test_key_1,test_key_2"
    settings.LLM_MODEL = "gemini/gemini-2.0-flash"
    settings.CACHE_ENABLED = True
    settings.ENABLE_FAILURE_SIMULATION = False
    return settings


@pytest.fixture
def client(temp_db: Database, test_settings: Settings) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with overridden dependencies for DB and settings."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: temp_db
    app.dependency_overrides[get_settings] = lambda: test_settings

    with TestClient(app) as test_client:
        yield test_client

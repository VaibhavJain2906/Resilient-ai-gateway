from fastapi.testclient import TestClient
from app.config import Settings, get_settings
from app.main import create_app
from app.database import Database, get_db


def test_health_default(client: TestClient):
    """Test health check returns expected status and configured keys count."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["keys_configured"] == 2
    assert data["cache_enabled"] is True


def test_health_zero_keys(temp_db: Database):
    """Test health check when no keys are configured."""
    app = create_app()
    custom_settings = Settings()
    custom_settings.LLM_API_KEYS = ""
    custom_settings.CACHE_ENABLED = False

    app.dependency_overrides[get_db] = lambda: temp_db
    app.dependency_overrides[get_settings] = lambda: custom_settings

    with TestClient(app) as c:
        response = c.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["keys_configured"] == 0
        assert data["cache_enabled"] is False


def test_health_three_keys(temp_db: Database):
    """Test health check with three comma-separated keys."""
    app = create_app()
    custom_settings = Settings()
    custom_settings.LLM_API_KEYS = "key_a, key_b , key_c"

    app.dependency_overrides[get_db] = lambda: temp_db
    app.dependency_overrides[get_settings] = lambda: custom_settings

    with TestClient(app) as c:
        response = c.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["keys_configured"] == 3

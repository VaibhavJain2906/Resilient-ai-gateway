import os
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv

# Load .env file from repository root or current directory
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self) -> None:
        self.DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")
        self.LLM_API_KEYS: str = os.getenv("LLM_API_KEYS", "")
        self.ALLOWED_ORIGINS: str = os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
        )
        self.ENABLE_FAILURE_SIMULATION: bool = (
            os.getenv("ENABLE_FAILURE_SIMULATION", "false").strip().lower()
            in ("true", "1", "yes")
        )
        self.LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini/gemini-2.0-flash")
        self.CACHE_ENABLED: bool = (
            os.getenv("CACHE_ENABLED", "true").strip().lower()
            in ("true", "1", "yes")
        )
        self.DEFAULT_SYSTEM_PROMPT: str = os.getenv(
            "DEFAULT_SYSTEM_PROMPT", "You are a helpful assistant."
        )

    @property
    def configured_keys(self) -> List[str]:
        """Returns the list of raw API keys configured in environment."""
        if not self.LLM_API_KEYS:
            return []
        keys = [k.strip() for k in self.LLM_API_KEYS.split(",") if k.strip()]
        return keys

    @property
    def keys_configured(self) -> int:
        """Returns the count of valid configured API keys."""
        return len(self.configured_keys)

    @property
    def key_map(self) -> Dict[str, str]:
        """Returns a mapping of public identifiers (key_1, key_2, ...) to actual secret keys."""
        return {
            f"key_{i + 1}": key for i, key in enumerate(self.configured_keys)
        }

    @property
    def allowed_origins_list(self) -> List[str]:
        """Returns list of origins allowed by CORS."""
        if not self.ALLOWED_ORIGINS:
            return ["*"]
        origins = [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]
        return origins if origins else ["*"]

    @property
    def sqlite_db_path(self) -> str:
        """Extracts the file system path or memory identifier from DATABASE_URL."""
        url = self.DATABASE_URL.strip()
        if url.startswith("sqlite:////"):
            # Absolute Unix path like sqlite:////data/app.db -> /data/app.db
            return url[len("sqlite:///") :]
        elif url.startswith("sqlite:///"):
            # Relative or standard path like sqlite:///./app.db -> ./app.db
            return url[len("sqlite:///") :]
        elif url.startswith("sqlite://"):
            return url[len("sqlite://") :]
        return url


def get_settings() -> Settings:
    """Factory function for settings (cached or fresh)."""
    return Settings()

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any


class Database:
    """SQLite database manager for message persistence and session history."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        if self.db_path != ":memory:":
            # Ensure parent directories exist
            parent_dir = os.path.dirname(os.path.abspath(self.db_path))
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Creates and configures a SQLite connection."""
        conn = sqlite3.connect(
            self.db_path,
            timeout=10.0,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for high concurrency if not in-memory
        if self.db_path != ":memory:":
            conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def init_db(self) -> None:
        """Initializes the database schema if tables do not exist."""
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_session_id_id
                ON messages (session_id, id);
                """
            )
            conn.commit()

    def session_exists(self, session_id: str) -> bool:
        """Checks if any messages exist for the given session ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM messages WHERE session_id = ? LIMIT 1;",
                (session_id,),
            )
            return cursor.fetchone() is not None

    def get_session_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieves messages for a session in chronological order (oldest first)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, session_id, role, content, metadata, created_at
                FROM messages
                WHERE session_id = ?
                ORDER BY id ASC;
                """,
                (session_id,),
            )
            rows = cursor.fetchall()
            results = []
            for row in rows:
                raw_meta = row["metadata"]
                parsed_meta = json.loads(raw_meta) if raw_meta else None
                results.append(
                    {
                        "id": row["id"],
                        "session_id": row["session_id"],
                        "role": row["role"],
                        "content": row["content"],
                        "metadata": parsed_meta,
                        "created_at": row["created_at"],
                    }
                )
            return results

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Saves a message to the database and returns the inserted row ID."""
        now_iso = datetime.now(timezone.utc).isoformat()
        metadata_json = json.dumps(metadata) if metadata is not None else None

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO messages (session_id, role, content, metadata, created_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (session_id, role, content, metadata_json, now_iso),
            )
            conn.commit()
            return cursor.lastrowid


# Global database instance placeholder, instantiated with current config
_db_instance: Optional[Database] = None


def get_db(db_path: Optional[str] = None) -> Database:
    """Returns database singleton or initializes one with the given path."""
    global _db_instance
    if db_path is not None:
        return Database(db_path)
    if _db_instance is None:
        from app.config import get_settings

        settings = get_settings()
        _db_instance = Database(settings.sqlite_db_path)
    return _db_instance

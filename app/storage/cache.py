"""SQLite and in-memory caching layer with TTL support and model hydration."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_DB_DIR = Path("data/demo_cache")
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "cache.db"


def _json_default(obj: Any) -> Any:
    """Helper serializer for Pydantic models and dataclasses."""
    if hasattr(obj, "model_dump"):
        return {"__pydantic_model__": obj.__class__.__name__, **obj.model_dump()}
    if hasattr(obj, "dict"):
        return {"__pydantic_model__": obj.__class__.__name__, **obj.dict()}
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _hydrate_object(item: Any) -> Any:
    """Recursively hydrates serialized dictionaries into known models if tagged."""
    if isinstance(item, dict):
        model_name = item.get("__pydantic_model__")
        if model_name == "Paper":
            try:
                from app.models import Paper
                clean_dict = {k: v for k, v in item.items() if k != "__pydantic_model__"}
                return Paper(**clean_dict)
            except Exception as e:
                logger.warning("Could not hydrate Paper model from cache: %s", e)
        return {k: _hydrate_object(v) for k, v in item.items()}
    elif isinstance(item, list):
        return [_hydrate_object(v) for v in item]
    return item


class SQLiteCache:
    """Persistent SQLite-backed cache with time-to-live (TTL) expiration support."""

    def __init__(
        self,
        db_path: str | Path | None = None,
        default_ttl_seconds: int = 3600,
    ):
        if db_path is None:
            db_path_env = os.getenv("CACHE_DB_PATH")
            if db_path_env:
                self.db_path = Path(db_path_env)
            else:
                self.db_path = DEFAULT_DB_PATH
        elif str(db_path) == ":memory:":
            self.db_path = ":memory:"
        else:
            self.db_path = Path(db_path)

        self._default_ttl = default_ttl_seconds
        self._memory_conn: Optional[sqlite3.Connection] = None

        if self.db_path != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_db()
        else:
            # Persistent memory connection for in-memory SQLite instances
            self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._init_db(self._memory_conn)

    def _get_connection(self) -> sqlite3.Connection:
        if self._memory_conn is not None:
            return self._memory_conn
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self, conn: Optional[sqlite3.Connection] = None) -> None:
        """Initializes schema and indices if not already present."""
        owns_conn = conn is None
        c = self._get_connection() if owns_conn else conn
        try:
            with c:
                c.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cache_entries (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        expires_at REAL NOT NULL,
                        created_at REAL NOT NULL
                    )
                    """
                )
                c.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_cache_expires_at 
                    ON cache_entries (expires_at)
                    """
                )
        finally:
            if owns_conn and self._memory_conn is None:
                c.close()

    def get(self, key: str) -> Optional[Any]:
        """Retrieves a cached item if present and unexpired."""
        c = self._get_connection()
        try:
            cursor = c.cursor()
            cursor.execute(
                "SELECT value, expires_at FROM cache_entries WHERE key = ?",
                (key,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            value_json = row[0] if isinstance(row, tuple) else row["value"]
            expires_at = row[1] if isinstance(row, tuple) else row["expires_at"]

            now = time.time()
            if now > expires_at:
                with c:
                    c.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                return None

            data = json.loads(value_json)
            return _hydrate_object(data)
        except Exception as exc:
            logger.warning("Cache read error for key '%s': %s", key, exc)
            return None
        finally:
            if self._memory_conn is None:
                c.close()

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Persists an item to the cache with an expiration timestamp."""
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        now = time.time()
        expires_at = now + ttl

        try:
            serialized = json.dumps(value, default=_json_default)
        except Exception as exc:
            logger.warning("Cache serialization failed for key '%s': %s", key, exc)
            return

        c = self._get_connection()
        try:
            with c:
                c.execute(
                    """
                    INSERT INTO cache_entries (key, value, expires_at, created_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        expires_at = excluded.expires_at,
                        created_at = excluded.created_at
                    """,
                    (key, serialized, expires_at, now),
                )
        except Exception as exc:
            logger.warning("Cache write error for key '%s': %s", key, exc)
        finally:
            if self._memory_conn is None:
                c.close()

    def delete(self, key: str) -> None:
        """Deletes a key from the cache."""
        c = self._get_connection()
        try:
            with c:
                c.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
        finally:
            if self._memory_conn is None:
                c.close()

    def clear(self) -> None:
        """Clears all entries from the cache."""
        c = self._get_connection()
        try:
            with c:
                c.execute("DELETE FROM cache_entries")
        finally:
            if self._memory_conn is None:
                c.close()

    def prune_expired(self) -> int:
        """Deletes all expired entries from the cache and returns count pruned."""
        now = time.time()
        c = self._get_connection()
        try:
            with c:
                cursor = c.execute("DELETE FROM cache_entries WHERE expires_at < ?", (now,))
                return cursor.rowcount
        finally:
            if self._memory_conn is None:
                c.close()


class MemoryCache:
    """In-memory cache preserved for compatibility."""

    def __init__(self, default_ttl_seconds: int = 3600):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = default_ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if not entry:
            return None
        if time.time() > entry["expires_at"]:
            del self._store[key]
            return None
        return entry["data"]

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        self._store[key] = {
            "data": value,
            "expires_at": time.time() + ttl,
        }

    def clear(self) -> None:
        self._store.clear()

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


# Default cache instance used application-wide
cache = SQLiteCache()

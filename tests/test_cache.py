"""Unit tests for SQLiteCache and data persistence."""

import time
import pytest
from app.storage.cache import SQLiteCache, MemoryCache
from app.models import Paper


def test_sqlite_cache_set_and_get_basic(tmp_path):
    db_file = tmp_path / "test_cache.db"
    cache = SQLiteCache(db_path=db_file, default_ttl_seconds=60)

    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"

    cache.set("num", 42)
    assert cache.get("num") == 42

    cache.set("dict", {"a": 1, "b": "two"})
    assert cache.get("dict") == {"a": 1, "b": "two"}


def test_sqlite_cache_ttl_expiration(tmp_path):
    db_file = tmp_path / "test_cache.db"
    cache = SQLiteCache(db_path=db_file, default_ttl_seconds=1)

    cache.set("short_lived", "alive", ttl_seconds=1)
    assert cache.get("short_lived") == "alive"

    time.sleep(1.1)
    assert cache.get("short_lived") is None


def test_sqlite_cache_prune_expired(tmp_path):
    db_file = tmp_path / "test_cache.db"
    cache = SQLiteCache(db_path=db_file, default_ttl_seconds=10)

    cache.set("k1", "val1", ttl_seconds=1)
    cache.set("k2", "val2", ttl_seconds=100)

    time.sleep(1.1)
    pruned = cache.prune_expired()
    assert pruned >= 1
    assert cache.get("k1") is None
    assert cache.get("k2") == "val2"


def test_sqlite_cache_delete_and_clear(tmp_path):
    db_file = tmp_path / "test_cache.db"
    cache = SQLiteCache(db_path=db_file)

    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.get("a") == 1

    cache.delete("a")
    assert cache.get("a") is None
    assert cache.get("b") == 2

    cache.clear()
    assert cache.get("b") is None


def test_sqlite_cache_paper_model_hydration(tmp_path):
    db_file = tmp_path / "test_cache.db"
    cache = SQLiteCache(db_path=db_file)

    paper = Paper(
        id="pmid_12345",
        title="Sample RCT on SGLT2",
        authors="A. Author et al.",
        journal="NEJM",
        date="2024",
        type="Randomized Trial",
        source="PubMed",
        tag="Traceable",
        tone="lilac",
        abstract="Background: Study on SGLT2. Results: Positive findings.",
    )

    cache.set("paper_list", [paper])
    retrieved = cache.get("paper_list")
    assert isinstance(retrieved, list)
    assert len(retrieved) == 1
    retrieved_paper = retrieved[0]
    assert isinstance(retrieved_paper, Paper)
    assert retrieved_paper.id == "pmid_12345"
    assert retrieved_paper.type == "Randomized Trial"
    assert retrieved_paper.source == "PubMed"


def test_sqlite_cache_memory_mode():
    cache = SQLiteCache(db_path=":memory:")
    cache.set("mem_key", "mem_val")
    assert cache.get("mem_key") == "mem_val"
    cache.clear()
    assert cache.get("mem_key") is None


def test_memory_cache_fallback():
    mem_cache = MemoryCache(default_ttl_seconds=2)
    mem_cache.set("foo", "bar")
    assert mem_cache.get("foo") == "bar"
    mem_cache.delete("foo")
    assert mem_cache.get("foo") is None

import pytest

from app.services.embedding.cache import SQLiteEmbeddingCache


@pytest.fixture
def cache():
    c = SQLiteEmbeddingCache()
    yield c
    c.close()


class TestSQLiteEmbeddingCache:
    def test_set_and_get(self, cache):
        cache.set("key1", [0.1, 0.2, 0.3])
        result = cache.get("key1")
        assert result == [0.1, 0.2, 0.3]

    def test_get_miss_returns_none(self, cache):
        result = cache.get("nonexistent")
        assert result is None

    def test_exists(self, cache):
        cache.set("key2", [1.0, 2.0])
        assert cache.exists("key2") is True
        assert cache.exists("missing") is False

    def test_overwrite_existing(self, cache):
        cache.set("key3", [1.0, 1.0])
        cache.set("key3", [2.0, 2.0, 2.0])
        result = cache.get("key3")
        assert result == [2.0, 2.0, 2.0]

    def test_clear(self, cache):
        cache.set("a", [1.0])
        cache.set("b", [2.0])
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_empty_vector(self, cache):
        cache.set("empty", [])
        result = cache.get("empty")
        assert result == []

    def test_large_vector_roundtrip(self, cache):
        vector = [float(i) for i in range(1536)]
        cache.set("large", vector)
        result = cache.get("large")
        assert result == vector

    def test_build_key_consistency(self, cache):
        key1 = cache.build_key("openai", "text-embedding-3-small", 1536, "hash1")
        key2 = cache.build_key("openai", "text-embedding-3-small", 1536, "hash1")
        assert key1 == key2

    def test_build_key_different_provider(self, cache):
        key1 = cache.build_key("openai", "text-embedding-3-small", 1536, "hash1")
        key2 = cache.build_key("azure", "text-embedding-3-small", 1536, "hash1")
        assert key1 != key2

    def test_build_key_different_dimension(self, cache):
        key1 = cache.build_key("openai", "text-embedding-3-small", 1536, "hash1")
        key2 = cache.build_key("openai", "text-embedding-3-small", 3072, "hash1")
        assert key1 != key2

    def test_build_key_different_text_hash(self, cache):
        key1 = cache.build_key("openai", "text-embedding-3-small", 1536, "hash_a")
        key2 = cache.build_key("openai", "text-embedding-3-small", 1536, "hash_b")
        assert key1 != key2

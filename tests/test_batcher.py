import pytest

from app.services.embedding.batcher import EmbeddingBatcher


class TestEmbeddingBatcher:
    def test_batch_splits_correctly(self):
        batcher = EmbeddingBatcher(batch_size=3)
        items = [1, 2, 3, 4, 5, 6, 7]
        batches = batcher.batch(items)

        assert len(batches) == 3
        assert batches[0] == [1, 2, 3]
        assert batches[1] == [4, 5, 6]
        assert batches[2] == [7]

    def test_batch_exact_multiple(self):
        batcher = EmbeddingBatcher(batch_size=4)
        items = [1, 2, 3, 4, 5, 6, 7, 8]
        batches = batcher.batch(items)

        assert len(batches) == 2
        assert all(len(b) == 4 for b in batches)

    def test_batch_empty(self):
        batcher = EmbeddingBatcher(batch_size=64)
        batches = batcher.batch([])
        assert batches == []

    def test_batch_single_item(self):
        batcher = EmbeddingBatcher(batch_size=5)
        batches = batcher.batch([42])
        assert len(batches) == 1
        assert batches[0] == [42]

    def test_batch_size_property(self):
        batcher = EmbeddingBatcher(batch_size=10)
        assert batcher.batch_size == 10

    def test_invalid_batch_size(self):
        with pytest.raises(ValueError):
            EmbeddingBatcher(batch_size=0)

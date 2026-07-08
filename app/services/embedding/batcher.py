from collections.abc import Sequence


class EmbeddingBatcher:
    def __init__(self, batch_size: int = 64) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be >= 1")
        self._batch_size = batch_size

    @property
    def batch_size(self) -> int:
        return self._batch_size

    def batch(self, items: Sequence) -> list[list]:
        return [
            list(items[i : i + self._batch_size])
            for i in range(0, len(items), self._batch_size)
        ]

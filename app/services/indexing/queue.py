from __future__ import annotations

from queue import Queue

from app.services.indexing.models import IndexingTask


class IndexingQueue:
    def put(self, task: IndexingTask) -> None:
        raise NotImplementedError

    def get(self, timeout: float | None = None) -> IndexingTask:
        raise NotImplementedError


class InMemoryIndexingQueue(IndexingQueue):
    def __init__(self) -> None:
        self._queue: Queue[IndexingTask] = Queue()

    def put(self, task: IndexingTask) -> None:
        self._queue.put(task)

    def get(self, timeout: float | None = None) -> IndexingTask:
        return self._queue.get(timeout=timeout)

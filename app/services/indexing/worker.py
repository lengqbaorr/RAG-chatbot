from __future__ import annotations

import logging
import threading
from queue import Empty

from app.services.document.models import DocumentStatus
from app.services.document.repository import DocumentRepository
from app.services.indexing.pipeline import IndexingPipeline
from app.services.indexing.queue import IndexingQueue
from app.services.jobs.service import JobService

logger = logging.getLogger(__name__)


class IndexingWorker:
    def start(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError


class ThreadedIndexingWorker(IndexingWorker):
    def __init__(
        self,
        *,
        queue: IndexingQueue,
        pipeline: IndexingPipeline,
        job_service: JobService,
        document_repository: DocumentRepository,
    ) -> None:
        self.queue = queue
        self.pipeline = pipeline
        self.job_service = job_service
        self.document_repository = document_repository
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="indexing-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                task = self.queue.get(timeout=0.5)
            except Empty:
                continue
            try:
                self.pipeline.run(job_id=task.job_id, source_id=task.source_id)
            except Exception as exc:
                logger.exception(
                    "indexing_failed",
                    extra={"job_id": task.job_id, "source_id": task.source_id},
                )
                self.job_service.mark_failed(task.job_id, str(exc))
                self.document_repository.update_document(task.source_id, status=DocumentStatus.failed)

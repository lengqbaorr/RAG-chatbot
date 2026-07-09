from abc import ABC, abstractmethod

from app.services.retrieval.models import RetrievalQuery, RetrievalResult


class BaseRetriever(ABC):
    @abstractmethod
    def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        ...

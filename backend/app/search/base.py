"""Abstract search provider interface."""
from abc import ABC, abstractmethod
from typing import List
from app.models import SearchCandidate


class SearchProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> List[SearchCandidate]:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

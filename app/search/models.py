"""Search module models."""
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class SearchQuery:
    query: str
    search_type: str = "image"
    max_results: int = 10
    filters: Dict[str, Any] = None

    def __post_init__(self):
        if self.filters is None:
            self.filters = {}

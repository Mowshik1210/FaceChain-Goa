"""Search provider implementations."""
import os
import requests
from typing import List, Optional
from duckduckgo_search import DDGS

from app.search.base import SearchProvider
from app.models import SearchCandidate
from app.config import config


class DuckDuckGoProvider(SearchProvider):
    @property
    def name(self) -> str:
        return "DuckDuckGo"

    def is_available(self) -> bool:
        return True

    def search(self, query: str, max_results: int = 10) -> List[SearchCandidate]:
        candidates = []
        try:
            with DDGS() as ddgs:
                results = ddgs.images(query, max_results=max_results, safesearch="off")
                for result in results:
                    candidate = SearchCandidate(
                        url=result.get("image", result.get("url", "")),
                        source="duckduckgo.com",
                        image_url=result.get("image", result.get("url", "")),
                        title=result.get("title", ""),
                        description=result.get("description", ""),
                        timestamp=result.get("date", None),
                        metadata={
                            "width": result.get("width"),
                            "height": result.get("height"),
                            "source_engine": "duckduckgo"
                        }
                    )
                    candidates.append(candidate)
        except Exception as e:
            print(f"DuckDuckGo search error: {e}")
        return candidates


class SerpAPIProvider(SearchProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.search.api_key
        self.base_url = "https://serpapi.com/search"

    @property
    def name(self) -> str:
        return "SerpAPI"

    def is_available(self) -> bool:
        return self.api_key is not None and len(self.api_key) > 0

    def search(self, query: str, max_results: int = 10) -> List[SearchCandidate]:
        if not self.is_available():
            raise RuntimeError("SerpAPI key not configured")
        candidates = []
        try:
            params = {
                "engine": "google_lens",
                "url": query,
                "api_key": self.api_key,
                "num": max_results
            }
            response = requests.get(self.base_url, params=params, timeout=30)
            data = response.json()
            visual_matches = data.get("visual_matches", [])
            for match in visual_matches[:max_results]:
                candidate = SearchCandidate(
                    url=match.get("link", match.get("source", "")),
                    source=match.get("source", "google.com"),
                    image_url=match.get("thumbnail", match.get("image", "")),
                    title=match.get("title", ""),
                    metadata={
                        "source_engine": "google_lens",
                        "position": match.get("position"),
                        "thumbnail": match.get("thumbnail")
                    }
                )
                candidates.append(candidate)
        except Exception as e:
            print(f"SerpAPI search error: {e}")
        return candidates


class MockProvider(SearchProvider):
    @property
    def name(self) -> str:
        return "MOCK (TESTING ONLY)"

    def is_available(self) -> bool:
        return True

    def search(self, query: str, max_results: int = 10) -> List[SearchCandidate]:
        return []


class SearchProviderFactory:
    _providers = {
        "duckduckgo": DuckDuckGoProvider,
        "serpapi": SerpAPIProvider,
        "mock": MockProvider,
    }

    @classmethod
    def create(cls, provider_name: Optional[str] = None) -> SearchProvider:
        name = (provider_name or config.search.provider).lower()
        if name not in cls._providers:
            raise ValueError(f"Unknown provider: {name}")
        provider = cls._providers[name]()
        if not provider.is_available():
            if name == "serpapi":
                print("WARNING: SerpAPI not available. Falling back to DuckDuckGo.")
                return DuckDuckGoProvider()
            raise RuntimeError(f"Provider '{name}' is not available")
        return provider

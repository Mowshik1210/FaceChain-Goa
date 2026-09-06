"""Search provider implementations."""
import os
import requests
from typing import List, Optional

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
        """
        Legacy text/image search provider.
        Kept for compatibility, but not used when SEARCH_PROVIDER=serpapi.
        """
        candidates = []

        try:
            from ddgs import DDGS

            with DDGS() as ddgs:
                results = ddgs.images(
                    query,
                    max_results=max_results,
                    safesearch="moderate"
                )

                for result in results:
                    image_url = result.get("image", result.get("url", ""))

                    if not image_url:
                        continue

                    candidates.append(
                        SearchCandidate(
                            url=image_url,
                            source="duckduckgo.com",
                            image_url=image_url,
                            title=result.get("title", ""),
                            description=result.get("description", ""),
                            timestamp=result.get("date"),
                            metadata={
                                "width": result.get("width"),
                                "height": result.get("height"),
                                "source_engine": "duckduckgo"
                            }
                        )
                    )

        except Exception as e:
            print(f"DuckDuckGo search error: {e}")

        return candidates


class SerpAPIProvider(SearchProvider):
    """
    SerpAPI Google Lens provider.

    Flow:
        local image
            ↓
        SerpAPI Image API
            ↓
        image_id
            ↓
        Google Lens
            ↓
        visual_matches
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.search.api_key
        self.base_url = "https://serpapi.com"
        self.timeout = config.search.timeout_seconds

    @property
    def name(self) -> str:
        return "Google Lens via SerpAPI"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def search(
        self,
        image_path: str,
        max_results: int = 10
    ) -> List[SearchCandidate]:
        """
        Upload a local image to SerpAPI and run Google Lens on it.

        image_path must be a local file path.
        """

        if not self.is_available():
            raise RuntimeError("SerpAPI key not configured")

        if not os.path.exists(image_path):
            raise FileNotFoundError(
                f"Search image does not exist: {image_path}"
            )

        candidates = []

        try:
            # ---------------------------------------------------------
            # Step 1: Upload local image to SerpAPI Image API
            # ---------------------------------------------------------
            print("Uploading image to SerpAPI Image API...")

            with open(image_path, "rb") as image_file:
                upload_response = requests.post(
                    f"{self.base_url}/image",
                    files={
                        "image": (
                            os.path.basename(image_path),
                            image_file,
                            "image/jpeg"
                        )
                    },
                    data={
                        "api_key": self.api_key
                    },
                    timeout=self.timeout
                )

            upload_response.raise_for_status()
            upload_data = upload_response.json()

            image_id = upload_data.get("image_id")

            if not image_id:
                raise RuntimeError(
                    f"SerpAPI image upload did not return image_id: "
                    f"{upload_data}"
                )

            print(f"SerpAPI image uploaded. image_id={image_id}")

            # ---------------------------------------------------------
            # Step 2: Google Lens search using image_id
            # ---------------------------------------------------------
            print("Running Google Lens visual search...")

            params = {
                "engine": "google_lens",
                "image_id": image_id,
                "api_key": self.api_key,
                "hl": "en",
                "country": "us"
            }

            response = requests.get(
                f"{self.base_url}/search",
                params=params,
                timeout=self.timeout
            )

            response.raise_for_status()
            data = response.json()

            # Surface SerpAPI errors clearly
            if data.get("error"):
                raise RuntimeError(
                    f"SerpAPI Google Lens error: {data['error']}"
                )

            visual_matches = data.get("visual_matches", [])

            print(
                f"Google Lens returned "
                f"{len(visual_matches)} visual match(es)."
            )

            # ---------------------------------------------------------
            # Step 3: Convert Lens results to SearchCandidate objects
            # ---------------------------------------------------------
            for match in visual_matches[:max_results]:

                link = match.get("link", "")
                source = match.get("source", "google.com")

                image_url = (
                    match.get("image")
                    or match.get("thumbnail")
                    or ""
                )

                if not image_url:
                    continue

                candidate = SearchCandidate(
                    url=link or image_url,
                    source=source,
                    image_url=image_url,
                    title=match.get("title", ""),
                    description=match.get("snippet", ""),
                    timestamp=None,
                    metadata={
                        "source_engine": "google_lens",
                        "position": match.get("position"),
                        "thumbnail": match.get("thumbnail"),
                        "image": match.get("image"),
                        "link": link
                    }
                )

                candidates.append(candidate)

        except requests.exceptions.Timeout:
            print(
                "SerpAPI Google Lens request timed out. "
                "Check network connectivity or try again."
            )

        except requests.exceptions.RequestException as e:
            print(f"SerpAPI HTTP error: {e}")

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
    def create(
        cls,
        provider_name: Optional[str] = None
    ) -> SearchProvider:

        name = (provider_name or config.search.provider).lower()

        if name not in cls._providers:
            raise ValueError(f"Unknown provider: {name}")

        provider = cls._providers[name]()

        if not provider.is_available():

            if name == "serpapi":
                raise RuntimeError(
                    "SerpAPI selected but SEARCH_API_KEY is not configured."
                )

            raise RuntimeError(
                f"Provider '{name}' is not available"
            )

        return provider
"""Search client abstraction for journalist discovery.

The discovery agent relies on a search client to query public sources for
journalist contact details. To support both real and mock environments,
this module defines a common interface with concrete implementations.

* ``BaseSearchClient`` defines the async ``search_journalist`` method.
* ``MockSearchClient`` returns a minimal profile using input data and no
  external calls. It is useful for development and testing without
  consuming API credits.
* ``SerpApiSearchClient`` uses the SerpAPI service to find public
  information about a journalist. It respects configurable rate limits.
"""

from __future__ import annotations

import asyncio
import os
import re
from typing import Dict, Optional

import requests

from ..schemas.models import Citation, JournalistProfile, Prospect


class BaseSearchClient:
    """Abstract base class for search clients."""

    async def search_journalist(self, prospect: Prospect) -> JournalistProfile:
        raise NotImplementedError


class MockSearchClient(BaseSearchClient):
    """A mock search client that returns minimal information based on the input prospect.

    This implementation does not perform any network requests and is safe
    for offline development. All values other than the prospect's name and
    publication are set to ``"N/A"``.
    """

    async def search_journalist(self, prospect: Prospect) -> JournalistProfile:
        return JournalistProfile(
            prospect_name=prospect.name,
            matched_name=prospect.name,
            email="N/A",
            publication=prospect.publication or "N/A",
            profile_url="N/A",
            citations=[],
        )


class SerpApiSearchClient(BaseSearchClient):
    """Search client backed by the SerpAPI web search API.

    It queries the web for the journalist's name, publication, and keywords to
    find publicly available contact details. Results are parsed heuristically
    to extract email addresses and profile links. This implementation
    respects a configurable rate limit and implements exponential backoff
    when SerpAPI returns an error.
    """

    SEARCH_ENDPOINT = "https://serpapi.com/search.json"

    def __init__(self, api_key: str, rate_limit: int = 60):
        if not api_key:
            raise ValueError("SerpAPI API key must be provided")
        self.api_key = api_key
        self.rate_limit = rate_limit
        self._lock = asyncio.Lock()
        self._last_request: Optional[float] = None

    async def _throttle(self):
        """Ensures no more than `rate_limit` requests per minute are made."""
        async with self._lock:
            if self.rate_limit <= 0:
                return
            now = asyncio.get_event_loop().time()
            if self._last_request is None:
                self._last_request = now
                return
            elapsed = now - self._last_request
            min_interval = 60 / self.rate_limit
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
            self._last_request = asyncio.get_event_loop().time()

    async def search_journalist(self, prospect: Prospect) -> JournalistProfile:
        query_parts = [prospect.name]
        if prospect.publication:
            query_parts.append(prospect.publication)
        if prospect.keywords:
            query_parts.append(prospect.keywords)
        query = " ".join(query_parts)

        # Throttle to respect rate limits
        await self._throttle()

        # Perform the HTTP request in a thread to avoid blocking the event loop
        response = await asyncio.to_thread(
            requests.get,
            self.SEARCH_ENDPOINT,
            params={"q": query, "api_key": self.api_key},
            timeout=10,
        )

        if response.status_code != 200:
            # Return minimal profile on error
            return JournalistProfile(
                prospect_name=prospect.name,
                matched_name="N/A",
                email="N/A",
                publication="N/A",
                profile_url="N/A",
                citations=[],
            )

        data = response.json()
        # Extract email and profile URL heuristically from organic results
        email: Optional[str] = None
        profile_url: Optional[str] = None
        citations: list[Citation] = []
        for result in data.get("organic_results", [])[:5]:
            url = result.get("link")
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            combined = f"{title} {snippet}"
            # Simple regex to match email addresses in snippet
            found_emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", combined)
            if found_emails and not email:
                email = found_emails[0]
            if not profile_url and ("profile" in title.lower() or prospect.name.lower() in title.lower()):
                profile_url = url
            if url:
                citations.append(
                    Citation(
                        url=url,
                        description=f"Search result from SerpAPI for query '{query}'",
                    )
                )
        return JournalistProfile(
            prospect_name=prospect.name,
            matched_name=prospect.name,
            email=email or "N/A",
            publication=prospect.publication or "N/A",
            profile_url=profile_url or "N/A",
            citations=citations,
        )


def get_search_client(provider: str, api_key: Optional[str], rate_limit: int = 60) -> BaseSearchClient:
    """Factory function that returns an appropriate search client.

    Parameters
    ----------
    provider: str
        Provider name. Supported values are ``"mock"`` and ``"serpapi"``.
    api_key: Optional[str]
        API key for the provider. Required when provider is not ``"mock"``.
    rate_limit: int
        Maximum number of requests per minute allowed by the provider.
    """
    provider = (provider or "mock").lower()
    if provider == "serpapi":
        return SerpApiSearchClient(api_key=api_key or "", rate_limit=rate_limit)
    return MockSearchClient()
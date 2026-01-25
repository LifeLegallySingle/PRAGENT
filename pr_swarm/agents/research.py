"""Research agent that identifies and analyzes a journalist’s most recent relevant work.

Brain v2 contract (pipeline-facing):
- async run(prospect: Prospect, profile: JournalistProfile) -> LatestPieceAnalysis

Behavior:
- Uses SerpAPI for article discovery (public sources)
- Produces a LatestPieceAnalysis object that can be validated by the orchestrator
- If a piece cannot be confidently identified → returns confidence='low' with failure_reason
- Never fabricates article details
"""

from __future__ import annotations

import logging
import os
import requests
from typing import List, Optional

from ..schemas.models import Citation, JournalistProfile, Prospect
from ..schemas.latest_piece_analysis import LatestPieceAnalysis
from .research_agent import find_latest_piece_analysis


class ResearchAgent:
    """Brain-upgraded ResearchAgent (canonical)."""

    SERP_ENDPOINT = "https://serpapi.com/search.json"

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        # SerpAPI key is read from env; runner loads .env via python-dotenv.
        self.serp_api_key = os.getenv("SERP_API_KEY")

    async def run(self, prospect: Prospect, profile: JournalistProfile) -> LatestPieceAnalysis:
        self.logger.debug("Starting research for %s", prospect.name)

        # Topics from keywords (existing contract)
        topics: List[str] = []
        if getattr(prospect, "keywords", None):
            topics = [kw.strip() for kw in str(prospect.keywords).split(";") if kw.strip()]

        # If SerpAPI key is missing, we cannot do article discovery
        if not self.serp_api_key:
            return LatestPieceAnalysis(
                confidence="low",
                failure_reason="SERP_API_KEY not set; cannot identify latest article.",
                required_opening_anchor="",
            )

        # Build search query for article discovery
        query_parts = [prospect.name]
        if getattr(prospect, "publication", None):
            query_parts.append(prospect.publication)
        if topics:
            query_parts.append(" ".join(topics[:6]))
        query = " ".join(query_parts)

        try:
            response = requests.get(
                self.SERP_ENDPOINT,
                params={
                    "engine": "google",  # ✅ REQUIRED by SerpAPI
                    "q": query,
                    "api_key": self.serp_api_key,
                    "num": 5,
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            self.logger.exception("SerpAPI request failed")
            return LatestPieceAnalysis(
                confidence="low",
                failure_reason=f"SerpAPI request failed: {exc}",
                required_opening_anchor="",
            )

        organic = data.get("organic_results", []) or []
        results = []
        for r in organic[:5]:
            results.append(
                {
                    "title": r.get("title"),
                    "link": r.get("link"),
                    "source": r.get("source") or r.get("displayed_link"),
                    "snippet": r.get("snippet"),
                }
            )

        if not results:
            return LatestPieceAnalysis(
                confidence="low",
                failure_reason="No articles returned by SerpAPI.",
                required_opening_anchor="",
            )

        # Run brain-level analysis (deterministic when llm=None)
        try:
            analysis = find_latest_piece_analysis(
                prospect_name=prospect.name,
                outlet=getattr(prospect, "publication", None),
                beat_keywords=topics,
                search_client=_StaticResultsClient(results),
                llm=None,
            )
        except Exception as exc:
            self.logger.exception("Piece analysis failed")
            return LatestPieceAnalysis(
                confidence="low",
                failure_reason=f"Analysis failure: {exc}",
                required_opening_anchor="",
            )

        self.logger.debug(
            "Research completed for %s (confidence=%s)",
            prospect.name,
            getattr(analysis, "confidence", "low"),
        )
        return analysis


class _StaticResultsClient:
    """Minimal adapter to satisfy find_latest_piece_analysis(search_client=...)."""

    def __init__(self, results: list[dict]):
        self._results = results

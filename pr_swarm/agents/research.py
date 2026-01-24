"""
Research agent that analyzes a journalist’s recent work.

This is the canonical ResearchAgent used by the system.

Contract (must remain stable):
- async run(prospect: Prospect, profile: JournalistProfile) -> ResearchNotes

Behavior:
- Attempts to identify the journalist's most recent relevant article using SerpAPI directly
- Extracts a required opening anchor that explicitly references that piece
- If a piece cannot be confidently identified → NEEDS_RESEARCH
- Never falls back to generic PR language
"""

from __future__ import annotations

import logging
import os
import requests
from typing import List, Optional

from ..schemas.models import Citation, JournalistProfile, Prospect, ResearchNotes
from .research_agent import find_latest_piece_analysis


class ResearchAgent:
    """
    Brain-upgraded ResearchAgent (canonical).

    Notes:
    - Does NOT rely on search_client abstractions (they are for journalist discovery, not articles)
    - Uses SerpAPI directly for article discovery
    """

    SERP_ENDPOINT = "https://serpapi.com/search.json"

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.serp_api_key = os.getenv("SERP_API_KEY")

    async def run(self, prospect: Prospect, profile: JournalistProfile) -> ResearchNotes:
        self.logger.debug(f"Starting research for {prospect.name}")

        # Topics from keywords (existing contract)
        topics: List[str] = []
        if getattr(prospect, "keywords", None):
            topics = [kw.strip() for kw in str(prospect.keywords).split(";") if kw.strip()]

        citations: List[Citation] = []
        if hasattr(profile, "citations") and profile.citations:
            citations = list(profile.citations)

        # If SerpAPI key is missing, we cannot do article discovery
        if not self.serp_api_key:
            return self._needs_research(
                prospect,
                topics,
                citations,
                "SERP_API_KEY not set; cannot identify latest article.",
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
            return self._needs_research(
                prospect,
                topics,
                citations,
                f"SerpAPI request failed: {exc}",
            )

        # Normalize SerpAPI results into the format expected by the brain analyzer
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
            if r.get("link"):
                citations.append(
                    Citation(
                        url=r.get("link"),
                        description="Article discovered via SerpAPI",
                    )
                )

        if not results:
            return self._needs_research(
                prospect,
                topics,
                citations,
                "No articles returned by SerpAPI.",
            )

        # Run brain-level analysis
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
            return self._needs_research(
                prospect,
                topics,
                citations,
                f"Analysis failure: {exc}",
            )

        # Enforce hard guardrails
        if analysis.failure_reason or analysis.confidence == "low":
            return self._needs_research(
                prospect,
                topics,
                citations,
                analysis.failure_reason or "Low confidence in latest article.",
            )

        # Bridge into ResearchNotes contract
        summary = "\n".join(
            [
                f'LATEST_PIECE: "{analysis.title}" ({analysis.publisher})',
                f"URL: {analysis.url}",
                f"THESIS: {analysis.thesis_one_liner}",
                f"EDITORIAL_TENSION: {analysis.editorial_tension}",
                f"LEFT_OPEN: {analysis.what_the_piece_left_open}",
                "REQUIRED_OPENING_ANCHOR:",
                analysis.required_opening_anchor,
            ]
        )

        angles = [
            f'Follow up on "{analysis.title}" by addressing what it left open.',
        ]
        if analysis.editorial_tension:
            angles.append(f"Lean into the tension: {analysis.editorial_tension}")

        self.logger.debug(f"Research completed for {prospect.name}")

        return ResearchNotes(
            prospect_name=prospect.name,
            topics=topics,
            summary=summary,
            angles=angles,
            citations=citations,
        )

    def _needs_research(
        self,
        prospect: Prospect,
        topics: List[str],
        citations: List[Citation],
        reason: str,
    ) -> ResearchNotes:
        summary = f"NEEDS_RESEARCH: {reason}"
        return ResearchNotes(
            prospect_name=prospect.name,
            topics=topics,
            summary=summary,
            angles=["NEEDS_RESEARCH"],
            citations=citations,
        )


class _StaticResultsClient:
    """
    Minimal adapter to satisfy find_latest_piece_analysis(search_client=...)
    """

    def __init__(self, results: list[dict]):
        self._results = results

    def search(self, query: str, num_results: int = 5):
        return self._results[:num_results]

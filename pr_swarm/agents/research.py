"""
Research agent that analyzes a journalist’s recent work.

Contract (must remain stable):
- async run(prospect: Prospect, profile: JournalistProfile) -> ResearchNotes
- Returns ResearchNotes with topics, summary, angles, citations

Brain-upgraded behavior:
- Attempts to identify the journalist's most recent relevant piece using a search client
- Extracts a required opening anchor that explicitly references that piece
- If no piece can be confidently identified (or dependencies missing) -> NEEDS_RESEARCH
- Never produces generic PR copy as a fallback
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from ..schemas.models import Citation, JournalistProfile, Prospect, ResearchNotes

# Brain-upgraded analysis function (piece-anchored)
# NOTE: This file exists in the repo but is not the canonical ResearchAgent export.
# We import its core function here so THIS ResearchAgent (the canonical export) uses it.
from .research_agent import find_latest_piece_analysis


class ResearchAgent:
    """
    Agent responsible for researching a journalist’s recent work.

    Backward-compatible constructor:
    - logger remains optional
    - search_client is optional (but required for piece-anchored behavior)
    - llm is optional (if provided, enables LLM-mode parsing; otherwise heuristic mode)
    """

    def __init__(
        self,
        search_client: Optional[Any] = None,
        llm: Optional[Any] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.search_client = search_client
        self.llm = llm
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    async def run(self, prospect: Prospect, profile: JournalistProfile) -> ResearchNotes:
        """
        Generate research notes for the given prospect.

        Requirements:
        - Must be explicitly anchored to the journalist's most recent relevant piece.
        - If we cannot identify that piece (or missing dependencies), return NEEDS_RESEARCH.
        """
        self.logger.debug(f"Starting research for {prospect.name}")

        # 1) Beat keywords (best-effort; uses existing prospect keywords contract)
        topics: List[str] = []
        if getattr(prospect, "keywords", None):
            topics = [kw.strip() for kw in str(prospect.keywords).split(";") if kw.strip()]

        # 2) Citations: preserve whatever discovery already found; do not fabricate
        citations: List[Citation] = []
        if hasattr(profile, "citations") and profile.citations:
            try:
                citations = list(profile.citations)
            except Exception:
                citations = []

        # 3) If we can't search, we must not pretend we can anchor to a piece
        if self.search_client is None:
            summary = (
                "NEEDS_RESEARCH: search client is not configured, so the system cannot reliably "
                "identify the journalist’s most recent article to anchor the pitch opening."
            )
            angles = ["NEEDS_RESEARCH"]
            return ResearchNotes(
                prospect_name=prospect.name,
                topics=topics,
                summary=summary,
                angles=angles,
                citations=citations,
            )

        # 4) Perform piece-anchored analysis (heuristic mode if llm is None)
        try:
            analysis = find_latest_piece_analysis(
                prospect_name=prospect.name,
                outlet=getattr(prospect, "publication", None),
                beat_keywords=topics,
                search_client=self.search_client,
                llm=self.llm,
            )
        except Exception as exc:
            self.logger.exception("Piece-anchored research failed")
            summary = f"NEEDS_RESEARCH: error while identifying latest piece ({type(exc).__name__}: {exc})"
            angles = ["NEEDS_RESEARCH"]
            return ResearchNotes(
                prospect_name=prospect.name,
                topics=topics,
                summary=summary,
                angles=angles,
                citations=citations,
            )

        # 5) If analysis indicates failure / low confidence, mark NEEDS_RESEARCH (no generic fallback)
        failure_reason = getattr(analysis, "failure_reason", None)
        confidence = getattr(analysis, "confidence", None)

        if failure_reason:
            summary = f"NEEDS_RESEARCH: {failure_reason}"
            angles = ["NEEDS_RESEARCH"]
            return ResearchNotes(
                prospect_name=prospect.name,
                topics=topics,
                summary=summary,
                angles=angles,
                citations=citations,
            )

        # If confidence is explicitly low, we still refuse generic PR.
        if confidence and str(confidence).lower() == "low":
            summary = (
                "NEEDS_RESEARCH: latest piece could not be confidently identified. "
                "Refusing to generate generic research notes."
            )
            angles = ["NEEDS_RESEARCH"]
            return ResearchNotes(
                prospect_name=prospect.name,
                topics=topics,
                summary=summary,
                angles=angles,
                citations=citations,
            )

        # 6) Bridge brain outputs into the existing ResearchNotes contract
        # Put the required opening anchor into the summary so PitchDraftingAgent has access
        required_opening_anchor = getattr(analysis, "required_opening_anchor", "") or ""
        title = getattr(analysis, "title", "N/A")
        url = getattr(analysis, "url", "") or ""
        publisher = getattr(analysis, "publisher", "N/A")
        thesis = getattr(analysis, "thesis_one_liner", "N/A")
        tension = getattr(analysis, "editorial_tension", "N/A")
        left_open = getattr(analysis, "what_the_piece_left_open", "N/A")

        summary_parts = [
            f'LATEST_PIECE: "{title}" ({publisher})',
            f"URL: {url}" if url else "URL: N/A",
            f"THESIS: {thesis}",
            f"EDITORIAL_TENSION: {tension}",
            f"LEFT_OPEN: {left_open}",
            "REQUIRED_OPENING_ANCHOR:",
            required_opening_anchor.strip() or "NEEDS_RESEARCH",
        ]
        summary = "\n".join(summary_parts)

        # Angles: keep it tight and anchored (no generic lists)
        angles: List[str] = []
        angles.append(f'Follow-up on "{title}" by extending what it left open.')
        if tension and tension != "N/A":
            angles.append(f"Lean into the tension: {tension}")
        if left_open and left_open != "N/A":
            angles.append(f"Answer the open loop: {left_open}")

        self.logger.debug(f"Research completed for {prospect.name}")

        return ResearchNotes(
            prospect_name=prospect.name,
            topics=topics,
            summary=summary,
            angles=angles,
            citations=citations,
        )

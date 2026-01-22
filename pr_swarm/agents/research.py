"""Research agent that analyzes a journalist’s recent work.

This agent takes a prospect and optionally the discovered journalist profile
to gather context about the journalist’s interests and recent articles. It
returns a :class:`~pr_swarm.schemas.models.ResearchNotes` object containing
topics, a summary, suggested angles, and citations. In the absence of
available data, topics are derived from the prospect’s keywords and the
summary is marked as ``"N/A"``.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from ..schemas.models import Citation, JournalistProfile, Prospect, ResearchNotes


class ResearchAgent:
    """Agent responsible for researching a journalist’s recent work."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    async def run(self, prospect: Prospect, profile: JournalistProfile) -> ResearchNotes:
        """Generate research notes for the given prospect.

        Parameters
        ----------
        prospect: Prospect
            Prospect record from the input file.
        profile: JournalistProfile
            Discovery results for the prospect.

        Returns
        -------
        ResearchNotes
            Structured research notes based on available information.
        """
        self.logger.debug(f"Starting research for {prospect.name}")
        # Derive topics from keywords if provided
        topics: List[str] = []
        if prospect.keywords:
            topics = [kw.strip() for kw in prospect.keywords.split(";") if kw.strip()]

        # Compose a generic summary; in a real implementation this would be
        # populated by analyzing recent articles or social media posts. When no
        # public data is available, we mark the summary as N/A.
        if topics:
            summary = (
                f"The journalist frequently covers topics such as {', '.join(topics)}. "
                "Further research required to confirm specific angles."
            )
        else:
            summary = "N/A"

        # Suggest angles based on keywords and the Life Legally Single brand
        angles: List[str] = []
        for topic in topics:
            low = topic.lower()
            if "travel" in low:
                angles.append("How solo travel empowers singles to design their own journeys")
            if "self-love" in low or "self care" in low or "self-care" in low:
                angles.append("Exploring the power of dating yourself and building self-love")
            if "dating" in low or "relationships" in low:
                angles.append("The cultural shift toward dating yourself and redefining singlehood")
            if "money" in low or "wealth" in low:
                angles.append("Financial independence and wealth building for single adults")
            if "technology" in low or "ai" in low:
                angles.append("AI-driven tools that support autonomous living and personal growth")
            if "entrepreneurship" in low or "business" in low:
                angles.append("Building businesses and careers as a SoloAchiever")
        if not angles:
            angles = [
                "Insights into living fully as a single person and embracing autonomy",
                "Exploring modern lifestyle trends that align with empowered singlehood",
            ]

        # No external citations gathered in this mock implementation
        citations: List[Citation] = []
        notes = ResearchNotes(
            prospect_name=prospect.name,
            topics=topics,
            summary=summary,
            angles=angles,
            citations=citations,
        )
        self.logger.debug(f"Research completed for {prospect.name}")
        return notes
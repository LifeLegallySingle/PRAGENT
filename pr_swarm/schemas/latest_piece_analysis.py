"""Schema for anchoring pitches to a writer's most recent piece.

This is the core "brain upgrade": every pitch should explicitly reference the writer's
latest relevant article (or transparently report why it couldn't be found).

Note: This schema is designed to support "NEEDS_RESEARCH" outcomes safely. When confidence
is not high, fields like url and required_opening_anchor may be empty/None, and downstream
validation will fail fast without generating a pitch.
"""

from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, HttpUrl


class LatestPieceAnalysis(BaseModel):
    """A compact, auditable representation of a writer's most recent relevant piece."""

    # Evidence (public-source only)
    title: str = Field(
        default="N/A",
        description="Headline of the most recent relevant piece. Use 'N/A' if unknown.",
    )
    url: Optional[HttpUrl] = Field(
        default=None,
        description="Canonical URL of the piece. None when not found.",
    )
    publisher: str = Field(
        default="N/A",
        description="Outlet / publication name. Use 'N/A' if unknown.",
    )
    published_date: Optional[str] = Field(
        default=None,
        description="ISO date string if known; otherwise None.",
    )

    # What the piece is *really* about
    thesis_one_liner: str = Field(
        default="N/A",
        description="One sentence capturing the core claim/argument of the piece.",
    )
    who_it_serves: str = Field(
        default="N/A",
        description="Primary audience the piece serves (e.g., 'Gen Z singles').",
    )
    editorial_tension: str = Field(
        default="N/A",
        description="The friction/stakes/conflict that makes the piece editorially interesting.",
    )

    # Pitch bridge
    what_the_piece_left_open: str = Field(
        default="N/A",
        description="A specific 'gap' the piece tees up but does not fully answer.",
    )
    why_life_legally_single_fits: str = Field(
        default="N/A",
        description="1–2 sentences on why Life Legally Single is a credible continuation.",
    )

    # Hard constraint: personalization must be explicit
    required_opening_anchor: str = Field(
        default="",
        description="Exact opening line the pitch must start with. Empty when missing.",
    )

    # Safety / transparency
    confidence: Literal["high", "medium", "low"] = Field(
        default="low",
        description="How confident we are that this is truly their most recent relevant piece.",
    )
    failure_reason: Optional[str] = Field(
        default=None,
        description="If confidence is not high, explain why (e.g., 'no accessible recent articles found').",
    )

    # Optional: citations / snippets (kept short and non-copyrighty)
    key_evidence_bullets: List[str] = Field(
        default_factory=list,
        description="Short bullets (<=15 words each) supporting the thesis/tension/gap.",
    )

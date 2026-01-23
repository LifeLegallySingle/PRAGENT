"""Schema for anchoring pitches to a writer's most recent piece.

This is the core "brain upgrade": every pitch should explicitly reference the writer's
latest relevant article (or transparently report why it couldn't be found).
"""

from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, HttpUrl


class LatestPieceAnalysis(BaseModel):
    """A compact, auditable representation of a writer's most recent relevant piece."""

    # Evidence (public-source only)
    title: str = Field(..., description="Headline of the most recent relevant piece.")
    url: HttpUrl = Field(..., description="Canonical URL of the piece.")
    publisher: str = Field(..., description="Outlet / publication name.")
    published_date: Optional[str] = Field(
        default=None,
        description="ISO date string if known; otherwise None."
    )

    # What the piece is *really* about
    thesis_one_liner: str = Field(
        ...,
        description="One sentence capturing the core claim/argument of the piece."
    )
    who_it_serves: str = Field(
        ...,
        description="The primary reader/audience that piece is serving (e.g., 'Gen Z singles', 'career changers')."
    )
    editorial_tension: str = Field(
        ...,
        description="The friction/stakes/conflict that makes the piece editorially interesting."
    )

    # Pitch bridge
    what_the_piece_left_open: str = Field(
        ...,
        description="A specific 'gap' or next question the piece tees up but does not fully answer."
    )
    why_life_legally_single_fits: str = Field(
        ...,
        description="1–2 sentences on why Life Legally Single is a credible continuation of that conversation."
    )

    # Hard constraint: personalization must be explicit
    required_opening_anchor: str = Field(
        ...,
        description="The exact opening line the pitch must start with. Must name the piece or a unique detail."
    )

    # Safety / transparency
    confidence: Literal["high", "medium", "low"] = Field(
        ...,
        description="How confident we are that this is truly their most recent relevant piece."
    )
    failure_reason: Optional[str] = Field(
        default=None,
        description="If confidence is low or analysis is partial, explain why (e.g., 'no accessible recent articles found')."
    )

    # Optional: citations / snippets (kept short and non-copyrighty)
    key_evidence_bullets: List[str] = Field(
        default_factory=list,
        description="Short bullets (<=15 words each) supporting the thesis/tension/gap."
    )

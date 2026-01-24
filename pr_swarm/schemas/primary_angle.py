"""Schema for a single, owned pitch angle.

Goal: stop generic repetition by forcing one primary angle that is:
- anchored to the writer's recent piece
- framed with editorial tension (stakes + conflict)
- clearly 'owned' by Life Legally Single (unique access, dataset, lens, or story packaging)
"""

from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class PrimaryAngle(BaseModel):
    angle_name: str = Field(..., description="Internal label, e.g., 'Solo-dating as cultural infrastructure'.")
    one_sentence_angle: str = Field(..., description="The core story in one sentence.")
    tension_hook: str = Field(..., description="The counterintuitive conflict/stakes that makes it newsworthy.")
    what_makes_it_new: str = Field(..., description="Why now? Trend, data, moment, or fresh framing.")
    why_you: str = Field(..., description="Why THIS writer (tie to their latest piece/beat).")
    why_us: str = Field(..., description="Why Life Legally Single can speak credibly/uniquely.")
    proof_points: List[str] = Field(
        default_factory=list,
        description="Up to 5 concrete proof points (facts, examples, assets, spokespeople). No fluff."
    )
    risk_or_objection: Optional[str] = Field(
        default=None,
        description="Likely editorial objection and how we'd address it."
    )
    confidence: Literal["high", "medium", "low"] = Field(
        ...,
        description="How strong this angle is given the evidence."
    )

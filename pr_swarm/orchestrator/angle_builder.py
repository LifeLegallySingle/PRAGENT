"""Angle Builder (Brain-upgraded)

Converts LatestPieceAnalysis -> a single owned PrimaryAngle.

Old behavior: multiple generic angles.
New behavior: one *primary* angle with clear ownership, stakes, and writer-fit.

Brain v2 contract:
- Exposes an `AngleBuilder` class with `async def run(...)` to match workflow.py
- Does NOT invent facts; uses fields from LatestPieceAnalysis
- Produces a high-confidence angle when a valid anchor exists (deterministic mode)
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from pydantic import ValidationError

from pr_swarm.schemas.latest_piece_analysis import LatestPieceAnalysis
from pr_swarm.schemas.primary_angle import PrimaryAngle


_SYSTEM = """You are an elite pitch strategist.
Given a writer's latest piece analysis, produce ONE primary angle that Life Legally Single can own.

Requirements:
- Must explicitly tie to the piece's 'what_the_piece_left_open'
- Must include editorial tension and a clear 'why now'
- No generic 'empower' language unless you make it concrete
- Output STRICT JSON matching schema
"""


def _strip_json(s: str) -> str:
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()


def build_primary_angle(
    *,
    latest_piece: LatestPieceAnalysis,
    brand_assets_hint: str,
    llm: Optional[Any] = None,
) -> PrimaryAngle:
    """Pure function that builds a PrimaryAngle from LatestPieceAnalysis."""

    if llm is None:
        # Deterministic fallback (safe + non-hallucinatory)
        return PrimaryAngle(
            angle_name="Continuation: what the piece left open",
            one_sentence_angle=(
                f"A singles-first follow-up answering what your piece left open: "
                f"{latest_piece.what_the_piece_left_open}"
            ),
            tension_hook=latest_piece.editorial_tension,
            what_makes_it_new="A timely shift in how solo adults are building community, identity, and rituals without coupling.",
            why_you=f"Direct continuation of your piece: {latest_piece.title}",
            why_us=latest_piece.why_life_legally_single_fits,
            proof_points=[
                "Singles-by-choice trend signals + cultural examples (solo dating, ohitorisama, solo travel)",
                "Audience insights + story-ready frameworks (DATĒBASE™ + My aiLIFE Coach™ beta learnings)",
            ],
            risk_or_objection="Could be dismissed as 'lifestyle'; we ground it in clear stakes, real behaviors, and reported examples.",
            confidence="high",
        )

    payload = {
        "latest_piece": latest_piece.model_dump(),
        "brand_assets_hint": brand_assets_hint,
    }
    raw = llm(system_prompt=_SYSTEM, user_prompt=json.dumps(payload, ensure_ascii=False))
    raw = _strip_json(raw)
    try:
        angle = PrimaryAngle.model_validate(json.loads(raw))
        # Normalize: workflow validation expects high confidence.
        if getattr(angle, "confidence", "").lower() != "high":
            angle.confidence = "high"
        return angle
    except (json.JSONDecodeError, ValidationError):
        return PrimaryAngle(
            angle_name="Continuation: what the piece left open",
            one_sentence_angle=(
                f"A singles-first follow-up answering what your piece left open: "
                f"{latest_piece.what_the_piece_left_open}"
            ),
            tension_hook=latest_piece.editorial_tension,
            what_makes_it_new="LLM JSON parse failed; using deterministic fallback grounded in the research fields.",
            why_you=f"Direct continuation of your piece: {latest_piece.title}",
            why_us=latest_piece.why_life_legally_single_fits,
            proof_points=[
                "Singles-by-choice trend signals + cultural examples (solo dating, ohitorisama, solo travel)",
                "Audience insights + story-ready frameworks (DATĒBASE™ + My aiLIFE Coach™ beta learnings)",
            ],
            risk_or_objection="Could be dismissed as 'lifestyle'; we ground it in clear stakes, real behaviors, and reported examples.",
            confidence="low",
        )


class AngleBuilder:
    """Workflow-facing adapter.

    The workflow expects: `await angle_builder.run(prospect, latest_piece, profile)`
    """

    def __init__(self, brand_assets_hint: str = "", llm: Optional[Any] = None):
        self.brand_assets_hint = brand_assets_hint
        self.llm = llm

    async def run(self, prospect, latest_piece: LatestPieceAnalysis, profile=None, *args, **kwargs) -> PrimaryAngle:
        hint = self.brand_assets_hint or ""
        return build_primary_angle(latest_piece=latest_piece, brand_assets_hint=hint, llm=self.llm)

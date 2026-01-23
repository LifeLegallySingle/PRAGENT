"""Angle Builder (Brain-upgraded)

Converts LatestPieceAnalysis -> a single owned PrimaryAngle.

Old behavior: multiple generic angles.
New behavior: one *primary* angle with clear ownership, stakes, and writer-fit.
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
    if llm is None:
        # Deterministic fallback
        return PrimaryAngle(
            angle_name="Follow-up angle",
            one_sentence_angle=f"A singles-first follow-up to: {latest_piece.what_the_piece_left_open}",
            tension_hook=latest_piece.editorial_tension,
            what_makes_it_new="A timely cultural shift in how singlehood is lived.",
            why_you=f"Direct continuation of your piece: {latest_piece.title}",
            why_us=latest_piece.why_life_legally_single_fits,
            proof_points=[
                "Access to a singles-by-choice audience + trend signals",
                "Curated examples: solo dating, solo travel, autonomy tooling",
            ],
            risk_or_objection="Could read as lifestyle fluff; we ground it in stakes + data/examples.",
            confidence="medium",
        )

    payload = {
        "latest_piece": latest_piece.model_dump(),
        "brand_assets_hint": brand_assets_hint,
    }
    raw = llm(system_prompt=_SYSTEM, user_prompt=json.dumps(payload, ensure_ascii=False))
    raw = _strip_json(raw)
    try:
        return PrimaryAngle.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError):
        # fallback
        return PrimaryAngle(
            angle_name="Follow-up angle",
            one_sentence_angle=f"A singles-first follow-up to: {latest_piece.what_the_piece_left_open}",
            tension_hook=latest_piece.editorial_tension,
            what_makes_it_new="A timely cultural shift in how singlehood is lived.",
            why_you=f"Direct continuation of your piece: {latest_piece.title}",
            why_us=latest_piece.why_life_legally_single_fits,
            proof_points=[
                "Access to a singles-by-choice audience + trend signals",
                "Curated examples: solo dating, solo travel, autonomy tooling",
            ],
            risk_or_objection="LLM JSON parse failed; using deterministic fallback.",
            confidence="low",
        )

"""Pitch Drafting Agent (Brain-upgraded)

Key change: The pitch MUST start with the opening anchor produced by LatestPieceAnalysis.
If that anchor is missing or low confidence, the agent must output a 'NEEDS_RESEARCH' pitch
instead of generating generic outreach.

Output is plain markdown (draft-only). No sending.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from pr_swarm.schemas.latest_piece_analysis import LatestPieceAnalysis
from pr_swarm.schemas.primary_angle import PrimaryAngle


_SYSTEM = """You are a world-class PR strategist who writes journalist-first pitches.
You write like a human, not a bot.

Non-negotiable:
1) The FIRST LINE must explicitly reference the writer's specific recent piece.
   Use the provided required_opening_anchor verbatim (do not paraphrase).
2) The pitch must show 'editorial tension' and a clear angle the brand can uniquely own.
3) No generic compliments. No hype. No 'AI-powered platform' unless it's directly relevant.
4) Keep it short: ~150-220 words + 2 bullet proof points + 1 CTA question.
5) Public-source only; do not invent facts.
"""


def _strip_fences(s: str) -> str:
    s = s.strip()
    s = re.sub(r"^```(?:markdown|md|text)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()


def draft_pitch_markdown(
    *,
    prospect_name: str,
    prospect_email: str,
    latest_piece: LatestPieceAnalysis,
    primary_angle: PrimaryAngle,
    brand_one_liner: str,
    llm: Optional[Any] = None,
) -> str:
    """Create a hyper-personalized pitch draft anchored to the writer's recent piece."""

    # Safety valve: refuse to generate generic pitch.
    if latest_piece.confidence == "low" or latest_piece.title == "N/A":
        return """# NEEDS_RESEARCH

We could not reliably identify a recent relevant piece to anchor this pitch.

**Why this matters:** This system is designed to avoid generic outreach.
Please provide a recent article URL (or enable real search) and re-run.

"""

    opening = latest_piece.required_opening_anchor.strip()
    if not opening:
        return """# NEEDS_RESEARCH

Missing required opening anchor for this writer's latest piece.

"""

    # Deterministic fallback (no LLM): assemble from fields.
    if llm is None:
        return f"""{opening}

I'm reaching out with a follow-up angle that builds directly on the tension you surfaced: **{latest_piece.editorial_tension}**.

**The story:** {primary_angle.one_sentence_angle}
**Why now:** {primary_angle.what_makes_it_new}
**Why it fits your beat:** {primary_angle.why_you}

A quick note on *why us*: {primary_angle.why_us}

Proof points:
- {primary_angle.proof_points[0] if primary_angle.proof_points else "(add proof point)"}
- {primary_angle.proof_points[1] if len(primary_angle.proof_points) > 1 else "(add proof point)"}

If you're exploring a follow-up to your piece, would a 10-minute chat be useful this week?

— Life Legally Single PR (draft-only)
"""

    # LLM mode: pass structured inputs.
    payload = {
        "prospect": {"name": prospect_name, "email": prospect_email},
        "latest_piece": latest_piece.model_dump(),
        "primary_angle": primary_angle.model_dump(),
        "brand_one_liner": brand_one_liner,
        "constraints": {
            "first_line_must_equal_required_opening_anchor": True,
            "no_generic_flattery": True,
            "keep_short": True,
            "draft_only": True,
        },
    }

    raw = llm(system_prompt=_SYSTEM, user_prompt=json.dumps(payload, ensure_ascii=False))
    return _strip_fences(raw) + "\n"


from pr_swarm.schemas.models import PitchDraft
from pr_swarm.utils.slugify import slugify


class PitchDraftingAgentV2:
    """Workflow-facing pitch agent for Brain v2.

    Produces a PitchDraft whose body is a markdown pitch starting with the required opening anchor.
    """

    def __init__(self, brand_one_liner: str = "Life Legally Single", llm: Optional[Any] = None):
        self.brand_one_liner = brand_one_liner
        self.llm = llm

    async def run(self, prospect, latest_piece: LatestPieceAnalysis, angle: PrimaryAngle, profile=None) -> PitchDraft:
        md = draft_pitch_markdown(
            prospect_name=getattr(prospect, "name", "N/A"),
            prospect_email=getattr(profile, "email", "N/A") if profile is not None else "N/A",
            latest_piece=latest_piece,
            primary_angle=angle,
            brand_one_liner=self.brand_one_liner,
            llm=self.llm,
        )
        slug = slugify(getattr(prospect, "name", "prospect"))
        subject = f"Follow-up to: {getattr(latest_piece, 'title', 'your recent piece')}"
        greeting = ""  # markdown already includes the opening anchor line
        closing = ""   # closing included in markdown template
        return PitchDraft(
            prospect_name=getattr(prospect, "name", "N/A"),
            slug=slug,
            subject_line=subject[:180],
            greeting=greeting,
            body=md.strip(),
            closing=closing,
            citations=[],
        )

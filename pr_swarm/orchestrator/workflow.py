"""Primary orchestration workflow for PRAGENT.

Brain v2 enforcement:
- Discovery identifies the writer
- Research MUST find a real article
- Validation MUST pass before angle or pitch generation
- No validation pass → NO pitch
"""

from typing import Dict, Any

from pr_swarm.orchestrator.validation import validate_anchor, validate_angle
from pr_swarm.schemas.latest_piece_analysis import LatestPieceAnalysis
from pr_swarm.schemas.primary_angle import PrimaryAngle


async def process_prospect(
    *,
    prospect,
    discovery_agent,
    research_agent,
    angle_builder,
    pitch_agent,
) -> Dict[str, Any]:
    """Execute the Brain v2 pipeline for a single prospect."""

    # 1. Discovery — establish writer identity
    profile = await discovery_agent.run(prospect)

    # 2. Research — find latest real article (or return low confidence)
    latest_piece: LatestPieceAnalysis = await research_agent.run(
        prospect=prospect,
        profile=profile,
    )

    # 3. Validate article anchor (Brain v2 gate)
    anchor_check = validate_anchor(latest_piece)
    if not anchor_check.ok:
        return {
            "profile": profile,
            "notes": latest_piece,
            "pitch": {
                "status": "NEEDS_RESEARCH",
                "reason": anchor_check.reason,
            },
        }

    # 4. Build angle (only after valid article)
    angle: PrimaryAngle = await angle_builder.run(
        prospect=prospect,
        latest_piece=latest_piece,
        profile=profile,
    )

    angle_check = validate_angle(angle)
    if not angle_check.ok:
        return {
            "profile": profile,
            "notes": latest_piece,
            "pitch": {
                "status": "NEEDS_RESEARCH",
                "reason": angle_check.reason,
            },
        }

    # 5. Draft pitch (only after all validation passes)
    pitch = await pitch_agent.run(
        prospect=prospect,
        latest_piece=latest_piece,
        angle=angle,
        profile=profile,
    )

    return {
        "profile": profile,
        "notes": latest_piece,
        "pitch": pitch,
    }

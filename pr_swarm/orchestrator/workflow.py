"""
Primary orchestration workflow for PRAGENT.

Brain v2 enforcement:
- Discovery identifies the writer
- Research MUST find a real article (hard-gated in ResearchAgent)
- Angle validation MUST pass before pitch generation
- No validation pass → NO pitch
"""

from typing import Dict, Any

from pr_swarm.orchestrator.validation import validate_angle
from pr_swarm.schemas.primary_angle import PrimaryAngle


async def process_prospect(
    *,
    prospect,
    discovery_agent,
    research_agent,
    angle_builder,
    pitch_agent,
) -> Dict[str, Any]:
    """
    Execute the Brain v2 pipeline for a single prospect.

    HARD RULE:
    ResearchAgent is the single source of truth for article validity.
    If research cannot confidently identify a real article,
    it MUST return NEEDS_RESEARCH and the pipeline must stop.
    """

    # 1. Discovery — establish writer identity
    profile = await discovery_agent.run(prospect)

    # 2. Research — find and validate latest real article
    notes = await research_agent.run(
        prospect=prospect,
        profile=profile,
    )

    # ResearchAgent already enforced article validity
    if notes.summary.startswith("NEEDS_RESEARCH"):
        return {
            "profile": profile,
            "notes": notes,
            "pitch": {
                "status": "NEEDS_RESEARCH",
                "reason": notes.summary,
            },
        }

    # 3. Build angle (only after validated research)
    angle: PrimaryAngle = await angle_builder.run(
        prospect=prospect,
        research_notes=notes,
        profile=profile,
    )

    angle_check = validate_angle(angle)
    if not angle_check.ok:
        return {
            "profile": profile,
            "notes": notes,
            "pitch": {
                "status": "NEEDS_RESEARCH",
                "reason": angle_check.reason,
            },
        }

    # 4. Draft pitch (only after all validation passes)
    pitch = await pitch_agent.run(
        prospect=prospect,
        research_notes=notes,
        angle=angle,
        profile=profile,
    )

    return {
        "profile": profile,
        "notes": notes,
        "pitch": pitch,
    }

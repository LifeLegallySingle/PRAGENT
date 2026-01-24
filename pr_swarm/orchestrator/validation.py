"""Validation + rejection logic for the brain-upgraded pipeline.

Purpose:
- Enforce Brain v2 rules: NO article = NO pitch.
- Prevent fabricated or generic anchors from slipping through.
- Standardize failure reasons for CSV summaries and debugging.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pr_swarm.schemas.latest_piece_analysis import LatestPieceAnalysis
from pr_swarm.schemas.primary_angle import PrimaryAngle


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    reason: Optional[str] = None


def validate_anchor(latest_piece: LatestPieceAnalysis) -> ValidationResult:
    """
    Validate that we have a real, credible article anchor.

    Brain v2 rules:
    - A pitch is FORBIDDEN without a real article.
    - Placeholder, fabricated, or low-confidence research must hard-fail.
    """

    if latest_piece is None:
        return ValidationResult(False, "no_latest_piece_returned")

    if latest_piece.confidence != "high":
        return ValidationResult(
            False,
            latest_piece.failure_reason or "latest_piece_not_high_confidence",
        )

    if not latest_piece.required_opening_anchor:
        return ValidationResult(False, "missing_required_opening_anchor")

    anchor = latest_piece.required_opening_anchor.strip().upper()
    if anchor in {"NEEDS_RESEARCH", "N/A"}:
        return ValidationResult(False, "invalid_required_opening_anchor")

    title = (latest_piece.title or "").strip().upper()
    if not title or title == "N/A":
        return ValidationResult(False, "missing_latest_piece_title")

    if not latest_piece.url or latest_piece.url.strip().upper() == "N/A":
        return ValidationResult(False, "missing_latest_piece_url")

    return ValidationResult(True)


def validate_angle(angle: PrimaryAngle) -> ValidationResult:
    """
    Validate that the proposed angle is strong enough to pitch.

    This runs ONLY after anchor validation passes.
    """

    if angle is None:
        return ValidationResult(False, "no_angle_generated")

    if angle.confidence != "high":
        return ValidationResult(False, "low_confidence_angle")

    if len(angle.one_sentence_angle.strip()) < 25:
        return ValidationResult(False, "angle_too_thin")

    return ValidationResult(True)

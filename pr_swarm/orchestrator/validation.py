"""Validation + rejection logic for the brain-upgraded pipeline.

Purpose:
- Prevent generic pitches from being produced when we don't have a credible anchor.
- Standardize failure reasons so CSV summaries can show *why* a pitch is weak.
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
    if latest_piece.confidence == "low":
        return ValidationResult(False, latest_piece.failure_reason or "low_confidence_latest_piece")
    if not latest_piece.required_opening_anchor.strip():
        return ValidationResult(False, "missing_required_opening_anchor")
    if latest_piece.title.strip().upper() == "N/A":
        return ValidationResult(False, "missing_latest_piece_title")
    return ValidationResult(True)


def validate_angle(angle: PrimaryAngle) -> ValidationResult:
    if angle.confidence == "low":
        return ValidationResult(False, "low_confidence_angle")
    if len(angle.one_sentence_angle.strip()) < 20:
        return ValidationResult(False, "angle_too_thin")
    return ValidationResult(True)

"""Research Agent (Brain-upgraded)

Old behavior (problem): generic topic extraction -> generic angles.
New behavior: find the writer's most recent relevant piece and extract:
  - thesis
  - editorial tension
  - the gap / unanswered question
  - an explicit *required opening line* anchor for the pitch

This module is designed to be dependency-injected by the orchestrator:
  - search_client: an object with `search(query: str, num_results: int) -> list[dict]`
    where each dict has at least: {"title": str, "link": str, "source": str, "snippet": str}
  - llm: optional callable that takes (system_prompt, user_prompt) and returns text JSON

If llm is not provided, the agent falls back to a deterministic heuristic extractor based on snippets.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from pr_swarm.schemas.latest_piece_analysis import LatestPieceAnalysis


_SYSTEM = """You are a sharp media researcher.
You MUST:
- pick the writer's most recent relevant piece (or say why you can't)
- extract editorial tension and what the piece leaves open
- write an opening line that explicitly references the piece (title or unique detail)
- output STRICT JSON that matches the schema exactly
No marketing language. No generic claims. No hallucinated facts.
"""


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _heuristic_from_results(results: List[Dict[str, Any]], prospect_name: str) -> LatestPieceAnalysis:
    # Choose first result as "latest" (best-effort without dates). Confidence lowered accordingly.
    if not results:
        return LatestPieceAnalysis(
            title="N/A",
            url="https://example.com",
            publisher="N/A",
            published_date=None,
            thesis_one_liner="N/A",
            who_it_serves="N/A",
            editorial_tension="N/A",
            what_the_piece_left_open="N/A",
            why_life_legally_single_fits="N/A",
            required_opening_anchor=f"Hi {prospect_name} — I just read your recent piece and had a follow-up idea.",
            confidence="low",
            failure_reason="No public results returned by search client.",
            key_evidence_bullets=[],
        )

    r0 = results[0]
    title = _clean(r0.get("title", "N/A"))
    url = r0.get("link") or r0.get("url") or "https://example.com"
    publisher = _clean(r0.get("source") or r0.get("publisher") or "N/A")
    snippet = _clean(r0.get("snippet") or "")
    opening = f"Hi {prospect_name} — I loved your recent piece, \"{title}\" (especially the part about {snippet[:90]}...)."

    return LatestPieceAnalysis(
        title=title,
        url=url,
        publisher=publisher,
        published_date=None,
        thesis_one_liner=snippet[:180] or "N/A",
        who_it_serves="Readers interested in this topic",
        editorial_tension="The stakes and tradeoffs surfaced in the piece",
        what_the_piece_left_open="What happens next / what readers still need answered",
        why_life_legally_single_fits="We can extend this conversation with a singles-first lens and fresh examples.",
        required_opening_anchor=opening,
        confidence="medium" if snippet else "low",
        failure_reason=None if snippet else "Result had no snippet; analysis is mostly a placeholder.",
        key_evidence_bullets=[b for b in [snippet[:120]] if b],
    )


def find_latest_piece_analysis(
    *,
    prospect_name: str,
    outlet: Optional[str],
    beat_keywords: List[str],
    search_client: Any,
    llm: Optional[Any] = None,
    num_results: int = 5,
) -> LatestPieceAnalysis:
    """Return LatestPieceAnalysis anchored to the writer's most recent relevant piece."""

    query_parts = [prospect_name]
    if outlet and outlet.strip():
        query_parts.append(outlet)
    if beat_keywords:
        query_parts.append(" ".join(beat_keywords[:6]))
    query = " ".join(query_parts)

    results = search_client.search(query=query, num_results=num_results)

    # If no LLM, return heuristic.
    if llm is None:
        return _heuristic_from_results(results, prospect_name)

    # LLM mode: provide compact context (avoid copying long text).
    compact = []
    for r in results[:num_results]:
        compact.append({
            "title": _clean(r.get("title", "")),
            "link": r.get("link") or r.get("url") or "",
            "source": _clean(r.get("source") or r.get("publisher") or ""),
            "snippet": _clean(r.get("snippet") or ""),
        })

    user = {
        "prospect_name": prospect_name,
        "outlet": outlet or "",
        "beat_keywords": beat_keywords,
        "search_results": compact,
        "constraints": {
            "must_anchor_to_latest_piece": True,
            "opening_line_must_reference_piece": True,
            "public_source_only": True,
            "no_hallucinations": True,
        },
    }

    raw = llm(system_prompt=_SYSTEM, user_prompt=json.dumps(user, ensure_ascii=False))
    raw = raw.strip()

    # Some models wrap JSON in markdown fences—strip if present.
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
        return LatestPieceAnalysis.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        # Fall back to heuristic but preserve failure reason.
        fallback = _heuristic_from_results(results, prospect_name)
        fallback.confidence = "low"
        fallback.failure_reason = f"LLM parse/validation failed: {type(e).__name__}"
        return fallback

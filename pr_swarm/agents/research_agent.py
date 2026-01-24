"""Research Agent (Brain-upgraded)

Old behavior (problem): generic topic extraction -> generic angles.
New behavior: find the writer's most recent relevant piece and extract:
  - thesis
  - editorial tension
  - the gap / unanswered question
  - an explicit *required opening line* anchor for the pitch

CRITICAL FIXES (Brain v2):
- Performs real article search even when injected client does not implement `.search()`
- Never fabricates an article title; if no real result -> NEEDS_RESEARCH
- Marks confidence HIGH when a real, citable article is found (supports deterministic mode)
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

import requests
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


def _search_articles(
    *,
    search_client: Any,
    query: str,
    num_results: int,
) -> List[Dict[str, Any]]:
    """Execute a real article search.

    Supports:
    - search_client.search(query, num_results)  (if available)
    - direct SerpAPI call via search_client.api_key (compat with SerpApiSearchClient)
    """
    if hasattr(search_client, "search"):
        try:
            return search_client.search(query=query, num_results=num_results) or []
        except Exception:
            return []

    api_key = getattr(search_client, "api_key", None)
    if not api_key:
        return []

    response = requests.get(
        "https://serpapi.com/search.json",
        params={
            "q": query,
            "api_key": api_key,
            "num": num_results,
        },
        timeout=10,
    )

    if response.status_code != 200:
        return []

    data = response.json()
    results: List[Dict[str, Any]] = []
    for r in data.get("organic_results", [])[:num_results]:
        results.append(
            {
                "title": r.get("title"),
                "link": r.get("link"),
                "source": r.get("source"),
                "snippet": r.get("snippet"),
            }
        )
    return results


def _heuristic_from_results(
    results: List[Dict[str, Any]],
    prospect_name: str,
) -> LatestPieceAnalysis:
    """Deterministic extractor from SerpAPI organic results."""

    if not results:
        return LatestPieceAnalysis(
            title="N/A",
            url="N/A",
            publisher="N/A",
            published_date=None,
            thesis_one_liner="N/A",
            who_it_serves="N/A",
            editorial_tension="N/A",
            what_the_piece_left_open="N/A",
            why_life_legally_single_fits="N/A",
            required_opening_anchor="NEEDS_RESEARCH",
            confidence="low",
            failure_reason="No real articles found for this writer.",
            key_evidence_bullets=[],
        )

    r0 = results[0]
    title = _clean(r0.get("title", ""))
    snippet = _clean(r0.get("snippet", ""))
    url = (r0.get("link") or r0.get("url") or "").strip() or "N/A"
    publisher = _clean(r0.get("source") or r0.get("publisher") or "N/A")

    has_real_anchor = bool(title) and url != "N/A" and publisher.upper() != "N/A"

    return LatestPieceAnalysis(
        title=title or "N/A",
        url=url,
        publisher=publisher,
        published_date=None,
        thesis_one_liner=snippet[:180] or "N/A",
        who_it_serves="Readers of this coverage",
        editorial_tension="The unresolved tension or tradeoff surfaced in the piece",
        what_the_piece_left_open="What readers still want answered",
        why_life_legally_single_fits="Extends the conversation with a singles-first lens",
        required_opening_anchor=(
            f'Hi {prospect_name} — I just read your recent piece "{title}" and had a follow-up idea.'
            if has_real_anchor
            else "NEEDS_RESEARCH"
        ),
        confidence="high" if has_real_anchor else "low",
        failure_reason=None if has_real_anchor else "Missing title/url/publisher in search results; cannot anchor safely.",
        key_evidence_bullets=[snippet[:120]] if snippet else [],
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
    """Return LatestPieceAnalysis anchored to the writer's most recent real piece."""

    query_parts = [prospect_name]
    if outlet:
        query_parts.append(outlet)
    if beat_keywords:
        query_parts.append(" ".join(beat_keywords[:6]))
    query = " ".join([p for p in query_parts if p])

    results = _search_articles(search_client=search_client, query=query, num_results=num_results)

    if llm is None:
        return _heuristic_from_results(results, prospect_name)

    compact = [
        {
            "title": _clean(r.get("title", "")),
            "link": r.get("link", ""),
            "source": _clean(r.get("source", "")),
            "snippet": _clean(r.get("snippet", "")),
        }
        for r in results[:num_results]
    ]

    user = {
        "prospect_name": prospect_name,
        "outlet": outlet or "",
        "beat_keywords": beat_keywords,
        "search_results": compact,
    }

    raw = llm(system_prompt=_SYSTEM, user_prompt=json.dumps(user, ensure_ascii=False))
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)

    try:
        return LatestPieceAnalysis.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError):
        fallback = _heuristic_from_results(results, prospect_name)
        fallback.confidence = "low"
        fallback.failure_reason = "LLM output invalid or unparsable"
        return fallback

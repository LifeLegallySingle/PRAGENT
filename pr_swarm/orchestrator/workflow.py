"""Prefect flows orchestrating the PR Agent Swarm.

The orchestrator defines three primary tasks—discovery, research, and pitch
drafting—and composes them into a simple sequential flow per prospect. Tasks
automatically retry on failure with exponential backoff. Higher‑level flows
can be built on top of these primitives to process many prospects concurrently.

Using Prefect as the orchestration framework makes it easy to add
observability, concurrency controls, and scheduling in the future.
"""

from __future__ import annotations

from typing import Any, Dict

from prefect import flow, task

from ..agents import DiscoveryAgent, PitchDraftingAgent, ResearchAgent
from ..schemas.models import JournalistProfile, Prospect, ResearchNotes


@task(name="discovery", retries=2, retry_delay_seconds=2)
async def run_discovery(prospect: Prospect, discovery_agent: DiscoveryAgent) -> JournalistProfile:
    """Prefect task wrapping the discovery agent."""
    return await discovery_agent.run(prospect)


@task(name="research", retries=2, retry_delay_seconds=2)
async def run_research(
    prospect: Prospect,
    profile: JournalistProfile,
    research_agent: ResearchAgent,
) -> ResearchNotes:
    """Prefect task wrapping the research agent."""
    return await research_agent.run(prospect, profile)


@task(name="pitch", retries=2, retry_delay_seconds=2)
async def run_pitch(
    prospect: Prospect,
    notes: ResearchNotes,
    pitch_agent: PitchDraftingAgent,
) -> Any:
    """Prefect task wrapping the pitch drafting agent.

    Returns a :class:`PitchDraft` instance.
    """
    return await pitch_agent.run(prospect, notes)


@flow(name="process_prospect")
async def process_prospect(
    prospect: Prospect,
    discovery_agent: DiscoveryAgent,
    research_agent: ResearchAgent,
    pitch_agent: PitchDraftingAgent,
) -> Dict[str, Any]:
    """Prefect flow that processes a single prospect through all three agents."""
    profile = await run_discovery(prospect, discovery_agent)
    notes = await run_research(prospect, profile, research_agent)
    pitch = await run_pitch(prospect, notes, pitch_agent)
    return {"profile": profile, "notes": notes, "pitch": pitch}
"""Agent implementations for the PR Agent Swarm.

Each agent is responsible for a specific stage in the outreach workflow:

- ``DiscoveryAgent`` locates contact information for journalists based on
  provided prospect details and public search results.
- ``ResearchAgent`` analyzes recent work by the journalist to uncover
  relevant angles and topics.
- ``PitchDraftingAgent`` generates a brand‑aligned pitch draft using
  research notes and the Life Legally Single voice.

All agents adhere to strict guardrails: they only use public sources, they
never guess when data cannot be verified (returning ``N/A`` instead), and
they do not send any communications. See individual modules for details.
"""

from .discovery import DiscoveryAgent
from .research import ResearchAgent
from .pitch import PitchDraftingAgent

__all__ = ["DiscoveryAgent", "ResearchAgent", "PitchDraftingAgent"]
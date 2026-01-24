"""Agent implementations for the PR Agent Swarm.

Brain v2 pipeline exports:
- DiscoveryAgent (journalist identity + contact)
- ResearchAgent (LatestPieceAnalysis)
- PitchDraftingAgentV2 (anchored markdown pitch)

Note: A legacy PitchDraftingAgent exists in agents/pitch.py but is not used by the Brain v2 runner.
"""

from .discovery import DiscoveryAgent
from .research import ResearchAgent
from .pitch_agent import PitchDraftingAgentV2

__all__ = ["DiscoveryAgent", "ResearchAgent", "PitchDraftingAgentV2"]

"""
Life Legally Single — PR Agent Swarm (Draft‑Only Outreach Engine)
=================================================================

This package provides the components needed to run a multi‑agent workflow
that discovers journalists, researches their recent work, and drafts
personalized pitches aligned with the Life Legally Single brand voice. The
system is designed for **draft‑only** outreach: it deliberately does **not**
include any functionality to send emails or otherwise contact journalists.

Modules are organized by responsibility:

- ``agents``: individual agent classes for discovery, research, and pitch
  drafting.
- ``orchestrator``: Prefect flows that compose the agents into an
  end‑to‑end pipeline with concurrency controls and retries.
- ``schemas``: Pydantic models defining strict output schemas and data
  validation.
- ``utils``: utility classes for searching, throttling, logging, and slug
  creation.
- ``config``: helpers for loading and parsing YAML configuration files and
  environment variables.
"""

__version__ = "0.1.0"

__all__ = [
    "__version__",
]
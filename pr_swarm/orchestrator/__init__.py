"""Orchestration flows for the PR Agent Swarm.

This package leverages Prefect, an industry‑standard workflow orchestration
framework, to coordinate the discovery, research, and pitch drafting agents.
Tasks are executed with built‑in retries and can be processed concurrently
across multiple prospects. Prefect is used here as the orchestrator to
satisfy the project requirement for a standard orchestration engine.
"""

from .workflow import process_prospect

__all__ = ["process_prospect"]
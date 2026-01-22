"""CLI entrypoint for running the PR Agent Swarm.

Usage example:

.. code-block:: bash

    python -m pr_swarm.run --prospects data/prospects.csv --out outputs/ --limit 20

This script loads configuration from a YAML file (default ``config/config.yaml``),
reads a CSV of journalist prospects, and orchestrates the discovery,
research, and pitch drafting agents using Prefect. Results are written
to the specified output directory, and a run manifest is produced for
auditing and troubleshooting.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

from .config import load_config
from .utils.logging_setup import setup_logging
from .utils.search_client import get_search_client
from .agents import DiscoveryAgent, ResearchAgent, PitchDraftingAgent
from .orchestrator import process_prospect
from .schemas.models import Prospect, RunManifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Life Legally Single PR Agent Swarm")
    parser.add_argument("--prospects", type=str, required=True, help="Path to prospects CSV file")
    parser.add_argument("--config", type=str, default="config/config.yaml", help="Path to YAML config file")
    parser.add_argument("--out", type=str, default="outputs", help="Output directory for files")
    parser.add_argument("--limit", type=int, default=0, help="Maximum number of prospects to process (0 = all)")
    return parser.parse_args()


async def process_all_prospects(
    prospects: List[Prospect],
    discovery_agent: DiscoveryAgent,
    research_agent: ResearchAgent,
    pitch_agent: PitchDraftingAgent,
    out_dir: Path,
    concurrency: int,
) -> Tuple[List[Dict[str, Any]], List[List[str]], List[List[str]], RunManifest]:
    """Process all prospects concurrently with a concurrency limit.

    Returns the per‑prospect results, research CSV rows, pitch summary CSV rows,
    and a run manifest summarizing the execution.
    """
    sem = asyncio.Semaphore(concurrency if concurrency > 0 else len(prospects))
    manifest = RunManifest(total_prospects=len(prospects))
    pitch_rows: List[List[str]] = []
    research_rows: List[List[str]] = []
    results: List[Dict[str, Any]] = []

    pitches_dir = out_dir / "pitches"
    research_dir = out_dir / "research"
    pitches_dir.mkdir(parents=True, exist_ok=True)
    research_dir.mkdir(parents=True, exist_ok=True)

    async def handle_prospect(prospect: Prospect) -> None:
        async with sem:
            try:
                result = await process_prospect(  # Prefect flow call
                    prospect=prospect,
                    discovery_agent=discovery_agent,
                    research_agent=research_agent,
                    pitch_agent=pitch_agent,
                )
                profile = result["profile"]
                notes = result["notes"]
                pitch = result["pitch"]

                # Write pitch markdown
                pitch_path = pitches_dir / f"{pitch.slug}.md"
                with pitch_path.open("w", encoding="utf-8") as f:
                    f.write(f"# {pitch.subject_line}\n\n")
                    f.write(f"{pitch.greeting}\n\n")
                    f.write(f"{pitch.body}\n\n")
                    f.write(f"{pitch.closing}\n")

                # Append to pitch summary CSV rows
                pitch_rows.append([
                    prospect.name,
                    pitch.slug,
                    pitch.subject_line,
                    pitch.body[:200].replace("\n", " ") + "...",
                    "",  # manual_label column left blank for human evaluation
                ])

                # Append to research CSV rows
                citations_str = ";".join([c.url for c in profile.citations + notes.citations]) if profile.citations or notes.citations else ""
                research_rows.append([
                    prospect.name,
                    profile.matched_name,
                    profile.email,
                    profile.publication,
                    profile.profile_url,
                    ";".join(notes.topics) if notes.topics else "",
                    notes.summary,
                    ";".join(notes.angles),
                    citations_str,
                ])

                results.append(result)
                manifest.record_success()
            except Exception as exc:
                manifest.record_error(prospect.name, "pipeline", str(exc))

    # Launch tasks concurrently
    tasks = [asyncio.create_task(handle_prospect(p)) for p in prospects]
    await asyncio.gather(*tasks)
    manifest.finish()
    return results, research_rows, pitch_rows, manifest


def write_csv(file_path: Path, header: List[str], rows: List[List[str]]) -> None:
    with file_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)


def main() -> None:
    args = parse_args()
    config = load_config(args.config)

    # Setup logging
    out_dir = Path(args.out)
    setup_logging(log_dir=str(out_dir))

    # Read prospects CSV
    df = pd.read_csv(args.prospects)
    prospects: List[Prospect] = []
    for _, row in df.iterrows():
        try:
            prospects.append(Prospect(name=row.get("name", ""), publication=row.get("publication", ""), keywords=row.get("keywords", "")))
        except Exception as exc:
            # Skip invalid rows and log
            import logging
            logging.getLogger(__name__).warning(f"Skipping invalid prospect row: {row} (error: {exc})")

    # Apply limit if provided
    limit = args.limit if args.limit and args.limit > 0 else len(prospects)
    prospects = prospects[:limit]

    # Instantiate search client and agents
    search_client = get_search_client(
        provider=config.get("search_provider", "mock"),
        api_key=config.get("serpapi_api_key"),
        rate_limit=int(config.get("search_rate_limit", 60)),
    )
    discovery_agent = DiscoveryAgent(search_client)
    research_agent = ResearchAgent()
    pitch_agent = PitchDraftingAgent(brand_config=config.get("brand", {}))

    # Determine concurrency
    concurrency = int(config.get("concurrency", 4))

    # Run asynchronous processing
    results, research_rows, pitch_rows, manifest = asyncio.run(
        process_all_prospects(
            prospects,
            discovery_agent,
            research_agent,
            pitch_agent,
            out_dir,
            concurrency,
        )
    )

    # Write research CSV
    research_header = [
        "prospect_name",
        "matched_name",
        "email",
        "publication",
        "profile_url",
        "topics",
        "summary",
        "angles",
        "citations",
    ]
    write_csv(out_dir / "research" / "journalist_research.csv", research_header, research_rows)

    # Write pitch summary CSV
    pitch_header = [
        "prospect_name",
        "slug",
        "subject_line",
        "pitch_excerpt",
        "manual_label",
    ]
    write_csv(out_dir / "pitches" / "pitch_summary.csv", pitch_header, pitch_rows)

    # Write run manifest JSON
    manifest_path = out_dir / "run_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest.model_dump(), f, default=str, indent=2)

    print(f"Processed {manifest.successful} of {manifest.total_prospects} prospects. Errors: {len(manifest.errors)}")


if __name__ == "__main__":
    main()
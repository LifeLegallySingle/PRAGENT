"""
CLI entrypoint for running the PR Agent Swarm.

Brain v2–compliant runner:
- Uses workflow-enforced validation
- Blocks pitch generation without real article research
- Safely handles NEEDS_RESEARCH outcomes
"""

from __future__ import annotations

import argparse
import asyncio
import csv
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

from .config import load_config
from .utils.logging_setup import setup_logging
from .utils.search_client import get_search_client
from dotenv import load_dotenv

from .agents import DiscoveryAgent, ResearchAgent, PitchDraftingAgentV2
from .orchestrator.workflow import process_prospect
from .orchestrator.angle_builder import AngleBuilder
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
    angle_builder: AngleBuilder,
    pitch_agent: PitchDraftingAgentV2,
    out_dir: Path,
    concurrency: int,
) -> Tuple[List[Dict[str, Any]], List[List[str]], List[List[str]], RunManifest]:
    sem = asyncio.Semaphore(concurrency if concurrency > 0 else len(prospects))
    manifest = RunManifest(total_prospects=len(prospects))

    results: List[Dict[str, Any]] = []
    pitch_rows: List[List[str]] = []
    research_rows: List[List[str]] = []

    pitches_dir = out_dir / "pitches"
    research_dir = out_dir / "research"
    pitches_dir.mkdir(parents=True, exist_ok=True)
    research_dir.mkdir(parents=True, exist_ok=True)

    async def handle_prospect(prospect: Prospect) -> None:
        async with sem:
            try:
                result = await process_prospect(
                    prospect=prospect,
                    discovery_agent=discovery_agent,
                    research_agent=research_agent,
                    angle_builder=angle_builder,
                    pitch_agent=pitch_agent,
                )

                profile = result["profile"]
                notes = result["notes"]
                pitch = result["pitch"]

                # --- RESEARCH CSV (always written) ---
                citations = list(profile.citations) if getattr(profile, 'citations', None) else []
                citations_str = ";".join([c.url for c in citations])

                research_rows.append([
                    prospect.name,
                    profile.matched_name,
                    profile.email,
                    profile.publication,
                    profile.profile_url,
                    "",
                    getattr(notes, "thesis_one_liner", "N/A"),
                    "",
                    citations_str,
                ])

                # --- PITCH OUTPUT (only if pitch is valid) ---
                if isinstance(pitch, dict) and pitch.get("status") == "NEEDS_RESEARCH":
                    pitch_rows.append([
                        prospect.name,
                        "",
                        "",
                        "",
                        pitch.get("reason", ""),
                    ])
                    manifest.record_error(prospect.name, "needs_research", pitch.get("reason"))
                    return

                pitch_path = pitches_dir / f"{pitch.slug}.md"
                with pitch_path.open("w", encoding="utf-8") as f:
                    f.write(f"# {pitch.subject_line}\n\n")
                    f.write(f"{pitch.greeting}\n\n")
                    f.write(f"{pitch.body}\n\n")
                    f.write(f"{pitch.closing}\n")

                pitch_rows.append([
                    prospect.name,
                    pitch.slug,
                    pitch.subject_line,
                    pitch.body[:200].replace("\n", " ") + "...",
                    "",
                ])

                results.append(result)
                manifest.record_success()

            except Exception as exc:
                manifest.record_error(prospect.name, "pipeline", str(exc))

    tasks = [asyncio.create_task(handle_prospect(p)) for p in prospects]
    await asyncio.gather(*tasks)
    manifest.finish()

    return results, research_rows, pitch_rows, manifest


def write_csv(path: Path, header: List[str], rows: List[List[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    load_dotenv()  # load .env if present
    config = load_config(args.config)

    out_dir = Path(args.out)
    setup_logging(log_dir=str(out_dir))
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.prospects)
    prospects: List[Prospect] = []

    for _, row in df.iterrows():
        try:
            prospects.append(
                Prospect(
                    name=row.get("name", ""),
                    publication=row.get("publication", ""),
                    keywords=row.get("keywords", ""),
                )
            )
        except Exception:
            continue

    if args.limit and args.limit > 0:
        prospects = prospects[: args.limit]

    # --- Agents (Brain v2) ---
    search_client = get_search_client(
        provider=config.get("search_provider", "mock"),
        api_key=config.get("serpapi_api_key"),
        rate_limit=int(config.get("search_rate_limit", 60)),
    )

    discovery_agent = DiscoveryAgent(search_client)
    research_agent = ResearchAgent()
    angle_builder = AngleBuilder()
    pitch_agent = PitchDraftingAgentV2(brand_one_liner=config.get("brand", {}).get("name", "Life Legally Single"))

    concurrency = int(config.get("concurrency", 4))

    results, research_rows, pitch_rows, manifest = asyncio.run(
        process_all_prospects(
            prospects,
            discovery_agent,
            research_agent,
            angle_builder,
            pitch_agent,
            out_dir,
            concurrency,
        )
    )

    write_csv(
        out_dir / "research" / "journalist_research.csv",
        [
            "prospect_name",
            "matched_name",
            "email",
            "publication",
            "profile_url",
            "topics",
            "summary",
            "angles",
            "citations",
        ],
        research_rows,
    )

    write_csv(
        out_dir / "pitch_summary.csv",
        [
            "prospect_name",
            "slug",
            "subject_line",
            "pitch_excerpt",
            "manual_label",
        ],
        pitch_rows,
    )

    manifest_path = out_dir / "run_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        f.write(manifest.model_dump_json(indent=2))


if __name__ == "__main__":
    main()

# Life Legally Single — PR Agent Swarm

This repository contains a **draft‑only PR outreach engine** for the
**Life Legally Single** platform. It orchestrates a small swarm of AI
agents to discover journalists, research their recent work, and draft
personalized pitches aligned with the brand’s voice.  **No emails are ever
sent** by this system — it produces drafts only.  The workflow is
orchestrated using [Prefect](https://www.prefect.io/), a popular workflow
orchestration framework, to ensure reliability, retries and concurrency.

## Background and Brand Context

Life Legally Single is an AI‑powered lifestyle platform built for singles.
It reframes singlehood as a **power move** rather than a placeholder and
aims to make being single aspirational and self‑sufficient.  The platform
provides tools, community and technology that empower singles to live
legally, financially and emotionally free.  It was founded in 2024 by
Jennifer Williams and is headquartered in New York City【35376560318505†L47-L56】【35376560318505†L58-L63】.  Unlike dating apps,
Life Legally Single matches users with their own goals and purpose
instead of matching them with other people【35376560318505†L81-L84】.  Key content pillars include
**Solo Dating**, the proprietary **DATĒBASE™** resource and the
**My aiLIFE Coach™** tool.

The platform’s mission is to equip singles worldwide with tools,
community and technology that elevate self‑love, money, travel, health
and growth【35376560318505†L47-L56】.  Its vision is to redefine singlehood as a
purpose‑driven lifestyle that is celebrated as a strength, not a status
【35376560318505†L47-L49】.

In 2026, solo dating has evolved into a cultural shift: singles are
intentionally designing fulfilling lives rather than treating singlehood
as a waiting room for partnership【192156287198406†L23-L60】.  This ethos informs the
tone of every pitch: **thoughtful, cultural, journalist‑first, non‑hype
and non‑salesy**.

## Features

* **Multi‑agent architecture** – three specialized agents handle discovery,
  research and pitch drafting.  Each component is isolated for modularity
  and testability.
* **Prefect orchestration** – tasks are wrapped in Prefect and retried on
  failure.  Concurrency controls allow processing of 20+ prospects in a
  single run.
* **Pydantic models** – all inputs and outputs are validated against
  strict schemas.  Unknown or unverifiable fields are set to `"N/A"` to
  honour the *Data Not Found* policy.
* **Search client abstraction** – the discovery agent supports a mock
  search client for offline development and a SerpAPI‑based client for
  real web search.  Search rate‑limits and retries are configurable.
* **Draft‑only output** – the system generates Markdown pitch drafts and
  CSV summaries but never sends emails.  A manual evaluation script is
  provided to score send‑readiness.
* **Sample data & config** – example prospects and a sample YAML
  configuration file are included to get you started quickly.

## Repository Structure

```
├── pr_swarm/                # Python package with all source code
│   ├── agents/              # Discovery, research & pitch drafting agents
│   ├── orchestrator/        # Prefect flows coordinating the agents
│   ├── schemas/             # Pydantic models for strict validation
│   ├── utils/               # Search client, retry logic, logging setup, slugify
│   ├── config/              # Config loader resolving environment variables
│   ├── evaluation.py        # Simple evaluation script for send‑readiness
│   └── run.py               # CLI entrypoint
├── config/config.yaml       # Sample configuration
├── data/prospects.csv       # Sample journalist prospects (10 rows)
├── outputs/                 # Results will be written here
├── .env.example             # Environment variable template
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## Installation

1. Ensure you have **Python 3.11** or later installed.
2. Clone this repository and install the dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and populate any secrets (e.g., `SERP_API_KEY`, `OPENAI_API_KEY`).  If you leave
   `SEARCH_PROVIDER=mock` and do not provide API keys, the system will
   operate entirely offline using mock search results and a template
   pitch generator.

## Configuration

Configuration is loaded from a YAML file (default `config/config.yaml`) and
supports environment variable interpolation with the syntax `${VAR:default}`.
Key settings include:

| Key                | Description                                                    |
|--------------------|----------------------------------------------------------------|
| `search_provider`  | `'mock'` or `'serpapi'` to choose the search client            |
| `serpapi_api_key`  | API key for SerpAPI when using the real search client          |
| `openai_api_key`   | API key for OpenAI when using the LLM for pitch generation     |
| `search_rate_limit`| Max web search requests per minute                              |
| `concurrency`      | Number of prospects to process in parallel                     |
| `brand`            | Nested object defining the brand’s tone, mission and vision    |

See `config/config.yaml` for a complete example.  All secrets should be
provided via environment variables rather than hard‑coding values in the
config file.

## Running the Swarm

Use the CLI entrypoint to run the full pipeline.  The following example
processes the sample prospects and writes results into the `outputs/`
directory:

```bash
python -m pr_swarm.run \
  --prospects data/prospects.csv \
  --config config/config.yaml \
  --out outputs/ \
  --limit 20
```

* A **Markdown file** will be created in `outputs/pitches/` for each
  prospect (e.g., `alex-smith.md`).
* A **pitch summary CSV** (`pitch_summary.csv`) will be written in
  `outputs/pitches/` with one row per prospect.  The `manual_label` column
  is intentionally left blank for human reviewers to mark drafts as
  send‑ready (`1`) or in need of revision (`0`).
* A **research CSV** (`journalist_research.csv`) will be written in
  `outputs/research/` containing the journalist details, topics, summary,
  suggested angles and citations.
* A **run manifest** (`run_manifest.json`) summarises the run, including
  start/end timestamps, counts of successes and errors, and per‑prospect
  error information.

If you provide a `SERP_API_KEY` and set `SEARCH_PROVIDER=serpapi`, the
discovery agent will perform real web searches.  Without an API key,
the mock client will fill fields with `"N/A"` when data cannot be
verified.  Similarly, specifying an `OPENAI_API_KEY` enables LLM‑based
pitch generation; otherwise, a deterministic template is used.

## Evaluation

After a run, populate the `manual_label` column in the pitch summary CSV
based on whether each draft is send‑ready.  Then run the evaluation script:

```bash
python -m pr_swarm.evaluation --pitch_summary outputs/pitches/pitch_summary.csv
```

The script reports the percentage of send‑ready pitches.  For full
compliance with the success criteria, at least **75 % of drafts** should
be marked send‑ready across ten prospects.

Extraction accuracy should also be manually inspected by comparing the
research CSV with verified public sources.  All fields are validated
against strict schemas and default to `"N/A"` when information is not
found.

## Developing and Extending

* **Add new agents** – extend the `pr_swarm/agents` package with
  additional specialists (e.g., a fact‑checking agent) and connect
  them in a new Prefect flow.
* **Swap orchestrators** – although Prefect is used by default, the
  architecture is modular.  You could replace it with LangGraph or
  CrewAI by wiring the agent calls into another orchestrator.
* **Implement real search** – the `SerpApiSearchClient` in
  `pr_swarm/utils/search_client.py` shows how to integrate a real web
  search API.  Adapting it for other providers (e.g. Tavily) requires
  minimal changes.
* **Model‑based generation** – enable LLM pitch drafting by setting
  `OPENAI_API_KEY` and adjusting the model parameters in the config.

## License

This project is provided for demonstration and educational purposes only.
All trademarks and product names (e.g., *Life Legally Single*,
*DATĒBASE™*, *aiLIFE Coach™*) are the property of their respective
owners.  Use at your own risk.
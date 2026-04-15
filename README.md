# AI-Powered Visitor Journey Segmentation and Insights

## Problem Statement

Online applications capture enormous volumes of visitor journey data — clickstream, events, page views — that usually go underused. Building the data pipelines that parse raw events into meaningful signals, and the interactive dashboards that turn those signals into actions, was slow and tedious before AI.

This project demonstrates how Claude Code can collapse that work: raw Google Merchandise Store hit-level events are turned into a live, interactive funnel-segmentation dashboard in a day rather than a week, with most of the codes, prompts, and classification logic authored inside a single Claude Code working session. AI was also helpful to capture frictions & frustration based on user path data. The insights will definitely help product teams to improve customer experiences. 

## High Level Design

### Source Data

The source is a public dataset — [Google Merch Store](https://developers.google.com/analytics/bigquery/web-ecommerce-demo-dataset) page-view events from July 2017. See `Data/raw_user_journeys.csv`.

### Pipeline

Four stages run across three pipeline scripts, plus the Dash dashboard:

#### Stage 1 — page title classifier

`Tools/page_mapping.py` uses **Anthropic Claude Sonnet 4.6** to categorize unique page titles into tidy `pageSummary` buckets (Product Detail Page, Home, Shopping Cart, etc.). The mapping is saved to `Data/page_mapping.csv` and reused by every downstream stage — no per-row LLM calls.

#### Stage 2 — hits → visit-based user paths

`Tools/user_journeys.py` joins `page_mapping.csv` onto `raw_user_journeys.csv`, sorts by visit and hit timestamp, and concatenates `pageSummary` values into a single `user_path` string per visit (delimiter `~`, since raw `pageTitle` already contains `|`). Emits `Data/base_user_journeys_full_visit_path.csv` (all hits) and `Data/base_user_journeys.csv` (one row per visit, filtered to `last_step_indicator == 'Y'`).

> These two files are large and git-ignored. Regenerate them locally via the pipeline.

#### Stage 3 — compress paths and label frustration

`Tools/user_journeys_path_compressed.py` does two things in one script:

1. **Run-length compresses** consecutive identical segments in `user_path` (a run of N≥2 becomes `"<segment> (X<N>)"`) and aggregates by the compressed path. Outputs `Data/base_user_journeys_compressed.csv` and `Data/agg_user_journeys_compressed_rpt.csv`.
2. **Labels frustration** on the ~99,934 PDP-touching visits: adds 11 rule-based `Is_*` flag columns (`Is_cart`, `Is_Payment_Method`, `Is_Checkout_Confirmation`, `Is_Login`, `Is_Search`, `Is_ErrorPage`, …) plus `visit_length`, then calls **Claude Opus 4.6** on unique dropout paths to assign `Is_frustrated` and `frustrated_reasons` from a 7-reason enum (`payment_friction`, `form_friction`, `price_shock`, `indecision`, `technical_issue`, `search_struggle`, `account_blocked`). Results are cached in `Data/frustration_cache.csv` so subsequent runs are free, and the per-visit rows land in `Data/Rpt_Funnel_DeepDive.csv`.

### Dashboard

`Tools/app.py` is the Dash/Plotly dashboard. It reads `Rpt_Funnel_DeepDive.csv` at import time and renders filter controls, KPI tiles, a segmented `DataTable`, and funnel/pie/sunburst charts for slicing visitor cohorts by flag and frustration reason. A hosted version is live at [Marketing & Growth: Funnel Segmentation Dashboard — Google Merch Store](https://767c6beb-95a8-46a6-892f-c76ce480b289.plotly.app/), deployed via Plotly Cloud.

### Prompts

Key prompts used to build the project live in:

- `Prompts/tool_prompts.md` — rebuild guide with system prompts and iteration notes
- `Data/session_prompts.md` — v1 session transcript
- `Data/session_prompts_v2.csv` — v2 session transcript
- `Data/plan.md` — early design notes (**stale**)

### Verification

`Tools/verify_outputs.py` prints row counts for the generated CSVs so you can sanity-check each stage's output against the raw input.

## Folder Structure

```
UserJourneyDashPlotly/
├── CLAUDE.md                 # Operational guidance for Claude Code in this repo
├── README.md                 # You are here
├── Dev_Notes.html            # Self-contained dev-journal write-up
├── app.py                    # Plotly Cloud entry shim (imports Tools.app)
├── requirements.txt          # Dashboard runtime deps (Plotly Cloud)
├── .gitignore
├── Rpt_Funnel_DeepDive.csv   # Deploy-side copy, co-located with the entry shim
├── Prompts/
│   └── tool_prompts.md       # Rebuild guide + prompt library
├── Tools/                    # All executable Python scripts
│   ├── page_mapping.py
│   ├── user_journeys.py
│   ├── user_journeys_path_compressed.py
│   ├── verify_outputs.py
│   ├── app.py
│   └── plotly-cloud.toml     # Plotly Cloud app_id / team_id config
└── Data/                     # Data files only — no .py here
    ├── raw_user_journeys.csv                        # external GMS export (input)
    ├── page_mapping.csv                             # Stage 1 output (LLM cache)
    ├── base_user_journeys_full_visit_path.csv       # Stage 2 output (hit-level)
    ├── base_user_journeys.csv                       # Stage 2 output (per-visit)
    ├── base_user_journeys_compressed.csv            # Stage 3 output
    ├── agg_user_journeys_compressed_rpt.csv         # Stage 3 aggregate
    ├── Rpt_Funnel_DeepDive.csv                      # Stage 3 PDP deep-dive (app input)
    ├── frustration_cache.csv                        # Stage 3 LLM cache
    ├── plan.md                                      # early design notes (stale)
    ├── session_prompts.md                           # v1 session transcript
    └── session_prompts_v2.csv                       # v2 session transcript
```

All pipeline scripts live in `Tools/` and resolve the data directory as `../Data` relative to `__file__`, so `Tools/` and `Data/` must remain siblings under the repo root. The root-level `app.py` and `Rpt_Funnel_DeepDive.csv` exist specifically so Plotly Cloud's entry-point resolver can find them — they are deploy shims, not duplicates you should edit by hand.

## File Purposes

### `Tools/` — pipeline scripts

| File | Stage | Purpose |
| --- | --- | --- |
| `page_mapping.py` | 1 | Reads unique `pageTitle` values from `raw_user_journeys.csv`, sends them in a single streamed request to Claude (`claude-sonnet-4-6`) with a `SYSTEM_PROMPT` ruleset, and writes `page_mapping.csv` (`pageTitle, pageSummary`). Contains `HARDCODED_OVERRIDES` for deterministic one-off mappings. Requires `ANTHROPIC_API_KEY`. |
| `user_journeys.py` | 2 | Joins `page_mapping.csv` onto `raw_user_journeys.csv`, builds a per-visit `user_path` by concatenating `pageSummary` values with `~` as the delimiter (raw `pageTitle` already contains `|`). Emits `base_user_journeys_full_visit_path.csv` (all hits) and `base_user_journeys.csv` (one row per visit, filtered to `last_step_indicator == 'Y'`). |
| `user_journeys_path_compressed.py` | 3 | Run-length compresses `user_path` and aggregates by the compressed path, producing `base_user_journeys_compressed.csv` and `agg_user_journeys_compressed_rpt.csv`. Then filters to visits that touched a product detail page (~99,934 of 200,454), adds 11 `Is_*` flag columns plus `visit_length`, classifies `Is_frustrated` / `frustrated_reasons` on unique dropout paths via `claude-opus-4-6` (7-reason enum), and writes `Rpt_Funnel_DeepDive.csv`. Classification results are cached in `frustration_cache.csv`; reruns with a populated cache are free, and the script degrades gracefully to `Is_frustrated=Unknown` when `ANTHROPIC_API_KEY` is absent and a path is uncached. |
| `verify_outputs.py` | — | Sanity-check script that prints row counts for the generated CSVs so you can eyeball them against the raw input. |
| `app.py` | 4 | Dash/Plotly dashboard. Reads `Rpt_Funnel_DeepDive.csv` at **import time** via `_resolve_data_csv` (searches `Tools/`, the repo root, and `Data/`; `FUNNEL_DATA_CSV` overrides). Renders filter controls, KPI tiles, a segmented `DataTable`, and funnel/pie/sunburst charts. Serves locally at `http://127.0.0.1:8050/`. |

### `Data/` — data files

See the folder-structure table above. `raw_user_journeys.csv` is the only input supplied externally; everything else is derived. `plan.md` is early design notes and is **stale** — trust the code. `session_prompts.md` / `session_prompts_v2.csv` are user-facing transcripts kept for traceability.

### Root files

- `CLAUDE.md` — operational guidance for Claude Code instances working in this repo. Documents pipeline order, the `~` delimiter convention, the `Tools/`↔`Data/` split, and other architectural constraints.
- `README.md` — this file.
- `Dev_Notes.html` — self-contained development journal (Problem Statement, process, example prompts, validation, result walkthrough).
- `app.py` — Plotly Cloud entry shim (`from Tools.app import app, server`).
- `requirements.txt` — dashboard runtime dependencies for Plotly Cloud.
- `Rpt_Funnel_DeepDive.csv` — deploy-side copy of the Stage 3 output, placed next to the entry shim so the cloud deploy can find it.
- `Prompts/tool_prompts.md` — rebuild guide containing the prompts, business rules, and iteration log.

## Quickstart

All commands assume the repo root as CWD and the `.venv` interpreter on PATH.

```bash
# Stage 1 — classify pageTitles (one-time, needs API key)
export ANTHROPIC_API_KEY=...
python Tools/page_mapping.py

# Stage 2 — pure pandas, offline
python Tools/user_journeys.py

# Stage 3 — compression (offline) + frustration classification
# (needs API key the first time; cache-driven and free afterward)
python Tools/user_journeys_path_compressed.py

# Stage 4 — local dashboard
python Tools/app.py            # http://127.0.0.1:8050/

# Optional sanity check
python Tools/verify_outputs.py
```

Once `page_mapping.csv` and `frustration_cache.csv` both exist, Stages 2–4 rerun fully offline. Without the cache, Stage 3 degrades gracefully: missing classifications are marked `Is_frustrated=Unknown` and the rule-based flag columns still populate.

## Dependencies

Runtime dependencies are split between the local pipeline and the deployed dashboard:

- **Dashboard runtime** (pinned in `requirements.txt` for Plotly Cloud): `dash>=2.14`, `plotly>=5.18`, `pandas>=2.0`, `gunicorn>=21.2`.
- **Pipeline-only** (installed in `.venv`, not shipped to the cloud): `anthropic` and `pydantic` for the Stage 1 + Stage 3 LLM calls.

## Conventions

- **`~` is the `user_path` delimiter**, never `|` (pipes already appear inside raw `pageTitle` values). Every consumer splits on `~`.
- **`base_user_journeys.csv` is one row per visit** (filtered to `last_step_indicator == 'Y'`). `base_user_journeys_full_visit_path.csv` is the hit-level file.
- **LLM calls are confined to Stage 1 and Stage 3**, and both are cache-backed. Stage 1 runs `claude-sonnet-4-6` once over unique `pageTitle` values and caches results in `page_mapping.csv`. Stage 3 runs `claude-opus-4-6` over unique PDP dropout paths and caches results in `frustration_cache.csv`. Once both caches exist, the pipeline runs fully offline.
- **Stage 3's deep-dive is PDP-scoped.** `Rpt_Funnel_DeepDive.csv` contains only visits that touched a product detail page (~99,934 of 200,454 total visits). The 7-reason frustration enum lives in `Tools/user_journeys_path_compressed.py` and is documented in `Prompts/tool_prompts.md`.
- **Stages are idempotent and file-based.** Each stage reads CSVs and writes CSVs; no shared in-memory state.

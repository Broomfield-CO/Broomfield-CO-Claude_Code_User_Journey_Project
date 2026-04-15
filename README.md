# AI-Powered Visitor Journey Segmentation — Built with Claude Code, Dash & Plotly

## Problem Statement

Online applications usually capture a huge amount of visitor journey data, e.g. clickstream, events, etc., that was under used due to the volume and complexity, especially data pipelines for data parsing, insight mining, and Dashboards for pattern exploration and storytelling. Using Claude Code, this project is intended to showcase the capability of AI in automating both pipeline and dashboard building.

The source data (event data in July 2017) is from a Public dataset - [Google Merch Store](https://developers.google.com/analytics/bigquery/web-ecommerce-demo-dataset) . Based on the prompts 

A small exploratory project that turns a Google Merchandise Store (GMS) hit-level
export into an interactive **Dash/Plotly** dashboard visualizing user navigation
journeys. A four-stage Python pipeline classifies page titles with Claude,
stitches hits into per-visit paths, run-length compresses consecutive duplicates,
and renders the result as Public Dashboard that can be accessed via Plotly Cloud through URL https://767c6beb-95a8-46a6-892f-c76ce480b289.plotly.app/.

The LLM is used **once**, in Stage 1, to classify ~600 unique `pageTitle` values
into a small set of `pageSummary` buckets (e.g. `product detail page`, `Home`).
Every downstream stage is pure `pandas` — idempotent, file-based, offline-safe.

## Folder Structure

```
UserJourneyDashPlotly/
├── CLAUDE.md                 # Guidance for Claude Code working in this repo
├── README.md                 # You are here
├── Tools/                    # All executable Python scripts
│   ├── page_mapping.py
│   ├── user_journeys.py
│   ├── user_journeys_path_compressed.py
│   ├── verify_outputs.py
│   └── app.py
└── Data/                     # Data files only — no .py here
    ├── raw_user_journeys.csv                        # external GMS export (input)
    ├── page_mapping.csv                             # Stage 1 output
    ├── base_user_journeys_full_visit_path.csv       # Stage 2 output (hit-level)
    ├── base_user_journeys.csv                       # Stage 2 output (per-visit)
    ├── base_user_journeys_compressed.csv            # Stage 3 output
    ├── agg_user_journeys_compressed_rpt.csv         # Stage 3 aggregate (app input)
    ├── plan.md                                      # early design notes (stale)
    ├── session_prompts.md                           # v1 session transcript
    └── session_prompts_v2.csv                       # v2 session transcript
```

All scripts live in `Tools/` and resolve the data directory as `../Data` relative
to `__file__`. `Tools/` and `Data/` must remain siblings under the repo root.

## File Purposes

### `Tools/` — pipeline scripts

| File | Stage | Purpose |
| --- | --- | --- |
| `page_mapping.py` | 1 | Reads unique `pageTitle` values from `raw_user_journeys.csv`, sends them in a single streamed request to Claude (`claude-sonnet-4-6`) with a `SYSTEM_PROMPT` ruleset, and writes `page_mapping.csv` (`pageTitle, pageSummary`). Contains `HARDCODED_OVERRIDES` for deterministic one-off mappings. **Only script that requires `ANTHROPIC_API_KEY`.** |
| `user_journeys.py` | 2 | Joins `page_mapping.csv` onto `raw_user_journeys.csv`, builds a per-visit `user_path` by concatenating `pageSummary` values with `~` as the delimiter (since raw `pageTitle` already contains `|`). Emits `base_user_journeys_full_visit_path.csv` (all hits) and `base_user_journeys.csv` (one row per visit, filtered to `last_step_indicator == 'Y'`). |
| `user_journeys_path_compressed.py` | 3 | Run-length compresses consecutive identical segments in `user_path`: a run of 1 stays verbatim, a run of N≥2 becomes `"<segment> (X<N>)"`. Produces `base_user_journeys_compressed.csv` plus `agg_user_journeys_compressed_rpt.csv` — 30k+ distinct compressed paths with `unique_visitors` and `unique_visits` counts. |
| `verify_outputs.py` | — | Sanity-check script that prints row counts for every generated CSV so you can eyeball them against the raw input. |
| `app.py` | 4 | Dash/Plotly dashboard. Reads `agg_user_journeys_compressed_rpt.csv` at **import time**, strips `(XN)` run-length suffixes, computes a force-directed node layout via an inline Fruchterman-Reingold spring solver (~60 lines, no `networkx` dependency), and serves the figure at `http://127.0.0.1:8050/`. |

### `Data/` — data files

See the folder-structure table above. `raw_user_journeys.csv` is the only input
supplied externally; everything else is derived. `plan.md` is early design notes
and is **stale** — trust the code. `session_prompts*.md/csv` are user-facing
transcripts kept for traceability.

### Root files

- `CLAUDE.md` — operational guidance for Claude Code instances working in this
  repo. Documents the pipeline order, the `~` delimiter convention, the
  Tools/Data split, and other architectural constraints.
- `README.md` — this file.

## Quickstart

All commands assume the repo root as CWD and the `.venv` interpreter on PATH.

```bash
# Stage 1 — classify pageTitles (one-time, needs API key)
export ANTHROPIC_API_KEY=...
python Tools/page_mapping.py

# Stages 2-3 — pure pandas, offline
python Tools/user_journeys.py
python Tools/user_journeys_path_compressed.py

# Stage 4 — dashboard
python Tools/app.py            # http://127.0.0.1:8050/

# Optional sanity check
python Tools/verify_outputs.py
```

Once `page_mapping.csv` exists you can rerun Stages 2–4 offline. The dashboard
builds its force graph at module import, so startup takes a few seconds.

## Dependencies

Installed in `.venv` (no `requirements.txt` or build system):

- `dash`, `plotly` — dashboard and charts
- `pandas` — all Stage 2–4 transforms
- `anthropic` — Stage 1 LLM calls
- `pydantic` — structured-output schema for classification results

## Conventions

- **`~` is the `user_path` delimiter**, never `|` (pipes already appear inside
  raw `pageTitle` values). Every consumer splits on `~`.
- **`base_user_journeys.csv` is one row per visit** (filtered to
  `last_step_indicator == 'Y'`). `base_user_journeys_full_visit_path.csv` is the
  hit-level file.
- **The LLM is isolated to Stage 1.** Classification rules live entirely in the
  `SYSTEM_PROMPT` constant inside `Tools/page_mapping.py` — there is no separate
  rules file.
- **Stages are idempotent and file-based.** Each stage reads CSVs and writes
  CSVs; no shared in-memory state.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Small exploratory project that turns a Google Merchandise Store hit-level export into a Dash/Plotly user-journey dashboard. Four scripts form a linear data pipeline; a single Dash app renders the result. No tests, no build system, no package manifest — dependencies (`dash`, `plotly`, `pandas`, `pydantic`, `anthropic`) live in `.venv`.

## Pipeline (run in order)

All commands assume the repo root as CWD and the `.venv` interpreter on PATH.

```bash
# Stage 1 — classify unique pageTitles into pageSummary via Claude (one-time, needs API key)
export ANTHROPIC_API_KEY=...    # required; script exits otherwise
python Tools/page_mapping.py    # raw_user_journeys.csv  -> page_mapping.csv

# Stage 2 — join mapping onto raw hits, build user_path per visit
python Tools/user_journeys.py   # raw_user_journeys.csv + page_mapping.csv
                                #   -> base_user_journeys_full_visit_path.csv (all hits)
                                #   -> base_user_journeys.csv                 (one row per visit)

# Stage 3 — run-length compress consecutive duplicates, aggregate by compressed path
python Tools/user_journeys_path_compressed.py
                                # -> base_user_journeys_compressed.csv
                                # -> agg_user_journeys_compressed_rpt.csv

# Stage 4 — Dash dashboard (reads agg_user_journeys_compressed_rpt.csv at import time)
python Tools/app.py             # serves http://127.0.0.1:8050/

# Sanity check row counts against the raw input
python Tools/verify_outputs.py
```

Stages are idempotent and file-based. Stage 1 is the only step that calls the LLM — downstream stages are pure pandas joins/transforms, so once `page_mapping.csv` exists you can rerun stages 2–4 offline.

## Architecture notes worth knowing before editing

- **All executable scripts live in `Tools/`. `Data/` is data-only.** The five pipeline scripts (`page_mapping.py`, `user_journeys.py`, `user_journeys_path_compressed.py`, `verify_outputs.py`, `app.py`) resolve the data directory as `../Data` relative to `__file__` — they must stay siblings of `Data/` under the repo root.
- **LLM is isolated to Stage 1.** `Tools/page_mapping.py` holds the entire classification ruleset as a multi-line `SYSTEM_PROMPT` constant (three detectors: `product detail page`, `shop by brand`, `shop by category`, plus an English-translation fallthrough). It sends all unique `pageTitle` values in one streamed request using `output_format=ClassificationResult` (Pydantic). Changing classification behavior means editing that prompt — there is no separate rules file. Model is pinned to `claude-sonnet-4-6`.
- **`~` is the path delimiter, not `|`.** Raw `pageTitle` values already contain `|`, so `user_journeys.py` joins `pageSummary` values with `~` when building `user_path`. Every downstream consumer (`user_journeys_path_compressed.py`, `app.py`) splits on `~`. Do not change this.
- **`base_user_journeys.csv` is one row per visit**, filtered to `last_step_indicator == 'Y'`. `base_user_journeys_full_visit_path.csv` is the hit-level file. `Data/plan.md` describes the opposite convention — it is stale; trust the code. Stage 3's groupby treats row count as visit count and depends on this.
- **Force graph is computed at import time.** `app.py` calls `_build_force_graph_figure()` at module load, which reads the aggregate CSV, strips `(XN)` run-length suffixes with `_COUNT_SUFFIX`, and lays nodes out via an inline Fruchterman-Reingold implementation (`_spring_layout`, ~60 lines, pure Python, no networkx). Startup is a few seconds. If you restructure the layout, keep the spring layout inline — avoiding `networkx` as a dependency is deliberate.
- **Run-length compression rule.** `Tools/user_journeys_path_compressed.py::compress_path` collapses consecutive identical `~`-segments: run of 1 → verbatim, run of N≥2 → `"<segment> (X<N>)"`. `_strip_count` in `app.py` is the inverse for graph rendering.
- **Session prompts live in `Data/session_prompts_v2.csv`** (v1 is `session_prompts.md`). These are user-facing transcripts kept for traceability, not inputs to any script.

## Data files (all in `Data/`, none checked into any build system)

| File | Produced by | Shape |
| --- | --- | --- |
| `raw_user_journeys.csv` | external (GMS export) | hit-level, ~90 MB |
| `page_mapping.csv` | `page_mapping.py` (LLM) | `pageTitle, pageSummary` |
| `base_user_journeys_full_visit_path.csv` | `user_journeys.py` | all hits + `user_path`, `last_step_indicator` |
| `base_user_journeys.csv` | `user_journeys.py` | one row per visit (200,454 rows) |
| `base_user_journeys_compressed.csv` | `user_journeys_path_compressed.py` | + `user_path_Compressed` |
| `agg_user_journeys_compressed_rpt.csv` | `user_journeys_path_compressed.py` | 30,403 distinct compressed paths with `unique_visitors`, `unique_visits` |

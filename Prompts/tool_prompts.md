# Tool Prompts — Reconstruction Guide

Consolidated prompts and business rules to rebuild the `UserJourneyDashPlotly`
pipeline from scratch using an LLM coding assistant. Each numbered prompt below
is self-contained: feed it to a fresh assistant in this repo and you should get
an equivalent file back. Prompts are ordered by pipeline stage; run them in
order because each stage consumes the previous stage's CSV output.

---

## 0. Project context (read this first, then paste it into every prompt)

You are building a data exploratory pipeline on a Google
Merchandise Store hit-level export. Five scripts in `Tools/` form a linear
pipeline; a single Dash app renders the result. No build system, no tests,
dependencies live in `.venv` (`dash`, `plotly`, `pandas`, `pydantic`,
`anthropic`).

**Layout rules (do not violate):**
- All executable scripts live in `Tools/`. `Data/` is data-only.
- Scripts resolve their data dir as `../Data` relative to `__file__`.
- `~` is the path delimiter inside `user_path` strings. Raw `pageTitle`
  already contains `|`, so never use `|` as a separator.
- `base_user_journeys.csv` is one row per visit, filtered to
  `last_step_indicator == 'Y'`. `base_user_journeys_full_visit_path.csv` is
  the hit-level file. Downstream groupbys treat row count as visit count.
- The LLM is isolated to **Stage 1** (page classification) and the
  **frustration pass in Stage 3**, both with file-cached outputs so reruns
  are free once the cache exists. Stages 2, 3 (non-frustration), and 4 are
  pure pandas.
- Both LLM calls use `claude-opus-4-6` or `claude-sonnet-4-6` with
  streaming + pydantic structured output (`output_format=<Model>`). Batch
  with a retry-missing loop keyed on the input string so paths that the
  model skips are re-asked until they land.

**Target output artifacts (what "done" looks like):**

| File | Producer | Shape |
| --- | --- | --- |
| `Data/raw_user_journeys.csv` | external (GMS export) | hit-level, ~90 MB |
| `Data/page_mapping.csv` | `Tools/page_mapping.py` | `pageTitle, pageSummary` |
| `Data/base_user_journeys_full_visit_path.csv` | `Tools/user_journeys.py` | hit-level + `user_path`, `last_step_indicator` |
| `Data/base_user_journeys.csv` | `Tools/user_journeys.py` | one row per visit (~200k rows) |
| `Data/base_user_journeys_compressed.csv` | `Tools/user_journeys_path_compressed.py` | + `user_path_Compressed`, `user_path_Compressed_no_Counts` |
| `Data/agg_user_journeys_compressed_rpt.csv` | `Tools/user_journeys_path_compressed.py` | unique compressed paths with `unique_visitors`, `unique_visits` |
| `Data/Rpt_Funnel_DeepDive.csv` | `Tools/user_journeys_path_compressed.py` | PDP-touching visits (~100k rows) with 11 `Is_*` flags + frustration columns |
| `Data/frustration_cache.csv` | `Tools/user_journeys_path_compressed.py` | `user_path_Compressed_no_Counts, is_frustrated, frustrated_reasons` |

---

## 1. Canonical business rules (paste into prompts 3 and 4)

### 1a. `pageSummary` tokens detected on the uncompressed `user_path`

Rule-based flags live in Stage 3. Match on the **uncompressed** `user_path`
(a `~`-delimited string); use substring checks, never regex, because several
segments have the form `"9: The Google Merchandise Store - Log In"` and
substring matching handles both prefixed and unprefixed variants.

| Flag column | Match token(s) (any-of, substring) |
| --- | --- |
| `Is_cart` | `Shopping Cart` |
| `Is_Checkout_Your_Information` | `Checkout Your Information` |
| `Is_Payment_Method` | `Payment Method` |
| `Is_Checkout_Review` | `Checkout Review` |
| `Is_Checkout_Confirmation` | `Checkout Confirmation` |
| `Is_Sales` | `Clearance Sale`, `Spring Sale` |
| `Is_Troubles` | `Frequently Asked Questions` |
| `Is_Login` | `Log In` |
| `Is_Search` | `Store search results` |
| `Is_ErrorPage` | `Page Unavailable` |
| `Is_Wishlist` | `Your Wishlist` |

All flag columns are the literal strings `"Y"` / `"N"` (not booleans) for
dashboard-filter legibility.

### 1b. Frustration reason enum (used by Stage 3 LLM and Stage 4 filter)

Opus picks zero or more of these; an empty list means the visitor is not
frustrated.

```
payment_friction   — repeated Payment Method visits, or abandon at/after payment
form_friction      — oscillation between Shopping Cart / Checkout Your Information / Checkout Review
price_shock        — viewed Shopping Cart or Checkout Your Information then exited without progressing
indecision         — many product detail page views, repeated cart interactions, long browse with no purchase
technical_issue    — path contains Page Unavailable
search_struggle    — repeated Store search results with no product detail page engagement
account_blocked    — repeated Log In / Register with no funnel progress afterward
```

Rules:
- `Is_frustrated = "Y"` iff `frustrated_reasons` is non-empty (pipe-joined).
- Completers (`Is_Checkout_Confirmation == "Y"`) are pre-labeled `N` with
  empty reasons; they never hit the LLM.
- Casual browses (short path, one or two PDPs, no cart activity) are NOT
  frustration.
- Never invent reasons outside the enum.

### 1c. Run-length compression rule (Stage 3)

Three passes of k-gram compression on the `~`-split token list: k=1, k=2,
k=3. Each pass slides a window of k tokens L→R and collapses consecutive
identical k-gram repetitions. Leaves are `("L", segment, count)`, groups are
`("G", (child_tok, ...), N)`. Groups from earlier passes are treated as
atomic in later passes. Pass 3 multiplies counts instead of nesting so leaf
runs collapse to `seg (XN)`.

Two render modes:
- `compress_path(path)` → with counts: `seg (X3)` or `[seg1~seg2] (X3)`
- `compress_path_no_counts(path)` → same structure but counts stripped, used
  as the cache key for the frustration classifier so `(X3)` vs `(X4)` don't
  split cache entries.

---

## 2. Prompt 1 — build `Tools/page_mapping.py` (Stage 1, LLM)

```
Build Tools/page_mapping.py. Purpose: read Data/raw_user_journeys.csv (GMS hit
export), extract unique pageTitle values, classify each into one of a small
set of pageSummary tokens using the Anthropic API, and write
Data/page_mapping.csv with columns [pageTitle, pageSummary].

Classification rules (put in the system prompt, verbatim):
- "product detail page" — pageTitle looks like a product listing page (has
  color/size/price markers, brand names, etc.)
- "shop by brand" — category/brand landing pages
- "shop by category" — generic category landing pages
- Otherwise: return the English translation of the pageTitle, stripped to a
  short canonical form (e.g. "The Google Merchandise Store - Log In" → "Log
  In", "Shopping Cart | …" → "Shopping Cart").

Constraints:
- Model: claude-opus-4-6 (or claude-sonnet-4-6 if explicitly asked). Use
  streaming + pydantic via output_format=ClassificationResult.
- Send ALL unique pageTitles in one streamed request (the input is small).
- pydantic models: ClassificationItem(pageTitle: str, pageSummary: str) and
  ClassificationResult(items: list[ClassificationItem]).
- max_tokens=32000, system prompt holds the full ruleset, user message is a
  numbered list of titles with an instruction to return exactly N items and
  echo pageTitle byte-for-byte.
- Retry-missing loop: if the parsed output is missing any input titles, call
  the model again with just the missing set, up to 3 retries.
- Cache: if Data/page_mapping.csv already exists, load it and only classify
  titles not yet in the cache.
- If ANTHROPIC_API_KEY is not set, print a loud warning and exit nonzero.

Resolve paths via os.path.join(os.path.dirname(os.path.abspath(__file__)),
"..", "Data", "<name>.csv"). Do not hard-code absolute paths.
```

---

## 3. Prompt 2 — build `Tools/user_journeys.py` (Stage 2, pure pandas)

```
Build Tools/user_journeys.py. Purpose: join Data/page_mapping.csv onto
Data/raw_user_journeys.csv (hit-level), build a user_path string per visit,
and emit two CSVs.

Logic:
1. Read raw hits + page_mapping. Left-join mapping onto hits on pageTitle so
   every hit has a pageSummary.
2. Sort hits within each (fullVisitorId, visitId) by hit sequence (hitNumber
   or visitStartTime + hit index, whichever is available).
3. For each (fullVisitorId, visitId), build user_path by joining pageSummary
   values with "~". Never use "|" — raw pageTitle already contains pipes.
4. Mark the last hit of each visit with last_step_indicator = "Y",
   everything else "N".
5. Emit Data/base_user_journeys_full_visit_path.csv (all hits with user_path
   + last_step_indicator).
6. Filter to last_step_indicator == "Y" and emit Data/base_user_journeys.csv
   — one row per visit.

Use pandas groupby + agg or transform; keep it vectorized where reasonable.
Resolve paths via __file__/../Data. Print row counts of both output files.
No LLM, no network calls.
```

---

## 4. Prompt 3 — build `Tools/user_journeys_path_compressed.py` (Stage 3)

```
Build Tools/user_journeys_path_compressed.py. Consumes
Data/base_user_journeys.csv from Stage 2 and produces THREE outputs:
Data/base_user_journeys_compressed.csv,
Data/agg_user_journeys_compressed_rpt.csv, and
Data/Rpt_Funnel_DeepDive.csv (plus a side-car
Data/frustration_cache.csv). main() drives all three.

### 3a. Compression (pure pandas, deterministic)

Implement three-pass k-gram compression (k=1, 2, 3) on the ~-split token
list. Leaves are ("L", segment, count). Groups are ("G", (child_tok, ...),
N). k=1 multiplies counts (no nesting); k>=2 nests as groups. Two public
renderers:
- compress_path(path)          → with counts: "seg (X3)" and "[seg1~seg2] (X3)"
- compress_path_no_counts(path) → same structure but counts stripped; used
                                   as the frustration cache key

Add two columns to the compressed CSV: user_path_Compressed and
user_path_Compressed_no_Counts. Then aggregate by user_path_Compressed →
agg CSV with [user_path_Compressed, unique_visitors=nunique(fullVisitorId),
unique_visits=size], sorted by unique_visits desc.

### 3b. Rpt_Funnel_DeepDive.csv (rule-based flags + LLM frustration pass)

Filter compressed df to rows whose user_path contains "product detail page"
→ pdp df (~100k rows, ~50% of input).

Add visit_length = user_path.count("~") + 1 (int).

Add 11 rule-based flag columns — all literal "Y"/"N" — per the business
rules table in Prompts/tool_prompts.md §1a (Is_cart, Is_Checkout_*,
Is_Payment_Method, Is_Sales, Is_Troubles, Is_Login, Is_Search, Is_ErrorPage,
Is_Wishlist). Match as substring on uncompressed user_path; "Is_Sales"
matches "Clearance Sale" OR "Spring Sale".

Add two frustration columns:
- Is_frustrated ("Y"/"N"/"Unknown")
- frustrated_reasons (pipe-joined subset of the 7-reason enum, or "")

Pre-label completers deterministically: any row with
Is_Checkout_Confirmation == "Y" → Is_frustrated="N", frustrated_reasons="".
They are NOT sent to the LLM.

For dropouts, dedupe by user_path_Compressed_no_Counts (~5.6k unique),
consult Data/frustration_cache.csv, classify only missing paths via
claude-opus-4-6 in streaming batches of 50 with pydantic
FrustrationResult(items: list[FrustrationItem]) where FrustrationItem has
(path: str, is_frustrated: Literal["Y","N"], reasons:
list[Literal[<7 reasons>]]). After each batch, flush the cache to disk so a
crash mid-run doesn't waste budget. Retry-missing loop up to 3 retries.
Give up on still-missing paths with ("Unknown", "").

If ANTHROPIC_API_KEY is unset, fall back to Is_frustrated="Unknown" for
missing paths and emit the file with a loud warning; do not raise.

Join the cache back onto pdp rows via user_path_Compressed_no_Counts. Emit
Data/Rpt_Funnel_DeepDive.csv with columns in this order:

fullVisitorId, visitId, visitStartTime, user_path, user_path_Compressed,
user_path_Compressed_no_Counts, visit_length, Is_cart,
Is_Checkout_Your_Information, Is_Payment_Method, Is_Checkout_Review,
Is_Checkout_Confirmation, Is_Sales, Is_Troubles, Is_Login, Is_Search,
Is_ErrorPage, Is_Wishlist, Is_frustrated, frustrated_reasons.

The system prompt for the LLM call lives inline as
FRUSTRATION_SYSTEM_PROMPT — a multi-line string defining the 7-reason enum
with the exact bullet definitions from Prompts/tool_prompts.md §1b, the
completer rule ("never sent to you"), the casual-browse rule ("NOT
frustration"), and a byte-for-byte path echo requirement.
```

---

## 5. Prompt 4 — build `Tools/app.py` (Stage 4, Dash dashboard)

```
Build Tools/app.py — a single-file Dash dashboard sourced from
Data/Rpt_Funnel_DeepDive.csv. No force graph, no networkx. Must be
deployable to Plotly Cloud (cloud.plotly.com) via web upload, so expose
`server = app.server` and support running under gunicorn with entry point
app:server.

### CSV path resolution (deploy-safe)
Write `_resolve_data_csv()` that probes, in order: $FUNNEL_DATA_CSV,
<script dir>/Rpt_Funnel_DeepDive.csv, <script dir>/../Rpt_Funnel_DeepDive.csv,
<script dir>/../Data/Rpt_Funnel_DeepDive.csv. Return the first path that
exists. If none exist, raise FileNotFoundError listing all tried paths.

### Layout
- Title "Funnel DeepDive", total rows footer, filter card, KPI row, 3
  charts in a flex row, DataTable at the bottom.
- Filter card contains:
  - One Dropdown per Is_* flag column (Any/Y/N) with id
    {"type": "flag-filter", "col": <col>} (pattern-matching).
  - RadioItems "logic-operator" (AND|OR, default AND) controlling how the
    flag submasks combine.
  - Multi-select Dropdown "reason-filter" over the 7 frustration reasons
    (reasons always combine as OR among themselves and AND with the flag
    mask).
  - RangeSlider "length-filter" over visit_length [1, max].
- KPI row: 4 cards — matching visits, unique visitors, completion rate
  (completers / total), frustration rate (Is_frustrated='Y' / total).
- Three filter-reactive figures:
  - funnel-fig: Plotly Funnel over Cart → Your Info → Payment → Review →
    Confirmation using sum of Is_<step>=='Y' per step.
  - reasons-fig: horizontal Bar of frustrated_reasons counts (split on
    '|', counted against the 7-reason enum, sorted desc, yaxis reversed).
  - length-fig: Histogram of visit_length with 40 bins.
- DataTable "visits-table": page_size=20, sort_action="native",
  filter_action="native". Cap output to TABLE_ROW_CAP=500 rows with a
  caption "Showing first N of M matching rows". Row tinting:
  Is_frustrated='Y' → #fff4f4; Is_Checkout_Confirmation='Y' → #f2faf2.
- Table columns: fullVisitorId, visitId, visit_length, user_path_Compressed,
  Is_cart, Is_Checkout_Your_Information, Is_Payment_Method,
  Is_Checkout_Review, Is_Checkout_Confirmation, Is_frustrated,
  frustrated_reasons.

### Callback
Single callback — Inputs: ALL flag-filter values + ids (pattern-matching),
logic-operator, reason-filter, length-filter. Outputs: visits-table data,
caption, kpi-row children, 3 figures. The filter engine ANDs length_mask,
flag_mask, reason_mask. flag_mask starts as the first active submask and
combines via OR or AND per operator; if no flag filter is active, pass
through. Every figure must degrade gracefully to an empty-state annotation
("No matching visits") via an _empty_fig helper.

### Entry point
if __name__ == "__main__": app.run()  # no debug=True in committed code
```

---

## 6. Prompt 5 — build `Tools/verify_outputs.py` (sanity check)

```
Build Tools/verify_outputs.py. Load raw_user_journeys.csv and each pipeline
output. Print row-count and unique-key sanity checks:
- full-visit-path row count matches raw hit count
- base_user_journeys.csv row count matches distinct (fullVisitorId, visitId)
  count in the raw file
- compressed row count matches base row count
- agg unique_visits column sums to base row count
- Rpt_Funnel_DeepDive row count matches PDP subset row count in base

Exit nonzero if any check fails. No LLM, no writes.
```

---

## 7. Prompt 6 — make it deployable to Plotly Cloud

```
Make the repo deployable to cloud.plotly.com/apps via direct web upload.
Entry point must be app:server (Plotly Cloud auto-detects). Requirements:

1. Create requirements.txt at the repo ROOT with:
     dash>=2.14
     plotly>=5.18
     pandas>=2.0
     gunicorn>=21.2
2. Create a root-level app.py shim that does:
     from Tools.app import app, server
     if __name__ == "__main__": app.run()
3. Copy Data/Rpt_Funnel_DeepDive.csv to the repo root next to app.py so the
   deploy bundle is self-contained. The CSV resolver in Tools/app.py
   already probes the repo root.
4. Add a .gitignore that excludes .venv/, __pycache__/, Data/ (except the
   one CSV at root), *.pyc.
5. Confirm total bundle size < 80 MiB (the Plotly Cloud web-upload limit).

Deploy steps for the user (print after build):
- Go to https://cloud.plotly.com/apps, sign in.
- Click New app, drag the repo folder into the browser.
- Plotly Cloud auto-detects app.py, reads requirements.txt, builds a
  container, and starts the app.
- No Procfile, no Dockerfile, no env vars needed.
```

---

## 8. Rebuild order

1. Put `raw_user_journeys.csv` in `Data/`.
2. `export ANTHROPIC_API_KEY=...`
3. `python Tools/page_mapping.py`
4. `python Tools/user_journeys.py`
5. `python Tools/user_journeys_path_compressed.py` (longest step — first run
   is ~$5 of Opus; second run is free thanks to `frustration_cache.csv`).
6. `python Tools/verify_outputs.py`
7. `python Tools/app.py` (dev) or `gunicorn app:server` (prod) or deploy to
   Plotly Cloud per prompt 6.

---

## 9. Session iteration log

What this session actually changed, in order, so a reader can retrace the
real path (not the idealized rebuild prompts above):

1. **Dropped the force-directed graph.** Original `Tools/app.py` had a
   ~60-line inline Fruchterman-Reingold spring layout over the aggregate
   CSV. User said "ignore force graph" → removed the graph, helpers, and
   sample figures entirely.
2. **Rewrote `Tools/app.py`** to source directly from
   `Data/Rpt_Funnel_DeepDive.csv` (produced in the prior session by Stage
   3), with a composable filter UI: Any/Y/N dropdowns per `Is_*` flag,
   AND/OR radio toggle, multi-select reason filter, visit-length
   RangeSlider. Added KPI cards, Plotly Funnel, reason histogram, length
   histogram, and a paginated DataTable capped at 500 rows with row tinting
   for frustrated / completer rows.
3. **Exposed `server = app.server`** for gunicorn / Plotly Cloud.
4. **Created `requirements.txt`** at repo root (`dash`, `plotly`, `pandas`,
   `gunicorn`) — first package manifest in the repo.
5. **Plotly Cloud deploy failed** → suspected path resolution.
   `DATA_CSV` was hard-coded to `../Data/Rpt_Funnel_DeepDive.csv` relative
   to `Tools/app.py`; that doesn't resolve on a flat deploy bundle.
   Replaced with `_resolve_data_csv()` probing `$FUNNEL_DATA_CSV`, `Tools/`,
   repo root, and `Data/` in order, with a clear `FileNotFoundError`
   listing all tried paths.
6. **Created a root-level `app.py` shim** (`from Tools.app import app,
   server`) so Plotly Cloud's root-level entry-point detection finds
   `app:server` without moving the real code out of `Tools/`.
7. **Removed `debug=True`** from the `__main__` block in `Tools/app.py`
   for production cleanliness; local debug runs now use
   `python -c "from app import app; app.run(debug=True)"`.
8. **Staged the deploy bundle**: copied `Rpt_Funnel_DeepDive.csv` to the
   repo root so the uploaded folder is self-contained and the resolver
   picks it up on the server.

---

## 10. Things NOT to do (collected gotchas)

- Do **not** use `|` as a path separator. Raw `pageTitle` values contain
  `|`, so splits/joins must use `~`.
- Do **not** move app.py out of `Tools/` and delete the root shim. The
  project convention is "all executables in `Tools/`"; the shim is how you
  reconcile that with Plotly Cloud's root-entry-point assumption.
- Do **not** ship `debug=True` in committed code. Use an env var or a
  one-liner for local dev.
- Do **not** re-run Stage 3 without `frustration_cache.csv` on a fresh
  machine unless you want to pay ~$5 for Opus again. Always copy the cache
  when moving environments.
- Do **not** trust `Data/plan.md` if it contradicts the code — it is stale;
  trust the code.
- Do **not** add `networkx` as a dependency. The inline spring layout was
  removed with the force graph; if you ever reintroduce a graph view, keep
  the layout inline.
- Do **not** use regex for flag detection. Substring matching handles the
  `"9: The Google Merchandise Store - Log In"` prefix variant correctly and
  has no escaping pitfalls.
- Do **not** send completer paths to the frustration LLM. They are
  pre-labeled `N` / `""` and dropping them saves ~40% of the LLM budget.

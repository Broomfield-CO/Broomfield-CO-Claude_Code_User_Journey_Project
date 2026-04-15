<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>UserJourneyDashPlotly — Development Notes</title>
<style>
  :root {
    --fg: #1f2933;
    --muted: #5c6b7a;
    --accent: #2c5282;
    --accent-soft: #ebf2fa;
    --border: #d9e1ec;
    --code-bg: #f4f6fa;
    --good: #2e7d32;
    --warn: #b7791f;
    --bad:  #b71c1c;
  }
  * { box-sizing: border-box; }
  body {
    font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: var(--fg);
    max-width: 960px;
    margin: 0 auto;
    padding: 40px 28px 80px;
    line-height: 1.55;
    background: #ffffff;
  }
  h1 {
    font-size: 28px;
    border-bottom: 3px solid var(--accent);
    padding-bottom: 10px;
    margin-bottom: 6px;
  }
  h2 {
    font-size: 22px;
    color: var(--accent);
    margin-top: 44px;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--border);
  }
  h3 {
    font-size: 17px;
    color: var(--fg);
    margin-top: 26px;
  }
  p, li { font-size: 15px; }
  .subtitle { color: var(--muted); margin: 0 0 8px; font-size: 14px; }
  .tagline { color: var(--muted); font-style: italic; margin-bottom: 20px; }
  code {
    background: var(--code-bg);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 1px 5px;
    font-family: "Consolas", "Menlo", monospace;
    font-size: 13px;
  }
  pre {
    background: var(--code-bg);
    border: 1px solid var(--border);
    border-left: 4px solid var(--accent);
    border-radius: 4px;
    padding: 14px 16px;
    overflow-x: auto;
    font-family: "Consolas", "Menlo", monospace;
    font-size: 13px;
    line-height: 1.45;
  }
  pre code { background: none; border: none; padding: 0; }
  table {
    border-collapse: collapse;
    width: 100%;
    margin: 14px 0;
    font-size: 14px;
  }
  th, td {
    border: 1px solid var(--border);
    padding: 8px 12px;
    text-align: left;
    vertical-align: top;
  }
  th { background: var(--accent-soft); font-weight: 600; }
  tr:nth-child(even) td { background: #fafbfd; }
  .callout {
    background: var(--accent-soft);
    border-left: 4px solid var(--accent);
    padding: 12px 16px;
    margin: 18px 0;
    border-radius: 4px;
  }
  .callout.warn { background: #fff8e1; border-left-color: var(--warn); }
  .callout.good { background: #e9f5ec; border-left-color: var(--good); }
  .prompt {
    background: #fbfbfd;
    border: 1px solid var(--border);
    border-left: 4px solid #8e44ad;
    border-radius: 4px;
    padding: 12px 16px;
    margin: 12px 0;
    font-size: 14px;
  }
  .prompt .label {
    display: block;
    color: #8e44ad;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 6px;
  }
  .prompt .body { white-space: pre-wrap; font-family: "Consolas","Menlo",monospace; font-size: 13px; color: var(--fg); }
  .toc {
    background: #fafbfd;
    border: 1px solid var(--border);
    padding: 14px 22px;
    border-radius: 4px;
    margin: 20px 0 30px;
  }
  .toc ol { margin: 6px 0 0 18px; padding: 0; }
  .toc a { color: var(--accent); text-decoration: none; }
  .toc a:hover { text-decoration: underline; }
  .stage-pill {
    display: inline-block;
    background: var(--accent);
    color: white;
    border-radius: 10px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.03em;
    margin-right: 6px;
    vertical-align: middle;
  }
  .metric {
    display: inline-block;
    background: var(--accent-soft);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 10px 16px;
    margin: 6px 8px 6px 0;
    min-width: 180px;
  }
  .metric .k { display: block; font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }
  .metric .v { display: block; font-size: 20px; font-weight: 700; color: var(--accent); margin-top: 2px; }
  footer { margin-top: 60px; color: var(--muted); font-size: 12px; border-top: 1px solid var(--border); padding-top: 14px; }
  .step-num {
    display: inline-block;
    width: 22px;
    height: 22px;
    line-height: 22px;
    text-align: center;
    background: var(--accent);
    color: white;
    border-radius: 50%;
    font-size: 12px;
    font-weight: 700;
    margin-right: 8px;
  }
</style>
</head>
<body>

<h1>UserJourneyDashPlotly — Development Notes</h1>
<p class="subtitle">A walk-through of how this project was built end-to-end with Claude Code.</p>
<p class="tagline">From a 90&nbsp;MB Google Merchandise Store hit-level export to a filterable funnel-analysis dashboard, delivered in a few conversations instead of a sprint.</p>

<div class="toc">
  <strong>Contents</strong>
  <ol>
    <li><a href="#problem">Problem Statement</a></li>
    <li><a href="#process">Process to Build the Project in Claude Code</a></li>
    <li><a href="#prompts">Example Prompts by Stage</a></li>
    <li><a href="#validation">Validation</a></li>
    <li><a href="#result">Result Walkthrough</a></li>
  </ol>
</div>

<!-- ============================================================= -->
<h2 id="problem">1. Problem Statement</h2>

<h3>What the project is trying to do</h3>
<p>
  The input is a Google Merchandise Store (GMS) hit-level export: ~90&nbsp;MB of row-per-click data
  with columns like <code>fullVisitorId</code>, <code>visitId</code>, <code>hitNumber</code>,
  <code>pageTitle</code>, and <code>pagePath</code>. There are ~600 unique <code>pageTitle</code>
  strings, many of which are product pages with noisy suffixes like
  <code>Men's Vintage Henley | Apparel | Google Merchandise Store</code>.
</p>
<p>
  The goal is to turn those raw hits into a <strong>per-visit navigation journey</strong>, then
  visualize the <strong>checkout funnel</strong> and the reasons visitors drop out, so a
  product/UX team can answer questions like:
</p>
<ul>
  <li>Where in the funnel are we losing people — Cart? Payment? Review?</li>
  <li>How many of our drop-outs look <em>frustrated</em> vs just casually browsing?</li>
  <li>What share of frustration is payment friction vs form friction vs price shock?</li>
  <li>Can a non-engineer slice the cohort by flags (cart-touched, PDP-touched, sale-visited, login-attempted…) and see paths change?</li>
</ul>

<h3>Traditional approach (without an LLM coding agent)</h3>
<table>
  <thead>
    <tr><th>Stage</th><th>Typical manual effort</th><th>Pain points</th></tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Classify pageTitle → pageSummary</strong></td>
      <td>Hand-maintain a regex/rule list (~600 unique values), review each one, keep the list in sync with new pages.</td>
      <td>Brittle — breaks on non-English titles, new products, localization. Hours of drudge to set up, ongoing maintenance tax.</td>
    </tr>
    <tr>
      <td><strong>Build the per-visit path</strong></td>
      <td>Pandas groupby, sort hits, join pageSummary, concat with a delimiter. A few hours of vectorized code + edge cases.</td>
      <td>Easy to get wrong on delimiters (pipe vs tilde) and last-hit filtering. No tests here means silent drift.</td>
    </tr>
    <tr>
      <td><strong>Compress path + aggregate</strong></td>
      <td>Write a run-length compressor, then a k-gram / group compressor for repeat sub-journeys. Multi-day task if done properly.</td>
      <td>Iteration is slow — each rule change forces a rebuild + eyeball of the output CSV.</td>
    </tr>
    <tr>
      <td><strong>Label frustration reasons</strong></td>
      <td>Either (a) hand-code 7 rule detectors, or (b) hire an analyst to label thousands of paths manually, or (c) skip it entirely.</td>
      <td>Option (a) produces terrible recall on messy paths; (b) is weeks of labeling; (c) abandons the most interesting question.</td>
    </tr>
    <tr>
      <td><strong>Build the Dash app</strong></td>
      <td>Scaffold layout, KPI cards, filter dropdowns, pattern-matching callback, Plotly Funnel/Pie/Bar, DataTable with native filters, row tinting.</td>
      <td>Dash callback plumbing is the slow part — each filter interaction is a round-trip of boilerplate.</td>
    </tr>
    <tr>
      <td><strong>Deploy to Plotly Cloud</strong></td>
      <td>Discover that <code>app:server</code> must be at repo root, fix CSV path resolution on a flat deploy bundle, write <code>requirements.txt</code>, trim the upload under 80&nbsp;MiB.</td>
      <td>First deploy always fails on path-resolution; fix-and-retry cycles without a collaborator are slow.</td>
    </tr>
  </tbody>
</table>

<h3>With Claude Code</h3>
<p>
  Claude Code collapses all of the above into a conversation. Rather than writing pandas or
  Plotly code directly, the user describes <strong>what</strong> the data should look like and
  <strong>why</strong>, and the agent produces the scripts, runs them, inspects the output,
  and iterates in the same loop. Two things mattered most in this specific project:
</p>
<ul>
  <li>
    <strong>LLM-at-design-time vs LLM-at-runtime decision.</strong> The first instinct would be to
    call an LLM on every <code>pageTitle</code> at runtime. Claude Code instead analyzed the ~600
    unique values, classified them once, and baked the result into a cached
    <code>page_mapping.csv</code>. Downstream stages then run as pure pandas — offline-safe and
    free to rerun.
  </li>
  <li>
    <strong>Strategic re-introduction of the LLM</strong> only where it adds clear value: the
    frustration-reasons classifier in Stage 3, where a 7-label enum over ~5.6k unique compressed
    drop-out paths is exactly the kind of judgment task that rules handle poorly and an LLM handles
    in one pass (~$5 one-time, cached afterward).
  </li>
</ul>

<div class="callout good">
  <strong>Bottom line:</strong> the same pipeline that would take 1–2 weeks of hand-written code
  and several rounds of stakeholder review landed in a handful of conversation turns, with the
  LLM used strategically (twice, both cached) rather than indiscriminately.
</div>

<!-- ============================================================= -->
<h2 id="process">2. Process to Build the Project in Claude Code</h2>

<p>
  The project was built in four stages plus a deploy pass. Each stage is a separate script in
  <code>Tools/</code>, file-based and idempotent, so any stage can be re-run without touching
  the others.
</p>

<table>
  <thead>
    <tr><th>Stage</th><th>Script</th><th>Input</th><th>Output</th><th>LLM?</th></tr>
  </thead>
  <tbody>
    <tr>
      <td><span class="stage-pill">1</span> Classify</td>
      <td><code>Tools/page_mapping.py</code></td>
      <td><code>raw_user_journeys.csv</code></td>
      <td><code>page_mapping.csv</code></td>
      <td>Yes (one call, cached)</td>
    </tr>
    <tr>
      <td><span class="stage-pill">2</span> Stitch</td>
      <td><code>Tools/user_journeys.py</code></td>
      <td>raw hits + <code>page_mapping.csv</code></td>
      <td><code>base_user_journeys.csv</code> (per visit) + hit-level file</td>
      <td>No</td>
    </tr>
    <tr>
      <td><span class="stage-pill">3a</span> Compress</td>
      <td><code>Tools/user_journeys_path_compressed.py</code></td>
      <td><code>base_user_journeys.csv</code></td>
      <td><code>base_user_journeys_compressed.csv</code>, <code>agg_user_journeys_compressed_rpt.csv</code></td>
      <td>No</td>
    </tr>
    <tr>
      <td><span class="stage-pill">3b</span> Funnel Deep-Dive</td>
      <td>same script</td>
      <td>compressed CSV + 11 rule-based flags + 7-reason enum</td>
      <td><code>Rpt_Funnel_DeepDive.csv</code> (~100k PDP-touching visits) + <code>frustration_cache.csv</code></td>
      <td>Yes (cached per-path)</td>
    </tr>
    <tr>
      <td><span class="stage-pill">4</span> Dashboard</td>
      <td><code>Tools/app.py</code></td>
      <td><code>Rpt_Funnel_DeepDive.csv</code></td>
      <td>Dash server at <code>http://127.0.0.1:8050/</code></td>
      <td>No</td>
    </tr>
  </tbody>
</table>

<h3>How a typical build turn looked</h3>
<ol>
  <li><span class="step-num">1</span><strong>Frame the problem.</strong> User describes the input file, the desired output, and the business rules in the system prompt.</li>
  <li><span class="step-num">2</span><strong>Plan mode.</strong> For non-trivial stages (especially Stage 3's frustration classifier), the agent drafts a plan file describing schema, cache strategy, cost estimate, and graceful-degradation path. User reviews before code is touched.</li>
  <li><span class="step-num">3</span><strong>Edit in place.</strong> The agent writes a new script or extends an existing one. All executables stay in <code>Tools/</code>; all data stays in <code>Data/</code>.</li>
  <li><span class="step-num">4</span><strong>Run it.</strong> The agent runs the script inline, reads the output, and spots errors (syntax, schema, shape, row counts) without asking the user to copy-paste stack traces.</li>
  <li><span class="step-num">5</span><strong>Verify.</strong> <code>Tools/verify_outputs.py</code> prints row counts across all stages; visual spot-check confirms a handful of rows match expectations.</li>
  <li><span class="step-num">6</span><strong>Iterate.</strong> The user looks at the dashboard, asks for a new KPI card / chart annotation / filter behavior, and the agent edits the callback in place and hot-reloads.</li>
</ol>

<div class="callout">
  <strong>Architectural choice that matters:</strong> stages 2, 3 (non-frustration), and 4 never
  call the LLM. Once <code>page_mapping.csv</code> and <code>frustration_cache.csv</code> exist,
  the full pipeline runs offline, so you can re-cut the dashboard after a rule change without
  paying for tokens or touching the network.
</div>

<!-- ============================================================= -->
<h2 id="prompts">3. Example Prompts by Stage</h2>
<p>
  These are paraphrased from the actual session transcripts in
  <code>Data/session_prompts.md</code> and <code>Data/session_prompts_v2.csv</code>. They
  illustrate the level of specificity the agent needed at each stage — the closer the prompt
  to a product-manager-style spec with <em>explicit business rules</em>, the fewer iterations it
  took.
</p>

<h3>Stage 1 — classify pageTitle → pageSummary</h3>
<div class="prompt">
  <span class="label">From session_prompts_v2.csv row 7</span>
  <div class="body">build a mapping table in a new file page_mapping under folder Data.
- page_mapping.csv has 2 columns: pageTitle and pageSummary.
- Business rules for pageSummary:
  * pageTitle ending with "| Google Merchandise Store" AND starting with
    product names (Drinkware, Apparel, Electronics, …) separated by pipes
    → mark as "product detail page".
  * pageTitle with no pipes but clearly a product (e.g. "Google Vintage
    Henley Grey/Black") → also "product detail page".
  * else: copy pageTitle to pageSummary as-is.
- Build the mapping with python code in page_mapping.py.
- Source is raw_user_journeys.csv.
Show your plan before execution.</div>
</div>

<div class="prompt">
  <span class="label">Follow-up that expanded the ruleset (row 26)</span>
  <div class="body">Adjustments on pageSummary:
1. in addition to "navigation" and "product detail page", add
   "shop by brand" if the pageTitle mentions a brand, and
   "shop by category" if it contains categorical keywords (Apparel,
   Accessories, …). Combine them if both apply.
2. For multilingual pageTitles, translate the pageSummary to English
   but keep the same rules.</div>
</div>

<h3>Stage 2 — stitch hits into per-visit paths</h3>
<div class="prompt">
  <span class="label">From session_prompts.md (initial request)</span>
  <div class="body">Data processing requirements:
- Source: Data/raw_user_journeys.csv
- Metadata: fullVisitorId, visitId, visitNumber, visitStartTime,
  hitNumber, hitTime, pageTitle, pagePath
- Convert visitStartTime (milliseconds) + hitTime (seconds) into a
  UTC hit_timestamp.
- Sort by fullVisitorId, visitNumber, hitNumber.
- Concat pageTitle per (visitor, visit) into user_path, separator = "|".
- Store as Data/base_user_journeys.csv.
- Python code lives in Data/user_journeys.py.</div>
</div>

<div class="prompt">
  <span class="label">Clarifications that followed (rows 9–10 of session_prompts.md and row 28 of v2)</span>
  <div class="body">- Keep ALL hit-level rows (don't drop anything).
- Add a last_step_indicator column: "Y" on the final hit per visit.
- Emit base_user_journeys_full_visit_path.csv with last_step_indicator == "Y"
  only, one row per visit.
- For the user_path column, use pageSummary (not pageTitle) and replace
  the delimiter "|" with "~" because raw pageTitle already contains "|".
- You must not send anything other than unique pageTitle to the LLM.</div>
</div>

<h3>Stage 3 — compression + funnel deep-dive</h3>
<div class="prompt">
  <span class="label">Paraphrased from the Stage-3 plan file</span>
  <div class="body">Extend user_journeys_path_compressed.py to emit a third CSV
Rpt_Funnel_DeepDive.csv scoped to visits that touched a product detail
page (~100k rows, ~50% of the input).

For each row, add:
- visit_length = user_path.count("~") + 1
- 11 rule-based Is_* flags (Is_cart, Is_Checkout_*, Is_Payment_Method,
  Is_Sales, Is_Troubles, Is_Login, Is_Search, Is_ErrorPage, Is_Wishlist)
  as literal "Y"/"N" strings. Substring match on the uncompressed user_path.
- Is_frustrated ("Y"/"N"/"Unknown") and frustrated_reasons
  (pipe-joined subset of a fixed 7-reason enum).

Frustration pipeline:
1. Pre-label completers (Is_Checkout_Confirmation=Y) as N with no reasons.
2. Dedupe dropouts by user_path_Compressed_no_Counts (~5.6k unique).
3. Sidecar frustration_cache.csv — classify only new paths.
4. Call claude-opus-4-6 streamed, batches of 50, pydantic structured
   output, retry missing up to 3 times.
5. If ANTHROPIC_API_KEY is unset, fall back to "Unknown" and warn loudly.
Cost estimate: ~$5 one-time, $0 on reruns.</div>
</div>

<h3>Stage 4 — Dash dashboard</h3>
<div class="prompt">
  <span class="label">Initial Dash prompt (session_prompts_v2.csv row 1)</span>
  <div class="body">Build a Dash and Plotly app showing a simple line chart and pie
chart on a webpage. The webpage runs on the Dash local server.</div>
</div>

<div class="prompt">
  <span class="label">Later prompt — full dashboard rewrite</span>
  <div class="body">Rewrite Tools/app.py to source directly from
Data/Rpt_Funnel_DeepDive.csv. Layout:
- Title bar + filter card + KPI row + 3 charts in a flex row + DataTable.
- Filter card: one Any/Y/N dropdown per Is_* flag (pattern-matching id),
  AND/OR radio to combine them, multi-select reason dropdown, and a
  visit_length RangeSlider.
- KPIs: matching visits, unique visitors, completion visits, frustration
  visits, completion rate, frustration rate.
- Charts:
  * Funnel over Cart → Your Info → Payment → Review → Confirmation.
  * Pie of frustration reasons with the total in the center of the donut.
  * Stacked bar "drop-off drivers per step" — committed vs not-frustrated
    vs 7 reason segments, with total labels above each bar.
- DataTable: native column filters (including numeric compare on
  visit_length like ">10"), no row cap, caption reflects the actual
  filtered visit count, row tinting: frustrated → pink, completer → green.
- Single pattern-matching callback drives the whole thing.
- Expose server = app.server for gunicorn / Plotly Cloud.</div>
</div>

<h3>Deploy — Plotly Cloud</h3>
<div class="prompt">
  <span class="label">Deploy prompt</span>
  <div class="body">Make the repo deployable to cloud.plotly.com/apps via web upload.
- Entry point must be app:server at the repo root.
- Write requirements.txt at repo root.
- Create a root-level app.py shim: "from Tools.app import app, server".
- Copy Rpt_Funnel_DeepDive.csv to the repo root so the deploy bundle is
  self-contained; Tools/app.py's _resolve_data_csv() already probes for it.
- Confirm total bundle size &lt; 80 MiB.</div>
</div>

<!-- ============================================================= -->
<h2 id="validation">4. Validation</h2>

<h3>Automated row-count checks</h3>
<p>
  <code>Tools/verify_outputs.py</code> is a pure-pandas sanity checker that prints row and
  distinct-key counts across every stage. It confirms the pipeline is lossless:
</p>
<pre><code>python Tools/verify_outputs.py

# Expected (approximate):
# all_rows (hit-level full visit path)          ≈ raw_user_journeys.csv row count
# last_rows (base_user_journeys.csv)            ≈ 200,454 visits
# unique_visits_in_raw                          ≈ 200,454
# compressed row count                          = base row count
# agg unique_visits column sum                  = base row count
# Rpt_Funnel_DeepDive row count                 ≈ 99,934 (PDP-touching visits)</code></pre>

<h3>Spot-checks that caught real bugs</h3>
<table>
  <thead><tr><th>Check</th><th>What it caught</th></tr></thead>
  <tbody>
    <tr>
      <td>Did every <code>Is_Checkout_Confirmation=Y</code> row get <code>Is_frustrated=N</code>?</td>
      <td>Confirmed completer pre-labeling short-circuited the LLM call (saves ~40% of budget).</td>
    </tr>
    <tr>
      <td>Does at least one row exist per non-empty reason in the enum?</td>
      <td>Verified the LLM was actually using the full label set, not collapsing everything to "indecision".</td>
    </tr>
    <tr>
      <td>Does the DataTable native filter <code>&gt;10</code> actually filter <code>visit_length</code>?</td>
      <td>Found a numeric-type issue: the column was read as int64 but serialized as a numpy scalar; fix applied in two layers (explicit <code>int(...)</code> coercion + <code>{"format": {"specifier": "d"}}</code>).</td>
    </tr>
    <tr>
      <td>Does the header caption reflect the filtered visit count, not the cap?</td>
      <td>Removed <code>TABLE_ROW_CAP=500</code> and rewrote the caption to show the actual filtered total and unique-visitor count.</td>
    </tr>
    <tr>
      <td>Does the frustration-reasons pie have a readable total?</td>
      <td>Added a donut-hole center annotation ("<em>N</em> frustrated visits") via <code>fig.update_layout(annotations=[...])</code>.</td>
    </tr>
    <tr>
      <td>Do the stacked bars in the drop-off driver chart show the total above?</td>
      <td>Plotly's per-trace <code>text</code> only labels the top segment correctly; switched to layout-level <code>add_annotation</code> with <code>yshift=12</code> and <code>range=[0, max_y * 1.18]</code> for headroom.</td>
    </tr>
  </tbody>
</table>

<h3>Graceful-degradation tests</h3>
<div class="callout warn">
  <strong>Offline reruns must work.</strong> After the first successful run, delete
  <code>ANTHROPIC_API_KEY</code> from the environment and re-run Stages 2–4. The pipeline
  should finish without errors, reusing <code>page_mapping.csv</code> and
  <code>frustration_cache.csv</code>. Any path not yet in the cache is marked
  <code>Unknown</code> with a loud warning — not a hard failure.
</div>

<h3>Deploy smoke test</h3>
<ol>
  <li>Open the deployed URL (see §5).</li>
  <li>Confirm the header shows <code>99,934</code> PDP-touching visits.</li>
  <li>Toggle <code>Is_cart = Y</code>, verify the KPI row, funnel, pie, and bar chart all update within one round-trip.</li>
  <li>Type <code>&gt;10</code> into the <code>visit_length</code> column filter and confirm the table shrinks.</li>
  <li>Select <code>payment_friction</code> from the reason filter and confirm the caption updates to the filtered count.</li>
</ol>

<!-- ============================================================= -->
<h2 id="result">5. Result Walkthrough</h2>

<p>
  The final dashboard is a single Dash app backed by one CSV
  (<code>Rpt_Funnel_DeepDive.csv</code>), deployed on Plotly Cloud:
</p>
<div class="callout good">
  <strong>Live URL:</strong>
  <a href="https://767c6beb-95a8-46a6-892f-c76ce480b289.plotly.app/" target="_blank" rel="noopener">
    https://767c6beb-95a8-46a6-892f-c76ce480b289.plotly.app/
  </a>
</div>

<h3>Scale</h3>
<div>
  <div class="metric"><span class="k">Raw input size</span><span class="v">~90&nbsp;MB</span></div>
  <div class="metric"><span class="k">Total visits</span><span class="v">200,454</span></div>
  <div class="metric"><span class="k">PDP-touching visits</span><span class="v">99,934</span></div>
  <div class="metric"><span class="k">Completers (Confirmation)</span><span class="v">3,108</span></div>
  <div class="metric"><span class="k">Unique drop-out compressed paths</span><span class="v">~5,621</span></div>
  <div class="metric"><span class="k">One-time Opus cost</span><span class="v">~$5</span></div>
  <div class="metric"><span class="k">Rerun cost (cached)</span><span class="v">$0</span></div>
</div>

<h3>What the user sees on the dashboard</h3>
<ul>
  <li>
    <strong>Header narrative.</strong> A one-line caption that reflects the currently filtered
    cohort (e.g. "Exploring 99,934 PDP-touching visits based on July 2017 GMS data"), recomputed
    from the filter state on every callback.
  </li>
  <li>
    <strong>Filter card.</strong>
    <ul>
      <li>Pattern-matching dropdowns (<em>Any / Y / N</em>) for each <code>Is_*</code> flag.</li>
      <li>An AND/OR radio to combine the flag filters.</li>
      <li>A multi-select dropdown over the 7 frustration reasons (always OR within themselves).</li>
      <li>A <code>visit_length</code> range slider (1 → max).</li>
    </ul>
  </li>
  <li>
    <strong>KPI row (6 cards):</strong> matching visits, unique visitors, completion visits,
    frustration visits, completion rate, frustration rate. Rates are recomputed from the current
    filtered set.
  </li>
  <li>
    <strong>Chart 1 — Plotly Funnel</strong> over Cart → Your Info → Payment → Review → Confirmation
    using <code>sum(Is_&lt;step&gt;==Y)</code>. Shows where the cohort drops out.
  </li>
  <li>
    <strong>Chart 2 — Frustration-reasons donut</strong> with the total count of frustrated visits
    annotated in the center of the hole. Each slice is a reason from the 7-label enum.
  </li>
  <li>
    <strong>Chart 3 — "Drop-off drivers per step"</strong> stacked bar. Each funnel step has two
    side-by-side bars (committed vs not-committed), and the not-committed bar is stacked by
    frustration reason. A layout-level annotation sits above each bar showing the total. Axis
    headroom (<code>range=[0, max_y * 1.18]</code>) keeps the labels from clipping.
  </li>
  <li>
    <strong>Data table</strong> with native column filters (including numeric compare on
    <code>visit_length</code>), no row cap, sort, and row tinting:
    <span style="background:#fff4f4; padding: 0 6px; border-radius:3px; border:1px solid #f2c0c0;">frustrated pink</span>
    &nbsp;and&nbsp;
    <span style="background:#f2faf2; padding: 0 6px; border-radius:3px; border:1px solid #cde8cc;">completer green</span>.
  </li>
</ul>

<h3>What the artifact pile looks like at the end</h3>
<table>
  <thead>
    <tr><th>File</th><th>Produced by</th><th>Purpose</th></tr>
  </thead>
  <tbody>
    <tr><td><code>Data/raw_user_journeys.csv</code></td><td>external GMS export</td><td>hit-level input</td></tr>
    <tr><td><code>Data/page_mapping.csv</code></td><td>Stage 1 (LLM)</td><td>cached pageTitle → pageSummary</td></tr>
    <tr><td><code>Data/base_user_journeys_full_visit_path.csv</code></td><td>Stage 2</td><td>hit-level + user_path</td></tr>
    <tr><td><code>Data/base_user_journeys.csv</code></td><td>Stage 2</td><td>one row per visit</td></tr>
    <tr><td><code>Data/base_user_journeys_compressed.csv</code></td><td>Stage 3a</td><td>per-visit + compressed path</td></tr>
    <tr><td><code>Data/agg_user_journeys_compressed_rpt.csv</code></td><td>Stage 3a</td><td>aggregate by compressed path</td></tr>
    <tr><td><code>Data/Rpt_Funnel_DeepDive.csv</code></td><td>Stage 3b</td><td>PDP-touching visits + Is_* flags + frustration columns — dashboard input</td></tr>
    <tr><td><code>Data/frustration_cache.csv</code></td><td>Stage 3b (LLM)</td><td>cached frustration labels by compressed path</td></tr>
    <tr><td><code>app.py</code> (root shim)</td><td>deploy step</td><td>Plotly Cloud entry point</td></tr>
    <tr><td><code>Tools/app.py</code></td><td>Stage 4</td><td>real Dash app</td></tr>
    <tr><td><code>requirements.txt</code></td><td>deploy step</td><td>dash, plotly, pandas, gunicorn</td></tr>
  </tbody>
</table>

<h3>What you can answer on the live dashboard in &lt; 30 seconds</h3>
<ul>
  <li><em>What fraction of PDP-touching visits actually complete?</em> — glance at the KPI row.</li>
  <li><em>Which funnel step loses the most people?</em> — look at Chart 1, cross-check Chart 3's bars.</li>
  <li><em>Of the drop-outs at the Payment step, what share look frustrated and why?</em> — filter <code>Is_Payment_Method=Y</code>, read the pie and the stacked bar.</li>
  <li><em>Are long-visit paths mostly indecision or technical issues?</em> — set <code>visit_length &gt; 20</code> on the slider, check the reason breakdown.</li>
  <li><em>Do the frustrated paths look realistic?</em> — scroll the DataTable's pink rows and read <code>user_path_Compressed</code>.</li>
</ul>

<footer>
  UserJourneyDashPlotly — exploratory project on a Google Merchandise Store export. Built with
  Dash, Plotly, pandas, pydantic, and Claude Code. See <code>CLAUDE.md</code> for repo conventions,
  <code>README.md</code> for the quickstart, and <code>Prompts/tool_prompts.md</code> for a
  self-contained rebuild guide.
</footer>

</body>
</html>

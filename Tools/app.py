import os

import dash
import pandas as pd
from dash import ALL, Input, Output, State, ctx, dash_table, dcc, html
import plotly.express as px
import plotly.graph_objects as go

APP_TITLE = "Marketing & Growth: Funnel Segmentation Dashboard - Google Merch Store"
SUNBURST_LEVELS = 5
SUNBURST_TOP_PREFIXES = 200


def _resolve_data_csv() -> str:
    env_path = os.environ.get("FUNNEL_DATA_CSV")
    if env_path:
        return env_path
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "Rpt_Funnel_DeepDive.csv"),
        os.path.join(here, "..", "Rpt_Funnel_DeepDive.csv"),
        os.path.join(here, "..", "Data", "Rpt_Funnel_DeepDive.csv"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return os.path.abspath(p)
    raise FileNotFoundError(
        "Rpt_Funnel_DeepDive.csv not found. Tried:\n  "
        + "\n  ".join(os.path.abspath(p) for p in candidates)
        + "\nSet FUNNEL_DATA_CSV to override."
    )


DATA_CSV = _resolve_data_csv()

FLAG_COLS = [
    "Is_cart",
    "Is_Checkout_Your_Information",
    "Is_Payment_Method",
    "Is_Checkout_Review",
    "Is_Checkout_Confirmation",
    "Is_Sales",
    "Is_Troubles",
    "Is_Login",
    "Is_Search",
    "Is_ErrorPage",
    "Is_Wishlist",
    "Is_frustrated",
]

REASON_ENUM = [
    "payment_friction",
    "form_friction",
    "price_shock",
    "indecision",
    "technical_issue",
    "search_struggle",
    "account_blocked",
]

REASON_PALETTE = {
    "payment_friction": "#E15759",
    "form_friction": "#F28E2B",
    "price_shock": "#B07AA1",
    "indecision": "#EDC948",
    "technical_issue": "#4E79A7",
    "search_struggle": "#76B7B2",
    "account_blocked": "#9C755F",
}

FUNNEL_STEPS = [
    ("Cart", "Is_cart"),
    ("Your Info", "Is_Checkout_Your_Information"),
    ("Payment", "Is_Payment_Method"),
    ("Review", "Is_Checkout_Review"),
    ("Confirmation", "Is_Checkout_Confirmation"),
]

STEP_PROGRESSION = [
    ("Cart", "Is_cart", "Is_Checkout_Your_Information"),
    ("Your Info", "Is_Checkout_Your_Information", "Is_Payment_Method"),
    ("Payment", "Is_Payment_Method", "Is_Checkout_Review"),
    ("Review", "Is_Checkout_Review", "Is_Checkout_Confirmation"),
    ("Confirmation", "Is_Checkout_Confirmation", None),
]

TABLE_COLS = [
    "fullVisitorId",
    "visitId",
    "visit_length",
    "user_path_Compressed",
    "Is_cart",
    "Is_Checkout_Your_Information",
    "Is_Payment_Method",
    "Is_Checkout_Review",
    "Is_Checkout_Confirmation",
    "Is_frustrated",
    "frustrated_reasons",
]

TABLE_ROW_CAP = 500

STMT_FIELD_OPTIONS = (
    [{"label": c, "value": c} for c in FLAG_COLS]
    + [
        {"label": "frustrated_reasons", "value": "frustrated_reasons"},
        {"label": "visit_length", "value": "visit_length"},
        {"label": "user_path_Compressed", "value": "user_path_Compressed"},
    ]
)

STMT_OP_OPTIONS = [
    {"label": "=", "value": "="},
    {"label": "≠", "value": "!="},
    {"label": "contains", "value": "contains"},
    {"label": ">", "value": ">"},
    {"label": "<", "value": "<"},
]

STMT_COMBINE_OPTIONS = [
    {"label": "AND", "value": "AND"},
    {"label": "OR", "value": "OR"},
]

FIELD_MEANINGS = {
    "Is_cart": "reached the Shopping Cart page",
    "Is_Checkout_Your_Information": "reached the Checkout 'Your Information' form",
    "Is_Payment_Method": "reached the Payment Method step",
    "Is_Checkout_Review": "reached the Checkout Review step",
    "Is_Checkout_Confirmation": "completed checkout (Confirmation page)",
    "Is_Sales": "browsed a sale / clearance page",
    "Is_Troubles": "visited the FAQ / troubleshooting page",
    "Is_Login": "visited a Log In page",
    "Is_Search": "used site search",
    "Is_ErrorPage": "hit an error / unavailable page",
    "Is_Wishlist": "touched the Wishlist",
    "Is_frustrated": "showed at least one frustration signal",
    "frustrated_reasons": "frustration reasons (pipe-joined list)",
    "visit_length": "number of uncompressed path segments in the visit",
    "user_path_Compressed": "compressed user journey path (run-length encoded)",
}

REASON_MEANINGS = {
    "payment_friction": "repeated payment-method visits or abandon at/after payment",
    "form_friction": "bouncing between cart / your-info / review forms",
    "price_shock": "viewed cart or your-info then exited without continuing",
    "indecision": "many PDPs, repeated cart, long browse, no purchase",
    "technical_issue": "hit an error or unavailable page",
    "search_struggle": "repeated site search with no PDP engagement",
    "account_blocked": "repeated login / register without funnel progress",
}


df = pd.read_csv(DATA_CSV, dtype="string", low_memory=False)
df["visit_length"] = (
    pd.to_numeric(df["visit_length"], errors="coerce").fillna(0).astype(int)
)


app = dash.Dash(__name__, title=APP_TITLE)
server = app.server  # exposed for gunicorn / Plotly server deployment


def _statement_row(idx: int) -> html.Div:
    return html.Div(
        id={"type": "stmt-row", "idx": idx},
        style={
            "display": "flex",
            "gap": "8px",
            "alignItems": "center",
            "marginTop": "8px",
        },
        children=[
            dcc.Dropdown(
                id={"type": "stmt-combine", "idx": idx},
                options=STMT_COMBINE_OPTIONS,
                value="AND",
                clearable=False,
                style={"width": "80px", "fontSize": "12px"},
            ),
            dcc.Dropdown(
                id={"type": "stmt-field", "idx": idx},
                options=STMT_FIELD_OPTIONS,
                value=FLAG_COLS[0],
                clearable=False,
                style={"width": "240px", "fontSize": "12px"},
            ),
            dcc.Dropdown(
                id={"type": "stmt-op", "idx": idx},
                options=STMT_OP_OPTIONS,
                value="=",
                clearable=False,
                style={"width": "110px", "fontSize": "12px"},
            ),
            dcc.Input(
                id={"type": "stmt-value", "idx": idx},
                type="text",
                placeholder="value (e.g., Y, payment_friction, 50)",
                debounce=True,
                style={
                    "flex": "1",
                    "minWidth": "180px",
                    "fontSize": "12px",
                    "padding": "6px 8px",
                    "border": "1px solid #ccc",
                    "borderRadius": "4px",
                },
            ),
            html.Button(
                "×",
                id={"type": "stmt-remove", "idx": idx},
                n_clicks=0,
                title="Remove statement",
                style={
                    "width": "32px",
                    "height": "32px",
                    "border": "1px solid #ccc",
                    "borderRadius": "4px",
                    "background": "#fff",
                    "cursor": "pointer",
                    "fontSize": "16px",
                    "lineHeight": "1",
                },
            ),
        ],
    )


def _kpi_card(label: str, value: str, tint: str) -> html.Div:
    return html.Div(
        style={
            "flex": "1",
            "padding": "12px 16px",
            "borderRadius": "6px",
            "background": "#ffffff",
            "border": "1px solid #e6e8eb",
            "borderLeft": f"4px solid {tint}",
            "minWidth": "140px",
        },
        children=[
            html.Div(label, style={"fontSize": "12px", "color": "#666"}),
            html.Div(
                value,
                style={"fontSize": "22px", "fontWeight": "700", "color": "#222"},
            ),
        ],
    )


app.layout = html.Div(
    style={
        "fontFamily": "Arial, sans-serif",
        "maxWidth": "1400px",
        "margin": "0 auto",
        "padding": "20px",
    },
    children=[
        html.H1(APP_TITLE, style={"textAlign": "center", "color": "#333"}),
        html.P(
            f"Exploring {len(df):,} Product Detail Page (PDP) -touching visits based on "
            f"Google Merch Store July 2017 Data",
            style={"textAlign": "center", "color": "#666"},
        ),
        html.Div(
            style={
                "border": "1px solid #eee",
                "borderRadius": "8px",
                "padding": "16px",
                "background": "#fafbfc",
            },
            children=[
                html.Div(
                    style={
                        "display": "flex",
                        "justifyContent": "space-between",
                        "alignItems": "center",
                    },
                    children=[
                        html.H3("Filter statements", style={"margin": "0"}),
                        html.Button(
                            "+ Add statement",
                            id="add-statement-btn",
                            n_clicks=0,
                            style={
                                "border": "1px solid #4C78A8",
                                "borderRadius": "4px",
                                "background": "#4C78A8",
                                "color": "#fff",
                                "padding": "6px 12px",
                                "fontSize": "12px",
                                "cursor": "pointer",
                            },
                        ),
                    ],
                ),
                html.Div(
                    style={"fontSize": "11px", "color": "#888", "marginTop": "4px"},
                    children=(
                        "Each row is one condition: [AND/OR] · [field] · [= / ≠ / "
                        "contains / > / <] · [value]. Rows are evaluated left-to-right. "
                        "The AND/OR on the first row is ignored. Press Enter in the "
                        "value box to apply."
                    ),
                ),
                dcc.Store(id="stmt-ids-store", data=[0]),
                html.Div(
                    id="statements-container",
                    children=[_statement_row(0)],
                ),
            ],
        ),
        html.Div(
            id="narrative-block",
            style={
                "margin": "20px 0 0 0",
                "padding": "14px 18px",
                "background": "#f5f8fb",
                "borderLeft": "4px solid #4C78A8",
                "borderRadius": "4px",
                "fontSize": "13px",
                "color": "#333",
                "lineHeight": "1.5",
            },
            children=[dcc.Markdown(id="narrative", children="")],
        ),
        html.Div(
            id="kpi-row",
            style={
                "display": "flex",
                "gap": "16px",
                "margin": "16px 0",
                "flexWrap": "wrap",
            },
        ),
        html.Div(
            style={"display": "flex", "gap": "20px", "flexWrap": "wrap"},
            children=[
                dcc.Graph(
                    id="funnel-fig",
                    style={"flex": "1 1 420px", "minWidth": "380px"},
                ),
                dcc.Graph(
                    id="reasons-fig",
                    style={"flex": "1 1 420px", "minWidth": "380px"},
                ),
                dcc.Graph(
                    id="step-driver-fig",
                    style={"flex": "1 1 520px", "minWidth": "420px"},
                ),
            ],
        ),
        dcc.Graph(
            id="sunburst-fig",
            style={"marginTop": "20px", "height": "560px"},
        ),
        html.H3(
            "Matching visits",
            style={"marginTop": "24px", "color": "#333"},
        ),
        html.Div(
            id="table-caption",
            style={"fontSize": "12px", "color": "#666", "marginBottom": "6px"},
        ),
        html.Div(
            "Tip: type in the row just below each column header and press Enter to "
            "filter the visible rows. Examples: `Y`, `contains payment`, `> 20`, "
            "`!= N`. Clear a cell and press Enter to remove that filter.",
            style={
                "fontSize": "11px",
                "color": "#888",
                "marginBottom": "6px",
                "fontStyle": "italic",
            },
        ),
        dash_table.DataTable(
            id="visits-table",
            columns=[
                {
                    "name": c,
                    "id": c,
                    "type": "numeric" if c == "visit_length" else "text",
                    **(
                        {"format": {"specifier": "d"}}
                        if c == "visit_length"
                        else {}
                    ),
                }
                for c in TABLE_COLS
            ],
            page_size=20,
            sort_action="native",
            filter_action="native",
            filter_options={"case": "insensitive", "placeholder_text": "filter…"},
            style_table={"overflowX": "auto"},
            style_cell={
                "fontFamily": "Arial",
                "fontSize": "12px",
                "padding": "6px",
                "textAlign": "left",
                "maxWidth": "360px",
                "whiteSpace": "normal",
                "height": "auto",
            },
            style_header={"backgroundColor": "#f0f2f5", "fontWeight": "bold"},
            style_filter={
                "backgroundColor": "#fff9e6",
                "borderBottom": "2px solid #4C78A8",
            },
            style_filter_conditional=[
                {
                    "if": {"column_id": c},
                    "fontStyle": "italic",
                    "color": "#333",
                }
                for c in TABLE_COLS
            ],
            style_data_conditional=[
                {
                    "if": {"filter_query": "{Is_frustrated} = 'Y'"},
                    "backgroundColor": "#fff4f4",
                },
                {
                    "if": {"filter_query": "{Is_Checkout_Confirmation} = 'Y'"},
                    "backgroundColor": "#f2faf2",
                },
            ],
        ),
    ],
)


def _statement_mask(field: str, op: str, value: str) -> pd.Series | None:
    if not field or op is None or value is None or value == "":
        return None
    if field == "visit_length":
        try:
            num = float(value)
        except ValueError:
            return None
        series = df["visit_length"]
        if op == "=":
            return series == num
        if op == "!=":
            return series != num
        if op == ">":
            return series > num
        if op == "<":
            return series < num
        if op == "contains":
            return series.astype("string").str.contains(
                str(value), regex=False, na=False
            )
        return None
    if field not in df.columns:
        return None
    series = df[field].fillna("")
    if op == "=":
        return series == value
    if op == "!=":
        return series != value
    if op == "contains":
        return series.str.contains(value, regex=False, na=False, case=False)
    if op in (">", "<"):
        try:
            num = float(value)
        except ValueError:
            return None
        numeric = pd.to_numeric(series, errors="coerce")
        return (numeric > num) if op == ">" else (numeric < num)
    return None


def _statements_mask(
    fields: list[str],
    ops: list[str],
    values: list[str],
    combines: list[str],
) -> pd.Series:
    mask: pd.Series | None = None
    for f, o, v, c in zip(fields, ops, values, combines):
        sub = _statement_mask(f, o, v)
        if sub is None:
            continue
        if mask is None:
            mask = sub
        elif c == "OR":
            mask = mask | sub
        else:
            mask = mask & sub
    if mask is None:
        return pd.Series(True, index=df.index)
    return mask


def _apply_filters(
    stmt_fields: list[str],
    stmt_ops: list[str],
    stmt_values: list[str],
    stmt_combines: list[str],
) -> pd.DataFrame:
    return df[_statements_mask(stmt_fields, stmt_ops, stmt_values, stmt_combines)]


def _primary_reason(s: str) -> str:
    if not s:
        return ""
    return s.split("|")[0]


def _reason_counts(filtered: pd.DataFrame) -> dict[str, int]:
    counts = {r: 0 for r in REASON_ENUM}
    for s in filtered["frustrated_reasons"].fillna(""):
        if not s:
            continue
        for r in s.split("|"):
            if r in counts:
                counts[r] += 1
    return counts


def _build_reasons_pie(filtered: pd.DataFrame) -> go.Figure:
    if filtered.empty:
        return _empty_fig("Frustration reasons")
    counts = _reason_counts(filtered)
    items = [(k, v) for k, v in counts.items() if v > 0]
    items.sort(key=lambda kv: -kv[1])
    if not items:
        return _empty_fig("Frustration reasons (none flagged)")
    labels = [k for k, _ in items]
    values = [v for _, v in items]
    colors = [REASON_PALETTE.get(k, "#999") for k in labels]
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.35,
            marker=dict(colors=colors),
            textinfo="label+value+percent",
            texttemplate="%{label}<br>%{value:,} (%{percent})",
            textposition="outside",
            hovertemplate="%{label}<br>%{value:,} visits<br>%{percent}<extra></extra>",
            sort=False,
        )
    )
    total_flagged = sum(values)
    fig.update_layout(
        title="Frustration reasons (share of flagged visits)",
        margin=dict(t=60, l=20, r=20, b=40),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        showlegend=False,
        annotations=[
            dict(
                text=f"<b>{total_flagged:,}</b><br>frustrated<br>visits",
                x=0.5,
                y=0.5,
                font=dict(size=14, color="#333"),
                showarrow=False,
            )
        ],
    )
    return fig


def _build_step_driver_chart(filtered: pd.DataFrame) -> go.Figure:
    if filtered.empty:
        return _empty_fig("Drop-off drivers per funnel step")

    step_labels: list[str] = []
    committed_counts: list[int] = []
    total_at_step_counts: list[int] = []
    not_frustrated_counts: list[int] = []
    reason_breakdown: dict[str, list[int]] = {r: [] for r in REASON_ENUM}

    for label, this_flag, next_flag in STEP_PROGRESSION:
        at_step = filtered[filtered[this_flag] == "Y"]
        step_labels.append(label)
        total_at_step_counts.append(len(at_step))
        if next_flag is not None:
            committed = int((at_step[next_flag] == "Y").sum())
        else:
            committed = len(at_step)
        committed_counts.append(committed)
        primary = at_step["frustrated_reasons"].fillna("").apply(_primary_reason)
        not_frustrated_counts.append(int((primary == "").sum()))
        for r in REASON_ENUM:
            reason_breakdown[r].append(int((primary == r).sum()))

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="committed to next step",
            x=step_labels,
            y=committed_counts,
            offsetgroup="committed",
            marker=dict(color="#59A14F"),
            text=[f"{c:,}" for c in committed_counts],
            textposition="outside",
            textfont=dict(size=11, color="#333"),
            cliponaxis=False,
            hovertemplate="%{x} — committed<br>%{y:,} visits<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            name="not frustrated",
            x=step_labels,
            y=not_frustrated_counts,
            offsetgroup="total",
            marker=dict(color="#c9d6df"),
            hovertemplate="%{x} — not frustrated<br>%{y:,} visits<extra></extra>",
        )
    )
    for r in REASON_ENUM:
        fig.add_trace(
            go.Bar(
                name=r,
                x=step_labels,
                y=reason_breakdown[r],
                offsetgroup="total",
                marker=dict(color=REASON_PALETTE[r]),
                hovertemplate="%{x} — "
                + r
                + "<br>%{y:,} visits<extra></extra>",
            )
        )
    fig.update_layout(
        barmode="stack",
        title=(
            "Drop-off drivers per step — left bar: committed to next step · "
            "right bar: total at step (stacked by primary frustration reason)"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.45,
            xanchor="left",
            x=0,
            font=dict(size=10),
        ),
        margin=dict(t=80, l=40, r=20, b=120),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        yaxis_title="visits",
    )
    max_y = max([*committed_counts, *total_at_step_counts, 1])
    fig.update_yaxes(range=[0, max_y * 1.18])
    for label, tot in zip(step_labels, total_at_step_counts):
        fig.add_annotation(
            x=label,
            y=tot,
            text=f"<b>{tot:,}</b>",
            showarrow=False,
            yshift=12,
            xshift=16,
            font=dict(size=11, color="#333"),
        )
    return fig


def _build_sunburst(filtered: pd.DataFrame) -> go.Figure:
    if filtered.empty:
        return _empty_fig("Top path prefixes")
    paths = filtered["user_path_Compressed_no_Counts"].fillna("")
    split = paths.str.split("~", n=SUNBURST_LEVELS - 1, expand=True)
    for i in range(split.shape[1], SUNBURST_LEVELS):
        split[i] = None
    level_cols = [f"L{i + 1}" for i in range(SUNBURST_LEVELS)]
    split.columns = level_cols
    split = split.fillna("(end)")
    agg = (
        split.groupby(level_cols, dropna=False)
        .size()
        .reset_index(name="visits")
        .nlargest(SUNBURST_TOP_PREFIXES, "visits")
    )
    fig = px.sunburst(
        agg,
        path=level_cols,
        values="visits",
        color="visits",
        color_continuous_scale="Blues",
    )
    fig.update_layout(
        title=(
            f"Top {min(SUNBURST_TOP_PREFIXES, len(agg))} path prefixes "
            f"(first {SUNBURST_LEVELS} segments of compressed journey)"
        ),
        margin=dict(t=60, l=10, r=10, b=10),
        paper_bgcolor="#ffffff",
    )
    return fig


def _describe_statement(
    field: str,
    op: str,
    value: str,
    combine: str,
    is_first: bool,
) -> str | None:
    if not field or not op or value is None or value == "":
        return None
    meaning = FIELD_MEANINGS.get(field, field)
    if field in FLAG_COLS:
        v_upper = str(value).upper()
        if op == "=" and v_upper == "Y":
            phrase = f"{meaning}"
        elif op == "=" and v_upper == "N":
            phrase = f"did NOT {meaning}"
        elif op == "!=" and v_upper == "Y":
            phrase = f"did NOT {meaning}"
        elif op == "!=" and v_upper == "N":
            phrase = f"{meaning}"
        else:
            phrase = f"{field} {op} {value}"
    elif field == "visit_length":
        if op == "=":
            phrase = f"visit length equals {value} segments"
        elif op == "!=":
            phrase = f"visit length is not {value} segments"
        elif op == ">":
            phrase = f"visit length greater than {value} segments"
        elif op == "<":
            phrase = f"visit length less than {value} segments"
        else:
            phrase = f"visit length {op} {value}"
    elif field == "frustrated_reasons":
        if op == "contains":
            phrase = f"frustration reason includes '{value}'"
        elif op == "=":
            phrase = f"frustration reasons equals exactly '{value}'"
        elif op == "!=":
            phrase = f"frustration reasons NOT equal to '{value}'"
        else:
            phrase = f"frustrated_reasons {op} {value}"
    elif field == "user_path_Compressed":
        if op == "contains":
            phrase = f"journey path includes '{value}'"
        else:
            phrase = f"journey path {op} '{value}'"
    else:
        phrase = f"{field} {op} {value}"

    prefix = "" if is_first else f"**{combine}** "
    return f"- {prefix}{phrase}"


def _build_narrative(
    total: int,
    visitors: int,
    completed: int,
    frustrated: int,
    stmt_fields: list[str],
    stmt_ops: list[str],
    stmt_values: list[str],
    stmt_combines: list[str],
    reason_counts_map: dict[str, int],
) -> str:
    stmt_lines: list[str] = []
    any_stmt = False
    for i, (f, o, v, c) in enumerate(
        zip(stmt_fields, stmt_ops, stmt_values, stmt_combines)
    ):
        line = _describe_statement(f, o, v, c, is_first=not any_stmt)
        if line:
            stmt_lines.append(line)
            any_stmt = True

    conditions_block = (
        "\n".join(stmt_lines)
        if stmt_lines
        else "- *(no filter conditions applied — showing all PDP-touching visits)*"
    )

    if not total:
        return (
            "**Conditions you selected**\n"
            f"{conditions_block}\n\n"
            "**Outcome** — no visits match these conditions. Relax a condition "
            "(flip AND→OR, widen a range, or remove a row) to see data."
        )

    comp_rate = completed / total * 100
    frust_rate = frustrated / total * 100

    top_reasons = sorted(
        [(r, c) for r, c in reason_counts_map.items() if c > 0],
        key=lambda kv: -kv[1],
    )[:3]
    if top_reasons:
        top_reason_str = ", ".join(
            f"**{r}** ({c:,} visits — {REASON_MEANINGS[r]})" for r, c in top_reasons
        )
    else:
        top_reason_str = "no frustration signals flagged in this selection"

    if not stmt_lines:
        selection_meaning = (
            "You're looking at every PDP-touching visit in the dataset — the "
            "baseline population for any funnel analysis."
        )
    else:
        selection_meaning = (
            "Together, these conditions describe a specific visitor cohort. Every "
            "number below reflects only visits that satisfy all of the above "
            "(taking the AND/OR combiners into account)."
        )

    if comp_rate >= 10:
        outcome_read = (
            f"**{comp_rate:.1f}%** of these visits completed checkout — a relatively "
            "healthy conversion rate for this cohort."
        )
    elif comp_rate >= 2:
        outcome_read = (
            f"Only **{comp_rate:.1f}%** of these visits completed checkout. Most "
            "visitors matching your conditions dropped off before confirmation."
        )
    else:
        outcome_read = (
            f"**{comp_rate:.1f}%** of these visits completed checkout — this cohort "
            "is effectively non-converting. The right-hand chart shows where they "
            "stopped."
        )

    frustration_read = (
        f"{frust_rate:.1f}% of the cohort shows at least one frustration signal."
    )

    return (
        "**Conditions you selected**\n"
        f"{conditions_block}\n\n"
        f"**What this cohort means** — {selection_meaning} Cohort size: "
        f"**{total:,} visits** from **{visitors:,} unique visitors**.\n\n"
        f"**Outcome** — {outcome_read} {frustration_read}\n\n"
        "**How to read this view** — The funnel on the left shows how this "
        "cohort progressed from PDP → Cart → Your Info → Payment → Review → "
        "Confirmation. The pie chart breaks down the *why* behind frustration "
        f"for this cohort — top drivers: {top_reason_str}. The right-hand "
        "bar chart compares, at each funnel step, **visits that committed to the "
        "next step** (green) vs **total visits at that step** stacked by primary "
        "frustration reason — the tallest colored segment is where you'd focus "
        "a fix first. The sunburst below shows the dominant path shapes taken "
        "by this cohort."
    )


def _empty_fig(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=title,
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        margin=dict(t=50, l=30, r=30, b=30),
        annotations=[
            dict(
                text="No matching visits",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=14, color="#888"),
            )
        ],
    )
    return fig


@app.callback(
    Output("visits-table", "data"),
    Output("table-caption", "children"),
    Output("kpi-row", "children"),
    Output("narrative", "children"),
    Output("funnel-fig", "figure"),
    Output("reasons-fig", "figure"),
    Output("step-driver-fig", "figure"),
    Output("sunburst-fig", "figure"),
    Input({"type": "stmt-field", "idx": ALL}, "value"),
    Input({"type": "stmt-op", "idx": ALL}, "value"),
    Input({"type": "stmt-value", "idx": ALL}, "value"),
    Input({"type": "stmt-combine", "idx": ALL}, "value"),
)
def _update(stmt_fields, stmt_ops, stmt_values, stmt_combines):
    stmt_fields = stmt_fields or []
    stmt_ops = stmt_ops or []
    stmt_values = stmt_values or []
    stmt_combines = stmt_combines or []

    filtered = _apply_filters(stmt_fields, stmt_ops, stmt_values, stmt_combines)

    total = len(filtered)
    visitors = filtered["fullVisitorId"].nunique() if total else 0
    completed = (
        int((filtered["Is_Checkout_Confirmation"] == "Y").sum()) if total else 0
    )
    frustrated = int((filtered["Is_frustrated"] == "Y").sum()) if total else 0
    comp_rate = f"{completed / total * 100:.1f}%" if total else "—"
    frust_rate = f"{frustrated / total * 100:.1f}%" if total else "—"

    kpis = [
        _kpi_card("Matching visits", f"{total:,}", "#4C78A8"),
        _kpi_card("Unique visitors", f"{visitors:,}", "#59A14F"),
        _kpi_card("Completion visits", f"{completed:,}", "#2E7D32"),
        _kpi_card("Frustration visits", f"{frustrated:,}", "#B71C1C"),
        _kpi_card("Completion rate", comp_rate, "#F28E2B"),
        _kpi_card("Frustration rate", frust_rate, "#E15759"),
    ]

    if total:
        funnel_labels = ["PDP Visits"] + [label for label, _ in FUNNEL_STEPS]
        funnel_counts = [total] + [
            int((filtered[col] == "Y").sum()) for _, col in FUNNEL_STEPS
        ]
        funnel_fig = go.Figure(
            go.Funnel(
                x=funnel_counts,
                y=funnel_labels,
                textinfo="value+percent initial",
                marker={"color": "#4C78A8"},
            )
        )
        funnel_fig.update_layout(
            title="Checkout funnel (share of PDP visits)",
            margin=dict(t=50, l=30, r=30, b=30),
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
        )
    else:
        funnel_fig = _empty_fig("Checkout funnel")

    reasons_fig = _build_reasons_pie(filtered)
    step_driver_fig = _build_step_driver_chart(filtered)
    sunburst_fig = _build_sunburst(filtered)

    reason_counts_map = _reason_counts(filtered) if total else {r: 0 for r in REASON_ENUM}
    narrative = _build_narrative(
        total=total,
        visitors=visitors,
        completed=completed,
        frustrated=frustrated,
        stmt_fields=stmt_fields,
        stmt_ops=stmt_ops,
        stmt_values=stmt_values,
        stmt_combines=stmt_combines,
        reason_counts_map=reason_counts_map,
    )

    table_df = filtered[TABLE_COLS].copy()
    table_df["visit_length"] = table_df["visit_length"].astype(int)
    table_rows = table_df.to_dict("records")
    for row in table_rows:
        row["visit_length"] = int(row["visit_length"])
    if total:
        caption = (
            f"Showing all {total:,} visits matching your filter conditions "
            f"(from {visitors:,} unique visitors). Use the row below each column "
            f"header to filter further."
        )
    else:
        caption = "No matching visits"

    return (
        table_rows,
        caption,
        kpis,
        narrative,
        funnel_fig,
        reasons_fig,
        step_driver_fig,
        sunburst_fig,
    )


@app.callback(
    Output("statements-container", "children"),
    Output("stmt-ids-store", "data"),
    Input("add-statement-btn", "n_clicks"),
    Input({"type": "stmt-remove", "idx": ALL}, "n_clicks"),
    State("stmt-ids-store", "data"),
    prevent_initial_call=True,
)
def _manage_statements(add_clicks, remove_clicks, ids):
    trigger = ctx.triggered_id
    if trigger is None:
        return [_statement_row(i) for i in ids], ids
    if trigger == "add-statement-btn":
        next_id = (max(ids) + 1) if ids else 0
        ids = list(ids) + [next_id]
    elif isinstance(trigger, dict) and trigger.get("type") == "stmt-remove":
        triggering = next(
            (t for t in ctx.triggered if t["value"] not in (None, 0)),
            None,
        )
        if triggering is None:
            return [_statement_row(i) for i in ids], ids
        remove_idx = trigger["idx"]
        ids = [i for i in ids if i != remove_idx]
    return [_statement_row(i) for i in ids], ids


if __name__ == "__main__":
    app.run()

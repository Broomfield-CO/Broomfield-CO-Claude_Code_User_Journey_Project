import os
from typing import List, Literal

import pandas as pd
from pydantic import BaseModel


FUNNEL_FLAGS: dict[str, tuple[str, ...]] = {
    "Is_cart": ("Shopping Cart",),
    "Is_Checkout_Your_Information": ("Checkout Your Information",),
    "Is_Payment_Method": ("Payment Method",),
    "Is_Checkout_Review": ("Checkout Review",),
    "Is_Checkout_Confirmation": ("Checkout Confirmation",),
    "Is_Sales": ("Clearance Sale", "Spring Sale"),
    "Is_Troubles": ("Frequently Asked Questions",),
    "Is_Login": ("Log In",),
    "Is_Search": ("Store search results",),
    "Is_ErrorPage": ("Page Unavailable",),
    "Is_Wishlist": ("Your Wishlist",),
}

FrustrationReason = Literal[
    "payment_friction",
    "form_friction",
    "price_shock",
    "indecision",
    "technical_issue",
    "search_struggle",
    "account_blocked",
]

FRUSTRATION_REASONS: tuple[str, ...] = (
    "payment_friction",
    "form_friction",
    "price_shock",
    "indecision",
    "technical_issue",
    "search_struggle",
    "account_blocked",
)

FRUSTRATION_MODEL = "claude-opus-4-6"
FRUSTRATION_BATCH = 50


# Three-pass multi-gram compression: 1-gram -> 2-gram -> 3-gram.
# Each pass slides a window of k tokens L->R and collapses consecutive
# identical k-gram repetitions into a single group token with a count.
#
# Token representation:
#   ("L", segment_str, count)               leaf — one original segment
#   ("G", (child_tok, child_tok, ...), N)   group of k children repeating N times
# A pass treats group tokens from earlier passes as atomic; k-gram equality is
# structural tuple equality, so Pass 2 can match windows that contain Pass 1
# groups. Pass 3 (k=1) multiplies counts instead of nesting, so leaf runs
# collapse to `seg (XN)` as usual.


def _leaf(seg: str) -> tuple:
    return ("L", seg, 1)


def _kgram_pass(tokens: list, k: int) -> list:
    out: list = []
    i = 0
    n = len(tokens)
    while i < n:
        if i + 2 * k <= n:
            window = tuple(tokens[i:i + k])
            count = 1
            j = i + k
            while j + k <= n and tuple(tokens[j:j + k]) == window:
                count += 1
                j += k
            if count >= 2:
                if k == 1:
                    kind, value, inner_count = window[0]
                    out.append((kind, value, inner_count * count))
                else:
                    out.append(("G", window, count))
                i = j
                continue
        out.append(tokens[i])
        i += 1
    return out


def _compress_tokens(path: str) -> list:
    if not isinstance(path, str) or path == "":
        return []
    tokens = [_leaf(s) for s in path.split("~")]
    tokens = _kgram_pass(tokens, 1)
    tokens = _kgram_pass(tokens, 2)
    tokens = _kgram_pass(tokens, 3)
    return tokens


def _render_with_counts(tok: tuple) -> str:
    kind, value, count = tok
    if kind == "L":
        return value if count == 1 else f"{value} (X{count})"
    inner = "~".join(_render_with_counts(c) for c in value)
    return f"[{inner}] (X{count})" if count > 1 else f"[{inner}]"


def _render_no_counts(tok: tuple) -> str:
    kind, value, _ = tok
    if kind == "L":
        return value
    return "~".join(_render_no_counts(c) for c in value)


def compress_path(path: str) -> str:
    tokens = _compress_tokens(path)
    if not tokens:
        return ""
    return "~".join(_render_with_counts(t) for t in tokens)


def compress_path_no_counts(path: str) -> str:
    tokens = _compress_tokens(path)
    if not tokens:
        return ""
    return "~".join(_render_no_counts(t) for t in tokens)


def _flag_column(user_path_series: pd.Series, tokens: tuple[str, ...]) -> pd.Series:
    mask = pd.Series(False, index=user_path_series.index)
    for tok in tokens:
        mask = mask | user_path_series.str.contains(tok, regex=False, na=False)
    return mask.map({True: "Y", False: "N"})


class FrustrationItem(BaseModel):
    path: str
    is_frustrated: Literal["Y", "N"]
    reasons: List[FrustrationReason]


class FrustrationResult(BaseModel):
    items: List[FrustrationItem]


FRUSTRATION_SYSTEM_PROMPT = f"""You are a web-analytics behavior classifier for the Google Merchandise Store.

You will be given compressed user navigation paths. Each path is a '~'-separated
sequence of pageSummary tokens describing pages the visitor touched (in order).
Some path segments look like `[Home~product detail page] (X3)` — that means the
two-segment subsequence `Home~product detail page` repeated 3 times in a row.
A trailing `(XN)` on a single segment means that page repeated N times.

For EACH path, decide whether the visitor shows any sign of frustration, and
pick ZERO or more reasons from this fixed enum:

  payment_friction  — repeated Payment Method visits, or abandon at/after payment
  form_friction     — oscillation between Shopping Cart / Checkout Your Information / Checkout Review
  price_shock       — viewed Shopping Cart or Checkout Your Information then exited without progressing
  indecision        — many product detail page views, repeated cart interactions, long browse with no purchase
  technical_issue   — path contains Page Unavailable
  search_struggle   — repeated Store search results with no product detail page engagement
  account_blocked   — repeated Log In or Register with no funnel progress afterward

Rules:
- If ANY reason fires, return is_frustrated = "Y" and the list of reasons.
- If no reason fires, return is_frustrated = "N" and reasons = [].
- NEVER invent reasons outside the enum. Use the exact spellings above.
- Completers (paths containing "Checkout Confirmation") are classified upstream
  and will not be sent to you, so treat every path you see as a non-completion.
- Casual browses (short path, one or two product detail page views, no cart
  activity) are NOT frustration — return "N" with reasons = [].
- For EACH item you return, `path` MUST be the EXACT byte-for-byte input path
  string — do not edit, normalize, or strip it.

Return exactly one item per input path in the `items` list."""


def _call_frustration(
    client, paths: list[str]
) -> dict[str, tuple[str, str]]:
    numbered = "\n".join(f"{i}. {p!r}" for i, p in enumerate(paths))
    user_msg = (
        f"Classify the following {len(paths)} user paths. "
        f"Return exactly {len(paths)} items in 'items'. "
        f"For EACH item, set 'path' to the EXACT input path string "
        f"(byte-for-byte, no edits) and fill in is_frustrated + reasons "
        f"per the rules.\n\npaths:\n{numbered}"
    )

    with client.messages.stream(
        model=FRUSTRATION_MODEL,
        max_tokens=32000,
        system=FRUSTRATION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
        output_format=FrustrationResult,
    ) as stream:
        response = stream.get_final_message()

    parsed = response.parsed_output
    if parsed is None:
        raise RuntimeError(
            f"Parse failed. stop_reason={response.stop_reason!r} "
            f"usage={response.usage!r}"
        )
    return {
        item.path: (
            item.is_frustrated,
            "|".join(sorted(set(item.reasons))),
        )
        for item in parsed.items
    }


def _classify_frustration(
    unique_paths: list[str],
    cache_csv: str,
) -> dict[str, tuple[str, str]]:
    cache: dict[str, tuple[str, str]] = {}
    if os.path.exists(cache_csv):
        cached = pd.read_csv(cache_csv, dtype="string").fillna("")
        for _, r in cached.iterrows():
            cache[r["user_path_Compressed_no_Counts"]] = (
                r["is_frustrated"],
                r["frustrated_reasons"],
            )
        print(f"  Loaded frustration cache: {len(cache)} entries")

    missing = [p for p in unique_paths if p not in cache]
    if not missing:
        print(f"  All {len(unique_paths)} paths already cached, skipping LLM.")
        return cache

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            f"  WARNING: {len(missing)} paths uncached and ANTHROPIC_API_KEY "
            f"not set; marking as Unknown."
        )
        for p in missing:
            cache[p] = ("Unknown", "")
        return cache

    import anthropic

    client = anthropic.Anthropic()
    total = len(missing)
    print(f"  Classifying {total} new paths with {FRUSTRATION_MODEL} "
          f"(batch size {FRUSTRATION_BATCH})...")

    for start in range(0, total, FRUSTRATION_BATCH):
        batch = missing[start:start + FRUSTRATION_BATCH]
        batch_num = start // FRUSTRATION_BATCH + 1
        total_batches = (total + FRUSTRATION_BATCH - 1) // FRUSTRATION_BATCH
        print(f"    Batch {batch_num}/{total_batches}: {len(batch)} paths")

        result = _call_frustration(client, batch)

        retries = 0
        still_missing = [p for p in batch if p not in result]
        while still_missing and retries < 3:
            retries += 1
            print(f"      Retry {retries}: {len(still_missing)} paths missing")
            retry_result = _call_frustration(client, still_missing)
            result.update(retry_result)
            still_missing = [p for p in batch if p not in result]

        if still_missing:
            print(f"      Giving up on {len(still_missing)} paths, "
                  f"marking as Unknown")
            for p in still_missing:
                result[p] = ("Unknown", "")

        cache.update(result)
        _flush_frustration_cache(cache, cache_csv)

    return cache


def _flush_frustration_cache(
    cache: dict[str, tuple[str, str]],
    cache_csv: str,
) -> None:
    rows = [
        {
            "user_path_Compressed_no_Counts": p,
            "is_frustrated": v[0],
            "frustrated_reasons": v[1],
        }
        for p, v in cache.items()
    ]
    pd.DataFrame(rows).to_csv(cache_csv, index=False, encoding="utf-8")


def _build_funnel_deepdive(
    df: pd.DataFrame,
    output_csv: str,
    cache_csv: str,
) -> None:
    pdp = df[df["user_path"].fillna("").str.contains("product detail page", na=False)].copy()
    pdp["visit_length"] = pdp["user_path"].fillna("").str.count("~") + 1
    for col, tokens in FUNNEL_FLAGS.items():
        pdp[col] = _flag_column(pdp["user_path"].fillna(""), tokens)

    dropout_paths = (
        pdp.loc[
            pdp["Is_Checkout_Confirmation"] == "N",
            "user_path_Compressed_no_Counts",
        ]
        .dropna()
        .unique()
        .tolist()
    )
    print(f"Classifying frustration for {len(dropout_paths)} unique dropout paths")
    classification = _classify_frustration(dropout_paths, cache_csv)

    completer_mask = pdp["Is_Checkout_Confirmation"] == "Y"
    lookup_keys = pdp["user_path_Compressed_no_Counts"].fillna("")
    is_frustrated = []
    reasons = []
    for key, is_completer in zip(lookup_keys, completer_mask):
        if is_completer:
            is_frustrated.append("N")
            reasons.append("")
        else:
            v = classification.get(key, ("Unknown", ""))
            is_frustrated.append(v[0])
            reasons.append(v[1])
    pdp["Is_frustrated"] = is_frustrated
    pdp["frustrated_reasons"] = reasons

    cols = [
        "fullVisitorId",
        "visitId",
        "visitStartTime",
        "user_path",
        "user_path_Compressed",
        "user_path_Compressed_no_Counts",
        "visit_length",
        *FUNNEL_FLAGS.keys(),
        "Is_frustrated",
        "frustrated_reasons",
    ]
    available = [c for c in cols if c in pdp.columns]
    pdp[available].to_csv(output_csv, index=False, encoding="utf-8")
    print(f"Wrote: {output_csv} ({len(pdp)} rows)")


def main():
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Data")
    input_csv = os.path.join(base, "base_user_journeys.csv")
    compressed_csv = os.path.join(base, "base_user_journeys_compressed.csv")
    agg_csv = os.path.join(base, "agg_user_journeys_compressed_rpt.csv")

    if not os.path.exists(input_csv):
        raise SystemExit(f"ERROR: input file not found: {input_csv}")

    print(f"Reading: {input_csv}")
    df = pd.read_csv(
        input_csv,
        dtype={"fullVisitorId": "string", "user_path": "string"},
        low_memory=False,
    )

    df["user_path_Compressed"] = df["user_path"].fillna("").map(compress_path)
    df["user_path_Compressed_no_Counts"] = df["user_path"].fillna("").map(compress_path_no_counts)
    df.to_csv(compressed_csv, index=False, encoding="utf-8")
    print(f"Wrote: {compressed_csv} ({len(df)} rows)")

    agg = (
        df.groupby("user_path_Compressed", dropna=False)
          .agg(
              unique_visitors=("fullVisitorId", "nunique"),
              unique_visits=("fullVisitorId", "size"),
          )
          .reset_index()
          .sort_values("unique_visits", ascending=False)
    )
    agg.to_csv(agg_csv, index=False, encoding="utf-8")
    print(f"Wrote: {agg_csv} ({len(agg)} rows)")

    deepdive_csv = os.path.join(base, "Rpt_Funnel_DeepDive.csv")
    cache_csv = os.path.join(base, "frustration_cache.csv")
    _build_funnel_deepdive(df, deepdive_csv, cache_csv)


if __name__ == "__main__":
    main()

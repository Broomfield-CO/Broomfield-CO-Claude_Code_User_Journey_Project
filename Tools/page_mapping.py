import os
import sys
from typing import List

import pandas as pd
from pydantic import BaseModel
import anthropic


MODEL = "claude-sonnet-4-6"
PDP = "product detail page"

# "YouTube | Shop by Brand | Google Merchandise Store" and its translations.
# These pipe-delimited brand-landing titles all collapse to "Home" because the
# brand filter lands visitors on the same logical entry point as the homepage.
YOUTUBE_SHOP_BY_BRAND_VARIANTS: list[str] = [
    "YouTube | Shop by Brand | Google Merchandise Store",
    "YouTube | Shop by Brand | Google Merchandise Store - https://shop.googlemerchandisestore.com/Google+Redesign/Shop+by+Brand/YouTube",
    "YouTube | Acquista per marca | Merchandise Store di Google",
    "YouTube | Acquista per marca | Google Merchandise Store",
    "YouTube | Comprar por Marca | Google Merchandise Store",
    "YouTube | Comprar por marca | Google tienda de artículos",
    "YouTube | Loja por marca | Google Merchandise Store",
    "YouTube | Obchod podľa značky | Merchandise Store Google",
    "YouTube | Obchod podle značky | Merchandise Store Google",
    "YouTube | 品牌品牌| Google商品商店",
    "YouTube | Kõik brändid | Google meenepoest",
    "YouTube | Winkelen per Merk | Google Merchandise Store",
    "YouTube | Magasinez par marque | Google Merchandise Store",
    "YouTube | Магазин по бренду | Магазин Google Merchandise",
    "YouTube | Магазин по бренду | Google Магазин продукції",
    "YouTube | Магазин по бренду | Google Магазин продукции",
    "YouTube | Mua theo thương hiệu | Cửa Hàng Google Merchandise",
    "YouTube | Sklep wg marki | Sklep Google Merchandise",
    "YouTube | Valg av leverandør | Google Merchandise butikken",
    "YouTube | Einkaufen nach Marke | Google Merchandise Store",
    "YouTube | Kupujte po brandovima | Google Roba Store",
    "YouTube | ブランド別ショップ| Google Merchandise Store",
    "YouTube | 브랜드 별 쇼핑 | Google Merchandise Store",
    "YouTube | Markaya göre alışveriş | Google Merchandise Store",
    "يوتيوب | التسوق بالعلامة التجارية | مخزن بضائع جوجل",
    "По бренду товара магазин с YouTube | магазин | Гугл",
]

# Deterministic pageTitle -> pageSummary overrides applied AFTER the LLM pass.
HARDCODED_OVERRIDES: dict[str, str] = {
    "Google Online Store": "Home",
    **{title: "Home" for title in YOUTUBE_SHOP_BY_BRAND_VARIANTS},
}

SYSTEM_PROMPT = f"""You are a web analytics classifier for the Google Merchandise Store.

For every pageTitle you are given, produce a pageSummary by running the
product-detail-page detector below. If it does not fire, fall through to
the translate-to-English copy path.

==============================================================================
DETECTOR — "{PDP}"
==============================================================================
Fires if EITHER:
  A1) The title ends with "| Google Merchandise Store" (or any multilingual
      equivalent of that suffix, e.g. "Merchandise Store di Google",
      "Google商品商店", "Cửa Hàng Google Merchandise", "Tienda de Google",
      "Google マーチャンダイズ ストア", etc.) AND the first pipe-separated
      segment is a product or product-category name.
      EXCEPTION: if the first segment is "Shop by Brand", "YouTube", or a
      translation of either, the detector does NOT fire (fall through to
      English translation).
  A2) The title contains NO "|" AND is an actual product name
      (e.g. "Google Vintage Henley Grey/Black", "Waze Dress Socks",
      "25L Classic Rucksack", "Clip-on Compact Charger").
      Navigation / system titles are NOT products and do NOT fire A2. These
      include (in any language): Home, Shopping Cart, Store search results,
      Clearance Sale, Google Online Store, Checkout Confirmation, Checkout
      Review, Checkout Your Information, The Google Merchandise Store - Log In.

Examples where the detector fires:
  "Drinkware | Google Merchandise Store"                    → "{PDP}"
  "Men's T-Shirts | Apparel | Google Merchandise Store"     → "{PDP}"
  "Google Vintage Henley Grey/Black"                        → "{PDP}"
  "Accesorios | Google Merchandise Store"                   → "{PDP}"
  "Abbigliamento | Merchandise Store di Google"             → "{PDP}"
  "Ropa para mujer | Google tienda de artículos"            → "{PDP}"
  "男装| Google商品商店"                                      → "{PDP}"

==============================================================================
FALL-THROUGH — DETECTOR DID NOT FIRE
==============================================================================
If the detector does not fire, output the ENGLISH TRANSLATION of the pageTitle.
THE pageSummary MUST ALWAYS BE IN ENGLISH, regardless of the input language.
If the title is already English, copy it verbatim. If it is in another
language, translate it to the natural English equivalent.

Examples:
  "Home"                                         → "Home"
  "Shopping Cart"                                → "Shopping Cart"
  "Casa"                                         → "Home"
  "Acasă"                                        → "Home"
  "Inicio"                                       → "Home"
  "Accueil"                                      → "Home"
  "Startseite"                                   → "Home"
  "ホーム"                                        → "Home"
  "홈"                                           → "Home"
  "หน้าแรก"                                       → "Home"
  "Ana Sayfa"                                    → "Home"
  "Google Online Store"                          → "Home"
  "Carrito de compras"                           → "Shopping Cart"
  "Carrello"                                     → "Shopping Cart"
  "Panier"                                       → "Shopping Cart"
  "Warenkorb"                                    → "Shopping Cart"
  "De Google Merchandise Store - Inloggen"       → "The Google Merchandise Store - Log In"
  "Возвращение Политики"                          → "Return Policy"
  "品牌品牌| Google商品商店"                        → "Brand Brand | Google Merchandise Store"

Step-prefix rule: if the title has a leading step prefix like "9: " or
"10 ", PRESERVE the prefix on the output side. Example: "9: Casa" → "9: Home".

Empty string → empty string.

==============================================================================
INPUT CONTRACT (CRITICAL)
==============================================================================
For each item you return, the "title" field MUST be the EXACT byte-for-byte
input pageTitle — do NOT edit, translate, normalize, or strip it. Only the
"summary" field carries the classification or English translation."""


class Classification(BaseModel):
    title: str
    summary: str


class ClassificationResult(BaseModel):
    classifications: List[Classification]


def extract_unique_titles(input_csv: str) -> List[str]:
    titles = pd.read_csv(
        input_csv,
        usecols=["pageTitle"],
        dtype={"pageTitle": "string"},
        low_memory=False,
    )
    unique = (
        titles["pageTitle"]
        .fillna("")
        .drop_duplicates(keep="first")
        .tolist()
    )
    return unique


def announce(n: int, sample: List[str]) -> None:
    print()
    print(f"Extracted {n} unique pageTitle values from raw_user_journeys.csv.")
    print("Sample (first 10):")
    for i, t in enumerate(sample[:10], 1):
        print(f"  {i:2d}. {t!r}")
    print()
    print(f"Sending all {n} unique titles to Anthropic Claude ({MODEL})")
    print("for multilingual classification into pageSummary.")
    print()


def _call_classify(
    client: "anthropic.Anthropic", titles: List[str]
) -> dict:
    numbered = "\n".join(f"{i}. {t!r}" for i, t in enumerate(titles))
    user_msg = (
        f"Classify the following {len(titles)} pageTitle values. "
        f"Return exactly {len(titles)} items in 'classifications'. "
        f"For EACH item, set 'title' to the EXACT input pageTitle string "
        f"(byte-for-byte, no edits, no translation) and 'summary' to the "
        f"pageSummary produced by the rules. Do not skip any title.\n\n"
        f"pageTitles:\n{numbered}"
    )

    with client.messages.stream(
        model=MODEL,
        max_tokens=32000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
        output_format=ClassificationResult,
    ) as stream:
        response = stream.get_final_message()

    parsed = response.parsed_output
    if parsed is None:
        raise RuntimeError(
            f"Parse failed. stop_reason={response.stop_reason!r} "
            f"usage={response.usage!r}"
        )
    return {c.title: c.summary for c in parsed.classifications}


def classify_all(client: "anthropic.Anthropic", titles: List[str]) -> List[str]:
    print(f"  First pass: sending {len(titles)} titles...")
    result = _call_classify(client, titles)
    print(f"  First pass returned {len(result)} classified titles.")

    missing = [t for t in titles if t not in result]
    attempt = 1
    while missing and attempt <= 3:
        print(f"  Retry {attempt}: {len(missing)} titles missing, re-requesting...")
        retry_result = _call_classify(client, missing)
        result.update(retry_result)
        missing = [t for t in titles if t not in result]
        attempt += 1

    if missing:
        raise RuntimeError(
            f"After 3 retries, {len(missing)} titles still missing. "
            f"First 5: {missing[:5]!r}"
        )

    for t in titles:
        if t in HARDCODED_OVERRIDES:
            result[t] = HARDCODED_OVERRIDES[t]

    return [result[t] for t in titles]


def _short(s: str, width: int = 60) -> str:
    s = s.replace("\n", " ").replace("\r", " ")
    return s if len(s) <= width else s[: width - 1] + "…"


def classify_with_llm(titles: List[str]) -> List[str]:
    client = anthropic.Anthropic()
    n = len(titles)
    print(f"  Sending all {n} titles in a single streamed request...")
    summaries = classify_all(client, titles)
    for i, (t, s) in enumerate(zip(titles, summaries), start=1):
        print(f"    [{i}/{n}] {_short(t)}  ->  {_short(s)}")
    return summaries


def write_mapping(
    titles: List[str],
    summaries: List[str],
    output_csv: str,
) -> None:
    if len(titles) != len(summaries):
        raise RuntimeError(
            f"Length mismatch: {len(titles)} titles vs {len(summaries)} summaries"
        )
    rows = [{"pageTitle": t, "pageSummary": s} for t, s in zip(titles, summaries)]
    pd.DataFrame(rows).to_csv(output_csv, index=False, encoding="utf-8")
    print(f"Wrote: {output_csv} ({len(rows)} rows)")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Data")
    input_csv = os.path.join(base, "raw_user_journeys.csv")
    output_csv = os.path.join(base, "page_mapping.csv")

    if not os.path.exists(input_csv):
        raise SystemExit(f"ERROR: input file not found: {input_csv}")

    print(f"Reading: {input_csv}")
    titles = extract_unique_titles(input_csv)

    announce(len(titles), titles)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit(
            "ERROR: ANTHROPIC_API_KEY is not set in the environment. "
            "Set it and re-run."
        )

    print(f"Sending {len(titles)} titles to {MODEL} in a single request...")
    summaries = classify_with_llm(titles)
    print(f"Received {len(summaries)} summaries.")

    write_mapping(titles, summaries, output_csv)


if __name__ == "__main__":
    main()

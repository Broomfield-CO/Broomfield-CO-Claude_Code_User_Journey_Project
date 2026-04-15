import os
import sys
import pandas as pd


def process(input_path: str, out_full_path: str, out_last: str, plan_path: str = None, session_path: str = None):
    dtypes = {
        'fullVisitorId': 'string',
        'visitId': 'string',
        'visitNumber': 'Int64',
        'visitStartTime': 'Int64',
        'hitNumber': 'Int64',
        'hitTime': 'Int64',
        'hitHour': 'Int64',
        'hitMinute': 'Int64',
        'pagePath': 'string',
        'pageTitle': 'string'
    }

    df = pd.read_csv(input_path, dtype=dtypes, low_memory=False)

    # Merge in pageSummary from the pre-classified lookup (page_mapping.csv).
    # page_mapping.py is the only place that calls the LLM; this step is a
    # deterministic join keyed on pageTitle.
    mapping_path = os.path.join(os.path.dirname(input_path), 'page_mapping.csv')
    mapping = pd.read_csv(
        mapping_path,
        dtype={'pageTitle': 'string', 'pageSummary': 'string'},
    )
    df = df.merge(mapping, on='pageTitle', how='left')

    # Convert visitStartTime (milliseconds since epoch) to timezone-aware UTC datetime
    df['visitStartTime_dt'] = pd.to_datetime(df['visitStartTime'], unit='ms', utc=True)

    # Build hit_timestamp from normalized visit date + hitHour/hitMinute/hitTime
    df['hit_timestamp'] = (
        df['visitStartTime_dt'].dt.normalize()
        + pd.to_timedelta(df['hitHour'].fillna(0).astype(int), unit='h')
        + pd.to_timedelta(df['hitMinute'].fillna(0).astype(int), unit='m')
        + pd.to_timedelta(df['hitTime'].fillna(0).astype(int), unit='s')
    )

    # Ensure sorting
    df = df.sort_values(['fullVisitorId', 'visitNumber', 'hitNumber'], kind='mergesort')

    # Build user_path per group from pageSummary, joined with '~' (pipe is
    # reserved — it appears inside raw pageTitle values).
    grouped = df.groupby(['fullVisitorId', 'visitNumber'], sort=False)
    user_paths = grouped['pageSummary'].agg(lambda s: '~'.join(s.dropna().astype(str)))
    user_paths = user_paths.rename('user_path').reset_index()

    # Merge back so every hit row has the user_path for that visit
    df = df.merge(user_paths, on=['fullVisitorId', 'visitNumber'], how='left')

    # last_step_indicator: 'Y' if hitNumber == group's max
    max_hit = grouped['hitNumber'].transform('max')
    df['last_step_indicator'] = (df['hitNumber'] == max_hit).map({True: 'Y', False: ''})

    # Full hit-level output with the ~-joined user_path
    df.to_csv(out_full_path, index=False, encoding='utf-8')

    # One row per visit (last hits only) — deduped
    df_last = df[df['last_step_indicator'] == 'Y']
    df_last.to_csv(out_last, index=False, encoding='utf-8')

    # Optionally save plan and session prompts into Data folder if paths provided
    if plan_path and os.path.exists(plan_path):
        try:
            from shutil import copyfile
            copyfile(plan_path, os.path.join(os.path.dirname(out_full_path), os.path.basename(plan_path)))
        except Exception:
            pass

    if session_path and os.path.exists(session_path):
        try:
            from shutil import copyfile
            copyfile(session_path, os.path.join(os.path.dirname(out_full_path), os.path.basename(session_path)))
        except Exception:
            pass


def main():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Data")
    input_csv = os.path.join(base_dir, 'raw_user_journeys.csv')
    out_last = os.path.join(base_dir, 'base_user_journeys.csv')
    out_full_path = os.path.join(base_dir, 'base_user_journeys_full_visit_path.csv')
    plan_path = os.path.join(base_dir, 'plan.md')
    session_path = os.path.join(base_dir, 'session_prompts.md')

    if not os.path.exists(input_csv):
        print(f"ERROR: input file not found: {input_csv}")
        sys.exit(2)

    print(f"Reading: {input_csv}")
    process(input_csv, out_full_path, out_last, plan_path=plan_path, session_path=session_path)
    print(f"Wrote: {out_full_path}")
    print(f"Wrote: {out_last}")


if __name__ == '__main__':
    main()

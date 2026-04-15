## Plan: Process User Journey Hits to base_user_journeys.csv

TL;DR: Read `raw_user_journeys.csv`, convert `visitStartTime` (milliseconds) to UTC datetime, build `hit_timestamp` from `hitHour`/`hitMinute`/`hitTime`, sort by `fullVisitorId, visitNumber, hitNumber`, aggregate `pageTitle` per visitor+visit into `user_path` (pipe-delimited, ordered by `hitNumber`), add `last_step_indicator` marking the final hit per visit, write all-hit output to `base_user_journeys.csv`, and write one-row-per-visit last-hit output to `base_user_journeys_full_visit_path.csv`.

Steps:
1. Read CSV with `pandas.read_csv` using explicit dtypes for efficiency.
2. Convert `visitStartTime` to timezone-aware UTC datetime (`visitStartTime_dt`).
3. Build `hit_timestamp` = normalized visit date + `hitHour`/`hitMinute`/`hitTime`.
4. Sort by `fullVisitorId`, `visitNumber`, `hitNumber`.
5. Group by `fullVisitorId, visitNumber` and build `user_path` by `|`-joining `pageTitle` in hit order.
6. Mark `last_step_indicator` = 'Y' for rows where `hitNumber` equals group's max.
7. Write `base_user_journeys.csv` (all hits) and `base_user_journeys_full_visit_path.csv` (only last-hit rows).
8. Save this plan (this file) and the session prompts into the `Data/` folder for traceability.

Assumptions:
- `visitStartTime` is milliseconds since epoch.
- `hitTime` is seconds component; `hitNumber` is integer sequence index.

Verification:
- Input rows == rows in `base_user_journeys.csv`.
- Rows in `base_user_journeys_full_visit_path.csv` == unique visits.
- Spot-check `user_path` and `last_step_indicator` correctness.

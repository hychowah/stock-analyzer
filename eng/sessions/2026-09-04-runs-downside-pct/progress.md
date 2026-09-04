# Eng session 2026-09-04-runs-downside-pct

- Work type: W4
- Goal: Runs list Downside % overlay: (price - fv_bear) / price from as-of, live overwrite

## Log

- Scaffolded after strategic design review: Live overlay, not a MoS-like catalog sort key.
- Implemented `downside_pct` / `downside_title` in `templating.py`; runs table + run detail cells; `quotes.js` `fillDownside` after `applyQuotes`.
- Did not add catalog sort, `/api/runs` field, or mutate run dicts.
- Verify: `pytest apps/analysis_web/tests` 119 passed; `eng_verify.py` PASS (672). Live-archive smoke: home 200, first cell 73.6 for 000660.KS as-of vs bear, API has no `downside_pct`.
- Stale UI on :8765 returns 500 (`downside_title` undefined) until that process is restarted.
- No git commit (needs user agreement).

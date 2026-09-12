# 2026-09-12-analysis-report

- Goal: AnalysisReport document — ForecastTable, one duration map, reading shell, harness 2.43.0 write contract.
- Refactor: forecast display type lives in `kd_research.forecast_table` (named layouts only). Duration English lives in `kd_research.decision`; the website imports it. Composed report is a document type, not extra blocks on the old artifact card.

## Done

- `ForecastTable.from_session`: explicit_forecast, META parallel arrays, COHR `dcf.years`, ADYEN `paths`; unknown → None.
- Catalog allowlist `data/compute/valuation_result.json` only; in-progress still denies it.
- Wave 8 README gate accepts product English on ≥ 2.43.0.
- `/runs/{id}/report` + shared `reading.html` shell (desktop rail / phone chips). JSON forecast is the only year-by-year grid; markdown `## Forecast path` is stripped.
- Agent 5/7/11 prompts + exemplar + identity/table checks. `harness/VERSION` 2.43.0; `pins/2.43.0/` published.

## Verify

- `python scripts/eng_verify.py` PASS (1058 tests).
- Browser on `:8765`: META 2026-09-11 report shows Do not initiate, WACC list, Base path Y1 revenue $254.2B / FCF -$42.0B, Bear chip swaps to $230.0B; no second Forecast path. ACGL shows Hold and “This model has no year-by-year cash-flow table.” Desktop rail `display:block`, chips none; 390px rail none, chips sticky, site header static. `#forecast` hash works.

## Not committed

No git commit (needs user agreement).

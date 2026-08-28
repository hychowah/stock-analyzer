# Eng session 2026-08-28-mode-a-ticker-abort

- Work type: W1
- Goal: Abort Mode A when the typed symbol is not a real market ticker and has no obvious match.

## Log

- 2.21.0: `scripts/kd_research/ticker_lookup.py` + `scripts/verify_ticker.py`.
- `scaffold_session.py` CLI verifies by default (`--skip-ticker-check` tests/offline only). Python API default is off so unit tests stay hermetic.
- Does not auto-remap. Obvious typo/alias → abort and print matches. Garbage → abort unknown. Real quote → ok (META still works; `meta` is a reserved folder name but a listed equity).
- Live: APPL → abort_match AAPL, APP; ZZZNOPE → abort_unknown; META → ok.
- Tests: `test_ticker_lookup.py` 11 passed (FakeBackend, no network).

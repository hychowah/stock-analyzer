# Eng fixtures

Offline/CI mirror of the **archive shape** (not a second warehouse of truth).

```text
eng/fixtures/archive/
  research/<TICKER>/<SESSION_KEY>/   # slim session trees
  catalog/                           # tiny re-exported sqlite + indexes
  outcomes/                          # optional
```

**Production** always uses project `archive/`.  
**CI:** `ARCHIVE_ROOT=/path/to/eng/fixtures/archive`.

Refresh:

```bash
python3 scripts/sync_eng_fixtures.py --tickers META,JPM --dates 2026-08-03,2026-07-25
```

Do not point `scaffold_session` / `finalize_session` at fixtures as live research output.

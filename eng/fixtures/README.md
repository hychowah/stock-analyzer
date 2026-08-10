# Eng fixtures

Offline/CI mirror of the **archive shape** (not a second warehouse of truth).

```text
eng/fixtures/                 # fixture *project* root
  archive/                    # ARCHIVE_ROOT for CI
    research/<T>/<KEY>/       # slim session copies (no raw_sec/transcripts)
    catalog/
      research_compare.sqlite # re-exported from fixture sessions only
      runs_index.json
    outcomes/…                # optional slim copies
```

## Refresh from live archive

```bash
# Defaults: META@2026-08-03, JPM@2026-07-25
python3 scripts/sync_eng_fixtures.py

# Custom pairs
python3 scripts/sync_eng_fixtures.py --tickers META,SOFI --dates 2026-08-03,2026-08-09
```

## Use in CI / offline

```bash
export ARCHIVE_ROOT=$PWD/eng/fixtures/archive
python3 -m packages.catalog_api health
python3 -m packages.catalog_api list-runs --limit 5
ARCHIVE_ROOT=$PWD/eng/fixtures/archive python3 -m apps.analysis_web
```

**Production** always uses project `archive/`.  
Do not point `scaffold_session` / `finalize_session` at fixtures as live research output.

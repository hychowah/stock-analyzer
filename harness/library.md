# Ticker document library

Reusable **primary documents** (filings, earnings exhibits, transcripts). Not judgments.

```text
archive/library/<TICKER>/
  _inbox/          drop messy PDFs/HTML/txt, then ingest
  _unlabeled/      ingested but form/period unknown
  filings/ transcripts/ supplements/ ir/
  manifest.json
```

Operator commands:

```bash
python3 scripts/ingest_library.py --ticker META
python3 scripts/ingest_library.py --ticker META --label "foo.pdf:annual:FY2025:2026-01-29"
python3 scripts/bind_library.py --ticker META --date YYYY-MM-DD
python3 scripts/harvest_library.py --ticker META   # ops only; never from a new Mode A run
```

Conversion is `scripts/kd_research/doc_text.py` (code). Do **not** write `extract_sidecars.py` in `S/data/compute/`.

## Isolation (canonical)

Always-on: work under current `S` only; do **not** list `archive/research/<T>/`.

| Who | Live `archive/library/<T>/` |
|-----|------------------------------|
| `bind_library.py` / `ingest_library.py` | Read/write |
| Agent 2b | Write-through via CLI; `_unlabeled/` line-range **≤5 files**; never walk `filings/` to mine footnotes |
| 2e merge | Fetch **web → `S/data/transcripts/`** for `session_missing` latest-window slots only. Do not list or ingest the live library |
| 2e-year, 2a, 2c, 2d, 1d, 4, 5, 7, 8, 11, 13, Phase 0 | **Forbidden.** Session copies only |
| Harvest | User/ops only |

Year-readers, excerpt-in-source, and audit read `S/data/raw_sec/*.txt` and `S/data/transcripts/`. Bind copies **only if** a `.txt` sidecar exists.

## Required set (what bind copies into `S`)

Unique fiscal years/periods, one primary `.txt` per year (prefer `_EN`):

- Annuals: 3 (5 if `research_depth=deep` or `intensity=high`)
- Interims: 2
- Latest earnings exhibit + supplement
- Transcripts: last 8 unique periods

Do **not** bind the whole corpus (1c spawns one year-reader per annual **on disk**).

## Freshness (mechanical)

Two lists:

- `session_missing[]` — required-set slots not in `S` (including **newer** than bound). 2b/2e may fetch **only** these into `S`.
- `library_gaps[]` — older corpus holes. Mode A must **not** fetch them into `S`.

On-disk listing required after 2b: `registry/raw/filing_index.json` (US) or `ir_listing.json` (non-US). Freshness fields live on `registry/data_fetch_log.json` (`freshness`, `transcript_freshness`) — not a stub on `library_bind.json`.

Bind **refuses** completed sessions (`prediction_snapshot` or finalized `run_manifest`).

Inject this file into the **orchestrator and Agent 2b** only.

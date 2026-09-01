# Plan: Ticker document library

**Status:** implemented in harness 2.19.0.  
**Operator law:** `harness/library.md` (canonical isolation + required set + freshness).

## Why

Mode A was re-finding, downloading, and converting the same 10-Ks and transcripts every session. Conversion belonged in code; sessions still need a hermetic copy.

## Shape

`archive/library/<TICKER>/` is a fourth archive layer (sibling of `research/`, `outcomes/`, `catalog/`). Not a session. Not a FV store.

Mode A: `bind_library.py` copies the **required set** (unique FY; 3 or 5 annuals) into `S`. 2b fetches only `session_missing[]`. Write-through new docs via `ingest_library.py`. Year-readers stay on session `.txt`.

User: drop files in `_inbox/`, run ingest. Harvest is ops (`harvest_library.py`), never a new-run shortcut.

## Non-goals (still)

No analysis-web library browser. No catalog `run_id` for documents. No bind-all. No live-library reads from year-readers / Agent 4 / Agent 5.

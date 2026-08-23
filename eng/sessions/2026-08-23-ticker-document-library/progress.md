# Progress — ticker document library

Mode B W1. Harness **2.19.0**.

## What shipped

Fourth archive layer `archive/library/<TICKER>/` for reusable primary documents (filings, transcripts, exhibits). Sessions stay hermetic: `bind_library.py` copies the **required set** (unique FY; 3 annuals, or 5 if deep/high) into `S/data/raw_sec` and `S/data/transcripts` only when a `.txt` sidecar exists.

- User drop: `_inbox/` + `python scripts/ingest_library.py --ticker T`
- Mode A: bind after brief, before 2b; fetch only `session_missing[]` (not `library_gaps[]`)
- Conversion: `scripts/kd_research/doc_text.py` (HTML stdlib; PDF optional pypdf)
- Harvest: `harvest_library.py` (ops; not called from a new Mode A run). **Not run on live archive in this increment.**
- Isolation: live library is code + 2b unlabeled only. Agent 4 forbidden tokens include `archive/library` and `library_bind`. Bind refuses completed sessions.
- Gates: ≥ 2.19.0 require `library_bind.json` at 1_parallel **entry**; index + `data_fetch_log.freshness` at 1_parallel complete; `transcript_freshness` at 1c. Legacy SKIPPED.
- `annuals.is_annual_form` accepts `AR` so HK names spawn year-readers.
- Mode B law: research/outcomes immutable; library append-only. `RESEARCH_RUNTIME_PREFIXES` includes the three CLIs. `eng_verify` pytest list names the new tests.

## Refactors

- One home for library facts: `scripts/kd_research/library.py` (not a sibling `source_materials/` under research sessions).
- Canonical isolation paragraph in `harness/library.md`; prompts point at it instead of a run-wide “library allowed”.

## Verify

```
python -m pytest scripts/tests/test_library.py scripts/tests/test_doc_text.py -q
python scripts/eng_verify.py
```

eng_verify: PASS (158 passed, 1 skipped pypdf). VERSION bump vs main recorded.

## Instruction audit (independent, post-ship)

Two read-only auditors (Mode A law + prompt isolation). Verdict: residual-debt. Accepted and patched:

- All-agent conventions no longer name `archive/library` or `library.md` (orch + 2b only).
- 2b lede is inventory/bind-first; MCP/hermetic store is `session_missing[]` only.
- 2e reads/writes `S/data/transcripts` only (no ingest CLI); year-readers refuse non-`raw_sec` paths.
- Phase 0 / Agent 5 / 7 / 13: session artifacts; Agent 13 external = same accession on disk.
- Maps: bind is orchestrator; 2.19.0 §13 row; if-X-missing `library_bind`; Mode B append-library; completed-session bind refuse.
- 2b GOOD handoff exemplar is bind-then-`session_missing`.
- `session_isolation.json` notes no longer teach the unlabeled exception.

## Follow-ups (not this increment)

- User may run `harvest_library.py --ticker META` (and 02618.HK) to seed from existing `raw_sec` / `transcripts` / `source_materials`.
- Optional `pip install pypdf` for PDF sidecars (`scripts/requirements-research.txt`).
- No analysis-web library page.

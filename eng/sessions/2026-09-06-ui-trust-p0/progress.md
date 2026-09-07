# Eng session 2026-09-06-ui-trust-p0

- Created: 2026-09-06T10:37:37Z
- Work type: W4
- Goal: Fix confirmed P0 UI trust bugs: compare headline Jinja, HTML 404, Analyze reconcile painted as error, Compare abort vs empty.

## Log

- 2026-09-06T10:37:37Z scaffolded
- 2026-09-07 implemented Wave 1 (implementer; `passes` left for verifier).
- **headline:** `templating.headline_view` projects `headline.json` into `{sessions, rows: [{label, cells}]}`. English labels in `HEADLINE_LABELS`. Cells go through `fmt_num` (None → `—`). `page_compare_detail` passes the view; `compare_detail.html` iterates `row.label` / `row.cells` only. On-disk `"values"` unchanged. No blended delta.
- **html-404:** `app.py` `HTTPException` handler: Accept prefers `text/html` → `error.html` + `← Runs` (pass `request`); else JSON `{"detail": …}`. `error.html` default back is `/`. Router `_error()` copies not unified.
- **analyze-err:** `.err` only when status is failed/cancelled/abandoned or `job.abandoned`; otherwise notes `.muted`.
- **compare-abort:** `compares.html` skips “No compare packets yet.” when `error` is set; HTTP 404 + `is-abort` kept.
- Verify: `pytest apps/analysis_web/tests` 185 passed; `eng_verify.py` PASS (773). Curl against this-tree UI on :8766 (`--no-auto-restart`): unknown path + HTML Accept is chrome + `← Runs`; `/api/runs/nope` JSON Accept is `{"detail":"Run not found: nope"}`; `/compares?ticker=ZZZZNOTATICKER` aborts without empty-packet copy; complete MELI compare shows `1,922.73` / `631.27` / `1,031.96` in headline cells.
- No `ARCHITECTURE.md` edit (no new page, no new display math, no archive-plane change). No `harness/VERSION` bump (W4).
- No git commit (needs user agreement).

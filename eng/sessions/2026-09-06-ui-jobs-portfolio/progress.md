# Eng session 2026-09-06-ui-jobs-portfolio

- Created: 2026-09-06T10:37:38Z
- Work type: W4
- Goal: Human Analyze/Compare wait and verbs; portfolio blotter columns from stored catalog math.

## Log

- 2026-09-06T10:37:38Z scaffolded
- 2026-09-07 orient: on `ui-ux-compose` at `5864cf2` (Wave 4a run-reading; Wave 3 `e581694`, Wave 2 `e3f9755`, Wave 1 `d21af66`). Read `eng/AGENTS.md`, parent PLAN.md § Session 6 + file-ownership + How a later agent starts, `AGENT_BRIEF.md`, `handoffs/sdr-wave4c-jobs-portfolio.md`. Predecessor `eng/sessions/2026-09-06-ui-trust-p0/` (Wave 3 extras exist for portfolio Duration). SDR mixed/reshape: one wait loop (drop SSE reload); errors stay on the task; portfolio reuses Runs cells. Do not rewrite `base.html`, `quotes.js`, `app.css`, or IB ingest. No `/fragments/analyze`. No artifact `<ul>` in JS.
- 2026-09-07 implemented Wave 4c (implementer; `passes` left for verifier).
- **start-form:** Ticker + as-of + Harness first; slug/models/notes/ingest in `<details>`. Every field round-trips. Submit disables after confirm. Busy / Grok-missing / runbook-missing re-render the form (409/503), not `error.html`.
- **wait-loop:** JS patches badge, phase, error, `resume_hint`; reload only on terminal status. `<meta refresh=15>` while running/queued. Dropped `data-live-reload` on analyze/compare list and detail. No artifact list in JS. No phase-name map.
- **verbs:** Cancel confirm “Kill Grok, keep the session.” Cancel/Resume/Discard 303 with `?flash=`. Resume conflict/Busy stay on the job page. Failed Compare has Retry POST same pair. Unknown job still `error.html`.
- **portfolio-blotter:** `_catalog_fields` adds `fv_bear`, listing, dates, `decision_action`. Template As-of / Live / Downside use the Runs `data-quote-*` / `data-downside-pct` contract. Duration is stored action or `—`. Missing/no-PASS → `/analyze/new?ticker=`. Empty copy: “Import an IB activity statement” + path in `<code>`. Waterfall totals vs signed flows from a zero gutter inline in `portfolio.html`. `quotes.js` and `app.css` untouched.
- Verify (implementer, not flipping `passes`): `pytest apps/analysis_web/tests` 208 passed; `eng_verify.py` PASS (799, was 794). Did not rewrite `base.html`, `quotes.js`, `app.css`, IB ingest, or `harness/VERSION`.
- `ARCHITECTURE.md` § The website table (analyze wait, compare Retry, portfolio cells). No `harness/VERSION` bump (W4).
- No git commit (needs user agreement). Stay on `ui-ux-compose`.

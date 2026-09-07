# Agent brief — ui-jobs-portfolio (post-SDR)

Mode B W4. Read `eng/AGENTS.md` and parent `PLAN.md` § Session 6 plus `handoffs/sdr-wave4c-jobs-portfolio.md`.

**Start after** `ui-trust-p0`. You own Analyze/Compare wait+verbs and `portfolio.html` cells. Do not rewrite `base.html`, `quotes.js`, or `app.css`.

SDR verdict: **mixed / reshape**. Do not add a third wait path on `live.js`. Do not add list fragments. Do not rebuild artifacts from job JSON. Do not invent a portfolio Live dialect.

## Goal

Wait on a 2–8h Analyze like a human. Failed Compare can retry. Portfolio is a blotter using stored catalog math and the **same** quote/Downside cells as Runs.

## Slices

1. **start-form** — Ticker + as-of + Harness first; advanced in `<details>`. Round-trip. Busy/Grok-missing stay on the form.
2. **wait-loop** — Patch badge/phase/error/`resume_hint`; reload only on terminal status; `<meta refresh=15>`. **Drop `data-live-reload`** on analyze/compare list and detail pages. No artifact `<ul>` in JS. No phase-name map.
3. **verbs** — Cancel confirm. Resume shows `resume_hint` on the job page. `?flash=` after verbs. Retry failed Compare (new packet). Own `compare_detail.html` wait/verbs (headline view is Wave 1).
4. **portfolio-blotter** — Extend `_catalog_fields` (`fv_bear`, listing, dates, `decision_action` if present). Same `data-quote-*` / `data-downside-pct` contract as Runs. As-of vs IB Close labeled. Missing → `/analyze/new?ticker=`. Empty copy is import-an-IB-statement. Waterfall geometry **inline in the template**, not `app.css`.

## Non-goals

No FV until snapshot. No blended compare FV. No `/fragments/analyze`. No `quotes.js` edits. No IB ingest rewrite. Duration may be `—` until Wave 3 hydrate lands — that is acceptable.

## Verify

pytest analyze/compare/portfolio. `/analyze/new` advanced collapsed; running pages have meta refresh and no `data-live-reload`; `/portfolio` with sqlite uses the same live-cell attributes as Runs. `eng_verify`.

No commit until the user agrees.

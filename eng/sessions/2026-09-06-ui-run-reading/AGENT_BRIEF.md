# Agent brief — ui-run-reading (post-SDR)

Mode B W4. Read `eng/AGENTS.md` and parent `PLAN.md` § Session 4 plus `handoffs/sdr-wave4a-run-reading.md`.

**Start after** `ui-decision-blotter`. You own `page_run` reading facts, `render_session_report`, `price_chart.js`.

SDR verdict: **mixed / reshape**. Do not stuff session URL knowledge into `render_markdown()`. Do not guess the football PNG in the template. Do not edit the 800px media-query block.

## Goal

Open a run → see the cone (Agent 6 PNG + honest overlay) → read the CIO cover by title, not filename.

## Slices

1. **session-report** — `render_session_report(...) -> {title, toc, html}`. `render_markdown()` stays a plain sanitizer. Sibling `.md` resolved against `relpath`’s directory. One page H1.
2. **football** — `page_run` sets `football_href` or none. Cover CTA uses existing README href. Allowlist table in `<details>`.
3. **chart-copy** — One formatter for tooltip and readout. Clip named on `#price-chart-status`. `touchmove`/`touchend`. Stage **height** as a global `.chart-stage` rule; do not touch `@media (max-width: 800px)`.

## Non-goals

Do not replot a football field. Do not change `/` columns. Do not change nav. Do not rewrite the 800/1100 query.

## Verify

pytest on `render_session_report` href rewrite. Open a run that has `charts/valuation_football_field.png`. README “Full reports” links stay on `/artifact`. `eng_verify`.

No commit until the user agrees.

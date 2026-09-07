# Agent brief — ui-nav-ia (post-SDR)

Mode B W4. Read `eng/AGENTS.md` and parent `PLAN.md` § Session 2 plus `handoffs/sdr-wave2-nav-ia.md`.

**Start after** `2026-09-06-ui-trust-p0`. You own `templating.py` `render_page` and `base.html`.

SDR verdict: **mixed / reshape**. “Pass request into every `_render`” is not the from-scratch interface.

## Goal

Four primary jobs, quiet Lab, visible current page, skip-to-content, ticker crumb on details. All nine URLs stay.

## Slices

1. **render-page** — One `templating.render_page` injects `nav.current` from a prefix table. Collapse cloned `_render` helpers. Fragments stay chrome-less. `error.html` / report / artifact / `page_runs` go through it. `base.html` matches `nav.current`, not `request.url.path`.
2. **nav-group** — Primary vs Lab as two labeled `<nav>`s. Phone: each is its own **wrapped** `.disclose` so Menu cannot open Lab. Brand home link **Stock Research**. Tagline and **Compare** singular. Skip link `#content`.
3. **crumbs-lab** — `/?ticker_prefix=` beside existing back links on run/analyze/compare detail. Empty copy on experiments/calibration/health only. **Do not** edit `runs_table.html` or `portfolio.html`.

## Non-goals

Do not raise the 800px breakpoint. Do not reorder runs columns. Do not add `/ticker/META`. Do not replay query memory onto empty `/`.

## Verify

pytest + `eng_verify`. `/analyze` HTML has `aria-current="page"` on Analyze. Two disclose pairs cannot open each other. Skip link exists. Calibration empty has an exit.

No commit until the user agrees.

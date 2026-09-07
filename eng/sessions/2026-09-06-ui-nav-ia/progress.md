# Eng session 2026-09-06-ui-nav-ia

- Created: 2026-09-06T10:37:37Z
- Work type: W4
- Goal: Group analysis_web nav into primary jobs vs lab, current page, skip link, ticker crumbs, human chrome copy.

## Log

- 2026-09-06T10:37:37Z scaffolded
- 2026-09-07 orient: on `ui-ux-compose` at `d21af66` (Wave 1 ui-trust-p0). Read `eng/AGENTS.md`, parent PLAN.md § Session 2 + file-ownership + How a later agent starts, `AGENT_BRIEF.md`, `handoffs/sdr-wave2-nav-ia.md`. Predecessor `eng/sessions/2026-09-06-ui-trust-p0/`. Owns `templating.render_page` + `base.html`. Must not rewrite `runs_table.html`, `portfolio.html`, stack-table media query, or disclose tab-order (Wave 5). SDR mixed/reshape: one `render_page` injects `nav.current` from a prefix table; `base.html` matches `nav.current`, not `request.url.path`; no FastAPI Request in the template. Stale `:8765` is old chrome (`Archive Analysis`, `git_sha` —); this-tree UI booted on `:8772`.
- 2026-09-07 implemented Wave 2 (implementer; `passes` left for verifier).
- **render-page:** `templating.render_page` injects `nav` from `nav_for_path` (closed prefix table; `/analyze-artifact` does not collapse into a raw `/analyze` startswith). Cloned `_render` helpers in pages/analyze/compares/architecture/harness removed. `error.html` / report / artifact / `page_runs` go through `render_page`. Fragments use `render_fragment` (no nav). `base.html` matches `nav.current`. Request is not in the template.
- **nav-group:** Primary vs Lab as two labeled `<nav>`s. Each disclose pair wrapped in `.nav-disclose` so Menu cannot open Lab. Brand home **Stock Research**. Tagline operator jobs. Nav word **Compare**. Skip link `#content` first focusable. Phone Menu label is `nav.menu` (`Menu · Analyze`). Header CSS quiets Lab; 800px query not raised.
- **crumbs-lab:** `/?ticker_prefix=` beside existing back links on run/analyze/compare detail. Experiments empty + `h2` → `/?experiment_id=` when ids exist. Calibration empty has `← Runs`. Health human labels; Git SHA never silent `—`. Did not edit `runs_table.html` or `portfolio.html`.
- Verify: `pytest apps/analysis_web/tests` 190 passed; `eng_verify.py` PASS (778). Curl this-tree `:8772`: `/analyze` has `aria-current` on Analyze, two navs, skip-link; fragments have no header; `/health` shows boot SHA `d21af66…`; `/calibration` has `← Runs`; HTML 404 is chrome; run detail has ticker_prefix crumb.
- `ARCHITECTURE.md` § The website: header groups primary vs Lab; one `render_page` injects current section. No `harness/VERSION` bump (W4).
- No git commit (needs user agreement). Stay on `ui-ux-compose`. Product later landed in `e3f9755`.
- 2026-09-07 verifier (skeptical): pytest apps/analysis_web/tests 191 passed; eng_verify PASS 779. No `_render` clones. Live `:8773` SHA `e3f9755cdb42a6478feb35f999fc49beb7f72804`: `/analyze` aria-current on Analyze, two wrapped navs, skip-link first; fragments chrome-less; health SHA not silent `—`; calibration `← Runs`; run and compare details have `ticker_prefix` crumbs. `runs_table.html` / `portfolio.html` / `harness/VERSION` untouched vs Wave 1. `ARCHITECTURE.md` updated. Flipped `feature_list` passes; wrote `ship_note.json`. Did not git commit session metadata.

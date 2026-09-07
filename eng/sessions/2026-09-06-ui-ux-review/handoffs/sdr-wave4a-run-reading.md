# SDR — Wave 4a ui-run-reading

Target: Session 4 plan + `ui-run-reading` brief/issue/features, against current `run_detail.html`, `report.html`, `render_markdown.py`, `price_chart.js` (and the `/artifact` / `page_run` callers those files already have). Grain: feature/implementation plan. No product edits.

### Verdict
- **Direction:** `mixed`
- **Why:** The job is the from-scratch run sheet: tape for time, Agent 6 football PNG for the cone, CIO cover as a document (title, TOC, in-archive links), not a path dump. That split is already the parent’s winner (compose in this tree; do not replot FV). The four slices as written will still *patch nearby files*: sibling rewrite and title/TOC stuffed into the sanitizer, football existence guessed in the template, tooltip copied beside the readout, phone stage height fought inside a11y-phone’s media query. The structure you would have designed is three deep modules on the existing routes, not four UX nits.
- **Do:** `reshape`

### Keep
- FastAPI + Jinja + small JS. Catalog overlay JSON only. No second football field, no live MoS, no SPA.
- Tape vs envelope: keep price-centric `domainY` (bear/bull/weighted clip); put the cone in `charts/valuation_football_field.png` via the existing `/artifact` PNG path. Range chips, clipPath, sibling click-through, honest load/error copy stay.
- `render_markdown()` as the general sanitizer (bleach, heading ids, mermaid unwrap). Architecture and harness keep calling it with no session knowledge.
- `get_report_paths` README trio and `list_artifacts(prefix="reports/")` already exist; cover CTA is a chrome change over that, not a new lookup.
- Sequence: after decision-blotter (same `run_detail.html`); this session owns the reports/charts block, not column order or the decision strip. Parallel a11y-phone owns the 800→1100 query — this session must not rewrite that block.
- Verify the rewrite with pytest; open a run that actually has the PNG. Feature_list granularity can stay for `passes`.

### Candidates

### 1. Session report document (not sanitizer kwargs)
- **Change:** In `render_markdown.py`, add a second operation used only by artifact markdown routes, e.g. `render_session_report(text, *, run_id, relpath) -> {title, toc, html}`. `title` = first markdown H1 text (fallback `relpath`); `toc` = h2/h3 using ids already injected; `html` = sanitized body with **relative** `.md` hrefs rewritten after bleach. Resolve against `relpath`’s directory (so `01_….md` from `reports/00_…_README.md` becomes `reports/01_….md`, not `reports/` blindly prefixed). Reject `..` / non-allowlisted targets rather than emitting them. Leave `#` anchors and `http(s)` alone. `render_markdown(text)` stays `str` with no `run_id`. `report.html`: page `<title>` and h1 = `title`; `relpath` muted + Raw; TOC as a Jinja loop over `toc` (not sticky, not a second `|safe` HTML builder). Do not leave two equal H1s (extract title; do not also show the same heading as the first body h1). Wire `artifacts.py` this wave; compare/analyze markdown may pass the same helper **only** if the href base is a parameter (`/artifact` vs `/analyze-artifact` / `/compare-artifact`) — default of this wave is catalog `/artifact`.
- **Why:** Information leakage + special–general mixture: `render_markdown` is already used by architecture, harness, compare synthesis, and analyze. Optional kwargs for `/artifact?path=reports/…` leak the catalog URL into every caller and make the common (non-session) case carry rare features. Dual H1 is the current filename-vs-cover bug with a new label. Relative-to-`reports/` hardcoded is an unknown unknown the first time a link is `./foo.md` or already includes `reports/`. Pull complexity down: one document type, sanitizer stays deep and small.
- **When:** `this change`

### 2. Run-sheet reading column from `page_run`, not the template
- **Change:** `page_run` (allowed under `apps/analysis_web/`; name it — the ownership table omitted it) passes `football_href` (or none) by listing `charts/` and picking `valuation_football_field.png`, and keeps the existing README href for the CTA. Template: `<img>` only when href is present; else one muted line. One **Read CIO cover** control using the README link; wrap the allowlist table in `<details>` (drop the duplicate Path column while that table is open). Do not `<img src="…valuation_football_field.png">` on every run and hope `/artifact` 404s, and do not add a charts gallery (tornado/heatmap stay unlinked). Surgical to the reports/charts block so blotter’s strip + valuation-above-chart is not reverted.
- **Why:** Unknown unknown: without a route fact, “missing → muted” is `onerror` or a broken image. Shallow module: the template would re-encode the Agent 6 filename and the allowlist. `list_artifacts` is already the existence API (today it is only called with `reports/`). Common case stays one PNG and one cover button.
- **When:** `this change`

### 3. One chart copy path; own stage height outside the 800px query
- **Change:** One formatter used by readout and tooltip (same fields: date, close, bear, base, bull, currency; tooltip may join with newlines). After a successful `draw()`, if a stored this-run level is outside `ydom`, write that on `#price-chart-status` (e.g. `Bear 369,824 off-chart`); do not invent a second status node, and do not overwrite load/error sentences. Legend matches what is drawn (weighted + other sessions). `touchmove` / `touchend` next to existing `touchstart`. Size `pad.l` from the longest Y tick in `layout()`. **Stage height:** set one `.chart-stage` rule (`min-height: 260px; height: min(42vh, 320px)`), delete the 220px leftover; do **not** edit the `@media (max-width: 800px)` block a11y-phone will move to 1100px. `.swatch-weighted` may be added next to the existing swatch rules (not chrome). Keep price-centric `domainY`.
- **Why:** Repetition (tooltip is a worse readout). Error surface: status already means load/error; a second element or a silent clip is the viz F4 bug. File-ownership collision is change amplification with Wave 4 parallel. The 220/280 split is temporal leftover, not a product choice. From-scratch the chart module owns its stage and its copy; a11y-phone owns disclose/breakpoint/overflow, not this height.
- **When:** `this change`

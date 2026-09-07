# Strategic design review — Wave 3 ui-decision-blotter

Target: Session 3 plan (`PLAN.md` § Session 3), `eng/sessions/2026-09-06-ui-decision-blotter/{AGENT_BRIEF,issue,feature_list}.json`, current `runs_table.html`, `run_detail.html`, `catalog_api/client.py`, `export_compare_db.py`, `quotes.js`, `runs_query.py`, `runs.js`.
Grain: feature / implementation plan. Not implemented. Product CSS/HTML not edited.

### Verdict
- **Direction:** `mixed`
- **Why:** Wave 3 exists so an operator’s first glance is ticker · as-of/live · FV · MoS · Downside · stored duration · process audit, without a second fair value. Designed from scratch, that is **one catalog-backed blotter record** (named stored fields, omit if missing) plus **one list grain** (opt-in latest-per-ticker, as-of Downside sort as a query expression) painted by the existing Jinja table and run sheet; live Yahoo stays a chip overlay. The product shape in the plan (compose in this tree, display-only, chip not cell, empty `/` stays the dump until a visible Latest control, strip then valuation then chart) is that design. The *work split* is not: seven template/CSS/JS slices plus “thin extras projection” still lets the implementer unique the current 50-row page, `json.loads` `extras_json` in Jinja, hang Downside sort off a live overlay name, and paint duration `pass` with the Audit PASS badge — a patch around today’s `SELECT *` dict. Reshape the session so `catalog_api` + `RunQuery` *is* the blotter interface and HTML only ranks and labels it.
- **Do:** `reshape`

### Keep
- FastAPI + Jinja + small JS. No SPA, no second FV, no live MoS, no JS DCF. Archive immutable. Export already writes `decision_action` into extras and `verdict_line` as a sqlite column — do not reopen `export_compare_db.py` or add sqlite columns this wave.
- Audit stays process completeness; duration is the stored snapshot action; missing → omit, do not invent.
- Downside stays display math vs **stored** bear; live overwrite in `quotes.js` only; server sort (when added) is as-of, never the mutated cell. That honors the 2026-09-04 overlay decision instead of promoting Downside to a catalog FV.
- Empty `/` remains the catalog session dump until Latest is chosen. Shareable GET + `runs.js` “do not replay onto empty `/`” is a real compatibility constraint; opt-in Latest is the right first grain, not a silent default flip.
- `quotes.js` is the live module: signed % chip, price in default ink, loading `…` + `aria-busy`, still quote the first 50 when over cap. Do not reuse `.badge.pass` green for day-change.
- Sequential `run_detail.html` with Wave 4: this session owns strip + valuation **order**; run-reading owns football PNG, chart JS, CIO CTA. Do not link football fields here.
- Column rank Ticker · Session · As-of · Live · FV · MoS · Downside · Duration · Audit, context columns `desktop-only`, currency on As-of. Phone stack-table already has this strip; desktop should match it.
- Feature-list slices can stay as *verify checkpoints* once the catalog/query interface is named; they should not be separate modules.

### Candidates

### 1. Catalog blotter record (named fields, extras stay inside catalog_api)
- **Change:** In `list_runs` / `get_run` (one hydrate next to `_row_to_dict`), lift `verdict_line` (column), `decision_action` (extras), and `cheap_claim` (`extras.roic_cheap_claim`) onto the run dict the UI already renders. Missing keys omitted or null. Templates and `/api/runs` read `run.decision_action`, never `extras_json`. Do not add a `Run` dataclass — rows are dicts; a wrapper would be a shallow module. Export already stores the facts; this wave only projects them. Comment at the hydrate: extras blob is not a UI API.
- **Why:** Information leakage / unknown unknown. Today `SELECT *` may include `extras_json` as a string (and test schemas often lack it). Parsing in Jinja or `pages.py` copies the extras shape into the web app; jobs-portfolio will need Duration too and would duplicate the parse. From-scratch, catalog_api is the only extras reader.
- **When:** `this change`

### 2. Latest and as-of Downside sort are RunQuery grains, not page tricks
- **Change:** Add `latest: bool` (or equivalent) to `RunQuery`. `list_runs` / `count_runs` return at most one row per ticker (newest `session_date`, then `session_key`) **after** the existing filters, then apply sort/limit. Wire one GET key through `runs_query.RUN_QUERY_KEYS`, `_filter_href`, `runs.js` `QUERY_KEYS` (same list as today). Visible Latest vs All on `runs.html`; Reset / empty `/` omit the key. Add allowlisted sort `asof_downside_pct` as a SQL expression on stored `asof_price` vs `fv_bear` — not a `downside_pct` field on the run, not `data-sort="downside_pct"` (tests already treat that as overlay-not-sort). Default first-dir for that key is desc. Do not unique-by-ticker in Python on the current LIMIT 50 page.
- **Why:** Temporal decomposition / unknown unknown. Unique-ing 50 rows is not latest-per-ticker (AVGO×5 on a prefix; 89 matching). Dropping the GET key from `QUERY_KEYS` makes fragment fetch and “← Runs” forget Latest. Sorting the live-mutated cell, or stuffing `downside_pct` onto `/api/runs`, reopens the overlay-as-catalog-key design this tree already rejected. From-scratch, the blotter grain lives next to `comparable_only`.
- **When:** `this change`

### 3. Duration is not Audit
- **Change:** Duration column and run-detail strip show the stored action (`initiate|add|hold|trim|sell|short|pass|too_hard`) under the header **Duration**. Do **not** pipe it through `verdict_badge` (`s.upper() == "PASS"` would paint duration `pass` as Audit green — the exact false buy cue this wave exists to kill). Audit label becomes process completeness (e.g. “Audit (process)”). `verdict_line` is the one-line run-detail subhead; cheap claim belongs on the strip, not as a 10th list column. List legend: MoS vs base · as-of; Downside vs bear · live if printed else as-of. `.below-bear` is signed ink on negative Downside, not a green fill.
- **Why:** Special–general mixture / nonobvious code. Two English words `pass`/`PASS` already collide; sharing the badge interface makes the collision a visual fact. Pull the distinction down into one display rule instead of hoping column order is enough.
- **When:** `this change`

### 4. Own the surfaces the brief omitted; run sheet is strip then valuation, not grid2
- **Change:** AGENT_BRIEF / file ownership must name `runs_query.py`, `runs.js` query keys, `pages.py` `_SORT_HEADERS` / `_NUMERIC_SORT`, `templating.py` (duration ≠ audit badge; visible Downside vintage class), and `.decision` / `.below-bear` in `app.css`. Wave 3 owns those selectors; `ui-a11y-phone` must not restyle them and must not start in parallel on `app.css` (it is currently “after Wave 2”). Serialize a11y-phone after this session **or** partition: blotter-only rules in a marked block a11y-phone will not rewrite. On `run_detail.html`: decision strip + **full-width** Valuation above `#price-chart`; Context is not a twin `.grid2` column. Preserve (or add, since this session owns the table) session→run identity links Wave 2 wanted without Wave 2 editing `runs_table.html`.
- **Why:** Change amplification / overexposure. The brief lists templates + “thin catalog projection” + quotes.js; the load-bearing files for Latest/sort/type are unnamed, and PLAN already lets a11y-phone write `app.css` the same day. Moving Valuation above the chart but keeping `.grid2` with Context leaves visual F4 intact. From-scratch, type rank is part of the blotter, and the run sheet’s first screen is the call, not a 280px empty chart beside Exported-at.
- **When:** `this change`

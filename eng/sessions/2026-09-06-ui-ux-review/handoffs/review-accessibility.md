# Review: Accessibility (WCAG 2.2 AA)

## Verdict

This is a keyboard-reachable operator tool with real landmarks, labeled forms, and a few genuine ARIA wins (theme toggle, chart `role="img"`, compare checkbox names). It is not yet AA. The first Tab on every page lands on a 1px-clipped Menu checkbox whose label is `display:none` on desktop, so focus looks like it vanished — that single chrome bug will make a keyboard user conclude the site is not keyboardable. Highest-leverage change: in the same `base.html` + `.disclose` pass, take `#nav-open` / `#filters-open` out of the desktop tab order, paint a visible focus ring on the phone Menu/Filters label, and add a skip link in front of the nine header links.

Live limits: `/` (50 runs), `/runs/research:000660.KS:2026-07-29`, `/analyze`, `/analyze/new`, `/compares`, `/compares/new`, `/experiments`, `/calibration`, `/health`, `/portfolio` (empty book). `/architecture` returned FastAPI JSON 404 in this process; `/harness` rendered `workflow_spec failed` instead of tiles. Architecture pan/zoom and harness inspector are reviewed from templates/JS.

## Findings

### F1 — Disclose checkboxes are unnamed, clipped, and first in the tab order
- **Severity:** P0
- **Pages:** all (`base.html` Menu); `/` Filters
- **Evidence:** Live `<input id="nav-open" class="disclose" aria-controls="site-nav"/>` with no `aria-label` / `aria-expanded`. `.disclose` in `app.css` is `clip: rect(0,0,0,0); width/height: 1px` (still focusable). `.disclose-btn` is `display: none` above 800px, so the associated “Menu” / “Filters” name is gone on desktop. Phone: the visible 44px label is not a tab stop; Tab still hits the 1px box. Checking the box on desktop does nothing (panel hide is inside the 800px query only).
- **Why it matters:** WCAG 2.4.7 Focus Visible and 4.1.2 Name, Role, Value. First Tab on every page is an invisible, often unnamed checkbox. Sighted keyboard users think focus is broken; SR users hear a mystery checkbox before Runs.
- **Recommendation:** Desktop (`min-width: 801px`): `display: none` on `.disclose` and `.disclose-btn` (panel already stays open). Phone: keep the CSS checkbox, add `aria-label="Menu"` / `"Filters"` on the input, and `.disclose:focus-visible + .disclose-btn { outline: 2px solid var(--header-link); outline-offset: 2px; }`. Do not add a JS menu unless the checkbox-hack focus ring still fails.
- **Keep vs reshape:** Keep the CSS disclose mechanism (shipped phone chrome). Reshape only the desktop tab order and focus painting.

### F2 — Nine header links, no skip link, no current page
- **Severity:** P1
- **Pages:** all chrome
- **Evidence:** Live `base.html` has `<header>` → 9 `<nav>` links + theme button, then `<main>` with no `id`. No skip control in the HTML. No `aria-current="page"` on any nav item (Runs is `id="nav-runs"` only).
- **Why it matters:** 2.4.1 Bypass Blocks is A (required for AA). Every keyboard session tabs the whole chrome before the ticker field. Current page is visual-only.
- **Recommendation:** First focusable in `base.html`: `<a class="skip-link" href="#content">Skip to content</a>`, `id="content"` on `<main>`. Show the skip link on `:focus`. Set `aria-current="page"` on the matching header link in the template (or a one-line `theme.js`/`runs.js` sibling).
- **Keep vs reshape:** Keep the 9-link server nav. Do not collapse it into a JS menubar.

### F3 — Runs fragment swap drops focus, desyncs compare picks, and rarely announces
- **Severity:** P1
- **Pages:** `/`
- **Evidence:** `runs.js` `fetchTable()` sets `#runs-results.innerHTML`. Sort links and `.compare-pick` live inside that node. `aria-live="polite"` is on the count `<p>` *inside* the swapped HTML (`partials/runs_table.html`), so the live region is destroyed and recreated rather than updated. `compares.js` `updateBar()` is not called after sort/filter (only on `change` and `catalog-changed`); new checkboxes render unchecked while `selected` still holds ids. `#compare-hint` and `#quote-status` are not live regions. `#quote-status` stays `hidden` until a cap/error.
- **Why it matters:** Keyboard sort (Enter on a header) dumps focus to `body` — back through Menu + 9 links. SR often hears nothing when the table changes. Compare “exactly two” becomes a ghost selection.
- **Recommendation:** Persistent `#runs-status` *outside* the swap with `aria-live="polite"` (count + abort). After `innerHTML`, restore focus to `a.sort.is-active` or the ticker input; dispatch something `compares.js` already listens to (or call a tiny `updateBar`). Put `aria-live="polite"` on `#compare-hint` for the two-select rules.
- **Keep vs reshape:** Keep fragment HTML (not a SPA). Fix focus + one stable live node.

### F4 — Night primary buttons fail 4.5:1
- **Severity:** P1
- **Pages:** all Night theme (`html[data-theme=dark]`): Filter, Compare selected, Start analysis, Compare form submit, chart chips are separate
- **Evidence:** `--btn-bg: #3b82f6` / `--btn-fg: #fff` → **3.68:1** (AA normal text needs 4.5:1). Light primary `#2563eb` on white is **5.17:1** (pass). Secondary `#fff` on `#64748b` is **4.76:1** (pass both themes). Header links `#93c5fd` on `#0f172a` / `#020617` are **9.90:1 / 11.19:1** (pass — the asked pair is fine).
- **Why it matters:** Night is a shipped first-class theme. Every primary action in Night fails 1.4.3. Light is mostly OK.
- **Recommendation:** Darken Night `--btn-bg` to something ≥4.5:1 with white (e.g. `#2563eb`, same as Light) in the `html[data-theme="dark"]` table in `app.css`. One token, no component rewrite.
- **Keep vs reshape:** Keep the single chrome token table. Do not split button CSS per page.

### F5 — `--faint` (and one muted-on-page use) fails AA
- **Severity:** P1
- **Pages:** `/` and `/runs/{id}` live quote “daily close”; chart axis ticks; `/experiments` intro
- **Evidence:** `--faint: #94a3b8` on white **2.56:1** (`.quote-kind`). Chart grid text `--faint` on `--chart-stage #f8fafc` **2.45:1** (also fails 3:1 UI). Night `--faint: #64748b` on card `#1e293b` **3.07:1**. `.muted` on card white is **4.76:1** (pass); `.muted` on page `#f6f7f9` is **4.44:1** — `/experiments` puts the lead paragraph outside `.card`. chg-up/down `#14532d`/`#7f1d1d` on `#bbf7d0`/`#fecaca` are **7.52 / 6.93** (pass) and the signed `%` satisfies 1.4.1 Use of Color. Badges PASS/FAIL/running pass. Those chg fills are not theme-inverted; on Night they sit as light cells on `#1e293b` (surround contrast is high; not a text fail).
- **Why it matters:** “Daily close” and chart dates are the vintage a reader uses to trust the print. 2.5:1 is not readable.
- **Recommendation:** Point `.quote-kind` and `.chart-grid text` at `--muted` (or a new token ≥4.5:1 on both card and chart-stage). Wrap the Experiments lead in `.card` or use `--fg`. Leave chg-up/down hex as-is (they pass; color is redundant with `+`/`−`).
- **Keep vs reshape:** Keep semantic green/red fills. Retune `--faint` or stop using it for actual words.

### F6 — Phone stacked cards hide table headers from assistive tech
- **Severity:** P1
- **Pages:** `/`, `/analyze`, `/compares`, `/experiments`, `/calibration`, `/portfolio` (`.stack-table`)
- **Evidence:** At 800px `app.css` sets `.stack-table thead { display: none; }` and labels cells with `td::before { content: attr(data-label); }`. Live rows do have `data-label` (600 on `/`). `display:none` removes headers from the accessibility tree. CSS `::before` is unreliable as a name (NVDA/JAWS usually skip it). Pick column `<th class="pick"></th>` is empty (checkboxes have `aria-label` so desktop is OK).
- **Why it matters:** Leftover of the shipped phone restyle. A phone SR user hears unlabeled numbers (“35.5, 171.6, PASS”) instead of MoS / Downside / Audit.
- **Recommendation:** Do not `display:none` the thead. Clip it (same `.disclose` visually-hidden recipe) so headers stay in the a11y tree; keep `data-label` + `::before` for sighted cards. Empty pick `th`: `aria-label="Select for compare"` on `/` only.
- **Keep vs reshape:** Keep `.stack-table` + `data-label`. Do not fork a second card markup.

### F7 — Architecture figures pan/zoom are pointer-only
- **Severity:** P1
- **Pages:** `/architecture` (template `architecture.html`, `mermaid_boot.js`; live route 404 in this process)
- **Evidence:** `svgPanZoom` with `controlIconsEnabled: false`, wheel zoom gated on `pointerenter`/`pointerleave`, pan by drag. Only keyboard control is the generated Reset button. `.architecture-figure.is-interactive { overflow: hidden }` so a keyboard user cannot even scroll the SVG. Copy says “Drag… Wheel…”. WCAG 2.5.7 Dragging Movements (2.2 AA) and 2.1.1 Keyboard.
- **Why it matters:** If the diagram is larger than the frame, keyboard (and some SR) users cannot inspect it. Reset fits, but there is no non-drag way to pan to a node.
- **Recommendation:** Keep drag/wheel. Enable svg-pan-zoom `controlIconsEnabled: true` (or three small buttons: zoom in / zoom out / reset) inside `.architecture-figure`, keyboard-operable. Set `role="img"` + a short `aria-label` on the rendered SVG (or leave the mermaid source in a visually-hidden sibling).
- **Keep vs reshape:** Keep framed figures + Reset. Add a non-drag equivalent; do not require a new map UI.

### F8 — Harness tiles are buttons, but the inspector pattern is not keyboard-complete
- **Severity:** P1
- **Pages:** `/harness` (source; live page was `workflow_spec failed`)
- **Evidence:** Phase heads and agents are `<button>` (good). Phase head contains an `<h3>` (invalid: button content is phrasing-only; SR may double-speak heading + button). Inspector `#inspector-body` swaps with no `aria-live`, no `aria-controls`, no focus move. `harness.js` builds `role="tablist"` without `role="tab"` / `aria-selected` / `role="tabpanel"` — incomplete tabs are worse than no tabs (4.1.2). No `:focus-visible` in `harness.css`. Tiles have no 44px min-height (phone 44px rule in `app.css` applies to `button`, so they do grow on small viewports).
- **Why it matters:** The pipeline is the point of the page. Keyboard can click tiles; SR does not hear the inspector, and a fake tablist lies about widgets.
- **Recommendation:** Drop `role="tablist"`; two ordinary buttons is fine. Put `<h3>` *beside* the phase button, not inside. On select, `aria-live="polite"` on `#inspector` or move focus to the inspector heading (one or the other, not both).
- **Keep vs reshape:** Keep click-to-inspect tiles and on-demand Prompt. Do not build a full ARIA tab widget.

### F9 — Polish cluster (merge)
- **Severity:** P2
- **Pages:** chrome, `/runs/{id}`, `/portfolio`, `/health`, errors
- **Evidence:** No author `:focus-visible` anywhere (`grep` of css/js/html is empty) — UA outline is not `outline: none`, so 2.4.7 often still holds on light cards; dark header is the residual risk once F1 is fixed. Sort links have no `aria-sort`; indicator is `aria-hidden`. Chart readout/tooltip are hover/touch only; SVG `role="img"` plus the valuation table below is an acceptable text alternative — do not keyboard-plot every bar. `#price-chart-status` / `#quote-status` / `#live-flash` / `.flash` lack `role="alert"` or live. `error.html` and harness failure card have no heading. `/health` uses two `h1`s. Light perf bars `#86efac` / `#fca5a5` on white are **1.40 / 1.90** (1.4.11 non-text; `/portfolio` had no book live). Native compare checkboxes are below 24px (2.5.8; inline exception is arguable). Desktop range chips are small; phone already forces 44px.
- **Why it matters:** None of these block a session once F1–F8 are done.
- **Recommendation:** One `:focus-visible { outline: 2px solid var(--link); outline-offset: 2px; }` in `app.css`; `aria-sort` on the active `th`; `role="alert"` on `.flash` / `.err` when they appear; darker perf-bar fills on Light. Stop there.
- **Keep vs reshape:** Keep native controls and UA focus as the baseline.

## What already works

- `lang="en"`, viewport, `<header>` / `<nav>` / `<main>` landmarks, page `<h1>` on the primary screens.
- Theme toggle: `aria-pressed`, visible Night/Light text, `aria-label` that states the next action (`theme.js`). Tokens follow `prefers-color-scheme` until a click.
- Phone 44px targets for Menu, Filters, theme, form controls, and buttons (`app.css` 800px query) — leftover is the clipped checkbox (F1), not the 44px work.
- Filter/analyze/compare/portfolio/calibration controls wrap the input in `<label>`; range fields add `aria-label` (“MoS min”, “Session from”, …). Disclose checkboxes have no `name` (will not submit) — keep that.
- Compare picks: `aria-label="Select {ticker} {session_key}"` (50 on live `/`). Disabled Compare button until exactly two same-ticker ids (`compares.js`). Native `confirm()` on start.
- Abort paths: `role="alert"` on ticker-not-found (`runs_table.html`) and compares filter error.
- Chart: `role="group"` + `aria-label="Chart range"`, `aria-pressed` on chips (`price_chart.js` `setPressed`), SVG `role="img"` `aria-label="Price history with analysis overlay"`. Legend is a real `<ul>`. Signed live `%` plus fill (not color-only).
- `.stack-table` + `data-label` is the right visual phone pattern; `td.desktop-only` / `td[colspan]` exceptions are documented in CSS.
- No `outline: none`. Pass/fail/status badges include the word, not a color dot. `details/summary` for harness conventions.

## From-scratch keepers

- Server-rendered HTML + small JS (live cells, chart, theme). Native form controls and links.
- One token table in `app.css`; Night as `data-theme` (not a second stylesheet).
- CSS disclose for phone Menu/Filters, once F1 is applied.
- `.stack-table` cards via CSS on the same table, with a clipped (not `display:none`) thead.
- Price chart as an image plus range buttons and a numbers table — do not make the SVG a data grid.
- Compare as two named checkboxes + one button, not a drag-and-drop picker.

## Do not do

- React/SPA rewrite for a11y. Fragment swap is fixable (F3).
- A custom ARIA menubar or modal for the nine links. Skip link + `aria-current` is enough.
- Live-announcing every Yahoo print tick (noise). Announce table replacements and compare-hint / quote *errors* only.
- Recoloring chg-up/down as the sole up/down signal, or inventing a second FV to “explain” the chart to SR.
- Dropping `.stack-table` for a duplicate card template.
- AAA Focus Appearance / 44px everywhere on desktop. This is a localhost operator tool; 2.2 AA + keyboardable is the bar.
- Waiting on `/architecture` or `/harness` to be healthy before fixing F1–F5 — those are chrome/runs issues visible today.

# Playwright Wave 8 — ui-sheet (4516.T)

**Verdict: PASS** — cover-first order, English strip labels, bleached verdict HTML, `.table-scroll` (no `.stack-table` on strip/Context/Valuation), sibling vs comparable lists, phone document does not overflow, CIO cover H1 is the cover title (exactly one `<h1`).

- **URL:** http://127.0.0.1:8765/runs/research:4516.T:2026-09-06
- **Tooling:** Playwright MCP (`browser_resize` / `navigate` / `evaluate` / `click` / `snapshot` / `find`). No curl. Screenshots not used as proof.

## 1. Desktop 1440×900

`window.innerWidth × innerHeight` = **1440 × 900**. DOM evaluate (source index + `offsetTop` / absY + `compareDocumentPosition`), not a screenshot guess.

| Node | srcIndex | offsetTop | absY |
|------|----------|-----------|------|
| `img.football-field` | 76 | 439 | 439.41 |
| `a.btn` “Read CIO cover” | 78 | 986 | 985.77 |
| `#price-chart` | 100 | 1109 | 1108.55 |
| `.compare-form` | 242 | 2202 | 2202.44 |

`compareDocumentPosition` football→chart = **4** (`DOCUMENT_POSITION_FOLLOWING`); football→form = **4**; CIO→chart = **4**; CIO→form = **4**. Football PNG and CIO link are **above** the chart and Compare form in document order.

- Football: `img.football-field` exists; `src` = `/artifact?...path=charts%2Fvaluation_football_field.png`; `alt` = “Valuation football field”.
- CIO link text **exactly** `Read CIO cover`; `className` = `btn`.
- **H1:** `4516.T · 2026-09-06`; `className` = `""` (not `mono`).
- **run_id:** `<p class="mono muted">research:4516.T:2026-09-06</p>` (muted, not the H1).
- **Duration (strip):** visible text `Do not initiate`; `title="pass"` (token not shown as the cell text).
- **Cheap claim:** `Franchise MoS` (not `franchise_mos`).
- **Verdict HTML (escaped):** `&lt;strong&gt;&lt;code&gt;duration.action = pass&lt;/code&gt;&lt;/strong&gt; — Wide cone ((bull−bear)/base ≈116%) and &lt;code&gt;decision_usefulness=medium&lt;/code&gt; already blocked initiate/add at Phase 2; after stress, MATERIAL Uptravi cliff (haircut 28%, p=0.30) independently forbids initiate/add — MoS vs ¥3,448 is not a license to buy a cliff+binary cone (&lt;code&gt;registry/decision.json&lt;/code&gt;; &lt;code&gt;reopened_after_stress=true&lt;/code&gt;, &lt;code&gt;tsr_seen=true&lt;/code&gt;, &lt;code&gt;stress_bind.material=true&lt;/code&gt;).`
  - `innerHTML` around the verdict has **no** raw `**` and **no** backticks. `<strong>` / `<code>` present. `document.body.innerHTML.includes('**')` = false; backticks = false.
- **Tables:**
  - Strip (`th` As-of): parent `.table-scroll`; table `className` `""` (no `stack-table`).
  - Context (`th` Sector / region): parent `.table-scroll`; no `stack-table`.
  - Valuation (`th` As-of price): parent `.table-scroll`; no `stack-table`; inside `<details>` summary **Bear / base / bull / model**.
  - (Reports “File” table is inside “All reports” details, not one of the three required wrappers.)
- **sibling_links:** catalog has two 4516.T runs (`2026-08-04`, `2026-09-06`). Other session listed as `/runs/research:4516.T:2026-08-04` (text `2026-08-04`).
- **comparable_siblings → Grok select:** `select[name=run_id_b]` options = `(choose)` + `research:4516.T:2026-08-04` (`2026-08-04 · FV 5,534.81 · MoS 38.2%`).
- **`#price-chart-overlay` siblings:** comparable set only — `[{ run_id: "research:4516.T:2026-08-04", session_key: "2026-08-04", ... }]`. Same single peer as the Grok select.

## 2. Phone 390×844 (reload same URL)

`setViewportSize(390, 844)` then `goto` the run URL.

| | scrollWidth | clientWidth | equal |
|--|-------------|-------------|-------|
| `document.documentElement` | **375** | **375** | **true** |
| `document.body` | **375** | **375** | **true** |

`overflowDeltaHtml` = 0; `overflowDeltaBody` = 0. Nodes overflowing the viewport: **0 outside** `.table-scroll`; 13 inside `.table-scroll` (allowed). After opening Valuation details, html/body still 375 === 375.

(`innerWidth` 390 vs `clientWidth` 375 is the vertical scrollbar gutter; the **document** does not overflow horizontally.)

## 3. Click “Read CIO cover”

Landed: `http://127.0.0.1:8765/artifact?run_id=research%3A4516.T%3A2026-09-06&path=reports%2F00_4516.T_README.md`

- Count of `<h1` in document: **1** (DOM `querySelectorAll('h1').length` = 1; `outerHTML.match(/<h1\b/gi).length` = 1).
- That H1 text: **`4516.T — Nippon Shinyaku Co., Ltd. — CIO cover (2026-09-06)`** (cover title, not the raw filename as the only title).
- Filename `reports/00_4516.T_README.md` is a following paragraph, not the H1.

## 4. User interaction (run sheet)

Scrolled the run sheet. Clicked **Bear / base / bull / model** (`details.open` = true). Valuation table is **inside that details** and **after** `#price-chart` (`tableAbsY` 2046.30 vs `chartAbsY` 1081.06; `compareDocumentPosition` preceding = true). Rows include As-of / Live / FV bear·base·bull / weighted / p / MoS / Downside / Model.

## One-line verdict

**PASS** — football+CIO above chart/compare; H1 ticker not mono; duration “Do not initiate” (`title=pass`); cheap “Franchise MoS”; verdict bleached; strip/Context/Valuation in `.table-scroll` without `stack-table`; siblings `/runs/{id}` and overlay/Grok comparable-only; phone `scrollWidth === clientWidth`; CIO page one H1 titled as cover.

# Playwright Wave 9 — ui-job (wait page)

**Verdict: PASS** — wait page is `resume_hint` (phase wrap hidden when hint is non-empty); complete job offers `.btn` “Open catalog run” / “Read CIO cover”; artifact `<ul>` stays; reconcile/abandon notes are `.muted` on complete jobs; running jobs keep `meta refresh=15`; Wave 8 4516.T run sheet still has football + CIO above the chart.

- **Live app:** http://127.0.0.1:8765/
- **Tooling:** Playwright MCP (`browser_navigate` / `snapshot` / `find` / `click` / `evaluate` / `tabs` / `navigate_back`). No curl. No product-file edits.

## 1. `/analyze` → complete job (4516.T)

**Index:** http://127.0.0.1:8765/analyze  
Clicked ticker link `4516.T` (`/analyze/analyze:4516.T:2026-09-06`), Status complete.

**Job URL:** http://127.0.0.1:8765/analyze/analyze:4516.T:2026-09-06  
**Title:** `4516.T 2026-09-06 · Stock Research`  
**`data-analyze-status`:** `complete`  
**`data-analyze-id`:** `analyze:4516.T:2026-09-06`

| Node | Measurement |
|------|-------------|
| `#job-resume-hint` | text = `Session finalized. Audit PASS. No git commit.` (non-empty); `className` = `muted`; `hidden` = false; `display` = `block` |
| `#job-phase-wrap` | `hiddenAttr` = true; `hiddenProp` = true; `display` = `none`; `offsetParent` = null |
| `#job-phase-wrap` HTML | `<span id="job-phase-wrap" hidden=""> phase <span id="job-phase">done</span></span>` |
| Visible status line (`innerText`) | `complete` — **no** adjacent `phase orch` / `phase done` |
| `#job-status` | `complete`; `className` = `badge status-complete` |
| `Open catalog run` | `<a class="btn" href="/runs/research:4516.T:2026-09-06">` (class contains `btn`, not a bare text link) |
| `Read CIO cover` | `<a class="btn" href="/artifact?run_id=research%3A4516.T%3A2026-09-06&path=reports/00_4516.T_README.md">` |
| Artifacts | `<ul>` under heading `Artifacts`; **80** `<li>` |
| `#job-error` | empty, `className` = `muted`, `hidden` = true (no reconcile note on this job) |
| `meta[http-equiv=refresh]` | absent (complete; expected) |

### Click: Open catalog run

Landed: **http://127.0.0.1:8765/runs/research:4516.T:2026-09-06** (path matches `/runs/...`).

Back to job page: artifact `<ul>` still present (80 items).

### Click: Read CIO cover

Landed: **http://127.0.0.1:8765/artifact?run_id=research%3A4516.T%3A2026-09-06&path=reports/00_4516.T_README.md**

- `<h1>` count = **1**
- H1 text = **`4516.T — Nippon Shinyaku Co., Ltd. — CIO cover (2026-09-06)`** (cover title, not filename-only)
- Filename `reports/00_4516.T_README.md` is a following paragraph, not the H1
- Document title includes `CIO cover`

## 2. Reconcile / abandon copy (complete jobs with notes)

No live failed/cancelled/abandoned jobs in the Analyze table. Checked complete jobs that carry notes:

### COHR (abandon reconcile)

**URL:** http://127.0.0.1:8765/analyze/analyze:COHR:2026-09-03  
**status:** `complete` (`badge status-complete`); `abandoned` not shown as a loud badge.

| Node | Measurement |
|------|-------------|
| `#job-resume-hint` | `ABANDONED: specialist spawn failed. …` (non-empty) |
| `#job-phase-wrap` | `hidden` = true; `display` = `none` |
| wrap HTML | `phase <span id="job-phase">orch</span>` still in DOM (token **not** mapped to English) |
| Visible status line | `complete` — **no** `phase orch` |
| `#job-error` | text = `abandon.json present on finalized session; not treating as abandoned`; **`className` = `muted`**; `hidden` = false |
| `.err` nodes | **none** |
| `Open catalog run` | `class="btn"` → `/runs/research:COHR:2026-09-03` |
| `Read CIO cover` | absent (no allowlisted `*_README.md`; contract is “if README allowlisted”) |
| Artifacts `<ul>` | 6 items (includes `registry/abandon.json`) |

### WHR (non-fatal error on complete)

**URL:** http://127.0.0.1:8765/analyze/analyze:WHR:2026-08-30  
`#job-error` = `unreadable phase_status`; **`class="muted"`**; no `.err`. Phase wrap hidden (`resume_hint` non-empty). Both `.btn` actions present.

## 3. Running jobs (refresh + resume_hint)

Two in-flight rows on `/analyze`: `000660.KS` and `SOFI` (both Status running). Opened both like a user.

### 000660.KS

**URL:** http://127.0.0.1:8765/analyze/analyze:000660.KS:2026-09-07  
**`data-analyze-status`:** `running`

| Check | Result |
|-------|--------|
| `meta[http-equiv="refresh"]` | present; **`content="15"`** (`<meta http-equiv="refresh" content="15">`) |
| `#job-resume-hint` | `New session: start at phase orch (sector_config + market_context); all agents pending.` (non-empty; hint sentence may mention orch — that is the hint, not the status-line token) |
| `#job-phase-wrap` | `hidden` = true; `display` = `none` |
| Visible status line | `running` — **no** adjacent `phase orch` |
| `#job-error` | empty, `muted`, hidden |
| `analyze_detail.js` | loaded (`/static/analyze_detail.js`) |

### SOFI

**URL:** http://127.0.0.1:8765/analyze/analyze:SOFI:2026-09-07  
Same pattern: refresh **15**; hint non-empty; wrap `hidden`/`display:none`; visible line `running`.

## 4. Wave 8 run sheet (no Wave 9 regression)

**URL:** http://127.0.0.1:8765/runs/research:4516.T:2026-09-06

`getBoundingClientRect().top` (viewport px):

| Node | y | class / notes |
|------|---|----------------|
| `img.football-field` | **490** | alt `Valuation football field`; src `…path=charts%2Fvaluation_football_field.png` |
| `a.btn` “Read CIO cover” | **957** | class exactly `btn` |
| `#price-chart` | **1104** | H2 `Price vs analysis` |
| `.compare-form` | **2175** | after chart |

Football and CIO are **above** the chart (490 < 957 < 1104). H1 remains `4516.T · 2026-09-06` (not `mono`). Wave 9 must not edit `run_detail.html`; this page still matches Wave 8 cover-first order.

## Observation (not a fail)

`/analyze` **index** still has a Phase column (`000660.KS` / `SOFI` = “Phase orch”; some complete rows “Phase done”). Wave 9 wait-page law is `analyze_detail.html` + JS; the list column is out of this wave unless `analyze.html` was already open. Wait pages themselves do not show adjacent `phase orch`.

## One-line verdict

**PASS** — 4516.T complete: hint hides `#job-phase-wrap`, `.btn` Open catalog run → `/runs/research:4516.T:2026-09-06`, `.btn` Read CIO cover → one H1 titled as cover, artifact `<ul>` remains; COHR/WHR reconcile notes `.muted` not `.err`; running jobs refresh=15 and hide phase wrap; Wave 8 football+CIO still above the chart.

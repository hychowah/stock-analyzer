# UI/UX review contract (analysis_web)

Parent session: `eng/sessions/2026-09-06-ui-ux-review/`
Live UI: `http://127.0.0.1:8765/`
Stack: FastAPI + Jinja2 + `apps/analysis_web/static/` (no SPA).

## Reviewer duty

Read-only review. **Do not implement.** Do not mutate `archive/research/**` or `archive/outcomes/**`. Do not `git commit`. Write one file under this `handoffs/` folder named in your prompt.

## Surfaces to cover

Visit the live pages (curl HTML if you cannot browse) **and** read matching templates/CSS/JS.

| Path | Template / JS |
|------|----------------|
| `/` | `templates/runs.html`, `partials/runs_table.html`, `static/runs.js`, `quotes.js`, `compares.js`, `live.js` |
| `/runs/{run_id}` | `run_detail.html`, `price_chart.js` |
| `/artifact?...` | `artifact.html` / `report.html` |
| `/analyze`, `/analyze/new`, `/analyze/{id}` | `analyze.html`, `analyze_new.html`, `analyze_detail.html`, `analyze_detail.js` |
| `/compares`, `/compares/new`, `/compares/{id}` | `compares.html`, `compare_new.html`, `compare_detail.html`, `compare_detail.js` |
| `/portfolio` | `portfolio.html` |
| `/harness` | `harness.html`, `harness.css`, `harness.js` |
| `/architecture` | `architecture.html`, `mermaid_boot.js` |
| `/experiments`, `/calibration`, `/health` | matching templates |
| shared chrome | `base.html`, `error.html`, `static/app.css`, `theme.js` |

Also skim `apps/analysis_web/README.md` and `ARCHITECTURE.md` § The website.

## Already shipped (do not re-propose as new work unless still broken)

- Phone chrome: Menu disclosure, 44px targets, `.stack-table` cards at 800px (`2026-09-05-ui-phone-comfortable`)
- Night/Light theme tokens + `theme.js` (`2026-09-05-ui-theme-switch`)
- Price vs analysis chart (`2026-09-02-price-chart-ui`)
- Live quotes + chg background (`2026-09-02-live-quotes-ui`, `2026-09-04-quote-chg-background`)
- Downside % column (`2026-09-04-runs-downside-pct`)
- Architecture figures pan/zoom (`2026-09-05-architecture-page`)
- IB portfolio join (`2026-09-05-ib-portfolio-v1`)
- Runs live search/sort (`2026-08-22-runs-list-search`)
- Analyze + Compare job UIs

If those still fail your lens, say **regression / leftover**, not “add phone layout.”

## Output format (mandatory)

```markdown
# Review: <persona name>

## Verdict
One paragraph: what this product feels like through your lens, and the single highest-leverage change.

## Findings
For each finding:

### F<n> — <short title>
- **Severity:** P0 (blocks use / trust) | P1 (hurts every session) | P2 (polish)
- **Pages:** routes
- **Evidence:** template/CSS/JS path + what you saw live
- **Why it matters** (your persona)
- **Recommendation:** concrete, file-level, one idea not a menu of options
- **Keep vs reshape:** would a from-scratch design keep today’s mechanism?

## What already works
Bullets. Credit shipped work.

## From-scratch keepers
What you would keep if redesigning the UI tomorrow.

## Do not do
Anti-goals for this persona (SPA rewrite, second FV, etc.)
```

Severity budget: at most **3 P0**, at most **8 P1**. Merge small nits into one P2. Rank by user harm, not by how fun the CSS is.

## Product constraints (do not violate in recommendations)

- Display math only: never invent fair value / MoS. Downside % from stored bear FV vs price is allowed.
- Server-rendered HTML is the product. Extra JS is OK for live cells, charts, theme — not a React rewrite unless you argue the current tree cannot scale (that is a high bar).
- One chrome token table in `app.css`. Phone restyle is CSS on the same markup (`.stack-table`, `.disclose`).
- App state under `apps/analysis_web/.local/` only.
- English UI copy. Localhost product for the operator who runs research, not a public SaaS.
```

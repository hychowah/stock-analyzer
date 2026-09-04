# Plan: background color on live price-change

**Superseded:** the pill-on-`%` winner (A) shipped first and was not visible as a Live-column background. Shipped shape is **B for the Live cell only** (not the whole row): `quotes.js` puts `.chg-up` / `.chg-down` on `td.quote-live`; CSS fills that cell. Hover is `tr:hover`; signed Live cells keep their own background because hover no longer paints `td`. Zero/missing stay unfilled. `/static` revalidates (`Cache-Control: no-cache, must-revalidate`).

## Goal

Make the live `%` next to last print scannable at a glance on the **runs list** (`/`) and **run detail** (`/runs/{run_id}`). Today it is sign-colored text only (green/red). Add a green/red **background chip** on that `%` span.

## Current shape

- `quotes.js` `fillCell` already classifies `change_pct`: `.chg-up` (>0), `.chg-down` (<0), `.muted` (0). Missing/error prints stay `—` with no chip.
- CSS (`app.css`): `.quote-live .chg-up` / `.chg-down` set **text color only** (`#14532d` / `#7f1d1d`).
- Both pages share the same Live cell (`td.quote-live[data-quote-cell]`) and the same `fillCell` renderer. Portfolio has no live quotes.

## Design it twice

| | A — chip on the `%` span | B — tint the Live cell (or whole row) |
|---|---|---|
| Signal | Isolated to the number that is the change | Mixes price, currency, “daily close”, and hover |
| Hover | `tr:hover td { background: #f8fafc }` does not fight the span | Cell/row background fights hover |
| Interface | Existing classes; CSS-only | New cell/row class from JS; extra zero/missing rules |
| Visual language | Chip chrome + local green/red | New table-tint convention |

**Winner: A.** Common case is “is this print up or down today?” The `%` already carries that fact.

## Review (2026-09-04)

From-scratch test passed. Three nits absorbed:

1. Do **not** extract `--pass-bg` / shared tokens. Hex stays on the quote sign rules. Green/red rhyme with `.badge.pass`/`.fail` for scan; that is palette coincidence, not shared meaning (up ≠ pass).
2. Group chip chrome (`display` / `padding` / `border-radius`) once on both sign selectors. Color + background stay on the two sign rules. Do not copy `.badge` font-size or gray fill. Keep selectors nested under `.quote-live`. No new JS class.
3. Dedicated test that those two selectors set `background` (presence, not hex). Do not hang it on `test_home_ticker_prefix_field`. Do not assert unchanged `quotes.js` class names. Browser check of up / down / flat / missing on both pages is the real W4 proof.

## What to change

1. **`apps/analysis_web/static/app.css`**
   - One grouped rule for chip chrome on `.quote-live .chg-up, .quote-live .chg-down`.
   - Per-sign: keep text colors; add `background: #bbf7d0` (up) / `#fecaca` (down).
   - Short comment on those rules: chip chrome, not `.badge`; colors rhyme with pass/fail for scan, coincidence of palette.
   - Zero stays `.muted` (no chip). Unstamped / error stays em dash.

2. **JS / templates / API** — no change.

3. **Tests** — dedicated method in `test_analysis_web.py`: the two sign selectors’ rule bodies include `background`.

4. **Browser** — runs list and run detail: up chip, down chip, 0% muted, missing `—`, hover still works.

## Non-goals

- Magnitude heatmap / opacity by |change|.
- Coloring MoS %, Downside %, as-of, or whole rows.
- Portfolio, Compare, Analyze.
- CSS variables / a shared pass-fail token system.
- Reusing `.badge` or adding `.chg`.

## Verify

- `python -m pytest apps/analysis_web/tests -q`
- `python scripts/eng_verify.py`
- Live `/` and `/runs/{id}`: exercise up / down / flat / missing.

## Risks

- Chip padding on a dense Live column: acceptable; tabular nums stay on the cell.
- Catalog index dirt (`archive/catalog/*.json`) is unrelated; do not include in this change set.

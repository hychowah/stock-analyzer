# Live portfolio day-move heatmap

**Mode:** B (W4 UI)  
**Session:** `eng/sessions/2026-09-10-portfolio-heatmap`  
**Home:** enhance `/portfolio` — do not add a second page  
**Not:** a new valuation, a second poll, a D3/vendor chart, or a what-if heatmap

---

## Goal — done means

1. `/portfolio` shows a **live heatmap** of stock holdings. Tiles update from the same `GET /api/portfolio/live-nav` poll that paints Live NAV (no extra fetch).
2. **Tile area** is `|day_pl|` of that holding: change % applied to the holding’s value (`qty × (last − prev_close) × stmt_fx`). A 2% move in a large lot is bigger than a 10% move in a tiny lot.
3. **Gainers cluster, losers cluster.** Ups are not mixed with downs. Wide: gainers left, losers right. Narrow: gainers above, losers below. Split width/height follows each side’s Σ|day_pl|.
4. Color is signed (green up, red down); fill intensity follows `|change_pct|`. Each tile shows ticker + change %. Unquoted / zero-move lots are omitted. Empty: one muted sentence.
5. Display math only. Stored FV / MoS / Downside are untouched.

---

## Current shape

| Piece | What it actually does |
|-------|------------------------|
| Live NAV poll | `live_nav.js` → `GET /api/portfolio/live-nav`. Paints `#live-nav`, day P/L, `[data-live-value]`, then `quotes-applied` for Live/Downside. Sole Yahoo fetch on this page. |
| Marker | `mark_live_nav`: lots + quotes → aggregates + per-lot `rows`. Each row already has `change_pct`. **`day_pl` is only the book sum**, not on the row. The per-lot term `qty × (live − prev_close) × fx` is computed and thrown away. |
| Book MTM | Statement-period P/L bars (`performance.mtm`). Not live. Gains-top / losses-bottom is a **list**, not a 2D map. |
| Quotes CSS | `.quote-chip.chg-up` / `.chg-down` (semantic hex, not chrome tokens). |
| Charts | `price_chart.js` is run-detail SVG. What-if has `path.svg`. No treemap. |

The page already has the facts a heatmap needs. It does not project them.

---

## Design it twice

### A — Live-nav is the engine; heatmap is a signed two-region projection (winner)

Three jobs, three homes:

```text
mark_live_nav  →  each row.day_pl   # identity, same term as the book sum
live_nav.js    →  live-nav-applied  # body.rows after the existing paint
heatmap.js     →  SVG tiles         # split by sign, squarify each side by |day_pl|
```

```
day_pl_i = qty_i × (live_i − prev_close_i) × stmt_fx_i   # None if unquoted / no prev
Σ day_pl_i  =  body.day_pl                              # already on the payload
area_i      ∝  |day_pl_i|
```

Layout (one function, no library):

1. Keep lots with a numeric non-zero `day_pl`.
2. Partition `{day_pl > 0}` vs `{day_pl < 0}`.
3. If both sides exist, split the canvas by Σ|day_pl| (vertical split when width ≥ height, else horizontal).
4. Squarify each side independently (Bruls / van Wijk / van de Wetering). Sort each side by `|day_pl|` descending so large movers sit first in the cluster — not a global mix.

HTML: one empty `#heatmap` stage on the Book page (after the Live NAV card, before Change in NAV). First paint does not wait on Yahoo. Caption states the area identity in English.

**Why this is from-scratch:** the marked book is what callers already know; the map is a projection of those rows. Size is a fact (`day_pl`); clustering is display. One poll, one writer of `#quote-status`, no second resource.

### B — New `/heatmap` resource + mixed squarify + |change_pct| as area (rejected)

A fourth GET, a `HeatmapView` type, a second Yahoo path or a pass-through of live-nav, and a vendor treemap that interleaves green and red because the algorithm is global. Area ∝ `|change_pct|` makes a 40% move in a 0.2% weight look like the book. Hides that the heatmap **is** live-nav rows.

---

## What to change

### Marker (`services/live_nav.py`)

Put `day_pl` on each row (None when the lot cannot mark vs `prev_close`). Book `day_pl` stays the sum of those terms. Do not invent a second formula.

### Event (`static/live_nav.js`)

After a successful paint, dispatch `live-nav-applied` with `{ rows }`. Heatmap does not fetch. Keep `quotes-applied` as-is (Live cells / Downside).

### Heatmap (`static/heatmap.js` + `templates/portfolio.html` + `static/app.css`)

- Stage: `<div id="heatmap" class="heatmap">` + SVG; `#heatmap-status` for empty/error.
- Paint on `live-nav-applied`. ResizeObserver reflows without refetch.
- Tile: ticker, signed `change_pct`; `title` has ticker, change %, day P/L.
- Hide the label when the rect is too small to read; keep `title`.
- Colors reuse the existing chg-up / chg-down family (semantic hex). Intensity from `|change_pct|` clamped (e.g. 0–8%).
- Dark theme: same semantic fills, readable label ink.
- Script tag next to `live_nav.js` (defer).

### Tests

- `test_live_nav.py`: META fixture `day_pl` = `10 × (55 − 50) × 8`; `700` with flat print is `0` or omitted from the map; book `day_pl` equals Σ row `day_pl`.
- Page hooks: `#heatmap`, `/static/heatmap.js`, caption about area = |day change|.
- `live_nav.js` contains `live-nav-applied` and still does not call `/api/quotes`.
- `heatmap.js`: no `fetch(`/api/`; two-region split (gainers / losers) present in source.

### Docs

- `ARCHITECTURE.md` `/portfolio` row: one marked-book poll also paints the day-move heatmap.
- `apps/analysis_web/README.md`: same sentence on `/portfolio` and live-nav.

---

## Non-goals

- What-if / histories heatmap.
- Size by weight, market cap, or raw `|change_pct|`.
- Tick stream / WebSocket.
- Sector grouping inside a side.
- A new URL or nav item.
- Vendor chart libraries.

---

## Verify

```bash
python scripts/eng_verify.py
python -m pytest apps/analysis_web/tests/test_live_nav.py apps/analysis_web/tests/test_portfolio.py -q
```

Browser (required): run `python -m apps.analysis_web` (or the existing local server). Playwright subagent on `/portfolio`:

- Heatmap is present after live-nav lands; tiles exist when rows have day P/L.
- All green tiles share one region; all red tiles share the other (no interleaved checkerboard).
- Larger `|day_pl|` tiles are bigger than smaller ones on the same side.
- Header Live NAV / day P/L / holdings table still paint. Desktop and a phone viewport.
- Empty / failed live-nav: stage stays, no thrown overlay.

---

## Risks

- **Area vs % confusion.** Caption must say area is |dollar day change|, color is change %. If the user meant area ∝ `|change_pct|` regardless of size, that is a one-line layout key change, not a new API.
- **Squarify without grouping** would mix signs — the two-region split is load-bearing.
- **Label overflow** on small tiles: hide text, keep title.
- **Zero-move book** (all prints = prev close): empty sentence, not a blank card.

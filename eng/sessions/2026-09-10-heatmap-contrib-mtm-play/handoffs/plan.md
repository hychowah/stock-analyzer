# Heatmap NAV-contribution % and playable MTM P/L

**Mode:** B (W4 UI)  
**Session:** `eng/sessions/2026-09-10-heatmap-contrib-mtm-play`  
**Home:** enhance `/portfolio` Book — do not add a second page  
**Not:** a new valuation, a live-nav poll, a what-if path, or a vendor chart

Absorbed SDR (Direction mixed → reshape): Live vs period mode (not a 1D chip); one `holding-pl-applied` event and exclusive writer; path lots are the union of start and t (missing = 0).

---

## Goal — done means

1. Each live heatmap tile shows **two percentages**: the stock’s own `change_pct`, and **this holding’s contribution to my book** (`day_pl / live_nav × 100`). Title has both plus dollar P/L.
2. `/portfolio` Book has a **shared Live / period strip** (Live · 1W · 1M · YTD · statement) plus **Play / Pause** that drives both the heatmap and the MTM bars. Default is **Live** (existing poll + server-rendered IB MTM). Path chips enter **path mode**.
3. Path mode loads `GET /api/portfolio/mtm-path` once and plays daily frames. Heatmap area is `|pl|` (same two-region squarify). Extra % is `pl / start_nav × 100`. MTM bars follow the current frame (`signed_bar_rows` on the payload).
4. Display math only. Heatmap.js still does not fetch. Returning to Live restores poll tiles and the original IB tbody.

---

## Current shape

| Piece | What it actually does |
|-------|------------------------|
| Live NAV | `live_nav.js` → `GET /api/portfolio/live-nav`. Rows have `day_pl`, `change_pct`, `live_value_base`. Event `live-nav-applied` is `{ rows }` only. |
| Heatmap | Projects those rows: area ∝ `|day_pl|`, label = ticker + stock `%`. No second `%`. No `fetch`. |
| Book MTM | Server-rendered IB statement stocks via `signed_bar_rows`. One CSV window. No play. |
| Daily marks | `book_state.as_of_book` + `mark_book.mark_lots`. Used by what-if, not Book. |

---

## Design it twice

### A — Two engines, one tile event, Live vs period mode (winner)

```text
mark_live_nav     →  row.day_pl + row.contrib_pct     # Live; contrib = day_pl / live_nav
mtm_path          →  frames[{ t, rows, bars }]        # period; pl = value(t) − value(start)
                                                      # missing side = 0; None iff held unquoted
live_nav.js       →  holding-pl-applied               # only while mode is Live
mtm_play.js       →  holding-pl-applied + MTM tbody   # only while mode is path
heatmap.js        →  SVG from { ib_symbol, pl, change_pct, contrib_pct }
```

**Live (default).** Existing poll. Header + quotes-applied always. Tiles only if `data-mode="live"`. IB MTM tbody is the no-JS fact. Play disabled.

**Path.** Chips `1W` / `1M` / `YTD` / `statement` set `data-mode="path"`. One user-initiated GET (not a poll). Live-nav still paints the header and quotes, **does not** emit tiles. Player is the only tile/bar writer until Live resumes.

```
pl_i(t)        = value_i(t) − value_i(start)
                 not held on one side → 0
                 None only when a held lot is unquoted / unavailable
change_pct_i   = (close_t / close_start − 1) × 100   # listing, independent of qty
contrib_pct_i  = pl_i(t) / start_nav × 100
```

Names on a frame = union of lots at `start` and at `t`. Sold names keep `pl` (mark 0 after the sale). Do not stuff period P/L into `day_pl`. Do not put `live_nav` or `playing` on the tile event.

**Why this is from-scratch:** two engines (last-print vs daily walk), one projector schema, one mode so heatmap and MTM share a time base. Contribution is a named fact. Heatmap stays a projector.

### B — CSS grow of statement MTM + client-only extra % (rejected)

No period that means anything, no book walk, second % has no identity.

---

## What to change

### Marker (`services/live_nav.py`)

`contrib_pct` on each row when `day_pl` and `live_nav` are numeric and `live_nav ≠ 0`. Identity: `day_pl / live_nav × 100`.

### Event (`static/live_nav.js`)

Replace `live-nav-applied` with `holding-pl-applied` `{ rows: [{ ib_symbol, pl, change_pct, contrib_pct }] }` mapping `pl ← day_pl`. Emit **only** when `#book-pl-mode` is Live. Still sole writer of `#quote-status`. On `book-pl-mode-changed` back to Live, re-emit last rows. Do not recompute contrib from a book total on the event.

### Path (`services/mtm_path.py` + `routes/api.py`)

Pure module. No `alt_history_view`. `as_of_book`, `mark_lots` / `marks_on`, `HistoryService.get_many`, `range_for_span`.

`GET /api/portfolio/mtm-path?period=1w` → `{ period, start, end, start_nav, base_currency, frames: [{ t, nav, total_pl, rows, bars }] }`. Allowlisted: `1w`, `1m`, `ytd`, `statement`. Live is not this resource. Bad period → 400. Empty book → empty frames + English `error`. Each frame `bars` is `signed_bar_rows` on numeric `pl`. Path errors are not `#quote-status`.

### Player (`static/mtm_play.js` + shared strip on `portfolio.html`)

`#book-pl-mode` sits above Day move and is the time base for MTM too (waterfall stays between the two cards). Live chip vs path chips. Play / Pause / range. Fetches `mtm-path` in path mode. Dispatches `holding-pl-applied` and replaces `#mtm-tbody`. Restores cloned IB tbody on Live. Does not write `#quote-status`. Captions name Yahoo reconstruction vs the IB file.

### Heatmap (`static/heatmap.js` + CSS)

One listener: `holding-pl-applied`. Layout key is `pl`. Second label: `NAV` + `contrib_pct`. Hide NAV % before hiding the ticker. Title: ticker · stock % · NAV % · P/L. **No `fetch`.**

### Tests / docs

As in Verify. `ARCHITECTURE.md` `/portfolio` + README API row.

---

## Non-goals

- What-if / histories heatmap or playing those paths on Book.
- Intraday tick replay / WebSocket.
- Changing Live tile area (still `|day_pl|` / `|pl|` of that day).
- Vendor chart libraries / a new URL.
- Replacing IB statement MTM with Yahoo as the stored fact.
- Playing Live (one frame).
- Labeling Live as `1D`.

---

## Verify

```bash
python scripts/eng_verify.py
python -m pytest apps/analysis_web/tests/test_live_nav.py apps/analysis_web/tests/test_portfolio.py apps/analysis_web/tests/test_mtm_path.py -q
```

Browser: `python -m apps.analysis_web`. Playwright on `/portfolio`:

- Live tiles show stock % and NAV % after live-nav lands.
- Live does not call `/api/portfolio/mtm-path`.
- Select statement (fixture) or 1W: Play walks dates; regions stay signed; MTM bars follow; Pause stops; Live restores poll tiles and IB bars.
- Header Live NAV / day P/L / holdings still paint. Desktop and phone.
- No-JS: statement MTM table still in HTML.

---

## Risks

- **Two % on a small tile.** Hide NAV % first; keep both in `title`.
- **IB MTM vs Yahoo path.** Captions must not collapse them. Live keeps the IB table.
- **Poll vs Play clobber.** Exclusive emit by mode is load-bearing.
- **`heatmap.js` fetch test.** Player fetches; heatmap stays fetch-free.
- **What-if import.** `mtm_path` must not depend on `alt_history_view`.
- **FX.** Statement Forex close. No live FX series.

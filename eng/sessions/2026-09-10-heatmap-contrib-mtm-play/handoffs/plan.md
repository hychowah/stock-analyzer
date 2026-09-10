# Heatmap NAV-contribution % and playable MTM P/L

**Mode:** B (W4 UI)  
**Session:** `eng/sessions/2026-09-10-heatmap-contrib-mtm-play`  
**Home:** enhance `/portfolio` Book — do not add a second page  
**Not:** a new valuation, a live-nav poll, a what-if path, a heatmap film strip, or a vendor chart

Absorbed SDR (Direction mixed → reshape, 2026-09-10): one Book P/L writer for period Play; `live_nav.js` does not know mode.  
User correction: **Play animates Mark-to-market P/L bars, not the Day move heatmap.** Heatmap stays Live.

---

## Goal — done means

1. Each **Day move** heatmap tile shows **two percentages**: the stock’s `change_pct`, and this holding’s day P/L as % of Live NAV (`day_pl / live_nav × 100`). Title has both plus dollars. Tiles always come from the live-nav poll. Period Play does not paint the heatmap.
2. **Mark-to-market P/L** owns a **period strip** (Live · 1W · 1M · YTD · statement) plus **Play / Pause / scrub**. Live shows the server-rendered IB MTM table. A period chip loads `GET /api/portfolio/mtm-path` and Play walks those frames **on the bars**.
3. One time-base token on the MTM strip (`live` | `1w` | `1m` | `ytd` | `statement`). `live_nav.js` does not read it. Heatmap heading stays “Day move”.
4. Display math only. Heatmap.js still does not fetch. No-JS: IB MTM table stays in HTML.

---

## Current shape (after 046549d — wrong split)

| Piece | What it does now | What it should do |
|-------|------------------|-------------------|
| Heatmap | Also plays path frames; card still says “Day move” | Live day-move only, extra NAV % |
| Strip | Above Day move; `data-mode` + JS `period` + `aria-pressed` | On the MTM card; one `data-period` token |
| `live_nav.js` | Gates `holding-pl-applied` on mode | Always emit live tiles; no mode |
| `mtm_play.js` | Emits tiles + writes bars | Writes MTM bars only |

Python `mtm_path` identity is already right. Do not reopen it.

---

## Design it twice

### A — Heatmap is Live; MTM strip is the only period owner (winner)

```text
mark_live_nav  →  row.day_pl + row.contrib_pct     # contrib = day_pl / live_nav
live_nav.js    →  header, quotes-applied,
                  holding-pl-applied always         # pl ← day_pl; no mode
heatmap.js     →  SVG from that event               # fetch-free; heading Day move
mtm_path       →  frames[{ t, bars, rows }]         # pl = value(t) − value(start)
mtm_play.js    →  #mtm-tbody only                   # fetch, Play, captions
```

**Day move.** Unchanged poll. Extra % on tiles. Never calls `mtm-path`. Never listens to Play.

**MTM.** Strip lives on this card. Token `data-period`. Live = cloned IB tbody, Play disabled. Period = one GET, last frame painted, Play walks `bars` (width + P/L). Errors on `#book-pl-status`. Does not emit `holding-pl-applied`. Does not write `#quote-status` or `#heatmap-status`.

Path identity (unchanged):

```
pl_i(t)        = value_i(t) − value_i(start)
                 not held on one side → 0
                 None only when a held lot is unquoted
contrib_pct_i  = pl_i(t) / start_nav × 100   # on path rows; heatmap does not use them
```

**Why this is from-scratch given the user correction:** two engines stay; the film strip is a property of MTM, not of the live heatmap. Exclusive tile write is unnecessary once path does not paint tiles. SDR “one writer” still holds for **bars**: only `mtm_play.js` writes `#mtm-tbody` after first paint. `live_nav.js` is a poller, not a mode peer.

### B — Shared Live/path mode still driving both cards (rejected)

That is 046549d. Play on the heatmap contradicts “animation in Mark-to-market P/L”. It also forced the mutex the last review called a protocol, not an interface.

---

## What to change

### Plan / session

This file. Feature-list item for the reshape. `ARCHITECTURE.md` / README: Play is MTM bars; heatmap is live only.

### `live_nav.js`

Drop `bookPlMode`, `book-pl-mode-changed`, and the emit gate. Always map `pl ← day_pl` and emit `holding-pl-applied`. Still sole writer of `#quote-status`. Does not mention heatmap mode.

### `mtm_play.js` + `portfolio.html`

Move `#book-pl-mode` onto the Mark-to-market card. Rename to a single `data-period` (drop `data-mode="path"` and the parallel `period` var). Stop emitting `holding-pl-applied`. Stop touching heatmap captions/status. Play / Pause / scrub update `#mtm-tbody` from `frame.bars`. Restore cloned IB HTML on Live. Bar width uses a short CSS transition so Play is visible as motion, not only as new numbers.

### `heatmap.js`

Stay a projector of live `holding-pl-applied`. Empty copy: “No day moves yet”. No fetch.

### Tests / docs

- `live_nav.js` has `holding-pl-applied` and does **not** contain `book-pl-mode`.
- `mtm_play.js` fetches `mtm-path`, writes `mtm-tbody`, does **not** contain `holding-pl-applied`.
- Page: `id="book-pl-mode"` after “Mark-to-market P/L”, not before “Day move”.
- `ARCHITECTURE.md` `/portfolio`: heatmap extra %; Play walks MTM bars.

---

## Non-goals

- Playing the heatmap / changing Day move tile area.
- What-if / histories on Book.
- Intraday ticks / WebSocket / vendor charts.
- Replacing IB statement MTM as the stored / no-JS fact.
- Labeling Live as `1D`.
- Reopening `mtm_path.py` identity (union, missing = 0).

---

## Verify

```bash
python scripts/eng_verify.py
python -m pytest apps/analysis_web/tests/test_live_nav.py apps/analysis_web/tests/test_portfolio.py apps/analysis_web/tests/test_mtm_path.py -q
```

Browser: `/portfolio`

- Live heatmap: stock % + NAV %; does not change when 1W/Play runs.
- Live does not call `/api/portfolio/mtm-path`.
- On MTM card, 1W (or statement): Play walks bar widths and P/L; Pause stops; Live restores IB bars.
- Header Live NAV / day P/L / holdings still paint. Desktop and phone.
- No-JS: statement MTM table still in HTML.

---

## Risks

- **IB MTM vs Yahoo path.** Caption on the MTM card must name the played series. Live keeps the IB table.
- **Bar rebuild kills CSS transition.** Update width on existing rows (or set width after insert) so Play is motion.
- **`heatmap.js` fetch test.** Unchanged: heatmap has no `fetch`; player still does.
- **FX.** Statement Forex close.

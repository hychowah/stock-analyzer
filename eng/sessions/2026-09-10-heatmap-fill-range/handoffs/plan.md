# Heatmap fill-screen and period influence

**Mode:** B (W4 UI)  
**Session:** `eng/sessions/2026-09-10-heatmap-fill-range`  
**Home:** enhance `/portfolio` Book heatmap card — do not add a second page  
**Not:** a new valuation, a second P/L engine, playing the heatmap as a film strip, native Fullscreen API, or coupling the MTM Play strip to the map

This reopens “heatmap stays Live only” from `2026-09-10-heatmap-contrib-mtm-play`. That session’s user correction was **Play animates MTM bars, not the map**. This request is different: the map itself can show **holding influence over a chosen window** (last frame of that window, not a walk). Play stays on the MTM card.

Absorbed SDR (Direction mixed → reshape, 2026-09-10):

1. Named windows resolve once on the server. Heatmap chips GET `mtm-path?period=`; Show GET `start=`&`end=`. Fill From/To from `body.start` / `body.end`. Do not clone today−7 / YTD / statement dates in JS.
2. Live / range is one chrome+rows operation. `heatmap_range.js` owns token, heading, caption, status, chip pressed. Live restores cached `lastLiveRows` immediately (`heatmap-live`). A window clears tiles when the request starts. Failed fetch does not keep a range token over live tiles. `heatmap.js` is projector + fill + source gate only.

---

## Goal — done means

1. The Day move heatmap has a **Fill screen** control. The same SVG fills the viewport (chrome of the heatmap card stays: heading, range, caption, Exit). Escape and Exit restore the in-page stage. Tiles relayout to the new size (existing `ResizeObserver`).
2. The heatmap card has its **own time-base**: **Live** (today’s day-move from the live-nav poll) or a **from/to date window**. A window paints **one** map: last reconstructed frame of that range. Tile area is `|pl|` of that holding over the window; stock % is the listing move; NAV % is `pl / start_nav`. Gainers left, losers right.
3. Custom dates call the existing `GET /api/portfolio/mtm-path` with `start` and `end` (not a new resource). Period chips (1W / 1M / YTD / Statement) are shortcuts that fill those dates. Live does not fetch the path.
4. Display math only. `heatmap.js` still does not fetch. MTM Play strip is unchanged and does not paint tiles. No-JS: the empty stage and IB MTM table stay in HTML.

---

## Current shape

| Piece | What it does now |
|-------|------------------|
| `static/heatmap.js` | Fetch-free projector of `holding-pl-applied`. Squarify two regions. Observes `#heatmap` size. Stage is `min(42vh, 320px)`. |
| `static/live_nav.js` | Polls live-nav; always emits `holding-pl-applied` (`pl ← day_pl`). No mode. |
| `static/mtm_play.js` | Owns `#book-pl-mode` on the MTM card. Fetches `mtm-path?period=`. Writes `#mtm-tbody` only. |
| `services/mtm_path.py` | `build_mtm_path(start, end)` already walks daily frames with `rows[{ib_symbol, pl, change_pct, contrib_pct}]`. Public API only accepts `period ∈ {1w,1m,ytd,statement}`. |
| `templates/portfolio.html` | Heatmap card is heading + caption + `#heatmap` + status. No fill, no dates. |

Last-frame `rows` of `mtm-path` are already the heatmap’s period identity. The gap is: the API cannot take a free window, and the map cannot ignore live polls or grow to the viewport.

---

## Design it twice

### A — Heatmap card owns fill and its own time-base; path last-frame is the window (winner)

```text
live_nav.js        →  header + holding-pl-applied always     # unchanged
heatmap.js         →  SVG + fill-screen + mode gate          # still no fetch
heatmap_range.js   →  token + chrome; chips GET period=;
                     Show GET start=&end=; last frame → heatmap-range-applied
                     Live → heatmap-live (cached lastLiveRows, no wait)
mtm_path API       →  period= XOR start=&end=                # one calendar (resolve_period)
mtm_play.js        →  MTM bars only                          # unchanged
```

**Fill.** CSS class on `#heatmap-card` (`position: fixed; inset: 0; z-index`; stage `flex: 1`). Not `requestFullscreen` (hides the date controls; hostile on phones). Button `aria-pressed`. Escape / Exit clears the class. Same DOM, so `ResizeObserver` already relayouts.

**Time-base.** Token on the card: `data-heatmap-period="live"` or `"range"`. Default Live. Named chips call `?period=` (same `resolve_period` as MTM Play). Show calls `?start=&end=`. After either 200, From/To take `body.start` / `body.end`. `heatmap.js` paints `holding-pl-applied` when Live (always caches `lastLiveRows`); paints `heatmap-range-applied` when range; `heatmap-live` repaints the cache when the token returns to live. Exclusive SVG writer is still `heatmap.js`. Range chrome (heading, caption, status, chips) lives only in `heatmap_range.js`.

**Window.** Last frame only — influence over the selected period, not a film. Caption names the dates and `|period P/L|`. Heading is **Day move** on Live and **Holding influence** on a window.

**Why this is from-scratch given both user requests:** the map is a projector of `{ib_symbol, pl, change_pct, contrib_pct}` with a size and a time-base. Live is one source of those rows; a window’s last path frame is the other. Fill is a stage-size mode of the same projector. MTM Play remains a bar walker on a different card. One P/L engine per source (live-nav vs mtm-path). No shared strip protocol.

### B — Shared Book period strip drives heatmap + bars; native Fullscreen; new heatmap-path URL (rejected)

That is the 046549d shape the last review called a protocol, not an interface. Native Fullscreen hides the range UI. A second URL would clone `build_mtm_path`. Playing path frames on the map contradicts “Play is MTM bars.” Coupling the two cards means changing heatmap dates also rewrites the MTM table.

---

## What to change

### API (`routes/api.py` + `services/mtm_path.py`)

`GET /api/portfolio/mtm-path` accepts **either** `period` **or** `start`+`end` (YYYY-MM-DD, inclusive). 400 if neither, both, or `start > end`. Window path: `mtm_path_window(book, svc, start, end)` — same `build_mtm_path` + `window_listings`; `period` in the body is `""` or omitted. Token path stays `mtm_path_for`.

### Heatmap card (`templates/portfolio.html` + `static/app.css`)

- `id="heatmap-card"` on the Day move card. `data-heatmap-period="live"`. Stamp `data-period-from` / `data-period-to` from `view.ib` when present (date-picker hints, not the Statement window).
- Toolbar: Live · 1W · 1M · YTD · Statement chips (`data-heatmap-window`); From / To `type=date`; Show; Fill screen.
- `#heatmap-heading` so the range script can swap Day move / Holding influence.
- Fill CSS as in Design A. `body.heatmap-fill-open { overflow: hidden; }`. Phone: filled stage still uses the existing 1100px stack (gainers above losers).

### `heatmap.js`

- Fill toggle (class on `#heatmap-card`, Escape, `aria-pressed`). Layout-only.
- Source gate (header comment before the listeners): Live paints `holding-pl-applied` and caches `lastLiveRows` even during a window; range paints `heatmap-range-applied`; `heatmap-live` repaints `lastLiveRows` after the token returns to live. Still no `fetch(`. Empty copy “No day moves yet” only when Live. Does not write range heading/caption/status.

### `heatmap_range.js` (new)

- Owns the time-base end-to-end: token, heading, caption, `#heatmap-status`, chip pressed.
- Live: `data-heatmap-period="live"`, restore live heading/caption, dispatch `heatmap-live` (immediate cache paint; do not wait for the poller).
- Named chip: `GET /api/portfolio/mtm-path?period=1w|1m|ytd|statement`. Show: `?start=&end=`. On request start: set range token, heading Holding influence, dispatch empty `heatmap-range-applied` so day-move tiles do not sit under that heading, status loading. On 200: fill From/To from `body.start`/`body.end`, last-frame rows. Failed fetch calls Live restore with the error on `#heatmap-status` (no range token over live tiles).
- Does not write `#mtm-tbody`, `#quote-status`, or `holding-pl-applied`. Does not compute today−7 / YTD / statement dates.

### `live_nav.js` / `mtm_play.js`

Unchanged. Live poll keeps painting the header while the map is on a window.

### Tests / docs

- API: `start`+`end` returns frames; both `period` and dates → 400; `start > end` → 400.
- `heatmap.js`: fill class / Escape present; still no `fetch(`; still `holding-pl-applied`.
- `heatmap_range.js`: fetches `mtm-path`, dispatches `heatmap-range-applied`, does not contain `mtm-tbody`.
- `mtm_play.js` still does not contain `holding-pl-applied`.
- Page: `#heatmap-card`, Fill screen, date inputs, chips on the heatmap card (not the MTM strip).
- `ARCHITECTURE.md` `/portfolio` row and `apps/analysis_web/README.md`: heatmap fill-screen; Live or a from/to last-frame; MTM Play unchanged.

---

## Non-goals

- Animating / scrubbing the heatmap.
- Native Fullscreen API (`requestFullscreen`).
- Sharing `#book-pl-mode` with the map.
- A second path URL or a new P/L formula.
- What-if / histories heatmap.
- Intraday ticks / vendor treemap.
- Changing Live NAV header math.

---

## Verify

```bash
python scripts/eng_verify.py
python -m pytest apps/analysis_web/tests/test_live_nav.py apps/analysis_web/tests/test_portfolio.py apps/analysis_web/tests/test_mtm_path.py -q
```

Browser: `/portfolio`

- Default: live heatmap as today (stock % + NAV %). Fill screen grows tiles to the viewport; Exit and Escape restore; header Live NAV still updates.
- Pick 1W (or From/To + Show): heading becomes Holding influence; tiles are the window’s last frame; live-nav poll does not clobber them. Live chip restores day-move.
- MTM 1W / Play still walks bars only; does not change the map.
- Phone (≤1100px): fill-screen still stacks gainers / losers. Desktop and phone.
- No-JS: IB MTM table still in HTML; heatmap stage empty.

---

## Risks

- **Live poll clobbers a window.** Source gate in `heatmap.js` is the contract; tests must assert range script does not emit `holding-pl-applied` and heatmap ignores live events while `data-heatmap-period="range"`. Live chip must not wait for the next poll.
- **Two mtm-path consumers.** Heatmap range and MTM Play may fetch the same period independently. Do not share in-memory frames (that recouples the cards).
- **Date vs statement.** Do not clamp `end` to `period_to` — later fills exist. `max` on the input can be today.
- **Fill without a first paint.** ResizeObserver already no-ops until rows exist; fill an empty stage is a tall waiting card, not a hang.
- **ARCHITECTURE.md.** `/portfolio` currently says the heatmap stays live and does not play. Update that sentence in this change set.

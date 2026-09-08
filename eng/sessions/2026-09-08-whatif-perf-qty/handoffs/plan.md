# What-if: three views, visible partial sell

**Mode:** B (W4 UI)  
**Session:** `eng/sessions/2026-09-08-whatif-perf-qty`  
**Home:** `/portfolio/histories` — same frozen paper book as `2026-09-08-alt-history`  
**Not:** a new valuation, Live NAV, a broker, or a rewrite of replay identity

Absorbed SDR (Direction mixed → reshape): a history has **three views** with different I/O. Do not keep one `editor_payload` that does all of them. Bar sort and covering range live in `price_history`.

---

## Goal — done means

1. **Copy my trades** 303s onto an editor that already shows lots. That HTML GET does not fetch Yahoo and does not walk the NAV path.
2. **Show holdings** on a past date is paper-as-of-D plus that day’s marks. It does not rebuild the chart.
3. **Sell** takes a **visible quantity**. Selling 3 of 12 leaves 9. Buy qty is visible too.
4. Header Δ **is** the last path point (`nav = cash + Σ qty × daily close × stmt_fx`). Actual is this copy. No Live NAV.

---

## Current shape

Copy POST is already cheap (`create_from_ib`). The wait is the **303 onto the editor**, which calls `editor_payload`: sequential Yahoo `max` for every listing, then `compare_path` that **replays from seed on every bar day**. Changing the date is the same GET. Sell qty exists but is `.sr-only`, so Sell submits the whole lot.

---

## Design it twice

### A — Three views + one path walk (winner, after SDR)

```text
paper_on(hist, D)     → lots, cash, deceased     # replay only; no Yahoo
marked_on(hist, D, bars) → closes / values for D
nav_path(hist, bars)  → one overlay, two running books, last point = header Δ
```

```text
Copy POST                         persist History; no Yahoo
GET  /portfolio/histories/{id}    paper + chart shell + header placeholder
GET  /api/.../histories/{id}/holdings?date=   paper + marks (never path)
GET  /api/.../histories/{id}/path             walk (Yahoo + walk)
GET  /api/.../histories/{id}                  holdings-as-of, not a blob
```

JS: first paint is lots + visible qty; then path fills header/chart; date change hits holdings only. No-JS chart is the same path resource (`<img src=".../path.svg">`), not an `include_path` flag. Tests that care about Δ call `/path`.

Path algorithm:

```text
overlay = overlay_fills(seed, fills)          # once
actual_book, alt_book = seed, seed
for day in trading_days(fork, until):
    replay day's real fills  → actual_book
    replay day's overlay fills → alt_book
    mark both with last close ≤ day           # pointer per listing
    emit {t, actual_nav, alt_nav, delta}
```

Yahoo range and bar sort live in `price_history` (`range_for_span`, sort in `bars_from_closes`). `load_bars` / `close_getter` ask for a date span, not `"max"`. Parallel `HistoryService.get`; do not hold the lock across `backend.history`.

### B — Persist the path (rejected)

Derived marks depend on Yahoo. A saved path is a second cache. Holdings-as-of needs lots, not NAV. The slow part is the algorithm and the combined payload, not missing persistence.

---

## What to change

### `price_history.py`

- Sort `t` in `bars_from_closes`.
- `close_on`: bisect last bar `t ≤ date` (bars must be sorted). Same semantics as today’s scan.
- `range_for_span(start, end)` → allowlisted key covering a trailing Yahoo period from `end` back through `start` (`1y`/`2y`/`5y`/`max`).

### `alt_history.py`

- `compare_path`: the walk above. `compare_at` stays the single-day identity check.
- Do **not** change `replay`, `overlay_fills`, `mark_book`, seed freeze.

### `alt_history_view.py`

Replace `editor_payload` as the universe:

| Function | I/O | Used by |
|----------|-----|---------|
| `paper_on(hist, D)` | replay | HTML editor GET |
| `holdings_payload(hist, svc, D)` | replay + span bars for **D** | `/holdings`, date JS |
| `path_payload(hist, svc)` | span bars + walk | `/path`, list cards |
| `list_payload` | `path_payload` per card (Δ **is** the card) | list HTML/JSON |

`overlay_svg` consumes walk points, not per-day restart.

### HTTP

- HTML `GET /portfolio/histories/{id}` — `paper_on` + universe. No `load_bars`, no `compare_path`. Header NAV/Δ is a placeholder. Chart shell + `<img>` / JS fill from `/path`.
- `GET /api/portfolio/histories/{id}/holdings?date=` — holdings + marks. No `path`.
- `GET /api/portfolio/histories/{id}/path` — `{path, svg, actual_nav, alt_nav, delta}`. No `held`. Optional `GET .../path.svg` for no-JS `<img>`.
- `GET /api/portfolio/histories/{id}` — **holdings-as-of** (same as `/holdings`). Not held+path together.
- Date HTML GET `?date=` — `paper_on` only (same as first paint). Must not call `compare_path`.
- POST sell/buy error re-render — paper + error. Path still a separate resource.
- Sell 303 does not compute path on the server before the page exists.
- List API may still include per-card `path` because the card Δ is that path’s last point.

### UI

- Sell/buy qty: remove `.sr-only`. Labeled Qty, `max` = held, oversell 400.
- `alt_history.js`: fetch `/path` → header + SVG + hover; date form → `/holdings` → replace table.

### Docs

- `ARCHITECTURE.md` website row + quotes paragraph: editor first paint is the paper book; marks and path are their own GETs; copy does not mark.
- `apps/analysis_web/README.md` API table.

### Tests

- Walk vs `compare_at` (fork, a fill date, until) and vs a naive per-day restart on a multi-year synthetic book.
- Overlay-once walk vs `alt_state` (prefix overlay) on those days.
- `close_on` bisect = previous linear scan (holes, every bar later → None).
- `range_for_span` / `bars_from_closes` sort.
- HTML editor GET after copy: lots present; FakeHistoryBackend **calls empty** (no Yahoo).
- `GET .../holdings?date=` has `held`, no `path`; backend range is not `max` when a shorter span covers the fork.
- `GET .../path` has Δ; no `held`; independent of `date`.
- `GET /api/.../{id}` is holdings-as-of (no `path`).
- Sell qty not inside `.sr-only`; POST `quantity=1` of META 12 leaves remainder.
- No `live_nav.js`. List overlay chart still present.

### Verify

```bash
python -m pytest apps/analysis_web/tests/test_alt_history.py apps/analysis_web/tests/test_histories.py apps/analysis_web/tests/test_mark_book.py apps/analysis_web/tests/test_book_state.py apps/analysis_web/tests/test_price_history.py -q
python scripts/eng_verify.py
```

Browser: Copy trades → lots immediately; change date → holdings without ~10s; sell 1 of a lot >1; header Δ matches chart end once path loads.

---

## Non-goals

- Live NAV / last print on what-if
- Editing copied IB fills
- Persisting NAV paths
- Strategy optimizer
- Changing overlay clip rules
- Flipping leftover `passes: false` on `2026-09-08-alt-history`

---

## Risks

- **Identity drift** (full overlay then walk vs prefix overlay). Guard with `alt_state` / `compare_at` equality. Do not assume.
- **Yahoo periods are trailing from today**, not from fork. `range_for_span` must cover fork even when `until - fork` is short but fork is old.
- **No-JS header Δ** stays a placeholder; the chart `<img>` is the no-JS path. Acceptable: Δ is the chart’s right end.

---

## Feature list

1. **path-walk** — incremental `compare_path` + bisect `close_on` + `range_for_span` in `price_history`.
2. **three-views** — `paper_on` / holdings / path are separate; HTML GET has no Yahoo; date change is holdings-only.
3. **visible-qty** — sell and buy quantity on screen; partial sell HTTP.

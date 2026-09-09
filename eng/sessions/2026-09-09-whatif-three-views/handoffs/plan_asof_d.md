# What-if: the as-of book is D, and D means only D

**Mode:** B (W4 UI)  
**Lands in:** `eng/sessions/2026-09-09-whatif-three-views` (new session dir not writable)  
**Follows:** paper-book reshape (`c6ed54b`)  
**Absorbs:** 5-reviewer SDR, 4 of 5 mixed → reshape. Combined leftovers 1 and 2.  
**Not:** overlay 0-fill (disputed; one Keep, one candidate), Live NAV, stored paths, overlay clip / qty / cash math, list-card typing

---

## Goal — done means

1. `state_on(hist, D).as_of == D`. Seed vintage stays on `hist.seed.as_of`. Fill qty, cash, and overlay clip are unchanged.
2. `PaperView` is lots + cash + caveats as of D. No `history`. `PaperLot` has no `deceased`.
3. `HoldingsView` is `state_on` + `mark_alt`. No `deceased`. No `until`. JSON has no `deceased`.
4. `EditorPage` owns `history`, `paper`, `cash_today`, universe, fills, error, picker bounds, and `sold_later` (D listings missing from this copy’s actual today). No pass-through flatteners (`held`, `until`, …).
5. Holdings card shows cash as of D. Header keeps cash today. Date JS does not write holdings cash into the header.
6. HTML editor GET still does not fetch Yahoo. No Live NAV.

---

## Design it twice

### A — Stamp the snapshot; page composes two books (winner)

Replay still applies fills against the incoming book’s `as_of` (seed vintage on the first call). History-aware readers (`state_on`, `actual_state`, `alt_state`, `_apply_through`) stamp the requested through-date after that, including days with no fills. Fill floor and POST `day < hist.fork_date` stay as they are. Overlay clip is untouched.

Each as-of type has one date. Today-relative “sold later” is a set on the page. The holdings card is the D book (lots + cash on D). The header is today’s scoreboard (path + cash today).

### B — Keep `as_of` as seed vintage; hide it behind `view_date` (rejected)

That is the leftover the SDR named. Views would keep a second date of truth.

---

## What to change

### Cash book date (`alt_history.py`)

- After `replay` in `actual_state` / `alt_state`, if a through-date was given, `replace(book, as_of=D)`.
- `_apply_through` stamps `day` even when the batch is empty (bar day with no fills).
- Do not change `overlay_fills`, lot/cash math, or `day < state.as_of` inside `replay`.
- `mark_book` already copies `state.as_of` onto `MarkedNav`.

### Views (`alt_history_view.py`)

- Drop `deceased` from `PaperLot` / `HoldingsLot`.
- Drop `history` from `PaperView`.
- `EditorPage.history` is the aggregate. `sold_later: frozenset[str]`. Delete pass-through properties.
- `paper_on` builds lots from `state_on` only.
- `holdings_on` marks that same state; drop `until`; do not call `_paper_lots` for deceased.
- `sold_later_listings(hist, D)` = paper listings on D minus `actual_state(hist, today)`.

### HTTP / template / JS

- HTML GET still `editor_page`. Template binds `payload.history`, `payload.paper.*`, `payload.cash_today`, `payload.sold_later`, `payload.max_date` (not `until`).
- `held_table.html` takes `sold_later` and cash-on-D. Fragment and first paint use the same partial.
- Date JS still replaces the table only. Do not copy cash into `#hist-alt-nav` / header cash.

### Docs

- `ARCHITECTURE.md` website paragraph: holdings card cash is as of D; header cash is today.
- `apps/analysis_web/README.md`: same; holdings JSON has no `deceased`.

### Tests

- `state_on(hist, "2026-03-31").as_of == "2026-03-31"`; seed still `2025-12-31`.
- Walk vs `compare_at` still matches (qty/NAV identity).
- `PaperView` has no `history`; lots have no `deceased` / `close`.
- Holdings JSON has no `deceased`; cash on D equals `state_on`.
- `EditorPage` has `history` and `sold_later`; no `until` / `held` properties.
- HTML has `Cash (today)` and cash on the view date; no `live_nav.js`.
- HTML GET still does not call the price backend.

### Verify

```bash
python -m pytest apps/analysis_web/tests/test_alt_history.py apps/analysis_web/tests/test_histories.py apps/analysis_web/tests/test_mark_book.py apps/analysis_web/tests/test_book_state.py -q
python scripts/eng_verify.py
```

---

## Non-goals

- Overlay chart 0-fill of missing days
- Live NAV / last print on what-if
- Persisting NAV paths
- Changing overlay clip / replay qty or cash
- Typed list cards
- New valuation

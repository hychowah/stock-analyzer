# What-if: three typed views

**Mode:** B (W4 UI)  
**Session:** `eng/sessions/2026-09-09-whatif-three-views`  
**Follows:** `2026-09-08-whatif-perf-qty` (HTTP split, path walk, visible qty)  
**Not:** a new valuation, Live NAV, a replay rewrite, or a speed pass

Absorbed post-ship SDR (Direction mixed → reshape): the editor GETs were split; the **types** were not. `paper_on` still returns empty path slots. `holdings_payload` is that dict plus closes. `GET /{id}` is a second holdings URL. `compare_path(..., since=)` lets the list overlay leak into the path.

---

## Goal — done means

1. Three records, three I/O types. A payload cannot “forget the path” because path is not a field on paper or holdings.
2. Holdings-as-of-D is **one** JSON: `GET /api/portfolio/histories/{id}/holdings`. Cash on that resource is cash **as of D**. Header “cash today” is composed on the HTML page, not inherited by holdings.
3. `GET /api/portfolio/histories/{id}` is the history document (name, fork, fills) or it is gone. It is not holdings-as-of.
4. `compare_path` always starts at that history’s fork. List overlay joins walks on date; it does not ask a later fork to emit NAV before the copy exists.
5. Copy stays fast. Date change still hits holdings only. Sell qty stays visible. No Live NAV.

---

## Current shape (the leftover blob)

HTTP already matches the user’s three questions. The abstraction does not.

| Function | What it actually returns |
|----------|--------------------------|
| `paper_on` | Lots as of D, **cash as of today**, empty `path`/`svg`/`actual_nav`/`alt_nav`/`delta` |
| `holdings_payload` | `paper_on` with closes stuffed into `held` — still today’s cash, still empty path keys |
| `path_payload` | Walk. Clean. |
| `GET /{id}` | Same as `/holdings` plus decisions/caveats |
| `GET /{id}/holdings` | A slimmer slice of the same dict |
| `compare_path(..., since=)` | List overlay’s shared axis. Editor path omits `since`. Two series for one history. |

Template header reads `payload.alt_nav` / `payload.cash` from `paper_on`. JS overwrites NAV from `/path`. Cash today never comes from holdings.

---

## Design it twice

### A — Three frozen records (winner)

```text
PaperView     hist, view_date, lots as of D, cash as of D,
              deceased vs today’s actual, universe, decisions, error
              # no path, no svg, no Δ, no Yahoo

HoldingsView  view_date, lots + close + value as of D, cash as of D
              # no decisions, no path, no “cash today”

PathView      walk from fork → until, svg, last point = header Δ
              # no lots
```

HTML editor GET: `PaperView` + `cash_today` (a second `state_on` through today) + literal `—` for header NAV. Path JS fills NAV. Date JS replaces the table from `HoldingsView`.

```text
GET  /api/.../{id}              history document: id, name, fork, fills
                                no Yahoo, no held, no path
GET  /api/.../{id}/holdings     HoldingsView
GET  /api/.../{id}/path         PathView
GET  /api/.../{id}/path.svg     same SVG
```

`compare_path(hist, bars, until=)` starts at `hist.fork_date`. `overlay_svg_from_cards` already 0-fills missing `t`. Drop `since` from `compare_path` and `card_for`.

**Why this is from-scratch:** each view is one as-of and one I/O. Callers cannot confuse “cash today” with “cash on D.” List path and editor path are the same series.

### B — Strip keys, alias `GET /{id}` → `/holdings` (rejected)

Keep one dict, omit empty path fields, 302 the duplicate URL. Still one blob with optional holes. Still two holdings URLs (or a redirect that hides the leak). `since` stays if we “don’t touch path this round.” That is the patch the SDR named.

---

## What to change

### Types (`alt_history_view.py`)

Replace `paper_on` / `holdings_payload` dicts with frozen dataclasses (or NamedTuples) that **cannot** hold path fields.

```text
HeldLot     listing, qty, ib_symbol, catalog_ticker, currency,
            deceased, close?, value_base?

PaperView   history, view_date, until, fork_date, held: tuple[HeldLot],
            cash, caveats, universe, decisions, error, base_currency
            # cash = state_on(hist, view).cash_base

HoldingsView  view_date, fork_date, held (closes filled), cash as of D,
              base_currency

PathView    fork_date, until, path, svg, actual_nav, alt_nav, delta,
            base_currency
```

`editor_page(hist, *, view_date, universe, error)` is a thin HTML adapter: `PaperView` + `cash_today=state_on(hist, until).cash_base`. Header NAV keys are absent; the template prints `—` until JS.

`list_payload` / `card_for` consume `PathView` (or `compare_path` directly). No `since`.

### Path (`alt_history.py`)

Drop `since` from `compare_path`. Start is always `hist.fork_date`. Do not change `replay` / overlay / mark.

### HTTP (`histories.py`)

- HTML GET / POST error re-render: `editor_page`, not `paper_on` as a mega dict.
- `GET /api/.../{id}/holdings` — `HoldingsView` JSON. Cash is as of `date`.
- `GET /api/.../{id}` — history document only (`id`, `name`, `notes`, `fork_date`, `decisions`/`fills`, `base_currency`). **No** `held`, **no** `path`, **no** `date` query. No Yahoo.
- `GET /api/.../{id}/path` — `PathView`. Unchanged role.
- Tests that treated `GET /{id}?date=` as holdings move to `/holdings`.

### Template / JS

- Header cash binds `cash_today`. Holdings table still from paper lots on first paint (no closes until `/holdings`).
- Do not read `payload.path` / `payload.delta` from the HTML GET.
- Date JS already hits `/holdings`; keep that. Buy heading already follows `view_date`.

### Docs

- `ARCHITECTURE.md` quotes paragraph: `GET /{id}` is the document; holdings and path stay their own GETs; holdings cash is as of D.
- `apps/analysis_web/README.md` API table: same.

### Tests

- `paper_on` / `PaperView` has no `path` / `delta` attribute (or `assertNotIn` on `as_json`).
- `GET /{id}/holdings?date=D` cash equals `state_on(hist, D).cash_base`, not today, when they differ.
- `GET /{id}` has fills/name, no `held`, no `path`. HTML GET still does not call the price backend.
- `compare_path` has no `since`. Two histories with different forks: each card path starts at its own fork; overlay still renders; editor `/path` equals that card’s path.
- Existing: walk vs `compare_at`; partial sell; no `live_nav.js`; list overlay when ≥2.

### Verify

```bash
python -m pytest apps/analysis_web/tests/test_alt_history.py apps/analysis_web/tests/test_histories.py apps/analysis_web/tests/test_mark_book.py apps/analysis_web/tests/test_book_state.py -q
python scripts/eng_verify.py
```

Browser: copy still instant lots; date change still holdings-only; header Δ still last path point; cash today in the header while the holdings table is a past D.

---

## Non-goals

- Live NAV / last print on what-if
- Persisting NAV paths
- Changing overlay clip / replay identity
- Visible qty (already shipped)
- Speed of Yahoo itself (already parallel + span)

---

## Risks

- **Cash identity.** Tests and the muted line must say which cash is which: header = today; holdings JSON = view date. Mixing them again is the bug this increment exists to delete.
- **`GET /{id}` clients.** Only in-repo tests used it as holdings. Update those tests. No redirect that preserves the duplicate.
- **Overlay 0-fill.** Days before a later fork stay 0 on the overlay, not a fake pre-fork walk. That is overlay’s alignment, not the path’s.

---

## Feature list

1. **typed-views** — `PaperView` / `HoldingsView` / `PathView`; HTML adapter; one holdings URL; `GET /{id}` is the document.
2. **path-at-fork** — drop `since`; list overlay joins on date.

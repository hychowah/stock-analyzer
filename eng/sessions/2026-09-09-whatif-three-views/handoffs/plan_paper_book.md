# What-if: paper book is not the editor page

**Mode:** B (W4 UI)  
**Intended session:** `eng/sessions/2026-09-09-whatif-paper-book` (scaffold blocked: `eng/sessions` is not writable from this agent; land files here until a session dir exists)  
**Follows:** `2026-09-09-whatif-three-views` (typed views, path-at-fork, GET /{id} is the document)  
**Not:** a new valuation, Live NAV, a replay rewrite, a path persist, or a change to overlay clip

Absorbed post-ship SDR (5 reviewers; Direction mixed → reshape, 4 of 5). HTTP and the cash book are the from-scratch design. The leftover is one layer down: `PaperView` is still the editor bag with path keys deleted.

---

## Goal — done means

1. `PaperView` is the paper book as of D only. Lots, cash as of D, caveats, deceased-vs-this-copy’s-actual. No universe, no hyp fills, no error, no `until`, no close, no value, no path, no Δ.
2. `EditorPage` is a frozen HTML type: that paper + `cash_today` + universe + hyp fills + error + date-picker bounds. Routes and the template take `EditorPage`, not a dict unpacked from `PaperView`.
3. `holdings_on` builds `HoldingsView` from `state_on` + `mark_alt`. It does not construct a `PaperView`. Close and value exist only on the holdings lot type (a missing close is unquoted, not an omitted field).
4. One holdings table. First paint is paper columns (listing, qty, sell; close/value are “—”). Date JS replaces the table from the same Jinja partial rendered for `HoldingsView`. Delete the cloned table HTML in `alt_history.js`.
5. Holdings Yahoo span is fork → D, not fork → today. Copy stays fast. HTML editor GET still does not fetch Yahoo. Sell qty stays visible. No Live NAV.

---

## Current shape (the leftover blob)

The three GETs match the three questions. The types do not.

| Piece | What it actually is |
|-------|---------------------|
| `HeldLot` | Shared row with optional `close` / `value_base` — paper “forgets” marks the same way the old dict forgot path |
| `PaperView` | Editor bag: `history`, `universe`, `decisions`, `error`, `until`, plus paper lots |
| `paper_on(..., universe=, error=)` | Builds that bag |
| `editor_page` | Unpacks `PaperView` into an untyped dict and adds `cash_today` |
| `holdings_on` | Calls `paper_on`, throws away universe/decisions/error, stuffs closes into the same `HeldLot` |
| `history_document` | Hand-built dict (`decisions` for hyp fills) |
| First-paint table | Jinja in `history_detail.html` |
| Date-change table | Second copy in `alt_history.js` `renderHeld` |
| Holdings bars | `load_bars(..., start=fork, end=paper.until)` — today, not D |

`test_paper_view_has_no_path_fields` only checks path keys are absent. It does not check that paper cannot hold editor fields or marks.

---

## Design it twice

### A — Book, marked book, page (winner)

```text
PaperLot      listing, qty, ib_symbol, catalog_ticker, currency, deceased
              # no close, no value

PaperView     history, view_date, fork_date, held: tuple[PaperLot],
              cash as of D, caveats, base_currency
              # no universe, no decisions, no error, no until, no path

MarkedLot     PaperLot fields + close + value_base
              # close may be None when unquoted; that is a mark

HoldingsView  view_date, fork_date, held: tuple[MarkedLot], cash as of D,
              base_currency

EditorPage    paper: PaperView, cash_today, universe, decisions, error,
              min_date, max_date
              # frozen; template binds this, not a dict

HistoryDocument  id, name, notes, fork_date, fills, base_currency
                 # GET /{id}; keep wire key `decisions` if the API already shipped it
```

```text
paper_on(hist, D)              → PaperView          # replay only; no Yahoo
holdings_on(hist, svc, D)      → HoldingsView       # state_on + mark_alt
                                 bars: fork → D
editor_page(hist, D, universe, error) → EditorPage
                                 cash_today = state_on(hist, today).cash
GET  /api/.../{id}             HistoryDocument
GET  /api/.../{id}/holdings    HoldingsView (unchanged URL)
GET  /fragments/.../held       same held-table partial as first paint
```

HTML editor GET: `EditorPage`. Header NAV stays `—` until path JS. Date JS fetches the held-table fragment (JSON holdings stays for API tests). No-JS first paint is paper lots with close/value as “—”.

**Why this is from-scratch:** each record has exactly the fields of that question. Callers cannot confuse cash-today with cash-on-D by reading `PaperView`. Holdings cannot be “paper plus closes stuffed in.” The table has one renderer.

### B — Strip unused fields, keep one HeldLot (rejected)

Drop `universe` from `paper_on`’s return by omitting keys, keep `editor_page` as a dict, keep `holdings_on` → `paper_on`. Optional `close` stays on `HeldLot`. JS table stays. That is the patch the SDR named: holes moved from path keys onto lots and into the editor bag.

---

## What to change

### Types (`apps/analysis_web/services/alt_history_view.py`)

Replace the fat `PaperView` / shared `HeldLot`.

- `PaperLot` — no `close`, no `value_base`.
- `MarkedLot` — paper fields + `close` + `value_base` (`close` may be `None` when unquoted).
- `PaperView` — book as of D only. No `universe`, `decisions`, `error`, `until`, path, Δ.
- `HoldingsView.held` is `tuple[MarkedLot, ...]`.
- `EditorPage` — frozen: `paper` + `cash_today` + `universe` + `decisions` + `error` + picker bounds.
- `HistoryDocument` — identity + hyp fills; `.as_json()` for the API.

Functions:

- `paper_on(hist, *, view_date)` — no `universe`, no `error`, no `until`. Clamp against `utc_today()` and `fork_date` locally; do not store “today” on the paper type.
- `holdings_on` calls `state_on` / `_clamp_view` / `mark_alt` / `_marked_lots`. Do not call `paper_on`. `load_bars(..., start=hist.fork_date, end=view_date)`.
- `editor_page` returns `EditorPage`, not a dict. `cash_today = state_on(hist, utc_today()).cash_base`.
- Share lot-row construction that does not go through `PaperView` (`_paper_lots` vs `_marked_lots`). Deceased flag stays “not in today’s actual on this copy.”

Public JSON for `GET /{id}`: keep wire key `decisions` if tests and README already use it. The type field can still be `fills`.

### HTTP (`apps/analysis_web/routes/histories.py`)

- HTML GET / POST error re-render: pass `payload=editor_page(...)` as `EditorPage`. Jinja already uses attribute access (`payload.history`, `payload.cash_today`). Give `EditorPage` properties that compose paper + page extras (`held`, `view_date`, `fork_date`, `history`, `max_date`) so the template does not flatten through a dict. Do not unpack into a dict.
- Add `GET /fragments/portfolio/histories/{id}/held?date=` that renders `partials/held_table.html` from `HoldingsView`. `render_fragment` already exists. JSON `GET .../holdings` stays.
- Do not 302 `GET /{id}` to holdings. Do not call Live NAV.

### Template / JS

- Extract `apps/analysis_web/templates/partials/held_table.html`. First paint includes it with paper lots (close/value empty → `fmt_num` already prints “—”). Date JS fetches the fragment and sets `#hist-held-table` innerHTML. Delete `renderHeld`’s table string in `alt_history.js`.
- Caption and buy heading still update from `view_date` (date input or `data-view-date` on the fragment root).
- Header cash stays `cash_today`. Do not read cash from the holdings fragment into the header.

### Docs

- `ARCHITECTURE.md`: only if the fragment is a new user-facing surface — add it next to other fragments. Types themselves are not a map change. Do not churn the cash-book paragraph.
- `apps/analysis_web/README.md`: fragment row; restate that paper lots have no marks and holdings cash is as of D.

### Tests

- `PaperView` has no `universe`, `decisions`, `error`, `until`, `path`, `delta`. `PaperLot` has no `close` / `value_base`.
- `holdings_on` / `GET .../holdings?date=D` cash equals `state_on(hist, D).cash_base`. A `MarkedLot` may have `close is None`; the field exists.
- `editor_page` is `EditorPage`; HTML GET still has no `"path"` and does not call the price backend.
- `GET /{id}` still has name/fills, no `held`, no `path`.
- Holdings bar load: a spy/`HistoryService` records `end=D` when `view_date=D < today`.
- Held-table fragment HTML contains the sell qty input; date-change JS does not contain a `<table>` builder (no `renderHeld` clone).
- Existing: walk vs `compare_at`; partial sell; no `live_nav.js`; list overlay when ≥2; holdings cash today ≠ cash on an earlier D.

### Verify

```bash
python -m pytest apps/analysis_web/tests/test_alt_history.py apps/analysis_web/tests/test_histories.py apps/analysis_web/tests/test_mark_book.py apps/analysis_web/tests/test_book_state.py -q
python scripts/eng_verify.py
```

Browser: copy still instant lots (closes “—” until holdings); date change still holdings-only; header cash stays today after date change; holdings cash on a past D differs; sell qty visible; header Δ still last path point.

---

## Non-goals

- Live NAV / last print on what-if
- Persisting NAV paths
- Changing overlay clip / replay identity
- Changing `BookState.as_of` after replay (SDR candidate 2, **later**: today `replay` copies seed vintage through; do not mix that into this increment)
- Visible qty (already shipped)
- Speed of Yahoo itself
- New valuation

---

## Risks

- **Cash identity.** Header = today; holdings JSON = view date. Mixing them again is the bug the last increment deleted.
- **No-JS first paint.** HTML GET must not fetch Yahoo. Empty close/value on first paint is correct; the fragment fills them.
- **Wire key `decisions`.** Public `GET /{id}` already uses `decisions`. Keep the JSON key unless you update every test and the README in this same change.
- **Fragment vs JSON.** JSON holdings stays for API tests. The fragment is the table’s only HTML renderer.

---

## Feature list

1. **paper-not-editor** — `PaperView` is the book; `EditorPage` is the page; `holdings_on` does not call `paper_on`; `HistoryDocument` type; holdings bars fork → D.
2. **held-table-once** — one Jinja partial for first paint and date change; delete the JS table clone.

---

## Issue (for the new session when scaffold is possible)

```json
{
  "goal": "PaperView is the paper book as of D; EditorPage is the HTML page; holdings is not built from the editor.",
  "non_goals": [
    "Do not run research Phases 0–5",
    "Do not mutate archive/research or archive/outcomes history",
    "Do not call Live NAV from what-if",
    "Do not persist derived NAV paths",
    "Do not change overlay clip / replay identity",
    "Do not change BookState.as_of after replay"
  ],
  "work_type": "W4",
  "success_criteria": [
    "PaperView has no universe, decisions, error, until, path, or mark fields",
    "PaperLot has no close or value_base; MarkedLot does",
    "editor_page returns EditorPage, not a dict",
    "holdings_on does not call paper_on; holdings bars end at D",
    "One held-table partial; alt_history.js has no table HTML clone",
    "HTML editor GET still does not fetch Yahoo",
    "eng_verify.py passes"
  ]
}
```

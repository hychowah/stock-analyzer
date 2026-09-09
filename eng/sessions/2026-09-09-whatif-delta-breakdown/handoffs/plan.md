# What-if Δ breakdown (signed bars)

**Mode:** B (W4 UI)  
**Session:** `eng/sessions/2026-09-09-whatif-delta-breakdown`  
**Follows:** `2026-09-09-whatif-three-views` (typed paper / holdings / path)  
**Not:** a new valuation, Live NAV, a replay rewrite, or a date-picker Δ

Absorbed SDR (Direction mixed → reshape): the walk is the engine; contribution identity sits next to `MarkedNav`; signed bars take `(name, value)`.

---

## Goal — done means

1. The what-if editor shows a signed bar table of **why header Δ is that number**, in the same visual language as Book **Mark-to-market P/L** (name, bar, signed P/L).
2. Both tables **select** the largest names by `|value|` (top 20 + `other`), then **order** by signed value descending: largest gain at the top, largest loss at the bottom. Gains and losses are not mixed by magnitude.
3. Rows on the what-if table **sum to header Δ** (named + `other` + cash). Same mark, same day as the path’s last point.
4. Copy stays fast. First HTML paint still does not wait on Yahoo. Date change still hits holdings only.

---

## Current shape

| Piece | What it actually does |
|-------|------------------------|
| Book MTM | `portfolio._performance` takes IB stocks, `sorted(..., key=abs, reverse=True)`, top 20 + `other`, then `_bar_rows` for width/sign. Template: `portfolio.html` “Mark-to-market P/L”. Caption: “Largest 20 by \|P/L\| plus other.” |
| `_bar_rows` | Peak-normalizes width; does **not** sort. Left-origin bars (not a zero gutter). |
| What-if path | `compare_path` walks two books and **throws away** last-day `MarkedNav`. `PathView` is fork→until + svg + last NAV/Δ. `GET /path` fills header Δ and the chart. No per-name identity of Δ. |
| What-if holdings | As-of-D lots + paper Reg-T. Date picker is **not** header Δ. |

The ranking bug: `abs` sort puts a −90 loss between +100 and +40. The user wants −90 at the bottom.

---

## Design it twice

### A — Walk is the engine; one `(name, value)` bar table (winner)

Three modules, three jobs:

```text
walk_compare(hist, bars, until) → CompareWalk
  points: [{t, actual_nav, alt_nav, delta}, ...]
  actual: last MarkedNav | None
  alt:    last MarkedNav | None

compare_path = walk_compare(...).points     # overlay projection

contrib(actual, alt) → [(name, pl), ...]    # beside MarkedNav
  listing: alt_value − actual_value (unquoted = 0)
  Cash:    (alt.cash or 0) − (actual.cash or 0) when either cash is not None

signed_bar_rows([(name, value), ...]) → [{name, pl, bar_pct, sign}, ...]
  select top N by |v|, other nets the rest, order signed descending
```

`PathView.breakdown = signed_bar_rows(contrib(walk.actual, walk.alt))`. Empty path → empty breakdown. Raw `MarkedNav` does not appear on `PathView.as_json`.

```text
GET /api/portfolio/histories/{id}/path
  PathView + breakdown[]   # last point’s Δ, same fetch as the chart
```

HTML: empty table on the editor (next to the chart). JS paints `body.breakdown` in given order. Date change does not refetch it.

**Why this is from-scratch:** the walk is what callers know; the list is a projection. Subtraction is a mark-book fact; ranking is display. One pair in, one row out — MTM and Δ are adapters.

### B — New `/breakdown` resource; local sorts (rejected)

A fourth GET, a `BreakdownView` type, a second fetch, and two copies of rank policy. Hides that the breakdown **is** last-day path.

---

## What to change

### Walk (`alt_history.py`)

Named result `CompareWalk` (points + last actual/alt `MarkedNav`). `path_on_bars` builds `PathView` from that. `compare_path` is only `.points`. Do not widen the last series dict, return a tuple from `compare_path`, or call `compare_at` after the walk.

### Contribution (`mark_book.py`)

`nav_delta_rows(actual: MarkedNav, alt: MarkedNav) → tuple[tuple[str, float], ...]`  
Union of listings; missing/unquoted value is 0; cash as `"Cash"` when either cash is not None (missing cash as 0). Does not rank or paint. Identity: `sum(pl) == alt.nav - actual.nav`.

### Signed bars (`signed_bars.py`)

```text
signed_bar_rows(pairs: Iterable[tuple[str, float]], *, top_n=20, other_label="other")
  → list[{name, pl, bar_pct, sign}]
```

Select top N by `|v|`; remainder nets into `other` (omit if empty); sort displayed rows including `other` by signed value descending; peak-normalize among those rows. One module comment: select by `|v|`, then order signed (caption says both).

`_performance` maps IB stocks to `(ib_symbol, pl_total)` then `signed_bar_rows`. MTM template reads `row.name`. Delete `_bar_rows`.

`PathView.breakdown = signed_bar_rows(nav_delta_rows(...))`. JS paints in given order — no second sort.

### UI

- `portfolio.html`: caption “Largest 20 by |P/L| plus other. Gains at top, losses at bottom.” Column still Symbol; cell is `row.name`.
- `history_detail.html`: card “Contribution to Δ” with empty `perf-table`; `alt_history.js` fills from `body.breakdown` in the same path fetch that fills header Δ.
- Reuse `.perf-table` / `.perf-bar.pos|neg`.

### Tests

- `signed_bar_rows`: mixed signs keep +100, −90, +10 with `top_n=2` as **[+100, −90]** (not −90 then +100; not +100 then +10). `other` nets the rest and sits by its signed value.
- `_performance` MTM: fixture CLOSED (−10) is after META and 700; a unit case with a large loss not mixed into the gains. Template uses `row.name`.
- `nav_delta_rows`: sell META / buy AAPL + cash change sums to `alt.nav - actual.nav`.
- Path JSON: `sum(row.pl) ≈ delta`; breakdown order is signed; `compare_path` still returns only the series.
- Editor HTML contains the empty table; path fetch still does not run on date change.

### Docs

`ARCHITECTURE.md` website paragraph for `/portfolio/histories/{id}`: path JSON also carries the last-point Δ breakdown (display math, not a valuation). One sentence. README API line if the path payload is documented there.

---

## Non-goals

- Reorder Change-in-NAV waterfall (semantic statement order, not a rank).
- Breakdown as-of the date picker (that is holdings, not header Δ).
- New `/breakdown` URL or a fourth view type.
- Live last print, Live NAV, or IB MTM rows on the paper book.
- List-card per-history tables.
- Raw `MarkedNav` on `PathView` JSON.

---

## Verify

```bash
python3 scripts/eng_verify.py
python3 -m pytest apps/analysis_web/tests/test_portfolio.py apps/analysis_web/tests/test_ib_statement.py apps/analysis_web/tests/test_alt_history.py apps/analysis_web/tests/test_histories.py -q
```

Browser (`python3 -m apps.analysis_web`):

1. `/portfolio` — Mark-to-market P/L: largest gain at top, largest loss at bottom; bars still signed.
2. `/portfolio/histories/{id}` with at least one what-if fill — after path loads, Δ breakdown rows sum (visually) to header Δ; largest positive contribution at top, largest negative at bottom.
3. Change the holdings date — table of lots updates; Δ breakdown does **not** change (still today).
4. Narrow viewport — table still readable.

---

## Risks

- **Identity leak:** attaching breakdown to holdings-as-of-D would disagree with header Δ. PathView last point is the only legal home.
- **Second replay:** if the walk is not the engine, `compare_at` after `compare_path` can drift. Last marks come from the same walk.
- **Cash vs listings:** omitting cash makes the table not sum to Δ. Always include Cash when either book has cash.
- **`other` placement:** must participate in signed order, not always last, or a net-gain remainder would sit under losses.

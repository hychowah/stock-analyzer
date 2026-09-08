# Realtime NAV from holdings

**Mode:** B (W4 UI)  
**Home:** enhance `/portfolio` — do not add a second page  
**Data:** IB book in `apps/analysis_web/.local/` + Yahoo last prints  
**Not:** a broker stream, a new holdings store, or a second fair-value

**Shipped (supersedes bullets below):** `print_listing` is the holding’s market (`holding_print_listing`), not `quote_listing` else catalog overlay — GDS `HY9H` stays `HY9H`, not Korean `000660.KS`. Header is Live NAV + day P/L; no Period, Ending NAV, or Δ vs statement. See `../progress.md`.

Absorbed strategic design review (Direction `mixed` → reshape): one marked-book resource, lots not the catalog view, one print listing on the row. Dual poll / `book_view` + side `fx_closes` / template `quote_listing or yahoo_listing` are out.

---

## What you asked for

A webpage that keeps **NAV** (the portfolio’s net asset value) current from **holdings × live prices**.

Display math on the existing book, same family as Live price and Downside %: Yahoo last print in, stored bear FV untouched.

---

## What exists today

`/portfolio` already has the pieces, but they do not meet.

| Piece | Where | What it is |
|-------|--------|------------|
| Holdings, cash, statement NAV, TWR | `.local/portfolio.sqlite` (latest IB activity snapshot) | Qty, IB close, native value, statement FX. JSON fallback only if sqlite is missing. |
| Catalog overlay | `services/portfolio.py` | Research coverage, FV, MoS. View-time ticker map (`700`+SEHK → `0700.HK`). View drops the FX rate after using it for `value_base`. |
| Live print | `QuoteService` + `GET /api/quotes` + `quotes.js` (global, in `base.html`) | Yahoo last 1-minute bar, else daily close. TTL 120s. Cap 50 listings on the HTTP quotes API. |
| Headline “Ending NAV” | `portfolio.html` | **Statement period only.** Copy on the page says so. |
| Live column | same table | Price chip only. **Not** multiplied by qty. **Only** when a catalog run stamped `quote_listing` — uncovered names stay `—`. Two strings already on the row (`quote_listing`, `yahoo_listing`); the template uses the first. |

Nothing computes `Σ qty × live_price × FX`. SSE on this page reloads when the **sqlite file** changes (a new import), not when Yahoo ticks.

Typical live book (from the last ingest): ~21 stock positions, base currency HKD, mixed USD/HKD names.

---

## Recommended product

**One card on `/portfolio`:** statement Ending NAV stays; a **Live NAV** figure updates from **one** poll (~2 minutes while the tab is visible). That same payload paints Live cells, live value, and Downside. `quotes.js` does **not** fetch `/api/quotes` on this page.

Honesty on the card, always:

- Yahoo last print, not IB TWS / not a tick stream
- Holdings qty from the **latest imported statement** (trades after `period_to` do not move qty until you import again)
- FX at **statement** Forex Balances close in v1
- TWR stays IB-reported for the statement period — do not invent a live TWR

No new URL. Primary nav already has Portfolio. A dedicated `/nav` page would duplicate the book and force an architecture-page add for no new job.

---

## Formula (the whole design)

Keep IB Ending NAV as the identity, then **replace only what we can reprice**.

```
live_nav = ending_nav + Σ_repriced (qty × live_price × stmt_fx − stmt_value_base)
```

- **Repriced:** lot with a usable Yahoo last print **and** a statement FX rate on the lot.
- **Unquoted / missing FX / non-stock sleeves (cash, options, …):** keep the statement amount.
- Shorts: qty is signed; the same product works.
- Stock multiplier is 1 (current view is Stocks only).

Worked from the mini fixture (base HKD, USD/HKD = 8, ending NAV 5500):

- `700`: 100 × 10 × 1 = 1000 (already in statement)
- `META`: 10 × 50 × 8 = 4000
- If META live print is 55: delta = 10×55×8 − 4000 = +400 → **live NAV 5900**
- If `700` has no quote: keep 1000; only META moves.

JSON fallback (no sqlite), same function: `ending_nav is None` → live NAV is the sum of live lots (need `shares` on every row). No Δ vs statement. Weights-only books stay empty (“need shares or an IB statement”).

**Day change** (same payload; `QuotePrint.prev_close`):

```
day_pl = Σ_repriced qty × (live_price − prev_close) × stmt_fx
```

This is “since prior daily close,” not since statement `period_to`. Label it that way.

---

## What this is not (v1)

| Out | Why |
|-----|-----|
| IB Gateway / TWS streaming | No `ib_insync`, no extra daemon. Import stays CLI CSV. |
| Reconstruct qty from the trade ledger | Snapshot is the open book by contract. Ledger is fills. Mixing them without a position engine is a silent wrong NAV. |
| Live FX (`USDHKD=X`) | Yahoo search types are EQUITY/ETF/INDEX; FX is a second quote family. v1 labels “FX as of statement.” |
| Options, bonds, FX balances as live names | Current view is Stocks. Identity formula already keeps those sleeves at statement. |
| Live weights / live-weighted MoS | Statement weights stay. Live-value weights would look like a new research call. |
| Writing marks into sqlite or `archive/` | App-local book stays the statement. Live NAV is computed, never stored. |
| New FV / portfolio MoS in dollars | Mode B must not invent valuation. Live NAV vs stored bear is not in v1. |
| WebSocket | The app has none. Quotes are poll; SSE is file mtime. |
| Bumping `harness/VERSION` | UI only. |
| Dual poll (`quotes.js` + `live_nav.js` both hitting Yahoo) | Rejected in design review. Shared QuoteService TTL is not an interface. |
| `mark_live_nav(book_view, …, fx_closes=…)` | Marker must not see FV/MoS/audit or re-look-up FX. |
| Template `quote_listing or yahoo_listing` | One `print_listing` at join time. |

Follow-ups (not this ship): live FX; ledger-true qty; import UI; JSON books with mixed FX.

---

## Shape (from-scratch)

Three boundaries. Each hides a decision.

```
join (portfolio.py)     → lots + print_listing + stmt_fx on each holding
mark (live_nav.py)      → live_nav / vintage / per-row prints   (no Yahoo, no sqlite, no catalog)
fetch (GET live-nav)    → QuoteService.get_many(listings) then mark
paint (one poller)      → /portfolio polls only that GET
```

`quotes.js` stays a **painter + optional `/api/quotes` poller**. On Runs / run detail it still polls. On `/portfolio` it does not fetch; it applies a `quotes` array handed to it.

### 1. One print listing on the row

At catalog join, every position gets:

- `quote_listing` — research stamp only (null if uncovered). Unchanged meaning.
- `print_listing` — `quote_listing` if stamped, else the overlay (`map_catalog_ticker`). This is the only string that hits Yahoo.
- `stmt_fx` — statement Forex close used for `value_base` (1.0 when currency is base). The view currently drops this after converting; keep it on the row.

Stop using `yahoo_listing` as a quote key (`yahoo_listing` is already a duplicate of `catalog_ticker`). Template and live-nav route both read `print_listing`. Uncovered Tencent `700`+SEHK is `0700.HK` in one place.

### 2. Mark lots, not the catalog view

```
mark_live_nav(lots, quotes_by_listing, *, ending_nav, cash=None) -> dict
```

Each lot: `ib_symbol`, `listing` (`print_listing`), `quantity`, `stmt_value_base`, `stmt_fx`.

- Pure function. No Yahoo, sqlite, or catalog. No `book_view`. No side `fx_closes` dict.
- `cash` only if the payload shows `stock_live` / `cash_statement`.
- JSON-with-shares is this function with `ending_nav is None`.
- Weights-only: empty lots / no live NAV.

Route: statement join → lots → `QuoteService.get_many` (internal chunks of 50) → `mark_live_nav`. Chunking applies to **every** live cell on this page, not only the total.

### 3. One marked book, one portfolio poll

`GET /api/portfolio/live-nav` is the **only** Yahoo-facing fetch on `/portfolio`.

Payload is aggregates plus per-row prints (English keys):

```json
{
  "base_currency": "HKD",
  "statement_nav": 5500.0,
  "live_nav": 5900.0,
  "delta": 400.0,
  "delta_pct": 7.2727,
  "day_pl": 120.0,
  "cash_statement": 500.0,
  "stock_live": 5400.0,
  "vintage": "partial",
  "fx_vintage": "statement",
  "period_to": "2026-03-31",
  "n_positions": 21,
  "n_repriced": 18,
  "n_unquoted": 3,
  "as_of": "2026-09-08T14:32:00",
  "ttl_sec": 120,
  "quotes": [
    {
      "symbol": "META",
      "price": 55.0,
      "prev_close": 50.0,
      "change_pct": 10.0,
      "print_kind": "intraday",
      "error": null
    }
  ],
  "rows": [
    {
      "ib_symbol": "META",
      "listing": "META",
      "quantity": 10,
      "live_price": 55.0,
      "change_pct": 10.0,
      "stmt_value_base": 4000.0,
      "live_value_base": 4400.0,
      "print_kind": "intraday",
      "error": null
    }
  ]
}
```

`quotes` is the existing `QuotePrint` JSON (same shape as `/api/quotes`) so the painter stays generic.

Do **not** call Yahoo on HTML `GET /portfolio`. First paint is statement NAV (Live cells start as `—`). `/api/portfolio` stays statement-only so existing tests stay fast and deterministic.

---

## UX

On `/portfolio`, in the existing IB summary grid (not a new page):

1. **Ending NAV** — statement, unchanged, period dates next to it.
2. **Live NAV** — large number, base currency, vintage chip (`live` / `partial` / `statement`).
   - `live`: every stock lot repriced
   - `partial`: some names kept at statement (show count)
   - `statement`: no usable prints (keep the statement number, do not flash 0)
3. **Δ vs statement** — signed amount and % (`live_nav / ending_nav − 1`). Hidden when `ending_nav is None`.
4. **Day P/L** — vs prior close, muted, with the “prior close” label.
5. **Status line** — one writer (`#quote-status`):  
   `Yahoo last print · 2 min · FX as of 2026-03-31 · 18/21 stocks marked`

Positions table:

- `data-quote-symbol="{{ p.print_listing }}"` (not an `or` in the template).
- New column **Live value (base)** from the live-NAV `rows` (`—` if that lot was not repriced).
- Live price + Downside: same cells as today, painted from the payload `quotes` array (reuse `quotes.js` paint). No second interval.

Empty / error book: no live card (same as today: “Import an IB activity statement”).

Desktop + phone: the summary grid already stacks; Live NAV is a number in that grid, not a new chart.

---

## Frontend

`quotes.js` (general painter):

- Default: poll `/api/quotes` from `[data-quote-symbol]` (Runs, run detail). Unchanged.
- If the page opts out of polling (`data-quote-poll="0"` on `body`, set only by `portfolio.html`): do **not** fetch, do **not** arm a timer, do **not** write `#quote-status`.
- On `quotes-applied` (CustomEvent, `detail.quotes` + optional `detail.requested`): run the existing `applyQuotes` / `fillDownside`. That event is the interface, not a later nicety.

`live_nav.js` (portfolio only, `{% block scripts %}`):

- The only Yahoo-facing poll on this page: `GET /api/portfolio/live-nav` on load, every `ttl_sec`, on `visibilitychange` (pause when hidden).
- Paint `#live-nav`, `#live-nav-delta`, `#live-nav-day`.
- Patch `[data-live-value]` from `rows` keyed by `ib_symbol`.
- Dispatch `quotes-applied` with `quotes` so Live cells and Downside fill.
- Sole writer of `#quote-status` on this page.
- Do not listen to SSE for prices.

Template hooks:

- `body` `data-quote-poll="0"` (and keep `data-live-reload="1"`).
- `#live-nav` with `data-statement-nav`, `data-base-currency`.
- `#quote-status`.
- Per row: `data-quote-symbol` from `print_listing`, `data-live-value`, `data-ib-symbol`. `data-fv-bear` / `data-asof-price` stay for Downside.

---

## Files to touch

| File | Change |
|------|--------|
| `apps/analysis_web/services/portfolio.py` | Join emits `print_listing` + `stmt_fx` on every position. Do not fetch quotes here. |
| `apps/analysis_web/services/live_nav.py` | **new** — `mark_live_nav(lots, quotes, *, ending_nav, cash=None)` |
| `apps/analysis_web/routes/api.py` | `GET /api/portfolio/live-nav` |
| `apps/analysis_web/static/quotes.js` | Opt-out poll + `quotes-applied` applies an array. Still the poller on Runs / run detail. |
| `apps/analysis_web/static/live_nav.js` | **new** — only fetch on `/portfolio`; paint NAV; dispatch `quotes-applied` |
| `apps/analysis_web/templates/portfolio.html` | `data-quote-poll="0"`; Live NAV card; status; live-value column; `print_listing` on cells |
| `apps/analysis_web/tests/test_live_nav.py` | **new** — lots formula + HTTP with `FakeQuoteBackend` |
| `apps/analysis_web/tests/test_quotes.py` | Opt-out / `quotes-applied` does not hit `/api/quotes` |
| `apps/analysis_web/tests/test_portfolio.py` | Uncovered row has `print_listing` / `data-quote-symbol="0700.HK"`; page has live-nav hooks and `data-quote-poll="0"` |
| `apps/analysis_web/README.md` | Pages + API rows; portfolio does not poll `/api/quotes` |
| `ARCHITECTURE.md` | `/portfolio` row + display-math sentence (trigger: new API + NAV display math) |

No `archive/` writes. No harness bump.

---

## Tests (must be green before claiming done)

Formula (no network):

- Lots from the mini fixture: META print move → live NAV = ending + qty×Δpx×fx
- Missing quote → that lot stays at statement; vintage `partial`
- Missing `stmt_fx` on a USD lot → not repriced
- All quotes fail → `live_nav == statement_nav`, vintage `statement`
- `ending_nav is None` + shares lots → sum of live values, no delta
- Empty lots → no live NAV
- Marker never requires a catalog field (pass lots only)

HTTP:

- `FakeQuoteBackend` on `app.state`; `GET /api/portfolio/live-nav` returns aggregates + `quotes` + `rows`
- 51 listings still mark via internal chunking (Live cells included, not only the total)
- HTML: `#live-nav`, `#quote-status`, `data-quote-poll="0"`, `data-quote-symbol="0700.HK"` on uncovered `700`+SEHK

Client:

- `quotes.js` with `data-quote-poll="0"` does not request `/api/quotes`
- `quotes-applied` fills Live / Downside cells
- Runs page still polls `/api/quotes` (regression)

Regression:

- Existing portfolio / quotes / SSE tests
- `python3 scripts/eng_verify.py`

Browser (user rule): Playwright against a local server with fake quotes if possible, else the running UI — confirm Live NAV, Live cells, and Downside all move from **one** request to `/api/portfolio/live-nav` (no `/api/quotes` on that page), desktop and a phone viewport, and that Runs Live cells still poll `/api/quotes`.

---

## Docs

`ARCHITECTURE.md` (same change set):

- Website table: `/portfolio` also shows **Live NAV** = statement ending NAV adjusted by holdings × Yahoo last print, FX frozen at the statement, not a valuation. One marked-book poll paints Live cells too.
- Invariants / “what this system is”: same sentence as Downside % — display math, no second FV.

`apps/analysis_web/README.md`: document `/api/portfolio/live-nav`; `/api/portfolio` remains the statement join; `/portfolio` does not call `/api/quotes`.

---

## Eng session (when implementing)

```bash
python3 scripts/scaffold_eng_session.py --slug live-nav --work-type W4 --date 2026-09-08
```

Feature list (increments are abstractions; verify before `passes: true`):

| ID | Description |
|----|-------------|
| `print-listing-lots` | Join emits `print_listing` + `stmt_fx`. Lots are the marker input. Template uses `print_listing` only. |
| `marked-book-api` | `mark_live_nav(lots, …)` + `GET /api/portfolio/live-nav` (chunks of 50, `quotes` + `rows`) + `FakeQuoteBackend` tests |
| `one-portfolio-poll` | `quotes.js` opt-out + `quotes-applied`; `live_nav.js` is the only fetch on `/portfolio`; status has one writer |
| `docs-verify` | README + `ARCHITECTURE.md`; `eng_verify`; browser smoke (no `/api/quotes` on portfolio; Runs still polls) |

Git: implement and verify; **do not commit until you say so.**

---

## Implementation order

1. `print_listing` + `stmt_fx` on the join (one listing, lots have FX).
2. Pure `mark_live_nav(lots, …)` + tests on the mini IB fixture.
3. `GET /api/portfolio/live-nav`.
4. `quotes.js` opt-out + `quotes-applied`; `live_nav.js` + template.
5. Docs + `eng_verify` + browser.

---

## Risks

- **Wrong Yahoo listing** (GDS vs local, `HY9H` vs `000660.KS`) → wrong mark. Reuse the existing overlay; do not add a per-issuer map inside `yahoo_bars`.
- **Native print × statement FX** is not a live cross. USD names in an HKD book will miss FX moves until a live-FX follow-up. The card must say so.
- **Stale qty** after trades: live price on an old position is still the wrong NAV. Status should keep showing `period_to`.
- **`quotes.js` in `base.html`:** opt-out must be default-off (only `/portfolio` sets `data-quote-poll="0"`). A bug that disables polling globally would blank Runs Live cells.

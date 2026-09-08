# Alternative histories (what-if portfolio)

**Mode:** B (W4 UI)  
**Home:** `/portfolio/histories` — not a fifth primary nav item, not a rewrite of the live IB book  
**Data:** IB book **at copy time only** + catalog (buy universe at POST) + Yahoo **daily closes** + app-local overlay sqlite  
**Not:** a broker, a second fair-value, a strategy optimizer, or a change to Live NAV

Absorbed strategic design reviews: one **cash book**; then **copy the whole IB stock ledger** (not fork-and-hold); then **one self-contained paper book** — persist seed at copy, actual is replay of that copy, not a live IB walk.

---

## What you asked for

Go back to a date in the real book, take a decision you did not take — **buy** a name from the researched catalog, or **sell** something you held — and see how that book would have done. Keep **several** of these histories so you can later test strategies against them.

UI: first **copy the whole IB trade record**, pick a date, see holdings that day **including names later sold**, then sell. Later real sells of a name already sold in the paper book must clip/skip.

---

## Product in one sentence

Each **history** is a named, frozen paper copy of the IB stock book (seed lots + cash + copied stock fills) plus a dated list of what-if fills. Actual and alt are both `mark(replay(seed, fills))` on that copy. Live IB is not read again for compare.

That shape is the strategy hook: a strategy later emits the same decision list. v1 is manual.

---

## Cash book (the from-scratch type)

One type. Actual and alt are both instances of it.

```text
BookState = lots + cash_base + caveats

Lot = listing, currency, qty, stmt_fx
      + ib_symbol? + catalog_ticker?   # aliases, not two key spaces

as_of_book(ib, date) → BookState      # IB walk; copy time only
seed = as_of_book(ib, day_before(first stock date))
overlay_fills(seed, fills) → fills    # clip later real sells a hyp sell already used
replay(state, priced_fills) → BookState
mark(state, close_on_or_before(date)) → NAV
```

Mark identity (sibling of `mark_live_nav`, **not** that function):

```text
nav = cash + Σ qty × close × stmt_fx
```

Missing bar → last close on or before that day; else that lot contributes 0 and is flagged unquoted.

```text
Actual(date) = mark(replay(seed, real_fills ≤ date))
Alt(date)    = mark(replay(seed, overlay_fills(all_fills ≤ date)))
Δ(date)      = Alt(date) − Actual(date)
```

Today’s card Δ is `Δ(today)` on the **daily close**. It is the right endpoint of the chart. It is **not** Live NAV (snapshot qty × last print). `/portfolio` keeps Live NAV. What-if never borrows it.

`fork_date` is the ledger start of the copy (earliest stock trade / statement period), not a branch point. There is no user fork-date form.

A later re-ingest of `portfolio.sqlite` does **not** change a saved history. Card Δ stays “what-if vs this copy.”

---

## Decisions (locked unless you object)

| Choice | Call | Why |
|--------|------|-----|
| Copy-and-overlay | Create copies the whole IB stock ledger into seed + real fills. What-if fills sit on that copy. | Fork-and-hold hid names later sold and compared against a live walk that re-ingest can change. |
| Buy universe | Catalog **latest** run per ticker, checked **at POST**, then stored on the fill. Not “research that existed on D”. Not re-checked inside replay. | You are testing a missed buy with knowledge you have now. A saved history must not break if the catalog later drops the name. |
| Sell universe | Lots on the **alt** book after overlay fills `≤ D` (including unwinding a hypothetical buy). Cannot sell more than that qty. | “You held on this date” is the paper book. |
| Fill price | Resolved **at POST**: Yahoo daily close on or before the decision date, or numeric override. Stored. Replay never fetches Yahoo. If no close and no override, reject the fill. | Later Yahoo holes cannot break a saved history. |
| Cash | What-if buys funded from seed cash plus earlier fills on this history. Shortfall blocks the fill. Copied IB buys still apply if statement cash goes negative (that cash is approximate). | Honest paper book for decisions; the copy must replay the real ledger. |
| Overlay | Adding a what-if sell **produces an effective fill list**: later real sells of that listing are clipped or dropped. Stored real rows stay the IB copy. Persist via **`save(History)`**. | Replay stays qty-strict. The copy’s real rows are not rewritten. |
| FX | Statement Forex closes frozen on the seed at copy (`BookState.fx_by_ccy`, next to `base_currency`). Stored on each fill. New buys/sells look up that map, not the live statement. | A re-ingest must not stamp new fills with different FX than the frozen lots. Live FX is a second quote family. |
| Live NAV | Unchanged. Snapshot qty × last print on `/portfolio` only. What-if does **not** call it. | Separate actual: this copy, daily close. |

---

## What exists today

| Piece | Where | Relevance |
|-------|--------|-----------|
| Latest IB snapshot + full trade ledger | `.local/portfolio.sqlite` | Snapshot is the open book for Live NAV. Ledger is fills. Read **at copy** to freeze seed + real fills. |
| Catalog join | `services/portfolio.py` | `latest_run`, `holding_print_listing` vs catalog overlay (GDS trap). |
| Live NAV | `services/live_nav.py` | Stays on `/portfolio`. Do not reuse the function or the poll. |
| Daily closes | `services/price_history.py` + `yahoo_bars.py` | Inject a backend; `close_on(bars, date)`. |
| Mini IB fixture | `tests/fixtures/ib_activity_mini.csv` | 700 +100 on 2026-01-10, META +12 on 01-15 and −2 on 02-20, snapshot 31 Mar. |
| App-local state | `apps/analysis_web/.local/` (gitignored) | Overlay sqlite. Never `archive/`. |

The Live NAV plan refused “reconstruct qty from the trade ledger” **for the open book**. Alternative history uses that reconstruction **once**, at copy, then never again for that history.

---

## As-of book (copy time only)

Pure function, no Yahoo, no catalog, no writes:

```text
as_of_book(ib_book, date D) → BookState
seed_book(ib, fork) = as_of_book(ib, day_before(fork))
```

**Lots (stocks only; skip Forex/options):** start from snapshot open positions; reverse or apply stock trades relative to `period_to`; drop ~0 qty; listing from `holding_print_listing`.

Worked from the mini fixture (snapshot META 10, 700 100, period_to 2026-03-31):

- D = 2026-01-05 → both 0
- D = 2026-01-12 → 700 = 100, META = 0
- D = 2026-02-01 → 700 = 100, META = 12
- D = 2026-03-31 → snapshot (700 = 100, META = 10)

**Cash:** statement cash adjusted by stock-trade proceeds. Caveats live on `BookState`.

After copy, **do not** call `as_of_book` / `seed_book` on live IB for compare, deceased flags, or “held on D”. Those use `hist.seed` and `hist.fills`.

---

## Overlay store (never the IB file)

New file: `apps/analysis_web/.local/alt_histories.sqlite`

```text
histories
  id INTEGER PK
  name TEXT NOT NULL
  notes TEXT
  fork_date TEXT NOT NULL      -- ledger start of the copy
  seed_json TEXT NOT NULL      -- frozen BookState (lots + cash)
  created_at TEXT
  updated_at TEXT

decisions
  id INTEGER PK
  history_id INTEGER REFERENCES histories(id) ON DELETE CASCADE
  as_of TEXT NOT NULL
  side TEXT NOT NULL           -- buy | sell
  listing TEXT NOT NULL
  quantity REAL NOT NULL
  price_mode TEXT NOT NULL     -- close | override | ib
  fill_price REAL NOT NULL
  currency TEXT NOT NULL
  catalog_ticker TEXT
  ib_symbol TEXT
  notes TEXT
  created_at TEXT
  source TEXT NOT NULL         -- real | hyp
  cash_effect REAL             -- IB proceeds+commission in base, when known
```

- No computed NAV stored. Replay on read from seed + priced fills.
- Duplicate = new row + copied seed + copied fills.
- Delete is allowed (app-local overlay).
- **Never** INSERT into `portfolio.sqlite` trades.
- Persist the aggregate with **`save(History)`** (trials first). Do not insert a fill without a trial.

Identity in URLs: integer `history_id` under `/portfolio/histories/{id}`.

---

## POST vs replay

**At POST** (the only place policy and I/O meet):

1. Reject `as_of < fork_date`.
2. **Buy:** ticker must have a latest catalog run *now*; resolve listing and fill; store priced fill.
3. **Sell:** target is a lot on `state_on(hist, as_of)` keyed by **listing**.
4. `with_hyp_fill` / `drop_hyp_fill` produce a new `History`, trial overlay+replay, then **`save`**.
5. Cash shortfall (what-if), oversell, or zero qty → 400 on the editor.

**`overlay_fills`** clips later **real** sells of a listing a what-if sell already consumed. Stored real rows stay the IB copy.

**`replay`** is a pure function on already-priced fills. Oversell fails for every fill. What-if buys cannot overspend. Copied IB buys still apply if statement cash goes negative.

---

## Comparison (one mark, this copy)

```text
Actual(date) = mark(replay(seed, real_fills ≤ date))
Alt(date)    = mark(replay(seed, overlay_fills(all_fills ≤ date)))
Δ(date)      = Alt − Actual
```

List cards and the editor header show `Δ(today)` from this. The chart is Actual and Alt from `fork_date` → today. The last point **is** the header number.

Deceased / “sold later” = listing not in **this copy’s** actual today, not live `as_of_book(ib, today)`.

Do not call `GET /api/portfolio/live-nav`. Do not use last print. `data-quote-poll` stays off. These pages never load `live_nav.js`.

---

## UI / UX

Primary nav stays **Portfolio**. Sub-nav: `[ Book ] [ What-if ]`.

`/portfolio` is unchanged aside from that link.

### List — `/portfolio/histories`

Empty state: copy your IB trades, pick a date, sell what you held that day — including names you later sold. Buy from names you have researched.

Cards: name, copy start, what-if fill count, **Alt vs actual** (today, daily close) with signed Δ. **Copy my trades**. Overlay chart when ≥2 histories (actual line is the first copy’s actual).

### New — `/portfolio/histories/new`

Name only. POST copies IB stock trades, freezes seed, redirects to the editor.

### Editor — `/portfolio/histories/{id}`

**Sticky summary:** name, copy start, Alt vs Actual vs Δ (today / chart end), cash today, caveats.

**Holdings on this day:** date picker (`≥ fork`). Table includes names later sold on this copy. **Sell** qty on the row.

**Buy** under a disclose: researched names from today’s catalog.

**Compare chart** under the columns: two lines, copy start → today, same mark as the header. Server SVG; small JS hover.

Phone (`max-width: 1100px`): summary stacks, columns stack. Desktop and 390px both get a Playwright pass.

### Copy on the page (honesty)

- “Names you have researched (today’s catalog), not research you had on the decision date.”
- “Yahoo daily close, not IB fills, not live last print. FX is the statement Forex close frozen at copy.”
- “This does not change your IB book.”
- “The number on the card is the right end of the chart.”
- “Actual is this copy. Re-importing IB trades does not rewrite it.”

---

## Routes and APIs

HTML (all `nav.current = portfolio`):

| Path | Role |
|------|------|
| `GET /portfolio/histories` | List + overlay chart. Overlay sqlite only; no live IB. |
| `GET+POST /portfolio/histories/new` | **Only IB read.** Copy from IB (freeze seed + FX). |
| `GET /portfolio/histories/{id}` | Editor. History + Yahoo; no live IB. |
| `POST /portfolio/histories/{id}` | Rename / notes |
| `POST /portfolio/histories/{id}/decisions` | Resolve from `History` (catalog + close + seed FX) + `save(with_hyp_fill)` |
| `POST /portfolio/histories/{id}/decisions/{did}/delete` | `save(drop_hyp_fill)` |
| `POST /portfolio/histories/{id}/copy` | Duplicate (seed + fills) |
| `POST /portfolio/histories/{id}/delete` | Delete history |

JSON:

| Path | Role |
|------|------|
| `GET /api/portfolio/histories` | List summaries + `Δ(today)` from `mark`, not live-nav |
| `GET /api/portfolio/histories/{id}` | History + alt book at view date + path |

No `GET /api/portfolio/as-of`. No new SSE. Do not point `live_nav.js` at these pages.

---

## Code shape

| Module | Job |
|--------|-----|
| `services/book_state.py` | `BookState`, `Lot`, `as_of_book`, seed JSON. Fixture-tested. IB walk at copy only. |
| `services/mark_book.py` | `mark(state, prices)` → NAV. Sibling of `mark_live_nav`. |
| `services/alt_history.py` | `History` (seed + fills), `overlay_fills`, `replay`, `actual_state` / `alt_state`, POST policy. |
| `services/alt_history_store.py` | Overlay sqlite. **`save(History)`**. |
| `services/alt_history_view.py` | List/editor payloads from History, not live IB. |
| `routes/histories.py` | HTML + JSON. IB load on `/new` only. |
| `static/alt_history.js` | Search filter + chart hover. |
| templates | `histories.html`, `history_new.html`, `history_detail.html`, `partials/portfolio_subnav.html`. |

Reuse: `holding_print_listing` / `latest_run` / `FakeHistoryBackend`. Do not change Live NAV. Do not call `mark_live_nav` from what-if.

---

## Architecture / docs (same change set)

`ARCHITECTURE.md`: `/portfolio/histories` is a frozen paper copy; actual is replay of that copy; overlay sqlite never writes IB; card Δ is not Live NAV.

`apps/analysis_web/README.md`: same. No `harness/VERSION` bump. No commit until you agree.

---

## Feature list (increments are abstractions)

1. **book-state** — `as_of_book` on the mini fixture. Done.
2. **replay-mark** — priced-fill replay + mark. Done.
3. **pages-composer** — sub-nav, list/new/editor. Done.
4. **compare-ux** — card Δ equals chart end; SVG; overlay; Playwright. Done.
5. **ledger-copy-ui** — copy IB trades; date-first holdings including later-sold names. Done.
6. **frozen-paper-book** — persist seed; Actual = replay(seed, real fills); overlay clip outside replay; `save(History)`. Implemented; verifier has not flipped `passes`.
7. **history-only-after-copy** — IB load only at copy. Freeze statement FX on the seed. List/editor/JSON/POST buy-sell take `History`, not `IbBook`. GET what-if works if `portfolio.sqlite` is missing. Implemented; verifier has not flipped `passes`.

Verifier flips `passes` after the listed command is green. Implementer does not.

---

## Increment 7 in the tree: History is the only book after copy

Absorbed SDR (Direction `mixed` → reshape): the type was already a frozen paper book; the HTTP surface still loaded live IB on every list/editor/API/POST. That I/O leak is closed in code.

### From-scratch I/O

```text
create_from_ib(ib)     # only IB read
  seed.fx_by_ccy = snapshot.forex_closes   # frozen next to base_currency
  seed.lots / cash / copied fills as today

GET  /portfolio/histories            # overlay sqlite + Yahoo closes; no IB
GET  /portfolio/histories/{id}       # same
GET  /api/portfolio/histories[/{id}] # same
POST /portfolio/histories/{id}/decisions
     resolve_buy(api, hist, get_close) / resolve_sell(held, hist, get_close)
POST delete / copy / rename / delete-history
     # History only

GET+POST /portfolio/histories/new    # IB required (this is the copy)
```

If `portfolio.sqlite` is missing or a later re-ingest changed it: existing histories still list, open, sell, and buy. Copy-my-trades is the only screen that says “import an IB statement.”

### Seed FX (one place)

On `BookState`, next to `base_currency`:

```text
fx_by_ccy: tuple[(currency, rate), ...]  # frozen; JSON object in seed_json
fx_for(ccy) → rate | None                # 1.0 if ccy == base_currency
# named fx_by_ccy so it does not collide with Lot.stmt_fx (per-lot rate)
```

`as_of_book` / `seed_book` copy `snapshot.forex_closes` onto the state (the parser already puts base and HKD at 1). `history_from_ib` does not grow a second FX field on `History`. Old `seed_json` without the map: empty tuple; `fx_for` still returns 1.0 for base; any other currency is `missing_fx` (recopy).

`resolve_buy(api, hist, …)`: catalog ticker → listing/close as today; FX = `hist.seed.fx_for(ccy)`.  
`resolve_sell(held, hist, …)`: lot.stmt_fx, else `hist.seed.fx_for`. No `IbBook` argument.

### View / routes

- Drop `IbBook` from `list_payload` and `editor_payload`. Label currency from `hist.seed.base_currency` (list: first card’s seed, or blank if empty).
- Drop list `min_date` from live IB (unused on the list template). Copy form keeps `earliest_stock_date(ib)` for the “ledger starts …” line.
- `_need_book` only on GET+POST `/new`. List/editor/JSON never 404 for “no IB book.”

### Tests (this increment)

- `BookState` JSON roundtrip includes `stmt_fx`; `fx_for("USD")` on the mini fixture is 8.
- `resolve_buy` / `resolve_sell` take `History`; a mutated live `forex_closes` after copy does not change the fill’s `stmt_fx`.
- HTTP: copy, then hide/remove `portfolio.sqlite` → GET list 200 with the card, GET editor 200, POST sell 200, JSON 200. GET `/new` still errors without IB.
- What-if HTML still has no `live_nav.js`. IB trade count unchanged.

### Docs

Same change set: `ARCHITECTURE.md` / README — what-if reads IB only at copy; FX on the seed. Delete the plan line “POST may read the statement for FX.”

No `harness/VERSION`. No commit until you agree.

---

## Tests

- `test_book_state.py` — mini fixture walk; seed JSON roundtrip.
- `test_mark_book.py` — cash included; unquoted lot → 0 + flag; does not call `mark_live_nav`.
- `test_alt_history.py` — catalog at POST; oversell; cash shortfall on what-if; copy matches `as_of_book` at copy time; hyp sell clips later real sell in overlay, not in raw replay; compare uses frozen seed (empty seed → 0 actual while live IB still has lots); `save` roundtrip; IB trade count unchanged; `Δ(today)` equals last path point.
- `test_histories.py` — GET list empty; POST copy; POST buy/sell; 404; no `live_nav.js`.

---

## Out of v1

| Out | Why |
|-----|-----|
| Strategy runner / optimizer | Decision list is the hook; no generator yet |
| Fork-and-hold (user fork date; later real trades not copied) | Replaced by copy-and-overlay |
| Live `as_of_book` on every compare day | Re-ingest would change actual while hyp fills stay frozen |
| Buy any ticker | Ask was researched list only |
| Live FX, options, IB Gateway | Same as Live NAV |
| Rewriting Live NAV from the ledger | Different contract |
| Calling `/api/portfolio/live-nav` from what-if | Different qty and identity |
| Writing marks or decisions into `archive/` | App-local only |
| Fifth primary nav item | Portfolio sub-nav |
| Modal composer | Match existing forms + disclose |

---

## Risks

- **Cash before `period_from` is approximate.** Caveats on `BookState`. Copied IB buys may run cash negative in the walk; what-if buys still cannot overspend.
- **Corporate actions** not in the trade ledger (splits) will mis-size lots. v1 accepts this.
- **GDS / listing mismatch** — lots mark on `listing`. Do not mark a Frankfurt GDS with the Korean common.
- **Yahoo holes** on the decision date — prior close at POST; if none, reject. Replay uses the stored fill.
- **Today vs live last print** — what-if “today” is the last daily close, so it will not equal Live NAV on `/portfolio`.
- **Old overlay rows without `seed_json`** — cannot be reconstructed without a live IB walk; user recopies trades.

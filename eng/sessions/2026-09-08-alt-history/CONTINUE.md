# Continue here after context compact

**Status:** frozen paper book + IB-only-at-copy are in the tree. Verifier has not flipped `frozen-paper-book` or `history-only-after-copy`. `/smart-commit` is user agreement to commit.

## What the user wanted

1. Alternative histories: go back to a date, buy from researched names, sell what they held.
2. Multiple named histories (later: strategy tests).
3. UI: first **copy the whole IB trade record**, then pick a date, see holdings that day **including names later sold**, then sell.
4. Do not change Live NAV. Do not write `portfolio.sqlite`.

## What is in the tree now

- One self-contained paper book: `History.seed` + copied real fills + hyp fills.
- Seed freezes lots, cash, and statement FX (`fx_by_ccy`).
- `Actual(date) = mark(replay(seed, real_fills ≤ date))`
- `Alt(date) = mark(replay(seed, overlay_fills(all_fills ≤ date)))`
- `overlay_fills` clips later real sells; stored real rows stay the IB copy.
- `replay` oversell is strict; what-if cash is strict; copied IB buys may run cash negative.
- Persist via `save(History)`. Live IB is read only on `/portfolio/histories/new`.
- `handoffs/plan.md` matches this. Fork-and-hold is gone.

## Verify

```text
pytest apps/analysis_web/tests/test_alt_history.py apps/analysis_web/tests/test_histories.py apps/analysis_web/tests/test_book_state.py apps/analysis_web/tests/test_mark_book.py -q
python scripts/eng_verify.py
```

## Do not

- Flip `feature_list.json` `passes` (verifier role).
- Call Live NAV from what-if.
- Reconstruct the book from live IB on read.

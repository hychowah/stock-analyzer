# Eng session 2026-09-08-whatif-perf-qty

- Created: 2026-09-08
- Work type: W4
- Goal: What-if copy and date-holdings must be fast; sell must take a visible quantity, not the whole lot.

## Log

- Scaffolded; plan at `handoffs/plan.md`.
- SDR Direction mixed → reshape. Absorbed all three candidates: three views (`paper_on` / holdings / path), one resource per view (no blob / `include_path`), bar sort and `range_for_span` in `price_history`.
- Implemented path walk, split HTTP, visible qty.
- Verify: targeted pytest 68 passed; `eng_verify` PASS 931. Browser on :62874: copy 122 fills landed immediately; date change updated holdings without a path rebuild; sell 1 of META 30 left 29; header Δ matched chart end; `/portfolio` still Live NAV. Smoke history deleted.

## Refactors

- `compare_path` is one walk (overlay once, two running books, pointer closes), not per-day restart.
- Editor HTML is paper-only. Marks and the NAV path are their own GETs. Yahoo span/sort live in `price_history`.

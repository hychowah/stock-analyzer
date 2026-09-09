# Eng session 2026-09-09-whatif-delta-breakdown

- Created: 2026-09-09T08:14:04Z
- Work type: W4
- Goal: Signed what-if Δ breakdown table like Mark-to-market P/L; largest gains at top, largest losses at bottom.

## Log

- 2026-09-09T08:14:04Z scaffolded
- Plan written; SDR mixed → reshape. Absorb: Apply all three candidates (walk is the engine; contrib next to MarkedNav; signed bars take (name, value)).
- Implemented: `walk_compare` / `CompareWalk`; `nav_delta_rows` beside `MarkedNav`; `signed_bar_rows((name, value))`. PathView.breakdown on GET /path. Book MTM uses `row.name`, caption gains-top/losses-bottom. Tests 83 targeted + eng_verify PASS 963.
- Live check (port 8766): MTM first HY9H / last COHR, signed sorted. History 1 breakdown Cash + HY9H sums to Δ 46481.91. First HTML paint has empty `#hist-breakdown`; holdings JSON has no breakdown. Playwright MCP was locked; Chrome dump-dom hung on Live NAV poll. Date-change identity checked via holdings API, not a click in the browser.
- Refactor: `_bar_rows` deleted; rank policy lives once.

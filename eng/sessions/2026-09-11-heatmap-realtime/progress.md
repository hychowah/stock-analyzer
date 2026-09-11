# Eng session 2026-09-11-heatmap-realtime

- Created: 2026-09-11T05:40:00Z
- Work type: W4
- Goal: Heatmap loadup: live-nav is lots x prints, QuoteService.prime overlaps HTML, window is mtm-interval still

## Log

- 2026-09-11 scaffolded
- 2026-09-11 probe on :8765 (existing UI, 21 names): HTML 120ms/68ms; live-nav cold 4147ms warm 73ms; mtm-path 1W cold 2931ms warm 24ms; YTD warm 251ms / 740KB / 182 frames. Yahoo dominates cold Live. Warm live-nav already <100ms. YTD path payload and walk are the window wait.
- 2026-09-11 implemented Option A:
  - `GET /api/portfolio/live-nav` uses `load_live_lots` (IB snapshot lots, JSON fallback). No catalog join. `pass_only` dropped (never filtered lots).
  - `QuoteService.prime` starts `get_many` on a daemon thread. `/portfolio` HTML primes listings then joins catalog.
  - `GET /api/portfolio/mtm-interval` one still; `window_listings` is start ∪ end ∪ fills. Heatmap fetches interval. Play still fetches path.
  - heatmap.js: chrome+rows one commit; loading is a status line; `lastIntervalByUrl` cache.
- 2026-09-11 tests: 107 targeted passed; `eng_verify` PASS 1031.
- 2026-09-11 Playwright :8790 desktop + 390px: Live tiles from live-nav; 1W GET `mtm-interval?period=1w` (not path); heading Holding influence; dates filled; Live restores CMCSA day-move immediately; second 1W uses card cache (no second GET); YTD is a different map (HY9H +217.6% vs 1W +11.4%); Fill → Exit; phone still shows the YTD map. MTM strip stayed on Live.
- 2026-09-11 post-change warm :8790: interval YTD 42ms / 4.8KB / 37 rows vs path YTD 211ms / 740KB / 182 frames; live-nav 8ms.
- Implementer did not flip `passes: true` (verifier role).

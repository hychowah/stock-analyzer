# Eng session 2026-09-10-portfolio-heatmap

- Created: 2026-09-10T01:31:36Z
- Work type: W4
- Goal: Live day-move heatmap on /portfolio: tile area is |change % x holding value|, gainers and losers clustered

## Log

- 2026-09-10T01:31:36Z scaffolded
- 2026-09-10T01:33:00Z plan: live-nav is the engine; heatmap.js is a two-region projection of row.day_pl
- 2026-09-10T01:40:00Z SDR Plan: Direction right, Do proceed, Candidates none
- 2026-09-10T01:50:00Z shipped Day move heatmap on /portfolio
  - `mark_live_nav` puts `day_pl` on each row (same term as the book sum)
  - `live_nav.js` dispatches `live-nav-applied`; heatmap.js does not fetch
  - tile area ∝ |day_pl|; gainers/losers clustered (desktop left/right, phone max-width 1100px stacked)
  - Playwright: 19 tiles, ups clustered, area tracks |day_pl|; phone stack after matchMedia fix
- 2026-09-10T01:56:00Z verify: eng_verify PASS (984); pytest live_nav+portfolio; Playwright desktop+phone

## Refactor

None beyond the marker keeping the per-lot `day_pl` it already summed and dropped.

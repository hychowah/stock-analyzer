# Eng session 2026-09-10-heatmap-fill-range

- Created: 2026-09-10T14:42:15Z
- Work type: W4
- Goal: Portfolio heatmap fill-screen plus a date range that shows holding influence over that window

## Log

- 2026-09-10T14:42:15Z scaffolded
- 2026-09-10T14:50:00Z plan: heatmap card owns fill + own time-base; last mtm-path frame is the window; heatmap.js stays fetch-free
- 2026-09-10T15:20:00Z SDR mixed → reshape. Applied: named windows resolve on the server (`period=`); Live/range is one chrome+rows operation (cached lastLiveRows, no poll wait)
- 2026-09-10T22:50:00Z shipped heatmap fill-screen + period influence
  - `GET /api/portfolio/mtm-path` is `period=` XOR `start=&end=`
  - `heatmap.js` projector + fill + source gate; `heatmap_range.js` owns chrome and fetches last frame
  - pytest live_nav/portfolio/mtm_path; eng_verify PASS (1025)
  - Browser :8780 /portfolio: Fill grows SVG (Escape restores); heatmap 1W paints HY9H/COHR/META and fills dates from the server; custom 2026-01-01..03-31 is a different map; Live restores CMCSA day-move immediately; MTM 1W Play stays independent; phone fill stacks gainers/losers
- 2026-09-11T00:10:00Z SDR (Both) mixed → reshape: collapse heatmap.js + heatmap_range.js into one card module. Deleted heatmap-range-applied / heatmap-live. live_nav.js, mtm_play.js, mtm-path XOR unchanged.

# Eng session 2026-09-10-heatmap-contrib-mtm-play

- Created: 2026-09-10T06:58:00Z
- Work type: W4
- Goal: Heatmap extra NAV-contribution % plus playable Mark-to-market P/L over a selected period

## Log

- 2026-09-10T06:58:00Z scaffolded
- 2026-09-10T07:00:00Z plan: two engines (live-nav 1D + mtm_path period), heatmap.js stays a projector; extra % is day_pl/live_nav; Play walks daily frames
- 2026-09-10T07:20:00Z absorb SDR reshape (mixed → reshape):

| Candidate | Class | Why |
|-----------|-------|-----|
| 1. Live vs period, not a 1D chip | Apply | 1D next to 1W would lie: live last-print is not the same series as a daily path. Shared strip. |
| 2. One tile event, exclusive writer | Apply | Two listeners plus the poll would clobber frames. `holding-pl-applied` + mode. |
| 3. Path lots union, missing = 0 | Apply | Buys/sells must stay on the film; None only for a held unquoted lot. |
- 2026-09-10T07:25:00Z implemented + verified
  - `contrib_pct` on live-nav rows (`day_pl / live_nav`)
  - `mtm_path.py` + `GET /api/portfolio/mtm-path`
  - `holding-pl-applied` exclusive writer by Live vs path mode
  - Playwright: extra % on live tiles; 1W Play; Live restore; phone stacked regions
  - `eng_verify` PASS
- 2026-09-10T07:45:00Z reshape plan + code: Play is MTM bars, not Day move
  - User: animation in Mark-to-market P/L, not the heatmap
  - SDR: one period owner; live_nav.js does not know mode
  - Strip moved onto the MTM card; single `data-period` token
  - heatmap stays live `holding-pl-applied`; mtm_play.js does not emit tiles
  - pytest live_nav/portfolio/mtm_path green; Playwright: 1W Play changes MTM bars only, Live restores IB table

# Child sessions for analysis_web UI/UX

Parent plan: `eng/sessions/2026-09-06-ui-ux-review/PLAN.md` (Waves 1–5, shipped)
Remainder: `eng/sessions/2026-09-06-ui-ux-review/PLAN_POST_COMPOSE.md` (Waves 6–9, post-SDR recut)
Absorb: `handoffs/SDR_ABSORB.md` (Waves 1–5) · `handoffs/SDR_ABSORB_POST_COMPOSE.md` (Waves 6–9)
Reviews: `handoffs/review-*.md` · `handoffs/review-post-compose.md`

### Waves 1–5 (shipped)

| Wave | Session dir | Slug | Start after |
|------|-------------|------|-------------|
| 1 | `eng/sessions/2026-09-06-ui-trust-p0/` | ui-trust-p0 | done |
| 2 | `eng/sessions/2026-09-06-ui-nav-ia/` | ui-nav-ia | done |
| 3 | `eng/sessions/2026-09-06-ui-decision-blotter/` | ui-decision-blotter | done |
| 4a | `eng/sessions/2026-09-06-ui-run-reading/` | ui-run-reading | done |
| 4c | `eng/sessions/2026-09-06-ui-jobs-portfolio/` | ui-jobs-portfolio | done |
| 5 | `eng/sessions/2026-09-06-ui-a11y-phone/` | ui-a11y-phone | done |

### Waves 6–9 (remainder — operator surfaces)

Scaffold when starting the wave. See `PLAN_POST_COMPOSE.md` § File ownership.

| Wave | Slug | Interface | Start after |
|------|------|-----------|-------------|
| 6 | ui-readable | Night AA, SR numbers, chrome `--muted` | done (`eng/sessions/2026-09-07-ui-readable/`) |
| 7 | ui-scan | Latest home, English Duration, in-flight banner | Wave 6 |
| 8 | ui-sheet | Cover-first run page; two sibling lists | Wave 7 |
| 9 | ui-job | Wait page is `resume_hint` | Wave 6; parallel with Wave 8 |

**One writer at a time** on `app.css` (6 → 7 → 8) and `pages.py` (7 then 8). Wave 9 does not write those.

To start a remainder wave: paste `START_NEXT_SESSION.md` (Wave 7 `ui-scan`) or that wave’s section in `PLAN_POST_COMPOSE.md`. Do not implement remainder work in the parent session until a child is scaffolded.

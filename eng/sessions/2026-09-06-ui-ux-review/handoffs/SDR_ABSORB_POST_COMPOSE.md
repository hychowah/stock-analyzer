# Strategic design review — absorb (post-compose remainder)

One Plan-mode review of the first Waves 6–9 draft. **Direction mixed, Do reshape.**

This file is the coordinator’s judgement. `PLAN_POST_COMPOSE.md` is the recut.

## Sequence after absorb

```text
Wave 6  ui-readable
Wave 7  ui-scan          after Wave 6
Wave 8  ui-sheet         after Wave 7
Wave 9  ui-job           after Wave 6; parallel with Wave 8
```

## Accepted (`this change`)

| Candidate | Action |
|-----------|--------|
| Recut four waves by operator surface (split B) | Drop the CSS warehouse. Sessions are readable / scan / sheet / job. CSS and Jinja travel with the feature. |
| Wave 6 does not pre-land `.table-scroll` or `#compare-btn:disabled` | `.table-scroll` is Wave 8. Disabled-Compare look is Wave 7. |
| Whole `runs.html` is Wave 7 | Banner, Apply vs Filters, legend. Wave 9 no longer writes `runs.html`. |
| `verdict_line` bleach helper in Wave 7 `templating.py` | Wave 8 only applies it. Wave 7 does not edit `run_detail.html`. |
| Banner is `{ticker, href}` not raw jobs | Service under `apps/analysis_web/services/`. `pages.py` does not import `research_jobs`. |
| Wave 9 does not write `pages.py` | Parallel with Wave 8 is legal only after this recut. |
| Favicon is chrome → Wave 6 | Not a job-page leftover. |
| Two sibling lists on `page_run` | `sibling_links` (always) vs `comparable_siblings` (Grok select). Do not reuse `siblings` with a flag. |

## Rejected or deferred

| Item | Why |
|------|-----|
| Exclusive file-owner split (draft A) | Temporal decomposition; false parallel on `pages.py`; Wave 9 was a leftover bag. |
| Compare A/B labels, synthesis-above-headline, `error.html` `nav.label` in Wave 9 | Not the job-page interface. Later, when that file is open. |
| Mapping `orch` to English | `resume_hint` stays the human sentence. |

## Product shape (unchanged)

Winner A from the original compose: FastAPI + Jinja tree. No SPA, no second FV.

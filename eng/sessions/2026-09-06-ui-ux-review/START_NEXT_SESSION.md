# Start the next Grok session here

Branch: **`ui-ux-compose`**. Waves 1–7 shipped. Remainder: `PLAN_POST_COMPOSE.md`.

Paste:

```
Mode B W4. Checkout branch ui-ux-compose.

Read eng/AGENTS.md, then eng/sessions/2026-09-06-ui-ux-review/PLAN_POST_COMPOSE.md
Wave 8 (ui-sheet) only.

Cover-first run page: strip → football + Read CIO cover → tape.
Two sibling lists (sibling_links vs comparable_siblings). .table-scroll.
Do not edit templating.py, runs.js, or runs.html.

Boot python -m apps.analysis_web --no-auto-restart --port 8765.
Verify with Playwright on 4516.T. Do not git commit until I agree.
```

After Wave 8: Wave 9 `ui-job` (analyze wait page). Wave 9 must not edit `app.css`, `runs.html`, `pages.py`, or `run_detail.html`.

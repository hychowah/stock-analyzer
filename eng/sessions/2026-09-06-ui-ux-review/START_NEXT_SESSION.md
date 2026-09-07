# Start the next Grok session here

Branch: **`ui-ux-compose`**. Waves 1–8 shipped. Remainder: `PLAN_POST_COMPOSE.md`.

Paste:

```
Mode B W4. Checkout branch ui-ux-compose.

Read eng/AGENTS.md, then eng/sessions/2026-09-06-ui-ux-review/PLAN_POST_COMPOSE.md
Wave 9 (ui-job) only.

Analyze wait page is resume_hint; complete offers Open catalog run / Read CIO cover as .btn.
Owns: analyze_detail.html, static/analyze_detail.js (analyze.html phase column only if already open).
Do not edit app.css, run_detail.html, runs.html, or routes/pages.py.

Boot python -m apps.analysis_web --no-auto-restart --port 8765.
Verify a complete job: no adjacent phase orch when resume_hint exists; Open catalog run is a button.
Do not git commit until I agree.
```

After Wave 9: remainder in `PLAN_POST_COMPOSE.md` Out of scope (Compare A/B labels, synthesis card order, `error.html` back label) unless a later session owns those files.

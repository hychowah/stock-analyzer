# Start the next Grok session here

Branch: **`ui-ux-compose`**. Waves 1–6 shipped (Wave 6: `eng/sessions/2026-09-07-ui-readable/`). Remainder: `PLAN_POST_COMPOSE.md`.

Paste:

```
Mode B W4. Checkout branch ui-ux-compose.

Read eng/AGENTS.md, then eng/sessions/2026-09-06-ui-ux-review/PLAN_POST_COMPOSE.md
Wave 7 (ui-scan) only.

Latest as chrome home (/?latest=1), duration_label (pass → Do not initiate),
cheap_claim_label + verdict_line helper, Apply vs Filters, in-flight banner
as [{ticker, href}], Compare-on-Latest hint, portfolio empty copy.
Do not edit run_detail.html. Do not start Wave 8.

Boot python -m apps.analysis_web --no-auto-restart --port 8765.
Verify pytest apps/analysis_web/tests and Latest vs All grain.
Do not git commit until I agree.
```

After Wave 7: Wave 8 `ui-sheet` waits on Wave 7. Wave 9 `ui-job` may start after Wave 6 and run beside Wave 8 (must not edit `app.css`, `runs.html`, `pages.py`, or `run_detail.html`).

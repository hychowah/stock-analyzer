# Start the next Grok session here

Branch: **`ui-ux-compose`** (planning commit is on this branch; implement on it).

Paste:

```
Mode B W4. Checkout branch ui-ux-compose.

Read eng/AGENTS.md, then eng/sessions/2026-09-06-ui-trust-p0/AGENT_BRIEF.md
and eng/sessions/2026-09-06-ui-ux-review/PLAN.md § Session 1.

Implement Wave 1 only (headline view, 404 Accept negotiation, Analyze .err vs muted, Compare abort copy). Do not start Wave 2.

Boot the UI from this tree (--no-auto-restart). Verify with pytest apps/analysis_web/tests and eng_verify. Do not git commit until I agree.
```

After Wave 1 lands: Wave 2 `ui-nav-ia`, then Wave 3 `ui-decision-blotter`. Wave 4a (`ui-run-reading`) waits on Wave 3. Wave 4c (`ui-jobs-portfolio`) may start after Wave 1. Wave 5 (`ui-a11y-phone`) waits on Wave 2 **and** Wave 3.

Do not run two writers on `app.css` or `run_detail.html` at once.

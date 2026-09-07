# Agent brief — ui-trust-p0 (post-SDR)

You are a Mode B (W4) implementer. Read `eng/AGENTS.md`, then:

`eng/sessions/2026-09-06-ui-ux-review/PLAN.md` § Session 1
`eng/sessions/2026-09-06-ui-ux-review/handoffs/sdr-wave1-trust-p0.md`

This session is **Wave 1**. Start now. Do not rewrite nav, runs table, or theme.

SDR verdict: **mixed / reshape**. Do not ship `row['values'][key]` as the headline fix. Do not HTML-ify JSON `/api` 404s.

## Goal

The operator never sees a blank compare number grid, a JSON 404 in the browser, a Compare abort that also says “no packets,” or a red error on a **completed** Analyze.

## Slices (feature_list ids)

1. **headline** — Python projects `{sessions, rows: [{label, cells}]}`. Template iterates labels/cells only. English labels in one map. `fmt_num`; None → `—`. Do not rename on-disk `"values"`. No blended delta.
2. **html-404** — Content negotiation: HTML chrome + `← Runs` when Accept prefers `text/html`; JSON `{"detail":…}` for JSON Accept. Pass `request` into the render. Do not unify router `_error()` copies.
3. **analyze-err** — `.err` only for failed/cancelled/abandoned; reconcile notes `.muted`.
4. **compare-abort** — if `error`, skip “No compare packets yet.”

## Verify

```
python -m pytest apps/analysis_web/tests -q
python scripts/eng_verify.py
```

Boot UI from **this** tree. Complete `/compares/{id}` has numbers in headline cells. Unknown path + HTML Accept is chrome. `/api/runs/nope` with JSON Accept stays JSON.

## Non-goals

No SPA. No blended FV. No nav regroup. No git commit until the user agrees.

## When done

Update `progress.md`. Leave `passes: true` to a verifier. Propose a commit message; do not commit.

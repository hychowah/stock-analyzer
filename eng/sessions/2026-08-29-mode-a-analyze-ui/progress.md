# Eng session 2026-08-29-mode-a-analyze-ui

- Created: 2026-08-29T00:15:40Z
- Work type: W2 then W1 (runbook) then W4 (UI)
- Goal: Shared Grok job runtime then Mode A Analyze scheduler in analysis_web

## Log

- 2026-08-29T00:15:40Z scaffolded
- Slice 1: extracted `packages/agent_jobs` from Compare spawn (constraint 11). Windows `CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS` so killing the UI must not kill Grok. `pid_alive_for_job` treats PID reuse (process birth >60s after `spawned_at`) as dead. Capacity `ANALYZE_MAX=1` `COMPARE_MAX=1` `GROK_JOBS_MAX=2`. Compare fake stays in `compare_jobs`. No FastAPI shutdown kill.
- Slice 2: `packages/research_jobs` — `check_ticker` + in-process scaffold + fake spawn (job_dir only). Cancel = kill-only. Discard/`write_abandon` snapshot-guarded. Reconcile walks `job.json`. Lock around start. gitignore `archive/research_jobs/`. Allowlist + HARNESS_MAP + archive README.
- Slice 3: `harness/orchestrator_runbook.md` `## UI-scheduled runs (read this first)` before New run vs resume. `harness/VERSION` 2.21.0 → **2.22.0**.
- Slice 4–5: in-progress opener 403s FV/report bodies; SSE `analyze_changed`; UI `/analyze`; lifespan reconcile; 404 CTA; app 2.3.0.
- Slice 6: README + eng/runbook + AGENTS.md one-liner + fixtures note.

## Resume hint

Implementer has not flipped `passes`. Verifier: `python scripts/eng_verify.py` (256+ tests; VERSION bump vs main). No git commit until the user agrees.

## Refactor note

Spawn/PID/capacity now live in `packages/agent_jobs/` so Compare and Analyze share a runtime without merging job kinds.

# Eng session 2026-09-05-ui-git-restart

- Work type: W4
- Goal: Restart Analysis UI when git HEAD moves; leave Grok jobs running

## Log

- Scaffolded W4 session.
- Recent git: 068919e static no-cache / row hover; c486e4b live cell fill.
- Implemented process supervisor (`apps/analysis_web/supervise.py`) plus UI identity (`identity.py`, SSE hello `git_sha`, `/health` Process card, `live.js` SHA reload).
- Did **not** add job-typed 503 drain, restart banner, SHA in `CatalogApi.health()` / fingerprint token, or `taskkill /T` on the UI.
- `eng_verify.py` PASS (691 tests).
- HTTP smoke on :8777 `--no-auto-restart`: `/health` Process+git_sha, `/api/health` and fingerprint have no git_sha, SSE hello SHA `068919ee…`, live.js `onHelloSha`. No browser MCP in this session.

## Refactors

- Moved uvicorn.run out of `app.main` into `supervise.run_server` so process policy lives in one module (UI replace vs Grok spawn).

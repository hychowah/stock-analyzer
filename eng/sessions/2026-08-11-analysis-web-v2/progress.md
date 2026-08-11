# Eng session 2026-08-11-analysis-web-v2

- Created: 2026-08-11
- Work type: W4
- Goal: FastAPI foundation for analysis_web (realtime / portfolio / reports ready)

## Log

- scaffolded session
- Phase 0–1: replaced stdlib WSGI with FastAPI + Jinja2 templates
  - `apps/analysis_web/app.py` create_app + uvicorn entry
  - routes: pages, api, artifacts
  - static CSS; portfolio placeholder page + example book JSON
  - tests migrated to TestClient (9 passed)
  - README + eng/runbook updated
- Phase 2: markdown → sanitized HTML; CatalogApi.list_artifacts; run detail report index
  - services/render_markdown.py (markdown-it-py + bleach)
  - /artifact renders .md HTML by default; raw=1 for source
  - eng_verify PASS (72 tests)
- Next: Phase 3 SSE change feed

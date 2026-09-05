# Eng session 2026-09-05-architecture-page

- Created: 2026-09-05T13:49:38Z
- Work type: W4
- Goal: Add a website page that renders ARCHITECTURE.md

## Log

- 2026-09-05T13:49:38Z scaffolded
- Plan: one `/architecture` route; design review reshape — heading ids in `render_markdown`, own router not `pages.py`.
- Implemented: `routes/architecture.py`, nav link, heading ids after bleach, tests, ARCHITECTURE.md / README website table.
- Verify: analysis_web tests 165 passed; `eng_verify --quick` PASS; smoke GET http://127.0.0.1:18765/architecture 200 (nav, tables, heading ids, `/` and `/analyze` still 200). No in-app browser tools; used TestClient + curl-equivalent.

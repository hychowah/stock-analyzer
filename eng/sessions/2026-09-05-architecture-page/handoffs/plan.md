# Plan — Architecture page in the website

## Goal

A person can open the analysis website, click **Architecture**, and read the live repo `ARCHITECTURE.md` as a normal page: headings, tables, links. Done means:

- `GET /architecture` is 200 when the file exists
- Header nav on `base.html` includes the link
- Body is sanitized HTML (same stack as reports), not a raw dump
- Heading ids exist so in-doc `#anchors` work
- Missing file → 404
- Tests cover the happy path, nav, 404, and sanitizer reuse
- `ARCHITECTURE.md` website table lists the new page

## Current shape

The website already renders markdown for session reports and Compare packets:

- `apps/analysis_web/services/render_markdown.py` — markdown-it + bleach; no heading ids; mermaid fences become `<pre><code>`
- `apps/analysis_web/templates/report.html` — `report-body` + `| safe`
- `apps/analysis_web/templates/base.html` — global nav
- `apps/analysis_web/routes/pages.py` — catalog pages (`/`, `/runs/{id}`, experiments, calibration, portfolio, health)
- `apps/analysis_web/routes/harness.py` — `/harness` is a **pin workflow inspector**, not a markdown doc viewer
- Source of truth: repo-root `ARCHITECTURE.md` (not copied into going-forward `pins/`)

This page is a **live working-tree document**, not a catalog artifact and not a pin.

## Design it twice

### A — One route, reuse the report renderer (winner)

`GET /architecture` on its own router reads `PROJECT_ROOT / "ARCHITECTURE.md"`, runs `render_markdown` (which now also assigns GitHub-style heading ids after bleach), renders a small template that extends `base.html`. Nav gets one link.

Interface: one URL, one file, no query params. No `Depends(get_api)`. 404 if the file is missing.

Heading ids live in `render_markdown` after sanitizing. Inject ids ourselves; do not allow user-supplied `id`. Reports getting ids is additive. The architecture route only reads the file and renders.

Mermaid: leave as fenced code. The diagrams are still readable as flowchart text. Vendoring mermaid.js is a second feature.

Absorbed from design review: (1) heading ids in the renderer, not a local post-pass; (2) `routes/architecture.py`, not `pages.py`.

### B — Generic allowlisted `/docs/{name}`

A docs CMS: allowlist `architecture` → `ARCHITECTURE.md`, maybe later `AGENTS.md`. Optional pin version. TOC sidebar.

Worse for the common case: extra indirection, pin-awareness for a file pins do not contain, and a name registry we do not need. YAGNI.

**Winner: A.** Smallest interface that matches how this UI already shows markdown. B can wait until there is a second repo doc people actually open in the UI.

## What to change

| File | Change |
|------|--------|
| `apps/analysis_web/services/render_markdown.py` | After bleach, assign GitHub-style `id`s on headings; never take user `id` |
| `apps/analysis_web/tests/test_render_markdown.py` | Anchor `#keeping-this-document-current` matches heading id |
| `apps/analysis_web/routes/architecture.py` | `GET /architecture`; `architecture_md_path()`; 404 if missing |
| `apps/analysis_web/app.py` | `include_router(architecture.router)` |
| `apps/analysis_web/templates/architecture.html` | Title, `report-body`, source path |
| `apps/analysis_web/templates/base.html` | Nav link `Architecture` → `/architecture` |
| `apps/analysis_web/tests/test_analysis_web.py` | Nav href; 200 + title/heading/id; 404 when path missing |
| `ARCHITECTURE.md` | Website table: `/architecture` |
| `apps/analysis_web/README.md` | Pages table row |

Path helper lives next to the route: `architecture_md_path() -> PROJECT_ROOT / "ARCHITECTURE.md"`. Tests monkeypatch that function. Do not put this handler in `pages.py`.

## Non-goals

- Mermaid.js / CDN diagrams
- Serving `AGENTS.md` or harness law
- Pin version switcher
- Editing the file from the UI
- Catalog dependency

## Verify

```bash
python -m pytest apps/analysis_web/tests/test_analysis_web.py apps/analysis_web/tests/test_render_markdown.py -q
python scripts/eng_verify.py --quick
```

Browser: open `http://127.0.0.1:8765/architecture`, confirm nav, headings, a table, an in-page anchor, and that `/` still has the new nav link.

## Risks

- **Path:** must read the **repo** file, not `ARCHIVE_ROOT`. Tests that set `ARCHIVE_ROOT` to a temp archive must still find `ARCHITECTURE.md` on the project root (or we inject the path).
- **Sanitizer:** relative markdown links to other `.md` files will 404 in the browser; that is acceptable (point at repo paths as text).
- **Heading slug mismatch:** implement GitHub-ish slugs (`Keeping this document current` → `keeping-this-document-current`) to match the file’s existing anchors.

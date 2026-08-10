#!/usr/bin/env python3
"""Minimal analysis UI over packages.catalog_api (stdlib only).

Usage:
    python3 -m apps.analysis_web
    ARCHIVE_ROOT=/path/to/archive python3 -m apps.analysis_web --port 8765

Does not run research phases. Reads archive catalog only.
"""

from __future__ import annotations

import argparse
import html
import os
import sys
import traceback
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlencode
from wsgiref.simple_server import make_server

# Project root on path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.catalog_api.client import (  # noqa: E402
    ArtifactDenied,
    CatalogApi,
    DbMissing,
    RunNotFound,
    default_archive_root,
)


def _archive_root() -> Path:
    raw = os.environ.get("ARCHIVE_ROOT")
    if raw:
        return Path(raw).expanduser().resolve()
    return default_archive_root()


def get_api() -> CatalogApi:
    return CatalogApi(archive_root=_archive_root(), readonly=True)


def _esc(v: Any) -> str:
    if v is None:
        return ""
    return html.escape(str(v))


def _layout(title: str, body: str, *, flash: str | None = None) -> str:
    flash_html = f'<p class="flash">{_esc(flash)}</p>' if flash else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{_esc(title)} · Stock Research Archive</title>
  <style>
    :root {{ font-family: system-ui, sans-serif; color: #1a1a1a; }}
    body {{ margin: 0; background: #f6f7f9; }}
    header {{ background: #0f172a; color: #f8fafc; padding: 0.75rem 1.25rem; }}
    header a {{ color: #93c5fd; margin-right: 1rem; text-decoration: none; }}
    header a:hover {{ text-decoration: underline; }}
    main {{ max-width: 1100px; margin: 1rem auto; padding: 0 1rem 2rem; }}
    .card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
             padding: 1rem 1.25rem; margin-bottom: 1rem; box-shadow: 0 1px 2px rgba(0,0,0,.04); }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.92rem; }}
    th, td {{ text-align: left; padding: 0.45rem 0.5rem; border-bottom: 1px solid #e2e8f0; }}
    th {{ font-size: 0.8rem; text-transform: uppercase; letter-spacing: .03em; color: #64748b; }}
    tr:hover td {{ background: #f8fafc; }}
    .mono {{ font-family: ui-monospace, monospace; font-size: 0.85rem; }}
    .muted {{ color: #64748b; }}
    .badge {{ display: inline-block; padding: 0.1rem 0.45rem; border-radius: 999px;
              font-size: 0.75rem; background: #e2e8f0; }}
    .badge.pass {{ background: #bbf7d0; color: #14532d; }}
    .badge.fail {{ background: #fecaca; color: #7f1d1d; }}
    form.filters {{ display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: end; }}
    form.filters label {{ display: flex; flex-direction: column; font-size: 0.75rem; color: #64748b; }}
    form.filters input, form.filters select {{ padding: 0.35rem 0.5rem; border: 1px solid #cbd5e1;
              border-radius: 6px; min-width: 7rem; }}
    button, .btn {{ background: #2563eb; color: #fff; border: 0; border-radius: 6px;
              padding: 0.4rem 0.75rem; cursor: pointer; text-decoration: none; font-size: 0.9rem; }}
    button.secondary {{ background: #64748b; }}
    pre {{ background: #0f172a; color: #e2e8f0; padding: 0.75rem; border-radius: 6px;
           overflow: auto; max-height: 28rem; font-size: 0.8rem; }}
    .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }}
    @media (max-width: 800px) {{ .grid2 {{ grid-template-columns: 1fr; }} }}
    .flash {{ background: #fef3c7; border: 1px solid #f59e0b; padding: 0.5rem 0.75rem; border-radius: 6px; }}
    .err {{ background: #fef2f2; border: 1px solid #f87171; padding: 0.75rem; border-radius: 6px; }}
    .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  </style>
</head>
<body>
  <header>
    <strong>Archive Analysis</strong>
    <span class="muted" style="margin-left:0.75rem;color:#94a3b8;font-size:0.85rem">read-only · Mode B</span>
    <div style="margin-top:0.4rem">
      <a href="/">Runs</a>
      <a href="/health">Health</a>
      <a href="/experiments">Experiments</a>
    </div>
  </header>
  <main>
    {flash_html}
    {body}
  </main>
</body>
</html>"""


def _fmt_num(v: Any, digits: int = 2) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):,.{digits}f}"
    except (TypeError, ValueError):
        return _esc(v)


def _verdict_badge(v: Any) -> str:
    s = str(v or "")
    cls = "pass" if s.upper() == "PASS" else ("fail" if s.upper() == "FAIL" else "")
    return f'<span class="badge {cls}">{_esc(s or "—")}</span>'


def page_health(api: CatalogApi) -> str:
    h = api.health()
    rows = "".join(
        f"<tr><th>{_esc(k)}</th><td class='mono'>{_esc(v)}</td></tr>"
        for k, v in h.items()
    )
    body = f"""
    <div class="card">
      <h1>Catalog health</h1>
      <p class="muted">ARCHIVE_ROOT = <span class="mono">{_esc(h.get('archive_root'))}</span></p>
      <table>{rows}</table>
    </div>"""
    return _layout("Health", body)


def page_runs(api: CatalogApi, qs: dict[str, list[str]]) -> str:
    ticker = (qs.get("ticker") or [""])[0].strip() or None
    sector = (qs.get("sector") or [""])[0].strip() or None
    region = (qs.get("region") or [""])[0].strip() or None
    audit = (qs.get("audit_verdict") or [""])[0].strip() or None
    experiment_id = (qs.get("experiment_id") or [""])[0].strip() or None
    try:
        limit = int((qs.get("limit") or ["50"])[0])
    except ValueError:
        limit = 50
    limit = max(1, min(limit, 200))

    try:
        runs = api.list_runs(
            ticker=ticker,
            sector=sector,
            region=region,
            audit_verdict=audit,
            experiment_id=experiment_id,
            limit=limit,
            offset=0,
        )
    except DbMissing as e:
        return _layout(
            "Runs",
            f'<div class="card err"><p>Database missing: {_esc(e)}</p>'
            f"<p>Rebuild with <code>python3 scripts/export_compare_db.py --all</code></p></div>",
        )

    trs = []
    for r in runs:
        rid = r.get("run_id") or ""
        link = f"/run?run_id={quote(str(rid), safe='')}"
        trs.append(
            f"<tr>"
            f"<td><a class='mono' href='{link}'>{_esc(r.get('ticker'))}</a></td>"
            f"<td class='mono'>{_esc(r.get('session_key'))}</td>"
            f"<td>{_esc(r.get('primary_sector'))}</td>"
            f"<td>{_esc(r.get('region'))}</td>"
            f"<td class='num'>{_fmt_num(r.get('asof_price'))}</td>"
            f"<td class='num'>{_fmt_num(r.get('fv_base'))}</td>"
            f"<td class='num'>{_fmt_num(r.get('margin_of_safety_pct'), 1)}</td>"
            f"<td>{_verdict_badge(r.get('audit_verdict'))}</td>"
            f"<td>{_esc(r.get('tech_signal'))}</td>"
            f"</tr>"
        )
    table = (
        "<table><thead><tr>"
        "<th>Ticker</th><th>Session</th><th>Sector</th><th>Region</th>"
        "<th>Price</th><th>FV base</th><th>MoS %</th><th>Audit</th><th>Tech</th>"
        "</tr></thead><tbody>"
        + ("".join(trs) or "<tr><td colspan='9' class='muted'>No runs</td></tr>")
        + "</tbody></table>"
    )

    body = f"""
    <div class="card">
      <h1>Research runs</h1>
      <p class="muted">{len(runs)} row(s) · max {limit} · source: catalog sqlite</p>
      <form class="filters" method="get" action="/">
        <label>Ticker<input name="ticker" value="{_esc(ticker or '')}" placeholder="META"/></label>
        <label>Sector<input name="sector" value="{_esc(sector or '')}"/></label>
        <label>Region<input name="region" value="{_esc(region or '')}"/></label>
        <label>Audit
          <select name="audit_verdict">
            <option value="">(any)</option>
            <option value="PASS" {"selected" if audit=="PASS" else ""}>PASS</option>
            <option value="FAIL" {"selected" if audit=="FAIL" else ""}>FAIL</option>
          </select>
        </label>
        <label>Experiment<input name="experiment_id" value="{_esc(experiment_id or '')}"/></label>
        <label>Limit<input name="limit" value="{limit}" style="min-width:4rem"/></label>
        <button type="submit">Filter</button>
        <a class="btn secondary" href="/">Reset</a>
      </form>
    </div>
    <div class="card">{table}</div>
    """
    return _layout("Runs", body)


def page_run(api: CatalogApi, qs: dict[str, list[str]]) -> str:
    run_id = (qs.get("run_id") or [""])[0].strip()
    if not run_id:
        return _layout("Run", '<div class="card err">Missing run_id</div>')
    try:
        run = api.get_run(run_id)
        paths = api.get_report_paths(run_id)
    except RunNotFound:
        return _layout("Run", f'<div class="card err">Run not found: {_esc(run_id)}</div>')
    except DbMissing as e:
        return _layout("Run", f'<div class="card err">DB missing: {_esc(e)}</div>')

    metrics = f"""
    <div class="grid2">
      <div>
        <h3>Valuation</h3>
        <table>
          <tr><th>As-of price</th><td class="num">{_fmt_num(run.get("asof_price"))} {_esc(run.get("currency"))}</td></tr>
          <tr><th>FV bear / base / bull</th>
              <td class="num">{_fmt_num(run.get("fv_bear"))} / {_fmt_num(run.get("fv_base"))} / {_fmt_num(run.get("fv_bull"))}</td></tr>
          <tr><th>FV weighted</th><td class="num">{_fmt_num(run.get("fv_weighted"))}</td></tr>
          <tr><th>p bear / base / bull</th>
              <td class="num">{_fmt_num(run.get("p_bear"), 2)} / {_fmt_num(run.get("p_base"), 2)} / {_fmt_num(run.get("p_bull"), 2)}</td></tr>
          <tr><th>MoS %</th><td class="num">{_fmt_num(run.get("margin_of_safety_pct"), 1)}</td></tr>
          <tr><th>Model</th><td>{_esc(run.get("model_name"))}</td></tr>
        </table>
      </div>
      <div>
        <h3>Context</h3>
        <table>
          <tr><th>Sector / region</th><td>{_esc(run.get("primary_sector"))} / {_esc(run.get("region"))}</td></tr>
          <tr><th>Intensity</th><td>{_esc(run.get("intensity"))}</td></tr>
          <tr><th>Audit</th><td>{_verdict_badge(run.get("audit_verdict"))}</td></tr>
          <tr><th>Tech</th><td>{_esc(run.get("tech_signal"))} · {_esc(run.get("tech_regime"))}</td></tr>
          <tr><th>Experiment</th><td class="mono">{_esc(run.get("experiment_id"))}</td></tr>
          <tr><th>Exported</th><td class="mono">{_esc(run.get("exported_at"))}</td></tr>
        </table>
      </div>
    </div>
    """

    report_links = []
    for label, key in (
        ("README", "readme"),
        ("Fundamental", "fundamental"),
        ("Technical", "technical"),
    ):
        p = paths.get(key)
        if p:
            # Serve via artifact endpoint using relpath under session
            rel = None
            try:
                root = Path(paths["session_root"])
                rel = Path(p).resolve().relative_to(Path(root).resolve()).as_posix()
            except Exception:
                rel = None
            if rel:
                href = f"/artifact?run_id={quote(run_id, safe='')}&path={quote(rel, safe='')}"
                report_links.append(f'<li><a href="{href}">{label}</a> <span class="mono muted">{_esc(rel)}</span></li>')
            else:
                report_links.append(f'<li>{label} <span class="muted">(path unavailable)</span></li>')
        else:
            report_links.append(f'<li class="muted">{label}: missing</li>')

    body = f"""
    <div class="card">
      <p><a href="/">← Runs</a></p>
      <h1 class="mono">{_esc(run.get("ticker"))} · {_esc(run.get("session_key"))}</h1>
      <p class="mono muted">{_esc(run_id)}</p>
      {metrics}
    </div>
    <div class="card">
      <h2>Reports (allowlisted artifacts)</h2>
      <ul>{"".join(report_links)}</ul>
      <p class="muted">Served via open_artifact — raw_sec denied by design.</p>
    </div>
    """
    return _layout(f"{run.get('ticker')} {run.get('session_key')}", body)


def page_artifact(api: CatalogApi, qs: dict[str, list[str]]) -> tuple[str, bytes, str]:
    """Return (content_type, body, error_html_or_empty)."""
    run_id = (qs.get("run_id") or [""])[0].strip()
    rel = (qs.get("path") or [""])[0].strip()
    if not run_id or not rel:
        return "text/html", b"", _layout("Artifact", '<div class="card err">Missing run_id or path</div>')
    try:
        data = api.open_artifact(run_id, rel)
    except ArtifactDenied as e:
        return "text/html", b"", _layout("Artifact", f'<div class="card err">Denied: {_esc(e)}</div>')
    except (RunNotFound, FileNotFoundError) as e:
        return "text/html", b"", _layout("Artifact", f'<div class="card err">Not found: {_esc(e)}</div>')

    lower = rel.lower()
    if lower.endswith(".md") or lower.endswith(".txt") or lower.endswith(".json"):
        text = data.decode("utf-8", errors="replace")
        if lower.endswith(".md") or lower.endswith(".txt"):
            body = f"""
            <div class="card">
              <p><a href="/run?run_id={quote(run_id, safe='')}">← Run</a></p>
              <h1 class="mono">{_esc(rel)}</h1>
              <pre>{_esc(text)}</pre>
            </div>"""
            return "text/html; charset=utf-8", _layout(rel, body).encode("utf-8"), ""
        body = f"""
        <div class="card">
          <p><a href="/run?run_id={quote(run_id, safe='')}">← Run</a></p>
          <h1 class="mono">{_esc(rel)}</h1>
          <pre>{_esc(text)}</pre>
        </div>"""
        return "text/html; charset=utf-8", _layout(rel, body).encode("utf-8"), ""
    # binary (e.g. png) — return raw with simple type
    ctype = "application/octet-stream"
    if lower.endswith(".png"):
        ctype = "image/png"
    elif lower.endswith(".jpg") or lower.endswith(".jpeg"):
        ctype = "image/jpeg"
    return ctype, data, ""


def page_experiments(api: CatalogApi) -> str:
    try:
        runs = api.list_runs(limit=500)
    except DbMissing as e:
        return _layout("Experiments", f'<div class="card err">{_esc(e)}</div>')

    by_exp: dict[str, list[dict[str, Any]]] = {}
    for r in runs:
        eid = r.get("experiment_id") or "(none)"
        by_exp.setdefault(str(eid), []).append(r)

    sections = []
    for eid, group in sorted(by_exp.items(), key=lambda x: (-len(x[1]), x[0])):
        if eid == "(none)" and len(by_exp) > 1:
            # still show non-experiment runs briefly
            sections.append(
                f"<div class='card'><h2>No experiment_id</h2>"
                f"<p class='muted'>{len(group)} run(s) without experiment tagging</p></div>"
            )
            continue
        trs = []
        for r in group:
            rid = r.get("run_id") or ""
            link = f"/run?run_id={quote(str(rid), safe='')}"
            trs.append(
                f"<tr>"
                f"<td><a href='{link}'>{_esc(r.get('ticker'))}</a></td>"
                f"<td class='mono'>{_esc(r.get('session_key'))}</td>"
                f"<td class='num'>{_fmt_num(r.get('fv_base'))}</td>"
                f"<td class='num'>{_fmt_num(r.get('margin_of_safety_pct'), 1)}</td>"
                f"<td>{_verdict_badge(r.get('audit_verdict'))}</td>"
                f"<td class='mono'>{_esc(r.get('orchestrator_model'))}</td>"
                f"</tr>"
            )
        sections.append(
            f"<div class='card'><h2 class='mono'>{_esc(eid)}</h2>"
            f"<p class='muted'>{len(group)} run(s)</p>"
            f"<table><thead><tr><th>Ticker</th><th>Session</th><th>FV base</th>"
            f"<th>MoS %</th><th>Audit</th><th>Model</th></tr></thead>"
            f"<tbody>{''.join(trs)}</tbody></table></div>"
        )

    body = f"<h1>Experiments</h1><p class='muted'>Grouped from catalog runs (limit 500 scan)</p>{''.join(sections)}"
    return _layout("Experiments", body)


def application(environ, start_response):
    path = environ.get("PATH_INFO") or "/"
    qs = parse_qs(environ.get("QUERY_STRING") or "")
    method = environ.get("REQUEST_METHOD", "GET")

    if method not in ("GET", "HEAD"):
        start_response("405 Method Not Allowed", [("Content-Type", "text/plain")])
        return [b"Method not allowed"]

    try:
        api = get_api()
        if path in ("/", "/runs"):
            body = page_runs(api, qs).encode("utf-8")
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
            return [body] if method == "GET" else [b""]
        if path == "/health":
            body = page_health(api).encode("utf-8")
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
            return [body] if method == "GET" else [b""]
        if path == "/run":
            body = page_run(api, qs).encode("utf-8")
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
            return [body] if method == "GET" else [b""]
        if path == "/experiments":
            body = page_experiments(api).encode("utf-8")
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
            return [body] if method == "GET" else [b""]
        if path == "/artifact":
            ctype, raw, err = page_artifact(api, qs)
            if err:
                data = err.encode("utf-8")
                start_response("403 Forbidden" if "Denied" in err else "404 Not Found",
                               [("Content-Type", "text/html; charset=utf-8")])
                return [data] if method == "GET" else [b""]
            start_response("200 OK", [("Content-Type", ctype)])
            return [raw] if method == "GET" else [b""]
        start_response("404 Not Found", [("Content-Type", "text/html; charset=utf-8")])
        return [_layout("404", '<div class="card err">Not found</div>').encode("utf-8")]
    except Exception:  # noqa: BLE001
        tb = traceback.format_exc()
        start_response("500 Internal Server Error", [("Content-Type", "text/html; charset=utf-8")])
        page = _layout("Error", f'<div class="card err"><pre>{_esc(tb)}</pre></div>')
        return [page.encode("utf-8")]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args(argv)
    root = _archive_root()
    print(f"Archive Analysis UI")
    print(f"  ARCHIVE_ROOT={root}")
    print(f"  http://{args.host}:{args.port}/")
    with make_server(args.host, args.port, application) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

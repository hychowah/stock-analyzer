"""FastAPI smoke tests for apps.analysis_web (TestClient; no network bind)."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path


def _write_session(archive: Path, ticker: str, key: str, *, fv: float) -> None:
    research = archive / "research" / ticker / key
    (research / "reports").mkdir(parents=True, exist_ok=True)
    (research / "meta").mkdir(parents=True, exist_ok=True)
    (research / "data").mkdir(parents=True, exist_ok=True)
    (research / "reports" / f"00_{ticker}_README.md").write_text(
        f"# Hello {ticker}\n", encoding="utf-8"
    )
    (research / "data" / "valuation_model.json").write_text(
        '{"name":"dcf"}', encoding="utf-8"
    )
    (research / "meta" / "prediction_snapshot.json").write_text(
        json.dumps(
            {
                "asof_price": fv * 0.8,
                "fair_value": {"base": fv, "bear": fv * 0.7, "bull": fv * 1.3},
                "margin_of_safety_pct": 12.5,
                "audit_verdict": "PASS",
                "verdict_line": "pass",
            }
        ),
        encoding="utf-8",
    )


def _mini_archive(base: Path) -> Path:
    archive = base / "archive"
    research = archive / "research" / "META" / "2026-08-03"
    (research / "reports").mkdir(parents=True)
    (research / "meta").mkdir(parents=True)
    (research / "data").mkdir(parents=True)
    (research / "reports" / "00_META_README.md").write_text("# Hello META\n", encoding="utf-8")
    (research / "data" / "valuation_model.json").write_text('{"name":"dcf"}', encoding="utf-8")
    (research / "meta" / "prediction_snapshot.json").write_text(
        json.dumps(
            {
                "asof_price": 400.0,
                "fair_value": {"base": 500.0, "bear": 350.0, "bull": 650.0},
                "margin_of_safety_pct": 12.5,
                "audit_verdict": "PASS",
            }
        ),
        encoding="utf-8",
    )
    (research / "meta" / "run_manifest.json").write_text(
        json.dumps({"ticker": "META", "quote_symbol": "META"}),
        encoding="utf-8",
    )
    catalog = archive / "catalog"
    catalog.mkdir(parents=True)
    db = catalog / "research_compare.sqlite"
    conn = sqlite3.connect(str(db))
    conn.executescript(
        """
        CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT);
        INSERT INTO schema_migrations VALUES (3, '2026-08-10T00:00:00Z');
        CREATE TABLE runs (
          run_id TEXT PRIMARY KEY,
          ticker TEXT, session_date TEXT, session_key TEXT, path TEXT,
          experiment_id TEXT, audit_verdict TEXT, data_quality TEXT, status TEXT,
          asof_price REAL, currency TEXT, primary_sector TEXT, region TEXT, intensity TEXT,
          fv_bear REAL, fv_base REAL, fv_bull REAL, fv_weighted REAL,
          p_bear REAL, p_base REAL, p_bull REAL, margin_of_safety_pct REAL,
          model_name TEXT, tech_signal TEXT, tech_regime TEXT,
          exported_at TEXT, harness_version TEXT, harness_git_sha TEXT, orchestrator_model TEXT,
          quote_symbol TEXT, quote_listing TEXT, quote_listing_source TEXT
        );
        INSERT INTO runs (
          run_id, ticker, session_date, session_key, path, experiment_id,
          audit_verdict, primary_sector, region, asof_price,
          fv_bear, fv_base, fv_bull, margin_of_safety_pct,
          harness_version, exported_at, quote_symbol, quote_listing, quote_listing_source
        ) VALUES (
          'research:META:2026-08-03', 'META', '2026-08-03', '2026-08-03',
          'archive/research/META/2026-08-03', 'exp-demo',
          'PASS', 'growth', 'us', 400.0,
          350.0, 500.0, 650.0, 12.5, '2.5.0', '2026-08-10T00:00:00Z',
          'META', 'META', 'stamp'
        );
        """
    )
    conn.commit()
    conn.close()
    return archive


def _insert_run(
    archive: Path,
    *,
    ticker: str,
    session_key: str,
    fv_base: float,
    mos: float,
    sector: str = "growth",
    audit: str = "PASS",
    harness_version: str | None = None,
) -> None:
    db = archive / "catalog" / "research_compare.sqlite"
    conn = sqlite3.connect(str(db))
    conn.execute(
        """
        INSERT INTO runs (
          run_id, ticker, session_date, session_key, path, experiment_id,
          audit_verdict, primary_sector, region, fv_base, margin_of_safety_pct,
          harness_version, exported_at, quote_symbol, quote_listing, quote_listing_source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"research:{ticker}:{session_key}",
            ticker,
            session_key,
            session_key,
            f"archive/research/{ticker}/{session_key}",
            "exp-demo",
            audit,
            sector,
            "us",
            fv_base,
            mos,
            harness_version,
            "2026-08-10T00:00:00Z",
            None,
            ticker,
            "ticker",
        ),
    )
    conn.commit()
    conn.close()


def _css_rule_bodies(css: str, selector: str) -> str:
    bodies = []
    for chunk in css.split("}"):
        if "{" not in chunk:
            continue
        head, body = chunk.split("{", 1)
        if selector in " ".join(head.split()):
            bodies.append(body)
    return "\n".join(bodies)


class QuoteLiveChgCssTests(unittest.TestCase):
    def test_sign_selectors_set_background(self):
        css = (Path(__file__).resolve().parents[1] / "static" / "app.css").read_text(
            encoding="utf-8"
        )
        for sel in (".quote-live.chg-up", ".quote-live.chg-down"):
            self.assertIn("background", _css_rule_bodies(css, sel), sel)

    def test_quotes_js_puts_sign_on_cell(self):
        qjs = (Path(__file__).resolve().parents[1] / "static" / "quotes.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('classList.remove("chg-up", "chg-down")', qjs)
        self.assertIn('classList.add("chg-up")', qjs)
        self.assertIn('classList.add("chg-down")', qjs)

    def test_row_hover_does_not_paint_td(self):
        css = (Path(__file__).resolve().parents[1] / "static" / "app.css").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("tr:hover td", css)
        self.assertIn("tr:hover {", css.replace("\r\n", "\n"))
        for sel in (".quote-live.chg-up", ".quote-live.chg-down"):
            self.assertNotIn("hover", _css_rule_bodies(css, sel), sel)


class ThemeSwitchTests(unittest.TestCase):
    def test_chrome_tokens_and_cascade(self):
        css = (Path(__file__).resolve().parents[1] / "static" / "app.css").read_text(
            encoding="utf-8"
        )
        root_m = re.search(r":root\s*\{([^}]+)\}", css)
        self.assertIsNotNone(root_m)
        root = root_m.group(1)
        for name in (
            "--bg",
            "--fg",
            "--card",
            "--paper",
            "--chart-ink",
            "--chip-bg",
        ):
            self.assertIn(name, root, name)
        dark_m = re.search(r'html\[data-theme="dark"\]\s*\{([^}]+)\}', css)
        self.assertIsNotNone(dark_m)
        dark = dark_m.group(1)
        self.assertIn("--bg", dark)
        self.assertNotIn("--paper", dark)
        media = re.search(
            r"@media\s*\(prefers-color-scheme:\s*dark\)\s*"
            r"\{\s*html:not\(\[data-theme\]\)\s*\{([^}]+)\}",
            css,
        )
        self.assertIsNotNone(media)
        inner = media.group(1)
        self.assertIn("--bg", inner)
        self.assertNotIn("--paper", inner)
        self.assertNotIn('html[data-theme="light"]', css)
        fig = _css_rule_bodies(css, ".architecture-figure")
        self.assertIn("var(--paper)", fig)

    def test_semantic_chg_stays_hex(self):
        css = (Path(__file__).resolve().parents[1] / "static" / "app.css").read_text(
            encoding="utf-8"
        )
        for sel in (".quote-live.chg-up", ".quote-live.chg-down"):
            body = _css_rule_bodies(css, sel)
            self.assertIn("background", body, sel)
            self.assertNotIn("var(", body, sel)

    def test_theme_js_boot(self):
        js = (Path(__file__).resolve().parents[1] / "static" / "theme.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("analysis_web.theme", js)
        self.assertIn("prefers-color-scheme", js)
        self.assertIn('"light"', js)
        self.assertIn('"dark"', js)
        self.assertIn("localStorage.getItem", js)
        self.assertIn("localStorage.setItem", js)
        self.assertIn("private mode", js)
        self.assertIn("theme-toggle", js)

    def test_base_loads_theme_js_before_css(self):
        base = (
            Path(__file__).resolve().parents[1] / "templates" / "base.html"
        ).read_text(encoding="utf-8")
        js_at = base.index('src="/static/theme.js"')
        css_at = base.index('href="/static/app.css"')
        self.assertLess(js_at, css_at)
        self.assertNotIn('src="/static/theme.js" defer', base)
        self.assertIn("no defer", base)
        self.assertIn('id="theme-toggle"', base)


class PhoneChromeTests(unittest.TestCase):
    def test_base_has_nav_disclose(self):
        base = (
            Path(__file__).resolve().parents[1] / "templates" / "base.html"
        ).read_text(encoding="utf-8")
        self.assertIn('id="nav-open"', base)
        self.assertIn('for="nav-open"', base)
        self.assertIn('class="disclose"', base)
        self.assertIn("disclose-btn", base)
        self.assertIn("disclose-panel", base)
        self.assertIn('id="site-nav"', base)

    def test_disclose_css_phone_contract(self):
        css = (Path(__file__).resolve().parents[1] / "static" / "app.css").read_text(
            encoding="utf-8"
        )
        self.assertRegex(css, r"\.disclose-btn\s*\{[^}]*display:\s*none")
        self.assertIn(".disclose-panel", css)
        self.assertRegex(
            css,
            r"\.disclose:checked\s*~\s*\.disclose-panel\s*\{[^}]*display:\s*block",
        )
        self.assertIn(".header-nav .disclose-panel", css)
        self.assertIn(".header-nav .disclose:checked ~ .disclose-panel", css)
        self.assertIn("flex-basis: 100%", css)
        generic_panel = re.search(
            r"(?<!nav )\.disclose-panel\s*\{([^}]+)\}",
            css,
        )
        self.assertIsNotNone(generic_panel)
        self.assertIn("display: none", generic_panel.group(1))
        self.assertNotIn("flex-basis", generic_panel.group(1))
        self.assertNotIn("form.filters label.disclose-btn", css)
        self.assertNotRegex(
            css, r"\.header-links\s*\{[^}]*display:\s*none"
        )


class PhoneStackTableTests(unittest.TestCase):
    def test_css_stack_table_contract(self):
        css = (Path(__file__).resolve().parents[1] / "static" / "app.css").read_text(
            encoding="utf-8"
        )
        self.assertIn(".stack-table", css)
        self.assertIn("content: attr(data-label)", css)
        self.assertIn("td.desktop-only", css)
        self.assertIn("td[colspan]", css)

    def test_runs_partial_labels(self):
        html = (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "partials"
            / "runs_table.html"
        ).read_text(encoding="utf-8")
        self.assertIn("stack-table", html)
        self.assertIn('data-label="Ticker"', html)
        self.assertIn('data-label="Live"', html)
        self.assertIn('data-label="MoS %"', html)
        self.assertIn("desktop-only", html)
        self.assertIn('data-label="Harness"', html)
        self.assertIn("compare-pick", html)

    def test_health_template_not_stack_table(self):
        html = (
            Path(__file__).resolve().parents[1] / "templates" / "health.html"
        ).read_text(encoding="utf-8")
        self.assertNotIn("stack-table", html)


class PhoneControlsTests(unittest.TestCase):
    def test_runs_filters_disclose(self):
        html = (
            Path(__file__).resolve().parents[1] / "templates" / "runs.html"
        ).read_text(encoding="utf-8")
        self.assertIn('id="filters-open"', html)
        self.assertIn('for="filters-open"', html)
        self.assertIn('id="filters-extra"', html)
        ticker_at = html.index('name="ticker_prefix"')
        panel_at = html.index('id="filters-extra"')
        self.assertLess(ticker_at, panel_at)
        panel = html[panel_at:]
        self.assertIn("facet_select('sector'", panel)
        self.assertIn('name="experiment_id"', panel)
        self.assertNotIn('name="ticker_prefix"', panel)
        always = html[:panel_at]
        self.assertIn('name="sort"', always)
        self.assertIn('name="dir"', always)
        self.assertIn('id="runs-reset"', always)
        open_tag = re.search(r"<input[^>]*id=\"filters-open\"[^>]*>", html)
        self.assertIsNotNone(open_tag)
        self.assertNotIn("name=", open_tag.group(0))

    def test_stack_form_on_analyze_new(self):
        html = (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "analyze_new.html"
        ).read_text(encoding="utf-8")
        self.assertIn("stack-form", html)

    def test_phone_form_css(self):
        css = (Path(__file__).resolve().parents[1] / "static" / "app.css").read_text(
            encoding="utf-8"
        )
        self.assertIn(".header-nav .disclose-btn", css)
        self.assertIn("form.filters .filters-row label", css)
        self.assertNotIn("form.filters label.disclose-btn", css)
        self.assertIn(".compare-form select", css)
        self.assertIn(".stack-form", css)
        self.assertIn('input:not([type="checkbox"]):not([type="hidden"])', css)
        self.assertIn(".chart-ranges button", css)


class AnalysisWebTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.archive = _mini_archive(Path(self._td.name))
        os.environ["ARCHIVE_ROOT"] = str(self.archive)

        import importlib

        import apps.analysis_web.app as app_mod

        importlib.reload(app_mod)
        # Recreate app so deps pick up new ARCHIVE_ROOT
        self._app = app_mod.create_app()
        from fastapi.testclient import TestClient

        self.client = TestClient(self._app)

    def tearDown(self):
        self.client.close()
        os.environ.pop("ARCHIVE_ROOT", None)
        self._td.cleanup()

    def test_home_lists_run(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"META", r.content)
        self.assertIn(b"500", r.content)
        self.assertIn(b"Harness", r.content)
        self.assertIn(b"2.5.0", r.content)
        self.assertIn(b"stack-table", r.content)
        self.assertIn(b'data-label="Ticker"', r.content)

    def test_health(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"run_count", r.content)
        self.assertIn(b"git_sha", r.content)
        self.assertIn(b"Process", r.content)
        self.assertNotIn(b"stack-table", r.content)

    def test_architecture_page(self):
        r = self.client.get("/architecture")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Architecture", r.content)
        self.assertIn(b"What this system is", r.content)
        self.assertIn(b'id="keeping-this-document-current"', r.content)
        self.assertIn(b"report-body", r.content)
        self.assertIn(b"ARCHITECTURE.md", r.content)
        self.assertIn(b'class="mermaid"', r.content)
        self.assertIn(b"/static/mermaid_boot.js", r.content)
        self.assertIn(b"flowchart", r.content)
        self.assertIn(b"Drag a diagram", r.content)
        self.assertIn(b"Reset", r.content)

    def test_mermaid_boot_script(self):
        static = Path(__file__).resolve().parents[1] / "static"
        js = (static / "mermaid_boot.js").read_text(encoding="utf-8")
        self.assertIn("securityLevel", js)
        self.assertIn("strict", js)
        self.assertIn("pre.mermaid", js)
        self.assertIn("useMaxWidth", js)
        self.assertIn("svg-pan-zoom", js)
        self.assertIn("Reset", js)
        self.assertIn("pointerenter", js)
        self.assertIn("architecture-figure", js)
        self.assertIn(".architecture-doc pre.mermaid", js)
        css = (static / "app.css").read_text(encoding="utf-8")
        self.assertIn(".architecture-figure", css)
        self.assertNotIn(
            ".architecture-doc .mermaid svg {\n  max-width: 100%;",
            css.replace("\r\n", "\n"),
        )
        r = self.client.get("/static/mermaid_boot.js")
        self.assertEqual(r.status_code, 200)

    def test_nav_architecture(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'href="/architecture"', r.content)

    def test_architecture_missing_404(self):
        from unittest.mock import patch

        from apps.analysis_web.routes import architecture as arch_mod

        missing = Path(self._td.name) / "no-such-ARCHITECTURE.md"
        with patch.object(arch_mod, "architecture_md_path", return_value=missing):
            r = self.client.get("/architecture")
        self.assertEqual(r.status_code, 404)
        self.assertIn(b"missing", r.content)

    def test_api_health_is_catalog_only(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("git_sha", r.json())

    def test_live_js_reloads_on_hello_sha_not_token(self):
        js = (Path(__file__).resolve().parents[1] / "static" / "live.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("function onHelloSha(sha)", js)
        self.assertIn("window.location.reload()", js)
        self.assertIn('if (kind === "hello") return;', js)
        self.assertNotIn("catalog-changed", js.split("function onHelloSha")[1].split("function onToken")[0])
        self.assertIn("if (wantsReload()) startPoll()", js)

    def test_static_files_revalidate(self):
        r = self.client.get("/static/quotes.js")
        self.assertEqual(r.status_code, 200)
        cc = r.headers.get("cache-control", "")
        self.assertIn("no-cache", cc)
        self.assertIn("must-revalidate", cc)

    def test_theme_toggle_on_pages(self):
        r_js = self.client.get("/static/theme.js")
        self.assertEqual(r_js.status_code, 200)
        for path in ("/", "/harness", "/health"):
            r = self.client.get(path)
            self.assertEqual(r.status_code, 200, path)
            html = r.text
            self.assertIn("/static/theme.js", html, path)
            self.assertIn('id="theme-toggle"', html, path)
            self.assertLess(
                html.index("/static/theme.js"),
                html.index("/static/app.css"),
                path,
            )

    def test_api_health(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body.get("db_exists"))
        self.assertEqual(body.get("run_count"), 1)

    def test_run_detail(self):
        r = self.client.get("/runs/research:META:2026-08-03")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"FV", r.content)
        self.assertIn(b"12.5", r.content)
        self.assertIn(b"2.5.0", r.content)
        self.assertIn(b'id="price-chart"', r.content)
        self.assertIn(b'data-symbol="META"', r.content)
        self.assertIn(b'id="price-chart-overlay"', r.content)
        self.assertIn(b"/static/price_chart.js", r.content)
        self.assertIn(b'class="js-runs-back"', r.content)
        self.assertIn(b"/static/runs.js", r.content)
        self.assertIn(b'data-range="1y"', r.content)
        self.assertIn(b'"fv_bear": 350.0', r.content)
        self.assertIn(b'"fv_base": 500.0', r.content)
        self.assertIn(b'"fv_bull": 650.0', r.content)
        self.assertIn(b'"asof_price": 400.0', r.content)

    def test_legacy_run_redirect(self):
        r = self.client.get(
            "/run",
            params={"run_id": "research:META:2026-08-03"},
            follow_redirects=False,
        )
        self.assertIn(r.status_code, (302, 307))
        self.assertIn("/runs/research:META:2026-08-03", r.headers.get("location", ""))

    def test_artifact_markdown_rendered(self):
        r = self.client.get(
            "/artifact",
            params={
                "run_id": "research:META:2026-08-03",
                "path": "reports/00_META_README.md",
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Hello META", r.content)
        # Rendered heading, not only escaped source in a bare dump
        self.assertIn(b"<h1", r.content)
        self.assertIn(b"report-body", r.content)
        self.assertNotIn(b"mermaid_boot.js", r.content)

    def test_artifact_markdown_raw(self):
        r = self.client.get(
            "/artifact",
            params={
                "run_id": "research:META:2026-08-03",
                "path": "reports/00_META_README.md",
                "raw": "1",
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"# Hello META", r.content)

    def test_artifact_xss_stripped(self):
        # Write a second report with raw HTML/script in markdown
        research = self.archive / "research" / "META" / "2026-08-03" / "reports"
        research.mkdir(parents=True, exist_ok=True)
        (research / "evil.md").write_text(
            "# Safe\n\n<script>alert(1)</script>\n\n<img src=x onerror=alert(1)>\n",
            encoding="utf-8",
        )
        r = self.client.get(
            "/artifact",
            params={
                "run_id": "research:META:2026-08-03",
                "path": "reports/evil.md",
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"<h1", r.content)
        # No live HTML tags (escaped &lt;script&gt; / &lt;img…&gt; text is OK)
        self.assertNotIn(b"<script>", r.content.lower())
        self.assertNotIn(b"<img", r.content.lower())

    def test_run_detail_lists_reports(self):
        r = self.client.get("/runs/research:META:2026-08-03")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"00_META_README.md", r.content)
        self.assertIn(b"As-of price", r.content)
        self.assertIn(b">Live<", r.content)
        self.assertIn(b"Downside %", r.content)
        self.assertIn(b"data-downside-pct", r.content)
        self.assertRegex(r.text, r'data-downside-pct[\s\S]*?>\s*12\.5')
        self.assertIn(b'data-quote-symbol="META"', r.content)
        self.assertIn(b"All reports/", r.content)
        js = Path(__file__).resolve().parents[1] / "static" / "price_chart.js"
        text = js.read_text(encoding="utf-8")
        self.assertIn("/api/price-history", text)
        self.assertIn("loadGen", text)
        self.assertIn("Price is the scale", text)
        self.assertNotIn("vsBase", text)
        self.assertNotIn("price vs base", text)
        self.assertNotIn("var RANGES", text)

    def test_experiments(self):
        r = self.client.get("/experiments")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"exp-demo", r.content)

    def test_calibration_page(self):
        r = self.client.get("/calibration")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Calibration", r.content)

    def test_api_list_runs(self):
        r = self.client.get("/api/runs", params={"ticker": "META"})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["runs"][0]["ticker"], "META")
        self.assertEqual(data["runs"][0]["quote_symbol"], "META")
        self.assertNotIn("downside_pct", data["runs"][0])
        self.assertIn("quote_listing", data["runs"][0])
        self.assertNotIn("audit", data)

    def test_audit_verdict_filter_keeps_selected(self):
        r = self.client.get("/", params={"audit_verdict": "PASS"})
        self.assertEqual(r.status_code, 200)
        self.assertRegex(
            r.text,
            r'<option value="PASS" selected>',
        )
        self.assertIn('name="audit_verdict"', r.text)

    def test_home_ticker_prefix_field(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'name="ticker_prefix"', r.content)
        self.assertIn(b'id="filters-open"', r.content)
        self.assertIn(b'id="filters-extra"', r.content)
        self.assertIn(b'name="session_date_from"', r.content)
        self.assertIn(b'name="mos_min"', r.content)
        self.assertIn(b'name="sector"', r.content)
        self.assertIn(b"<select name=\"sector\"", r.content)
        self.assertIn(b'name="harness_version"', r.content)
        self.assertIn(b"<select name=\"harness_version\"", r.content)
        self.assertIn(b"/static/runs.js", r.content)
        self.assertIn(b'id="nav-runs"', r.content)
        self.assertIn(b'id="runs-reset"', r.content)
        self.assertIn(b"/static/quotes.js", r.content)
        self.assertIn(b'data-live-partial="1"', r.content)
        self.assertIn(b"As-of", r.content)
        self.assertIn(b'aria-label="As-of min"', r.content)
        self.assertIn(b"Live", r.content)
        self.assertIn(b"Downside %", r.content)
        self.assertIn(b'data-quote-symbol="META"', r.content)
        self.assertIn(b"data-downside-pct", r.content)
        self.assertIn(b'data-fv-bear="350.0"', r.content)
        self.assertIn(b'data-asof-price="400.0"', r.content)
        self.assertRegex(r.text, r'data-downside-pct[\s\S]*?>\s*12\.5')
        self.assertIn("as-of · 400.00 → bear 350.00", r.text)
        self.assertNotIn(b'data-sort="downside_pct"', r.content)
        self.assertNotIn(b'aria-label="Price min"', r.content)
        qjs = (Path(__file__).resolve().parents[1] / "static" / "quotes.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("fillDownside", qjs)
        self.assertIn("data-downside-pct", qjs)

    def test_unstamped_row_lists_folder_ticker_not_stamp(self):
        _insert_run(
            self.archive,
            ticker="JPM",
            session_key="2026-07-25",
            fv_base=200.0,
            mos=0.0,
            sector="bank",
        )
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'data-quote-symbol="META"', r.content)
        self.assertIn(b'data-quote-source="stamp"', r.content)
        self.assertIn(b">JPM</a>", r.content)
        self.assertIn(b'data-quote-symbol="JPM"', r.content)
        api = self.client.get("/api/runs")
        by = {row["ticker"]: row for row in api.json()["runs"]}
        self.assertEqual(by["META"]["quote_symbol"], "META")
        self.assertEqual(by["META"]["quote_listing"], "META")
        self.assertIsNone(by["JPM"]["quote_symbol"])
        self.assertEqual(by["JPM"]["quote_listing"], "JPM")
        self.assertEqual(by["JPM"]["quote_listing_source"], "ticker")

    def test_fragments_runs_keeps_quote_hooks(self):
        r = self.client.get("/fragments/runs")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'data-quote-cell', r.content)
        self.assertIn(b'data-quote-symbol="META"', r.content)
        self.assertIn(b"data-downside-pct", r.content)
        self.assertIn(b'data-fv-bear="350.0"', r.content)
        self.assertIn(b'data-asof-price="400.0"', r.content)

    def test_runs_js_dispatches_quotes_refresh(self):
        js = Path(__file__).resolve().parents[1] / "static" / "runs.js"
        self.assertIn("quotes-refresh", js.read_text(encoding="utf-8"))

    def test_runs_js_remembers_query_on_nav_links(self):
        from apps.analysis_web.services.runs_query import RUN_QUERY_KEYS

        root = Path(__file__).resolve().parents[1]
        js = (root / "static" / "runs.js").read_text(encoding="utf-8")
        base = (root / "templates" / "base.html").read_text(encoding="utf-8")
        keys_m = re.search(r"var QUERY_KEYS = \[([^\]]+)\]", js)
        self.assertIsNotNone(keys_m)
        js_keys = re.findall(r'"([^"]+)"', keys_m.group(1))
        self.assertEqual(js_keys, list(RUN_QUERY_KEYS))
        self.assertIn("analysis_web.runs.query", js)
        self.assertIn("js-runs-back", js)
        self.assertIn("nav-runs", js)
        self.assertIn("runs-reset", js)
        self.assertIn('DEFAULT_LIMIT = "50"', js)
        self.assertIn('key === "limit" && v === DEFAULT_LIMIT', js)
        self.assertIn("if (s) {\n      writeStored(s);", js)
        self.assertNotIn("window.RunsMemory", js)
        self.assertNotIn("QUERY_KEY_SET", js)
        self.assertIn('id="nav-runs"', base)
        nav_at = base.index('id="nav-runs"')
        script_at = base.index('src="/static/runs.js"')
        self.assertLess(nav_at, script_at)
        self.assertNotIn('<script src="/static/runs.js" defer>', base)
        health = self.client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertIn(b'id="nav-runs"', health.content)
        self.assertIn(b"/static/runs.js", health.content)

    def test_exact_ticker_query_still_exact(self):
        r = self.client.get("/", params={"ticker": "META"})
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"META", r.content)

    def test_api_unknown_exact_ticker_aborts(self):
        r = self.client.get("/api/runs", params={"ticker": "M"})
        self.assertEqual(r.status_code, 404)
        self.assertIn("not in the catalog", r.json()["detail"])

    def test_html_unknown_ticker_aborts(self):
        r = self.client.get("/", params={"ticker": "NOPE"})
        self.assertEqual(r.status_code, 404)
        self.assertIn(b"Aborted", r.content)
        self.assertIn(b"NOPE", r.content)
        self.assertNotIn(b"No runs", r.content)
        self.assertIn(b"/analyze/new?ticker=NOPE", r.content)

    def test_html_unknown_prefix_aborts(self):
        r = self.client.get("/", params={"ticker_prefix": "ZZZ"})
        self.assertEqual(r.status_code, 404)
        self.assertIn(b"Aborted", r.content)
        frag = self.client.get("/fragments/runs", params={"ticker_prefix": "ZZZ"})
        self.assertEqual(frag.status_code, 404)
        self.assertIn(b"Aborted", frag.content)

    def test_invalid_sort_http_400(self):
        r = self.client.get("/", params={"sort": "1;DROP TABLE runs"})
        self.assertEqual(r.status_code, 400)
        api = self.client.get("/api/runs", params={"sort": "not_a_column"})
        self.assertEqual(api.status_code, 400)
        overlay = self.client.get("/api/runs", params={"sort": "downside_pct"})
        self.assertEqual(overlay.status_code, 400)
        empty = self.client.get("/api/runs", params={"sort": "", "dir": ""})
        self.assertEqual(empty.status_code, 200)


class AnalysisWebQueryTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.archive = _mini_archive(Path(self._td.name))
        _insert_run(
            self.archive,
            ticker="JPM",
            session_key="2026-07-25",
            fv_base=200.0,
            mos=-5.0,
            sector="bank",
            harness_version="2.7.0",
        )
        _insert_run(
            self.archive,
            ticker="MSFT",
            session_key="2026-08-01",
            fv_base=400.0,
            mos=20.0,
            harness_version="2.17.0",
        )
        _insert_run(
            self.archive,
            ticker="MELI",
            session_key="2026-08-16",
            fv_base=1800.0,
            mos=8.0,
            harness_version="2.17.0",
        )
        os.environ["ARCHIVE_ROOT"] = str(self.archive)

        import importlib

        import apps.analysis_web.app as app_mod

        importlib.reload(app_mod)
        self._app = app_mod.create_app()
        from fastapi.testclient import TestClient

        self.client = TestClient(self._app)

    def tearDown(self):
        self.client.close()
        os.environ.pop("ARCHIVE_ROOT", None)
        self._td.cleanup()

    def test_html_ticker_prefix_m(self):
        r = self.client.get("/", params={"ticker_prefix": "M"})
        self.assertEqual(r.status_code, 200)
        body = r.content
        self.assertIn(b"META", body)
        self.assertIn(b"MELI", body)
        self.assertIn(b"MSFT", body)
        self.assertNotIn(b"JPM", body)
        self.assertIn(b"ticker_prefix", body)

    def test_fragment_is_table_only(self):
        r = self.client.get("/fragments/runs", params={"ticker_prefix": "M"})
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"META", r.content)
        self.assertNotIn(b"JPM", r.content)
        self.assertNotIn(b"<header>", r.content)
        self.assertNotIn(b"Archive Analysis", r.content)
        self.assertIn(b"runs-table", r.content)
        self.assertIn(b"stack-table", r.content)
        self.assertIn(b"compare-pick", r.content)
        self.assertIn(b'data-label="Ticker"', r.content)

    def test_api_ticker_prefix(self):
        r = self.client.get("/api/runs", params={"ticker_prefix": "M"})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        tickers = {row["ticker"] for row in data["runs"]}
        self.assertEqual(tickers, {"MELI", "META", "MSFT"})
        self.assertEqual(data["total"], 3)
        self.assertEqual(data["count"], 3)

    def test_sort_mos_desc(self):
        r = self.client.get(
            "/",
            params={"sort": "margin_of_safety_pct", "dir": "desc"},
        )
        self.assertEqual(r.status_code, 200)
        text = r.text
        i_msft = text.find("MSFT")
        i_meta = text.find(">META<")
        if i_meta < 0:
            i_meta = text.find("META")
        i_jpm = text.find("JPM")
        self.assertGreater(i_msft, 0)
        self.assertGreater(i_meta, i_msft)
        self.assertGreater(i_jpm, i_meta)

    def test_legacy_ticker_exact_excludes_msft(self):
        r = self.client.get("/", params={"ticker": "META"})
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"META", r.content)
        self.assertNotIn(b"MSFT", r.content)
        self.assertNotIn(b"JPM", r.content)

    def test_html_session_date_range(self):
        r = self.client.get(
            "/",
            params={"session_date_from": "2026-08-01", "session_date_to": "2026-08-10"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"META", r.content)
        self.assertIn(b"MSFT", r.content)
        self.assertNotIn(b"JPM", r.content)
        self.assertNotIn(b"MELI", r.content)

    def test_html_mos_min(self):
        r = self.client.get("/", params={"mos_min": "10"})
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"META", r.content)
        self.assertIn(b"MSFT", r.content)
        self.assertNotIn(b"JPM", r.content)
        self.assertNotIn(b"MELI", r.content)

    def test_html_sector_bank(self):
        r = self.client.get("/", params={"sector": "bank"})
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"JPM", r.content)
        self.assertNotIn(b"MSFT", r.content)
        self.assertIn(b'<option value="bank" selected>', r.content)
        self.assertIn(b'<option value="growth"', r.content)

    def test_known_ticker_empty_other_filters_is_no_runs(self):
        r = self.client.get("/", params={"ticker": "META", "sector": "bank"})
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"No runs", r.content)
        self.assertNotIn(b"Aborted", r.content)

    def test_api_combined_filters(self):
        r = self.client.get(
            "/api/runs",
            params={"ticker_prefix": "M", "mos_min": "10", "session_date_from": "2026-08-01"},
        )
        self.assertEqual(r.status_code, 200)
        tickers = {row["ticker"] for row in r.json()["runs"]}
        self.assertEqual(tickers, {"META", "MSFT"})

    def test_invalid_date_http_400(self):
        r = self.client.get("/", params={"session_date_from": "08-01-2026"})
        self.assertEqual(r.status_code, 400)
        api = self.client.get("/api/runs", params={"mos_min": "nope"})
        self.assertEqual(api.status_code, 400)

    def test_html_harness_version_filter(self):
        r = self.client.get("/", params={"harness_version": "2.17.0"})
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"MSFT", r.content)
        self.assertIn(b"MELI", r.content)
        self.assertNotIn(b"JPM", r.content)
        self.assertNotIn(b">META<", r.content)
        self.assertIn(b'<option value="2.17.0" selected>', r.content)
        self.assertIn(b'<option value="2.7.0"', r.content)
        self.assertIn(b'<option value="2.5.0"', r.content)
        # semver order in the dropdown: 2.7.0 after 2.5.0 and before 2.17.0
        idx_25 = r.text.find('option value="2.5.0"')
        idx_27 = r.text.find('option value="2.7.0"')
        idx_217 = r.text.find('option value="2.17.0"')
        self.assertLess(idx_25, idx_27)
        self.assertLess(idx_27, idx_217)

    def test_fragment_harness_version(self):
        r = self.client.get("/fragments/runs", params={"harness_version": "2.5.0"})
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"META", r.content)
        self.assertNotIn(b"MSFT", r.content)
        self.assertNotIn(b"JPM", r.content)
        self.assertIn(b"2.5.0", r.content)
        self.assertIn(b"version-filter", r.content)

    def test_sort_harness_version_semver(self):
        r = self.client.get(
            "/",
            params={"sort": "harness_version", "dir": "asc"},
        )
        self.assertEqual(r.status_code, 200)
        text = r.text
        i_meta = text.find(">META<")
        i_jpm = text.find("JPM")
        i_meli = text.find("MELI")
        self.assertGreater(i_meta, 0)
        self.assertGreater(i_jpm, i_meta)
        self.assertGreater(i_meli, i_jpm)
        desc = self.client.get(
            "/",
            params={"sort": "harness_version", "dir": "desc"},
        )
        self.assertEqual(desc.status_code, 200)
        dtext = desc.text
        self.assertLess(dtext.find("MELI"), dtext.find("JPM"))
        self.assertLess(dtext.find("JPM"), dtext.find(">META<"))

    def test_api_harness_version(self):
        r = self.client.get("/api/runs", params={"harness_version": "2.17.0"})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        tickers = {row["ticker"] for row in data["runs"]}
        self.assertEqual(tickers, {"MELI", "MSFT"})
        self.assertEqual(data["total"], 2)
        self.assertTrue(all(row["harness_version"] == "2.17.0" for row in data["runs"]))


class AnalysisWebCompareTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.archive = _mini_archive(Path(self._td.name))
        _write_session(self.archive, "META", "2026-08-10", fv=600.0)
        _write_session(self.archive, "JPM", "2026-07-25", fv=200.0)
        _insert_run(
            self.archive,
            ticker="META",
            session_key="2026-08-10",
            fv_base=600.0,
            mos=8.0,
        )
        _insert_run(
            self.archive,
            ticker="JPM",
            session_key="2026-07-25",
            fv_base=200.0,
            mos=-5.0,
            sector="bank",
        )
        os.environ["ARCHIVE_ROOT"] = str(self.archive)
        os.environ["COMPARE_SPAWN"] = "fake"

        import importlib

        import apps.analysis_web.app as app_mod

        importlib.reload(app_mod)
        self._app = app_mod.create_app()
        from fastapi.testclient import TestClient

        self.client = TestClient(self._app)

    def tearDown(self):
        self.client.close()
        os.environ.pop("COMPARE_SPAWN", None)
        os.environ.pop("ARCHIVE_ROOT", None)
        self._td.cleanup()

    def test_compare_picker_is_fv_only(self):
        _insert_run(
            self.archive,
            ticker="AAPL",
            session_key="2026-07-20",
            fv_base=None,
            mos=0.0,
        )
        r = self.client.get("/compares/new")
        self.assertEqual(r.status_code, 200)
        self.assertIn("research:META:2026-08-10", r.text)
        self.assertNotIn("research:AAPL:2026-07-20", r.text)

    def test_nav_and_picker_chrome(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'href="/compares"', r.content)
        self.assertIn(b"compare-pick", r.content)
        self.assertIn(b"compare-btn", r.content)
        self.assertIn(b"/static/compares.js", r.content)

    def test_api_start_and_detail(self):
        r = self.client.post(
            "/api/compares",
            json={
                "run_id_a": "research:META:2026-08-03",
                "run_id_b": "research:META:2026-08-10",
            },
        )
        self.assertEqual(r.status_code, 202, r.text)
        job = r.json()
        self.assertEqual(job["status"], "complete")
        cid = job["compare_id"]
        page = self.client.get(f"/compares/{cid}")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Compare complete", page.content)
        self.assertIn(b"Synthesis", page.content)
        listed = self.client.get("/compares")
        self.assertEqual(listed.status_code, 200)
        self.assertIn(b"META", listed.content)

    def test_compares_unknown_ticker_aborts(self):
        r = self.client.get("/compares", params={"ticker": "NOPE"})
        self.assertEqual(r.status_code, 404)
        self.assertIn(b"Aborted", r.content)
        self.assertIn(b"NOPE", r.content)

    def test_different_tickers_400(self):
        r = self.client.post(
            "/api/compares",
            json={
                "run_id_a": "research:META:2026-08-03",
                "run_id_b": "research:JPM:2026-07-25",
            },
        )
        self.assertEqual(r.status_code, 400)

    def test_form_start(self):
        r = self.client.post(
            "/compares/new",
            data={
                "run_id_a": "research:META:2026-08-03",
                "run_id_b": "research:META:2026-08-10",
            },
            follow_redirects=False,
        )
        self.assertEqual(r.status_code, 303)
        self.assertIn("/compares/compare:", r.headers.get("location", ""))

    def test_compare_artifact_deny_log(self):
        r = self.client.post(
            "/api/compares",
            json={
                "run_id_a": "research:META:2026-08-03",
                "run_id_b": "research:META:2026-08-10",
            },
        )
        cid = r.json()["compare_id"]
        denied = self.client.get(
            "/compare-artifact",
            params={"compare_id": cid, "path": "grok.log"},
        )
        self.assertEqual(denied.status_code, 403)
        ok = self.client.get(
            "/compare-artifact",
            params={"compare_id": cid, "path": "99_synthesis.md"},
        )
        self.assertEqual(ok.status_code, 200)
        self.assertIn(b"Synthesis", ok.content)

    def test_run_detail_has_compare_form(self):
        r = self.client.get("/runs/research:META:2026-08-03")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Compare with another META session", r.content)
        self.assertIn(b"research:META:2026-08-10", r.content)
        self.assertIn(b'"session_key": "2026-08-10"', r.content)
        self.assertIn(b'"fv_base": 600.0', r.content)


class AnalysisWebAnalyzeTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.archive = _mini_archive(Path(self._td.name))
        os.environ["ARCHIVE_ROOT"] = str(self.archive)
        os.environ["AGENT_SPAWN"] = "fake"
        import importlib

        import apps.analysis_web.app as app_mod

        importlib.reload(app_mod)
        self._app = app_mod.create_app()
        from fastapi.testclient import TestClient

        self.client = TestClient(self._app)

    def tearDown(self):
        self.client.close()
        os.environ.pop("AGENT_SPAWN", None)
        os.environ.pop("ARCHIVE_ROOT", None)
        self._td.cleanup()

    def test_nav_analyze(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'href="/analyze"', r.content)
        self.assertIn(b'href="/harness"', r.content)

    def test_harness_page_and_prompt(self):
        r = self.client.get("/harness")
        self.assertEqual(r.status_code, 200, r.text[:500])
        self.assertIn(b"harness-pipeline", r.content)
        self.assertIn(b"Source facts", r.content)
        self.assertIn(b"Valuation", r.content)
        self.assertIn(b"Pick a specialist", r.content)
        self.assertIn(b"harness-page-model", r.content)
        self.assertIn(b"from Orchestrator", r.content)
        self.assertIn(b"Conventions for all agents", r.content)
        self.assertNotIn(b"pin_root", r.content)
        self.assertNotIn(b"artifact-dag", r.content)
        r404 = self.client.get("/harness", params={"version": "9.9.9"})
        self.assertEqual(r404.status_code, 404)
        spec = self.client.get("/api/harness/spec")
        self.assertEqual(spec.status_code, 200)
        body = spec.json()
        self.assertGreaterEqual(len(body.get("phases") or []), 10)
        self.assertTrue(any(e.get("kind") == "entry" for e in body.get("edges") or []))
        self.assertNotIn("stages", body)
        prompt = self.client.get("/api/harness/prompt", params={"agent": "5"})
        self.assertEqual(prompt.status_code, 200)
        data = prompt.json()
        self.assertTrue(data.get("found"))
        self.assertIn("### Agent 5", data.get("title") or "")
        self.assertNotIn("### Agent 12", data.get("body") or "")
        self.assertEqual(data.get("label"), "Valuation")
        section_ids = [s.get("id") for s in data.get("sections") or []]
        self.assertIn("template", section_ids)
        pinned = self.client.get("/harness", params={"version": "2.27.0"})
        if pinned.status_code == 200:
            self.assertIn(b"2.27.0", pinned.content)

    def test_analyze_new_has_harness_select(self):
        r = self.client.get("/analyze/new")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'name="harness_version"', r.content)
        self.assertIn(b'value="live"', r.content)

    def test_analyze_new_without_catalog_ticker(self):
        r = self.client.get("/analyze/new")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"can run in parallel", r.content)
        r2 = self.client.get("/analyze", params={"ticker": "NOPE"})
        self.assertEqual(r2.status_code, 200)
        self.assertIn(b"No Analyze jobs", r2.content)
        self.assertIn(b"can run at once", r2.content)

    def test_post_fake_and_artifact_403(self):
        from unittest.mock import patch

        from packages.kd_research.ticker_lookup import TickerCheck

        def _check(raw, backend=None):
            t = (raw or "").strip().upper()
            if t == "COHR":
                return TickerCheck(typed=t, status="quoted")
            return TickerCheck(typed=t, status="abort_unknown", reason="not a market ticker")

        with patch("packages.research_jobs.jobs.check_ticker", side_effect=_check):
            html = self.client.post(
                "/analyze/new", data={"ticker": "COHR"}, follow_redirects=False
            )
            self.assertEqual(html.status_code, 303, html.text)
            loc = html.headers.get("location") or ""
            self.assertTrue(loc.startswith("/analyze/"))
            js = self.client.post("/api/analyze", json={"ticker": "META"})
            self.assertEqual(js.status_code, 400)
            page = self.client.get(loc)
            self.assertEqual(page.status_code, 200)
            self.assertIn(b"COHR", page.content)
            art = self.client.get(
                "/analyze-artifact",
                params={
                    "analyze_id": loc.rsplit("/", 1)[-1],
                    "path": "data/valuation_model.json",
                },
            )
            self.assertEqual(art.status_code, 403)
            rpt = self.client.get(
                "/analyze-artifact",
                params={
                    "analyze_id": loc.rsplit("/", 1)[-1],
                    "path": "reports/00_COHR_README.md",
                },
            )
            self.assertEqual(rpt.status_code, 403)

    def test_post_junk_still_400(self):
        from unittest.mock import patch

        from packages.kd_research.ticker_lookup import TickerCheck

        def _check(raw, backend=None):
            return TickerCheck(
                typed=(raw or "").strip().upper(),
                status="abort_unknown",
                reason="not a market ticker",
            )

        with patch("packages.research_jobs.jobs.check_ticker", side_effect=_check):
            r = self.client.post("/analyze/new", data={"ticker": "ZZZNOPE"})
            self.assertIn(r.status_code, (200, 400))
            self.assertIn(b"not a market ticker", r.content)

    def test_new_form_has_no_listing_picker(self):
        r = self.client.get("/analyze/new")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(b"Start with a market listing instead", r.content)


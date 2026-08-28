"""FastAPI smoke tests for apps.analysis_web (TestClient; no network bind)."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


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
    catalog = archive / "catalog"
    catalog.mkdir(parents=True)
    db = catalog / "research_compare.sqlite"
    conn = sqlite3.connect(str(db))
    conn.executescript(
        """
        CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT);
        INSERT INTO schema_migrations VALUES (1, '2026-08-10T00:00:00Z');
        CREATE TABLE runs (
          run_id TEXT PRIMARY KEY,
          ticker TEXT, session_date TEXT, session_key TEXT, path TEXT,
          experiment_id TEXT, audit_verdict TEXT, data_quality TEXT, status TEXT,
          asof_price REAL, currency TEXT, primary_sector TEXT, region TEXT, intensity TEXT,
          fv_bear REAL, fv_base REAL, fv_bull REAL, fv_weighted REAL,
          p_bear REAL, p_base REAL, p_bull REAL, margin_of_safety_pct REAL,
          model_name TEXT, tech_signal TEXT, tech_regime TEXT,
          exported_at TEXT, harness_version TEXT, harness_git_sha TEXT, orchestrator_model TEXT
        );
        INSERT INTO runs (
          run_id, ticker, session_date, session_key, path, experiment_id,
          audit_verdict, primary_sector, region, fv_base, margin_of_safety_pct,
          harness_version, exported_at
        ) VALUES (
          'research:META:2026-08-03', 'META', '2026-08-03', '2026-08-03',
          'archive/research/META/2026-08-03', 'exp-demo',
          'PASS', 'growth', 'us', 500.0, 12.5, '2.5.0', '2026-08-10T00:00:00Z'
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
          harness_version, exported_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        ),
    )
    conn.commit()
    conn.close()


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
        self._td.cleanup()

    def test_home_lists_run(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"META", r.content)
        self.assertIn(b"500", r.content)
        self.assertIn(b"Harness", r.content)
        self.assertIn(b"2.5.0", r.content)

    def test_health(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"run_count", r.content)

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
        self.assertIn(b"<h1>", r.content)
        self.assertIn(b"report-body", r.content)

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
        self.assertIn(b"<h1>", r.content)
        # No live HTML tags (escaped &lt;script&gt; / &lt;img…&gt; text is OK)
        self.assertNotIn(b"<script>", r.content.lower())
        self.assertNotIn(b"<img", r.content.lower())

    def test_run_detail_lists_reports(self):
        r = self.client.get("/runs/research:META:2026-08-03")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"00_META_README.md", r.content)
        self.assertIn(b"All reports/", r.content)

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

    def test_home_ticker_prefix_field(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'name="ticker_prefix"', r.content)
        self.assertIn(b'name="session_date_from"', r.content)
        self.assertIn(b'name="mos_min"', r.content)
        self.assertIn(b'name="sector"', r.content)
        self.assertIn(b"<select name=\"sector\"", r.content)
        self.assertIn(b'name="harness_version"', r.content)
        self.assertIn(b"<select name=\"harness_version\"", r.content)
        self.assertIn(b"/static/runs.js", r.content)
        self.assertIn(b'data-live-partial="1"', r.content)

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
        self._td.cleanup()

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


if __name__ == "__main__":
    unittest.main()


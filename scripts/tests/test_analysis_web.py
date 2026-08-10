"""WSGI smoke tests for apps.analysis_web (no network server required)."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def _mini_archive(base: Path) -> Path:
    archive = base / "archive"
    research = archive / "research" / "META" / "2026-08-03"
    (research / "reports").mkdir(parents=True)
    (research / "meta").mkdir(parents=True)
    (research / "reports" / "00_META_README.md").write_text("# Hello META\n", encoding="utf-8")
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
          exported_at TEXT, harness_git_sha TEXT, orchestrator_model TEXT
        );
        INSERT INTO runs (
          run_id, ticker, session_date, session_key, path, experiment_id,
          audit_verdict, primary_sector, region, fv_base, margin_of_safety_pct, exported_at
        ) VALUES (
          'research:META:2026-08-03', 'META', '2026-08-03', '2026-08-03',
          'archive/research/META/2026-08-03', 'exp-demo',
          'PASS', 'growth', 'us', 500.0, 12.5, '2026-08-10T00:00:00Z'
        );
        """
    )
    conn.commit()
    conn.close()
    return archive


class AnalysisWebTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.archive = _mini_archive(Path(self._td.name))
        import os

        os.environ["ARCHIVE_ROOT"] = str(self.archive)
        # Re-import app after env set
        import importlib

        import apps.analysis_web.app as app_mod

        importlib.reload(app_mod)
        self.app = app_mod.application

    def tearDown(self):
        self._td.cleanup()

    def _call(self, path: str, qs: str = "") -> tuple[str, bytes]:
        status_headers: list = []

        def start_response(status, headers):
            status_headers.append(status)
            status_headers.append(headers)

        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": path,
            "QUERY_STRING": qs,
            "wsgi.input": None,
            "wsgi.errors": sys.stderr,
            "wsgi.version": (1, 0),
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
            "wsgi.url_scheme": "http",
            "SERVER_NAME": "test",
            "SERVER_PORT": "80",
        }
        body = b"".join(self.app(environ, start_response))
        return status_headers[0], body

    def test_home_lists_run(self):
        status, body = self._call("/")
        self.assertTrue(status.startswith("200"))
        self.assertIn(b"META", body)
        self.assertIn(b"500", body)

    def test_health(self):
        status, body = self._call("/health")
        self.assertTrue(status.startswith("200"))
        self.assertIn(b"run_count", body)

    def test_run_detail(self):
        status, body = self._call("/run", "run_id=research:META:2026-08-03")
        self.assertTrue(status.startswith("200"))
        self.assertIn(b"FV", body)
        self.assertIn(b"12.5", body)

    def test_artifact(self):
        status, body = self._call(
            "/artifact",
            "run_id=research:META:2026-08-03&path=reports/00_META_README.md",
        )
        self.assertTrue(status.startswith("200"))
        self.assertIn(b"Hello META", body)

    def test_experiments(self):
        status, body = self._call("/experiments")
        self.assertTrue(status.startswith("200"))
        self.assertIn(b"exp-demo", body)


if __name__ == "__main__":
    unittest.main()

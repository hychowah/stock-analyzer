"""FastAPI smoke tests for apps.analysis_web (TestClient; no network bind)."""

from __future__ import annotations

import os
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

    def test_legacy_run_redirect(self):
        r = self.client.get(
            "/run",
            params={"run_id": "research:META:2026-08-03"},
            follow_redirects=False,
        )
        self.assertIn(r.status_code, (302, 307))
        self.assertIn("/runs/research:META:2026-08-03", r.headers.get("location", ""))

    def test_artifact(self):
        r = self.client.get(
            "/artifact",
            params={
                "run_id": "research:META:2026-08-03",
                "path": "reports/00_META_README.md",
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Hello META", r.content)

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
        self.assertEqual(data["runs"][0]["ticker"], "META")


if __name__ == "__main__":
    unittest.main()

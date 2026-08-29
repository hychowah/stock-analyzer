"""Unit tests for analysis_web change fingerprints + SSE smoke."""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


class ChangeFeedUnitTests(unittest.TestCase):
    def test_fingerprint_changes_on_db_touch(self):
        from apps.analysis_web.services.change_feed import (
            classify_change,
            fingerprint,
        )

        with tempfile.TemporaryDirectory() as td:
            ar = Path(td) / "archive"
            cat = ar / "catalog"
            cat.mkdir(parents=True)
            db = cat / "research_compare.sqlite"
            db.write_bytes(b"x")
            fp1 = fingerprint(root=ar)
            token1 = fp1["token"]
            db.write_bytes(b"xy")
            fp2 = fingerprint(root=ar)
            self.assertNotEqual(token1, fp2["token"])
            events = classify_change(fp1, fp2)
            self.assertIn("catalog_changed", events)

    def test_analyze_job_classified_not_catalog(self):
        from apps.analysis_web.services.change_feed import classify_change, fingerprint

        with tempfile.TemporaryDirectory() as td:
            ar = Path(td) / "archive"
            (ar / "catalog").mkdir(parents=True)
            fp1 = fingerprint(root=ar)
            packet = ar / "research_jobs" / "COHR" / "2026-08-29"
            packet.mkdir(parents=True)
            (packet / "job.json").write_text('{"status":"running"}', encoding="utf-8")
            phase = ar / "research" / "COHR" / "2026-08-29" / "registry"
            phase.mkdir(parents=True)
            (phase / "phase_status.json").write_text('{"current_phase":"orch"}', encoding="utf-8")
            fp2 = fingerprint(root=ar)
            events = classify_change(fp1, fp2)
            self.assertIn("analyze_changed", events)
            self.assertNotIn("catalog_changed", events)

    def test_sqlite_still_catalog_only(self):
        from apps.analysis_web.services.change_feed import classify_change, fingerprint

        with tempfile.TemporaryDirectory() as td:
            ar = Path(td) / "archive"
            cat = ar / "catalog"
            cat.mkdir(parents=True)
            db = cat / "research_compare.sqlite"
            db.write_bytes(b"x")
            fp1 = fingerprint(root=ar)
            db.write_bytes(b"xy")
            events = classify_change(fp1, fingerprint(root=ar))
            self.assertIn("catalog_changed", events)
            self.assertNotIn("analyze_changed", events)

    def test_compare_packet_classified(self):
        from apps.analysis_web.services.change_feed import classify_change, fingerprint

        with tempfile.TemporaryDirectory() as td:
            ar = Path(td) / "archive"
            (ar / "catalog").mkdir(parents=True)
            fp1 = fingerprint(root=ar)
            packet = ar / "comparisons" / "META" / "2026-08-26__a_vs_b"
            packet.mkdir(parents=True)
            (packet / "job.json").write_text('{"status":"running"}', encoding="utf-8")
            fp2 = fingerprint(root=ar)
            self.assertNotEqual(fp1["token"], fp2["token"])
            self.assertIn("compare_changed", classify_change(fp1, fp2))

    def test_portfolio_change_classified(self):
        from apps.analysis_web.services import change_feed as cf

        with tempfile.TemporaryDirectory() as td:
            ar = Path(td) / "archive"
            (ar / "catalog").mkdir(parents=True)
            # Point local_dir at temp via monkeypatch
            local = Path(td) / "local"
            local.mkdir()
            book = local / "portfolio.json"
            book.write_text('{"positions":[]}', encoding="utf-8")
            orig_local = cf.local_dir
            orig_archive = cf.archive_root
            try:
                cf.local_dir = lambda: local  # type: ignore[assignment]
                cf.archive_root = lambda: ar  # type: ignore[assignment]
                fp1 = cf.fingerprint(root=ar)
                book.write_text('{"positions":[{"ticker":"META"}]}', encoding="utf-8")
                fp2 = cf.fingerprint(root=ar)
                self.assertNotEqual(fp1["token"], fp2["token"])
                self.assertIn("portfolio_changed", cf.classify_change(fp1, fp2))
            finally:
                cf.local_dir = orig_local  # type: ignore[assignment]
                cf.archive_root = orig_archive  # type: ignore[assignment]


class EventsEndpointTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        archive = Path(self._td.name) / "archive"
        research = archive / "research" / "META" / "2026-08-03"
        (research / "reports").mkdir(parents=True)
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
              run_id, ticker, session_date, session_key, path,
              audit_verdict, fv_base, margin_of_safety_pct, exported_at
            ) VALUES (
              'research:META:2026-08-03', 'META', '2026-08-03', '2026-08-03',
              'archive/research/META/2026-08-03', 'PASS', 500.0, 12.5, '2026-08-10T00:00:00Z'
            );
            """
        )
        conn.commit()
        conn.close()
        os.environ["ARCHIVE_ROOT"] = str(archive)
        import importlib

        import apps.analysis_web.app as app_mod

        importlib.reload(app_mod)
        from fastapi.testclient import TestClient

        self.client = TestClient(app_mod.create_app())

    def tearDown(self):
        self.client.close()
        self._td.cleanup()

    def test_fingerprint_endpoint(self):
        r = self.client.get("/api/fingerprint")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("token", body)
        self.assertTrue(body.get("catalog_db_exists"))

    def test_events_hello_once(self):
        r = self.client.get("/api/events", params={"once": 1, "interval_ms": 200})
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/event-stream", r.headers.get("content-type", ""))
        text = r.text
        self.assertIn("event: hello", text)
        self.assertIn("data:", text)

    def test_runs_page_opt_in_live(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'data-live-reload="1"', r.content)
        self.assertIn(b"live.js", r.content)


if __name__ == "__main__":
    unittest.main()

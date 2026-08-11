"""CatalogApi tests against synthetic ARCHIVE_ROOT fixtures."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from packages.catalog_api.client import (  # noqa: E402
    ArtifactDenied,
    CatalogApi,
    DbMissing,
    RunNotFound,
    parse_run_id,
)


def _make_mini_archive(base: Path) -> Path:
    """Create archive/ shape with one run in sqlite + session files."""
    archive = base / "archive"
    research = archive / "research" / "META" / "2026-08-03"
    (research / "reports").mkdir(parents=True)
    (research / "meta").mkdir(parents=True)
    (research / "registry").mkdir(parents=True)
    (research / "data").mkdir(parents=True)
    (research / "reports" / "00_META_README.md").write_text("# META\n", encoding="utf-8")
    (research / "meta" / "prediction_snapshot.json").write_text(
        json.dumps({"ticker": "META", "session_date": "2026-08-03"}),
        encoding="utf-8",
    )
    (research / "data" / "raw_sec").mkdir()
    (research / "data" / "raw_sec" / "secret.txt").write_text("nope", encoding="utf-8")

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
          ticker TEXT,
          session_date TEXT,
          session_key TEXT,
          path TEXT,
          experiment_id TEXT,
          audit_verdict TEXT,
          data_quality TEXT,
          status TEXT,
          asof_price REAL,
          currency TEXT,
          primary_sector TEXT,
          region TEXT,
          intensity TEXT,
          fv_bear REAL, fv_base REAL, fv_bull REAL, fv_weighted REAL,
          p_bear REAL, p_base REAL, p_bull REAL,
          margin_of_safety_pct REAL,
          model_name TEXT,
          tech_signal TEXT,
          tech_regime TEXT,
          exported_at TEXT,
          harness_git_sha TEXT,
          orchestrator_model TEXT
        );
        """
    )
    conn.execute(
        """
        INSERT INTO runs (
          run_id, ticker, session_date, session_key, path,
          audit_verdict, primary_sector, region, fv_base, margin_of_safety_pct,
          exported_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "research:META:2026-08-03",
            "META",
            "2026-08-03",
            "2026-08-03",
            "archive/research/META/2026-08-03",
            "PASS",
            "growth",
            "us",
            500.0,
            10.0,
            "2026-08-10T00:00:00Z",
        ),
    )
    conn.commit()
    conn.close()
    return archive


class ParseRunIdTests(unittest.TestCase):
    def test_parse(self):
        t, k = parse_run_id("research:META:2026-08-03")
        self.assertEqual(t, "META")
        self.assertEqual(k, "2026-08-03")

    def test_parse_slug(self):
        t, k = parse_run_id("research:META:2026-08-03__r1")
        self.assertEqual(k, "2026-08-03__r1")


class CatalogApiTests(unittest.TestCase):
    def setUp(self):
        # ignore_cleanup_errors: Windows may hold SQLite URI handles briefly
        self._td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.archive = _make_mini_archive(Path(self._td.name))
        self.api = CatalogApi(archive_root=self.archive, readonly=True)

    def tearDown(self):
        self.api = None  # type: ignore[assignment]
        self._td.cleanup()

    def test_health(self):
        h = self.api.health()
        self.assertTrue(h["db_exists"])
        self.assertEqual(h["run_count"], 1)
        self.assertEqual(h["schema_version"], 1)

    def test_list_and_get(self):
        rows = self.api.list_runs(limit=10)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["ticker"], "META")
        run = self.api.get_run("research:META:2026-08-03")
        self.assertEqual(run["fv_base"], 500.0)

    def test_list_filter_ticker(self):
        self.assertEqual(self.api.list_runs(ticker="meta"), self.api.list_runs(ticker="META"))
        self.assertEqual(self.api.list_runs(ticker="AAPL"), [])

    def test_session_root_via_run_id(self):
        root = self.api.get_session_root("research:META:2026-08-03")
        self.assertTrue((root / "reports").is_dir())

    def test_report_paths(self):
        paths = self.api.get_report_paths("research:META:2026-08-03")
        self.assertIsNotNone(paths["readme"])

    def test_open_artifact_ok(self):
        data = self.api.open_artifact("research:META:2026-08-03", "reports/00_META_README.md")
        self.assertIn(b"META", data)

    def test_list_artifacts(self):
        items = self.api.list_artifacts("research:META:2026-08-03", prefix="reports/")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["name"], "00_META_README.md")
        self.assertEqual(items[0]["relpath"], "reports/00_META_README.md")
        self.assertIsInstance(items[0]["size_bytes"], int)

    def test_list_artifacts_denied_prefix(self):
        with self.assertRaises(ArtifactDenied):
            self.api.list_artifacts("research:META:2026-08-03", prefix="data/raw_sec/")

    def test_open_artifact_traversal_denied(self):
        with self.assertRaises(ArtifactDenied):
            self.api.open_artifact("research:META:2026-08-03", "../secret")
        with self.assertRaises(ArtifactDenied):
            self.api.open_artifact("research:META:2026-08-03", "reports/../../etc/passwd")

    def test_open_artifact_raw_sec_denied(self):
        with self.assertRaises(ArtifactDenied):
            self.api.open_artifact(
                "research:META:2026-08-03", "data/raw_sec/secret.txt"
            )

    def test_missing_run(self):
        with self.assertRaises(RunNotFound):
            self.api.get_run("research:NOPE:2020-01-01")

    def test_db_missing(self):
        with tempfile.TemporaryDirectory() as td:
            empty = Path(td) / "archive"
            empty.mkdir()
            api = CatalogApi(archive_root=empty, readonly=True)
            with self.assertRaises(DbMissing):
                api.list_runs()

    def test_rejects_writable_flag(self):
        with self.assertRaises(ValueError):
            CatalogApi(archive_root=self.archive, readonly=False)


class LiveArchiveSmokeTests(unittest.TestCase):
    """Optional: skip if project archive DB missing."""

    def test_live_health_if_present(self):
        live = ROOT / "archive"
        db = live / "catalog" / "research_compare.sqlite"
        if not db.is_file():
            self.skipTest("live archive sqlite not present")
        api = CatalogApi(archive_root=live, readonly=True)
        h = api.health()
        self.assertTrue(h["db_exists"])
        self.assertGreaterEqual(h["run_count"] or 0, 1)
        rows = api.list_runs(limit=3)
        self.assertGreaterEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()

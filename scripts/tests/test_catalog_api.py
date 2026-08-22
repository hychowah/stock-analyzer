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


def _insert_run(
    db: Path,
    *,
    ticker: str,
    session_key: str,
    fv_base: float = 100.0,
    mos: float = 0.0,
    sector: str = "growth",
    region: str = "us",
    audit: str = "PASS",
) -> None:
    session_date = session_key.split("__", 1)[0]
    conn = sqlite3.connect(str(db))
    conn.execute(
        """
        INSERT INTO runs (
          run_id, ticker, session_date, session_key, path,
          audit_verdict, primary_sector, region, fv_base, margin_of_safety_pct,
          exported_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"research:{ticker}:{session_key}",
            ticker,
            session_date,
            session_key,
            f"archive/research/{ticker}/{session_key}",
            audit,
            sector,
            region,
            fv_base,
            mos,
            "2026-08-10T00:00:00Z",
        ),
    )
    conn.commit()
    conn.close()


def _make_multi_archive(base: Path) -> Path:
    archive = _make_mini_archive(base)
    db = archive / "catalog" / "research_compare.sqlite"
    _insert_run(db, ticker="JPM", session_key="2026-07-25", fv_base=200.0, mos=-5.0, sector="bank")
    _insert_run(db, ticker="MSFT", session_key="2026-08-01", fv_base=400.0, mos=20.0, sector="growth")
    _insert_run(db, ticker="MELI", session_key="2026-08-16", fv_base=1800.0, mos=8.0, sector="growth")
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

    def test_list_runs_returns_list(self):
        rows = self.api.list_runs(limit=10)
        self.assertIsInstance(rows, list)


class CatalogQueryTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.archive = _make_multi_archive(Path(self._td.name))
        self.api = CatalogApi(archive_root=self.archive, readonly=True)

    def tearDown(self):
        self.api = None  # type: ignore[assignment]
        self._td.cleanup()

    def test_exact_ticker_unchanged(self):
        self.assertEqual(self.api.list_runs(ticker="meta"), self.api.list_runs(ticker="META"))
        self.assertEqual(self.api.list_runs(ticker="M"), [])
        self.assertEqual(len(self.api.list_runs(ticker="META")), 1)

    def test_ticker_prefix_starts_with(self):
        rows = self.api.list_runs(ticker_prefix="M", limit=50)
        tickers = {r["ticker"] for r in rows}
        self.assertEqual(tickers, {"MELI", "META", "MSFT"})
        self.assertNotIn("JPM", tickers)

    def test_ticker_prefix_case_insensitive(self):
        upper = {r["ticker"] for r in self.api.list_runs(ticker_prefix="m")}
        self.assertEqual(upper, {"MELI", "META", "MSFT"})

    def test_ticker_prefix_empty_is_all(self):
        self.assertEqual(len(self.api.list_runs(ticker_prefix="")), 4)
        self.assertEqual(len(self.api.list_runs(ticker_prefix="   ")), 4)

    def test_like_wildcards_are_literals(self):
        self.assertEqual(self.api.list_runs(ticker_prefix="ME%"), [])
        self.assertEqual(self.api.list_runs(ticker_prefix="M_"), [])
        self.assertEqual(self.api.list_runs(ticker_prefix="%"), [])

    def test_count_runs_matches_prefix(self):
        n = self.api.count_runs(ticker_prefix="M")
        rows = self.api.list_runs(ticker_prefix="M", limit=50)
        self.assertEqual(n, 3)
        self.assertEqual(n, len(rows))
        self.assertGreaterEqual(self.api.count_runs(), len(self.api.list_runs(limit=50)))

    def test_sort_mos_desc(self):
        rows = self.api.list_runs(sort="margin_of_safety_pct", dir="desc", limit=50)
        mos = [r["margin_of_safety_pct"] for r in rows]
        self.assertEqual(mos, sorted(mos, reverse=True))
        self.assertEqual(rows[0]["ticker"], "MSFT")

    def test_default_order_unchanged(self):
        rows = self.api.list_runs(limit=50)
        self.assertEqual([r["ticker"] for r in rows], ["JPM", "MELI", "META", "MSFT"])

    def test_invalid_sort_raises(self):
        with self.assertRaises(ValueError):
            self.api.list_runs(sort="1;DROP TABLE runs")
        with self.assertRaises(ValueError):
            self.api.list_runs(sort="fv_base", dir="sideways")
        with self.assertRaises(ValueError):
            self.api.list_runs(dir="desc")

    def test_exact_and_prefix_and(self):
        rows = self.api.list_runs(ticker="META", ticker_prefix="M")
        self.assertEqual([r["ticker"] for r in rows], ["META"])
        self.assertEqual(self.api.list_runs(ticker="JPM", ticker_prefix="M"), [])

    def test_session_date_range(self):
        rows = self.api.list_runs(
            session_date_from="2026-08-01",
            session_date_to="2026-08-10",
            limit=50,
        )
        self.assertEqual({r["ticker"] for r in rows}, {"META", "MSFT"})

    def test_session_date_from_only(self):
        rows = self.api.list_runs(session_date_from="2026-08-16", limit=50)
        self.assertEqual({r["ticker"] for r in rows}, {"MELI"})

    def test_mos_range(self):
        rows = self.api.list_runs(mos_min=8, mos_max=12, limit=50)
        self.assertEqual({r["ticker"] for r in rows}, {"META", "MELI"})
        high = self.api.list_runs(mos_min=15, limit=50)
        self.assertEqual({r["ticker"] for r in high}, {"MSFT"})

    def test_sector_exact(self):
        rows = self.api.list_runs(sector="bank", limit=50)
        self.assertEqual([r["ticker"] for r in rows], ["JPM"])

    def test_fv_base_min(self):
        rows = self.api.list_runs(fv_base_min=450, limit=50)
        self.assertEqual({r["ticker"] for r in rows}, {"META", "MELI"})

    def test_invalid_date_raises(self):
        with self.assertRaises(ValueError):
            self.api.list_runs(session_date_from="08-01-2026")
        with self.assertRaises(ValueError):
            self.api.list_runs(session_date_from="2026-08-10", session_date_to="2026-08-01")

    def test_invalid_mos_range_raises(self):
        with self.assertRaises(ValueError):
            self.api.list_runs(mos_min=20, mos_max=0)
        with self.assertRaises(ValueError):
            self.api.list_runs(mos_min="abc")

    def test_count_runs_honors_range(self):
        self.assertEqual(self.api.count_runs(mos_min=15), 1)
        self.assertEqual(self.api.count_runs(sector="growth"), 3)

    def test_list_run_facets(self):
        facets = self.api.list_run_facets()
        self.assertEqual(set(facets["sector"]), {"bank", "growth"})
        self.assertIn("us", facets["region"])
        self.assertEqual(facets["tech_signal"], [])


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

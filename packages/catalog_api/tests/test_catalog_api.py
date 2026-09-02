"""CatalogApi tests against synthetic ARCHIVE_ROOT fixtures."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.paths import PROJECT_ROOT as ROOT

from packages.catalog_api.client import (
    ArtifactDenied,
    CatalogApi,
    CompareNotFound,
    DbMissing,
    RunNotFound,
    parse_compare_id,
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

    def test_parse_compare_id(self):
        t, k = parse_compare_id("compare:META:2026-08-26__2026-08-03_vs_2026-08-10")
        self.assertEqual(t, "META")
        self.assertEqual(k, "2026-08-26__2026-08-03_vs_2026-08-10")


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
        self.assertIsNone(rows[0].get("quote_symbol"))
        self.assertEqual(rows[0].get("quote_listing"), "META")
        self.assertEqual(rows[0].get("quote_listing_source"), "ticker")
        run = self.api.get_run("research:META:2026-08-03")
        self.assertEqual(run["fv_base"], 500.0)
        self.assertIsNone(run.get("quote_symbol"))
        self.assertEqual(run.get("quote_listing"), "META")

    def test_quote_symbol_from_stamp_no_ticker_fallback(self):
        session = self.archive / "research" / "META" / "2026-08-03"
        (session / "meta" / "run_manifest.json").write_text(
            json.dumps({"ticker": "META", "quote_symbol": "META"}),
            encoding="utf-8",
        )
        rows = self.api.list_runs(limit=10)
        self.assertEqual(rows[0]["quote_symbol"], "META")
        self.assertEqual(rows[0]["quote_listing"], "META")
        self.assertEqual(rows[0]["quote_listing_source"], "stamp")
        run = self.api.get_run("research:META:2026-08-03")
        self.assertEqual(run["quote_symbol"], "META")

        (session / "meta" / "run_manifest.json").write_text(
            json.dumps({"ticker": "META", "quote_symbol": "ADYEN.AS"}),
            encoding="utf-8",
        )
        stamped = self.api.get_run("research:META:2026-08-03")
        self.assertEqual(stamped["quote_symbol"], "ADYEN.AS")
        self.assertEqual(stamped["quote_listing"], "ADYEN.AS")

        (session / "meta" / "run_manifest.json").write_text(
            json.dumps({"ticker": "META", "quote_symbol": None}),
            encoding="utf-8",
        )
        (session / "data").mkdir(exist_ok=True)
        (session / "data" / "price_snapshot.json").write_text(
            json.dumps({"ticker": "META", "quote_symbol": "ADYEN.AS"}),
            encoding="utf-8",
        )
        from_snap = self.api.get_run("research:META:2026-08-03")
        self.assertIsNone(from_snap["quote_symbol"])
        self.assertEqual(from_snap["quote_listing"], "ADYEN.AS")
        self.assertEqual(from_snap["quote_listing_source"], "snapshot")

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

    def test_require_ticker_aborts_unknown(self):
        from packages.catalog_api.client import TickerNotFound

        self.api.require_ticker(ticker="META")
        self.api.require_ticker(ticker_prefix="M")
        with self.assertRaises(TickerNotFound) as ctx:
            self.api.require_ticker(ticker="M")
        self.assertEqual(ctx.exception.kind, "ticker")
        with self.assertRaises(TickerNotFound):
            self.api.require_ticker(ticker_prefix="ZZZ")
        self.assertTrue(self.api.ticker_in_catalog(ticker="META"))
        self.assertFalse(self.api.ticker_in_catalog(ticker="NOPE"))

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
        self.assertEqual(facets["harness_version"], [])

    def test_harness_version_filter_without_column_empty(self):
        self.assertEqual(self.api.list_runs(harness_version="2.17.0", limit=50), [])
        self.assertEqual(self.api.count_runs(harness_version="2.17.0"), 0)
        self.assertEqual(self.api.list_runs(limit=50)[0]["ticker"], "JPM")
        with self.assertRaises(ValueError):
            self.api.list_runs(sort="harness_version", limit=50)

    def test_harness_version_exact_and_facet(self):
        db = self.archive / "catalog" / "research_compare.sqlite"
        conn = sqlite3.connect(str(db))
        conn.execute("ALTER TABLE runs ADD COLUMN harness_version TEXT")
        conn.execute("UPDATE runs SET harness_version = '2.5.0' WHERE ticker = 'META'")
        conn.execute("UPDATE runs SET harness_version = '2.4.0' WHERE ticker = 'JPM'")
        conn.execute(
            "UPDATE runs SET harness_version = '2.17.0' WHERE ticker IN ('MSFT', 'MELI')"
        )
        conn.commit()
        conn.close()

        rows = self.api.list_runs(harness_version="2.17.0", limit=50)
        self.assertEqual({r["ticker"] for r in rows}, {"MSFT", "MELI"})
        self.assertTrue(all(r["harness_version"] == "2.17.0" for r in rows))
        self.assertEqual(self.api.count_runs(harness_version="2.17.0"), 2)
        self.assertEqual(self.api.list_runs(harness_version="9.9.9", limit=50), [])
        self.assertEqual(
            {r["ticker"] for r in self.api.list_runs(harness_version="2.5.0", limit=50)},
            {"META"},
        )
        facets = self.api.list_run_facets()
        self.assertEqual(facets["harness_version"], ["2.4.0", "2.5.0", "2.17.0"])

    def test_harness_version_semver_sort(self):
        db = self.archive / "catalog" / "research_compare.sqlite"
        conn = sqlite3.connect(str(db))
        conn.execute("ALTER TABLE runs ADD COLUMN harness_version TEXT")
        conn.execute("UPDATE runs SET harness_version = '2.7.0' WHERE ticker = 'META'")
        conn.execute("UPDATE runs SET harness_version = '2.4.0' WHERE ticker = 'JPM'")
        conn.execute(
            "UPDATE runs SET harness_version = '2.17.0' WHERE ticker IN ('MSFT', 'MELI')"
        )
        conn.commit()
        conn.close()

        asc = [
            r["harness_version"]
            for r in self.api.list_runs(sort="harness_version", dir="asc", limit=50)
        ]
        self.assertEqual(asc, ["2.4.0", "2.7.0", "2.17.0", "2.17.0"])
        desc = [
            r["harness_version"]
            for r in self.api.list_runs(sort="harness_version", dir="desc", limit=50)
        ]
        self.assertEqual(desc[0], "2.17.0")
        self.assertEqual(desc[-1], "2.4.0")
        self.assertNotEqual(desc, sorted(desc, reverse=True))
        tickers_asc = [
            r["ticker"]
            for r in self.api.list_runs(sort="harness_version", dir="asc", limit=50)
        ]
        self.assertEqual(tickers_asc, ["JPM", "META", "MELI", "MSFT"])

    def test_null_fv_quarantined_from_comparable_list(self):
        db = self.archive / "catalog" / "research_compare.sqlite"
        _insert_run(db, ticker="AAPL", session_key="2026-07-20", fv_base=None, mos=0.0)
        comparable = self.api.list_runs(limit=50)
        self.assertNotIn("AAPL", {r["ticker"] for r in comparable})
        self.assertEqual(self.api.count_runs(), 4)
        all_rows = self.api.list_runs(comparable_only=False, limit=50)
        self.assertIn("AAPL", {r["ticker"] for r in all_rows})
        self.assertEqual(self.api.count_runs(comparable_only=False), 5)

    def test_calibration_pass_only_defaults_false(self):
        import inspect

        params = inspect.signature(CatalogApi.calibration).parameters
        self.assertFalse(params["pass_only"].default)

    def test_compare_packet_read_and_deny(self):
        packet = (
            self.archive
            / "comparisons"
            / "META"
            / "2026-08-26__2026-08-03_vs_2026-08-10"
        )
        packet.mkdir(parents=True)
        (packet / "job.json").write_text(
            json.dumps(
                {
                    "compare_id": "compare:META:2026-08-26__2026-08-03_vs_2026-08-10",
                    "ticker": "META",
                    "status": "complete",
                    "session_a": "2026-08-03",
                    "session_b": "2026-08-10",
                }
            ),
            encoding="utf-8",
        )
        (packet / "99_synthesis.md").write_text("# Synthesis\n\nOk.\n", encoding="utf-8")
        (packet / "grok.log").write_text("secret-log", encoding="utf-8")
        cid = "compare:META:2026-08-26__2026-08-03_vs_2026-08-10"
        job = self.api.get_compare(cid)
        self.assertEqual(job["ticker"], "META")
        self.assertTrue(job["synthesis_ready"])
        rows = self.api.list_compares(ticker="META")
        self.assertEqual(len(rows), 1)
        data = self.api.open_compare_artifact(cid, "99_synthesis.md")
        self.assertIn(b"Synthesis", data)
        with self.assertRaises(ArtifactDenied):
            self.api.open_compare_artifact(cid, "grok.log")
        with self.assertRaises(ArtifactDenied):
            self.api.open_compare_artifact(cid, "../research/META/2026-08-03/reports/00_META_README.md")
        with self.assertRaises(CompareNotFound):
            self.api.get_compare("compare:META:nope")


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


class InProgressSessionFilesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.session = Path(self._td.name) / "S"
        (self.session / "registry" / "handoffs").mkdir(parents=True)
        (self.session / "meta").mkdir()
        (self.session / "data").mkdir()
        (self.session / "reports").mkdir()
        (self.session / "registry" / "phase_status.json").write_text("{}", encoding="utf-8")
        (self.session / "data" / "valuation_model.json").write_text('{"fv":1}', encoding="utf-8")
        (self.session / "reports" / "00_COHR_README.md").write_text("# hi\n", encoding="utf-8")

    def tearDown(self) -> None:
        self._td.cleanup()

    def test_running_denies_fv_and_report_bodies(self) -> None:
        from packages.catalog_api.client import ArtifactDenied
        from packages.catalog_api.session_files import open_session_artifact

        open_session_artifact(
            self.session, "registry/phase_status.json", snapshot_ready=False
        )
        with self.assertRaises(ArtifactDenied):
            open_session_artifact(
                self.session, "data/valuation_model.json", snapshot_ready=False
            )
        with self.assertRaises(ArtifactDenied):
            open_session_artifact(
                self.session, "reports/00_COHR_README.md", snapshot_ready=False
            )

    def test_complete_allows_report_body(self) -> None:
        from packages.catalog_api.session_files import open_session_artifact

        data = open_session_artifact(
            self.session, "reports/00_COHR_README.md", snapshot_ready=True
        )
        self.assertIn(b"hi", data)


if __name__ == "__main__":
    unittest.main()

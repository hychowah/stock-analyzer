"""Ticker document library: ingest, bind, freshness, harvest, gates."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.annuals import is_annual_form, list_annuals_from_filenames
from packages.kd_research.library import (
    BIND_REL,
    LibraryError,
    bind_to_session,
    check_library_gates,
    check_library_path_citations,
    compare_freshness,
    harvest_session_documents,
    ingest_file,
    ingest_inbox,
    load_manifest,
    required_annual_count,
    session_enforces_library,
    session_is_completed,
)
from packages.kd_research.paths import (
    TICKER_BLOCKLIST,
    ensure_archive_tree,
    iter_research_sessions,
    library_root,
    ticker_library,
)


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, (dict, list)):
        path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    else:
        path.write_text(str(obj), encoding="utf-8")


def _stamp(session: Path, version: str) -> None:
    _write(
        session / "meta" / "run_manifest.json",
        {"harness_version": version, "status": "scaffolded", "ticker": "META"},
    )


def _annual_txt(lib_parent: Path, ticker: str, fy: int, extra: str = "") -> Path:
    name = f"{ticker}_AR_FY{fy}_202{fy % 10}-01-15{extra}.txt"
    p = lib_parent / name
    p.write_text(f"Item 1 Business FY{fy} annual report body.\n", encoding="utf-8")
    return p


class PathsTests(unittest.TestCase):
    def test_library_root_and_not_a_session(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            dirs = ensure_archive_tree(root)
            self.assertTrue(dirs["library"].is_dir())
            self.assertEqual(library_root(root), root / "archive" / "library")
            tlib = ticker_library("meta", root)
            tlib.mkdir(parents=True)
            (tlib / "filings").mkdir()
            rows = iter_research_sessions(root)
            self.assertEqual(rows, [])

    def test_library_reserved(self):
        self.assertIn("library", TICKER_BLOCKLIST)


class AnnualFormTests(unittest.TestCase):
    def test_ar_filename_is_annual(self):
        self.assertTrue(is_annual_form("02618.HK_AR_FY2025_EN.txt"))
        self.assertTrue(is_annual_form("AR"))
        self.assertFalse(is_annual_form("10-Q"))
        self.assertFalse(is_annual_form("RESULTS_FY2025.txt"))

    def test_unique_year_from_filenames(self):
        with tempfile.TemporaryDirectory() as td:
            raw = Path(td) / "data" / "raw_sec"
            raw.mkdir(parents=True)
            (raw / "X_AR_FY2025_EN.txt").write_text("en", encoding="utf-8")
            (raw / "X_AR_FY2025_C.txt").write_text("cn", encoding="utf-8")
            items = list_annuals_from_filenames(raw)
            years = {i["fiscal_year"] for i in items}
            self.assertEqual(years, {2025})


class IngestTests(unittest.TestCase):
    def test_inbox_txt_and_idempotent_hash(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            lib = ticker_library("META", root)
            inbox = lib / "_inbox"
            inbox.mkdir(parents=True)
            src = inbox / "META_10-K_FY2025_2026-01-29.txt"
            src.write_text("Item 1 Business hello\n", encoding="utf-8")
            rows = ingest_inbox("META", output_dir=root)
            self.assertEqual(rows[0]["status"], "ingested")
            self.assertFalse(src.exists())
            man = load_manifest(lib)
            self.assertEqual(len(man["documents"]), 1)
            doc = man["documents"][0]
            self.assertEqual(doc["kind"], "annual")
            self.assertFalse(doc["needs_label"])
            # duplicate
            again = lib / "_inbox" / "copy.txt"
            again.parent.mkdir(exist_ok=True)
            text = (lib / doc["files"]["text"]).read_text(encoding="utf-8")
            again.write_text(text, encoding="utf-8")
            rows2 = ingest_inbox("META", output_dir=root)
            self.assertEqual(rows2[0]["status"], "duplicate")
            self.assertEqual(len(load_manifest(lib)["documents"]), 1)

    def test_refuses_json(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = Path(td) / "valuation_model.json"
            p.write_text("{}", encoding="utf-8")
            with self.assertRaises(LibraryError):
                ingest_file("META", p, output_dir=root)

    def test_unlabeled_garbage_name(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inbox = ticker_library("META", root) / "_inbox"
            inbox.mkdir(parents=True)
            (inbox / "2023030900419_c.txt").write_text("mystery filing\n", encoding="utf-8")
            rows = ingest_inbox("META", output_dir=root)
            self.assertEqual(rows[0]["status"], "ingested")
            doc = rows[0]["document"]
            self.assertTrue(doc["needs_label"])
            self.assertEqual(doc["kind"], "other")


class BindTests(unittest.TestCase):
    def _seed_annuals(self, root: Path, n: int = 10) -> None:
        for fy in range(2016, 2016 + n):
            p = _annual_txt(root, "META", fy)
            ingest_file(
                "META",
                p,
                output_dir=root,
                kind="annual",
                fiscal_period=f"FY{fy}",
                ingested_from="typed_folder",
            )

    def test_required_set_three_not_ten(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_annuals(root, 10)
            session = root / "archive" / "research" / "META" / "2026-08-23"
            (session / "registry").mkdir(parents=True)
            (session / "data" / "raw_sec").mkdir(parents=True)
            _stamp(session, "2.19.0")
            bind = bind_to_session("META", session, output_dir=root)
            annuals = [b for b in bind["bound"] if b.get("kind") == "annual"]
            self.assertEqual(len(annuals), 3)
            on_disk = list((session / "data" / "raw_sec").glob("*.txt"))
            self.assertEqual(len(on_disk), 3)
            self.assertEqual(bind["required_set"]["annuals"], 3)

    def test_deep_five_annuals(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_annuals(root, 10)
            session = root / "archive" / "research" / "META" / "2026-08-23"
            (session / "registry").mkdir(parents=True)
            _write(session / "registry" / "research_brief.json", {"research_depth": "deep"})
            _stamp(session, "2.19.0")
            bind = bind_to_session("META", session, output_dir=root)
            annuals = [b for b in bind["bound"] if b.get("kind") == "annual"]
            self.assertEqual(len(annuals), 5)

    def test_refuses_completed_session(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = _annual_txt(root, "META", 2025)
            ingest_file("META", p, output_dir=root, kind="annual", fiscal_period="FY2025")
            session = root / "archive" / "research" / "META" / "2026-08-03"
            (session / "meta").mkdir(parents=True)
            _write(session / "meta" / "prediction_snapshot.json", {"ticker": "META"})
            with self.assertRaises(LibraryError):
                bind_to_session("META", session, output_dir=root)

    def test_empty_library_bind(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            session = root / "archive" / "research" / "META" / "2026-08-23"
            (session / "registry").mkdir(parents=True)
            _stamp(session, "2.19.0")
            bind = bind_to_session("META", session, output_dir=root)
            self.assertTrue(bind["library_empty"])
            self.assertEqual(bind["bound"], [])


class FreshnessTests(unittest.TestCase):
    def test_ten_indexed_three_session_missing(self):
        index = [
            {
                "kind": "annual",
                "form": "10-K",
                "fiscal_period": f"FY{y}",
                "filing_date": f"{y}-01-30",
            }
            for y in range(2016, 2026)
        ]
        split = compare_freshness(index, bound_docs=[], n_annual=3)
        self.assertEqual(len(split["session_missing"]), 3)
        self.assertEqual(len(split["library_gaps"]), 7)
        periods = {x["fiscal_period"] for x in split["session_missing"]}
        self.assertEqual(periods, {"FY2025", "FY2024", "FY2023"})


class HarvestTests(unittest.TestCase):
    def test_does_not_mutate_session_and_skips_json(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            session = root / "archive" / "research" / "META" / "2026-08-14"
            raw = session / "data" / "raw_sec"
            raw.mkdir(parents=True)
            txt = raw / "META_AR_FY2025.txt"
            txt.write_text("Item 1 Business harvested\n", encoding="utf-8")
            vm = session / "data" / "valuation_model.json"
            _write(vm, {"fv": 1})
            before = txt.read_bytes()
            vm_before = vm.read_bytes()
            rows = harvest_session_documents("META", session, output_dir=root)
            self.assertTrue(any(r.get("status") == "ingested" for r in rows))
            self.assertEqual(txt.read_bytes(), before)
            self.assertEqual(vm.read_bytes(), vm_before)
            man = load_manifest(ticker_library("META", root))
            kinds = {d.get("kind") for d in man["documents"]}
            self.assertIn("annual", kinds)
            self.assertTrue(all(d.get("kind") != "other" or "valuation" not in str(d) for d in man["documents"]))


class GateTests(unittest.TestCase):
    def test_legacy_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.18.1")
            rows = check_library_gates(s)
            self.assertEqual(rows[0][0], "SKIPPED")
            self.assertFalse(session_enforces_library(s))

    def test_219_entry_fails_without_bind(self):
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.19.0")
            self.assertTrue(session_enforces_library(s))
            rows = check_library_gates(s, phase="1_parallel_entry")
            self.assertTrue(any(r[0] == "FAIL" and "library_bind" in r[1] for r in rows), rows)

    def test_219_complete_needs_index_and_freshness(self):
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.19.0")
            _write(
                s / BIND_REL,
                {
                    "schema_version": 1,
                    "ticker": "META",
                    "session_key": "2026-08-23",
                    "bound": [],
                    "library_empty": True,
                    "unlabeled_count": 0,
                },
            )
            rows = check_library_gates(s, phase="1_parallel_complete")
            self.assertTrue(any(r[0] == "FAIL" and "library_index" in r[1] for r in rows), rows)
            _write(
                s / "registry" / "raw" / "filing_index.json",
                {"items": [{"kind": "annual", "fiscal_period": "FY2025"}]},
            )
            rows = check_library_gates(s, phase="1_parallel_complete")
            self.assertTrue(any(r[0] == "FAIL" and "freshness" in r[1] for r in rows), rows)
            _write(
                s / "registry" / "data_fetch_log.json",
                {
                    "freshness": {
                        "checked_at": "2026-08-23T00:00:00Z",
                        "index_source": "filing_index",
                        "session_missing": [],
                        "fetched_new": [],
                    }
                },
            )
            rows = check_library_gates(s, phase="1_parallel_complete")
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertEqual(fails, [], fails)

    def test_fdd_citing_library_fails_full(self):
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _write(
                s / "registry" / "filing_deep_dive.json",
                {"note": "see archive/library/META/filings/x.txt"},
            )
            rows = check_library_path_citations(s, full=True)
            self.assertEqual(rows[0][0], "FAIL")

    def test_session_completed_helper(self):
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            self.assertFalse(session_is_completed(s))
            _stamp(s, "2.19.0")
            self.assertFalse(session_is_completed(s))
            _write(s / "meta" / "prediction_snapshot.json", {})
            self.assertTrue(session_is_completed(s))


class RequiredCountTests(unittest.TestCase):
    def test_intensity_high(self):
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _write(s / "registry" / "market_context.json", {"intensity": "high"})
            self.assertEqual(required_annual_count(s), 5)


if __name__ == "__main__":
    unittest.main()

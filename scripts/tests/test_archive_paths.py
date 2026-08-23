"""Tests for archive path helpers, scaffold default location, dual resolve."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.kd_research.paths import (  # noqa: E402
    allocate_session_key,
    ensure_archive_tree,
    is_production_session_key,
    iter_research_sessions,
    library_root,
    make_session_key,
    parse_session_key,
    resolve_session,
    run_id,
    session_root,
)
from scripts.kd_research.outcomes import (  # noqa: E402
    direction_hit,
    mechanical_scorecard,
    pct_return,
    target_date_for,
)


def _load_scaffold():
    path = ROOT / "scripts" / "scaffold_session.py"
    spec = importlib.util.spec_from_file_location("scaffold_archive_test", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class PathsTests(unittest.TestCase):
    def test_run_id(self):
        self.assertEqual(run_id("meta", "2026-08-03"), "research:META:2026-08-03")
        self.assertEqual(
            run_id("meta", "2026-08-03__model-a"),
            "research:META:2026-08-03__model-a",
        )

    def test_session_key_slug(self):
        self.assertEqual(make_session_key("2026-08-03", "r1"), "2026-08-03__r1")
        self.assertEqual(parse_session_key("2026-08-03__r1"), ("2026-08-03", "r1"))

    def test_is_production_includes_rn(self):
        self.assertTrue(is_production_session_key("2026-08-03"))
        self.assertTrue(is_production_session_key("2026-08-03__r2"))
        self.assertTrue(is_production_session_key("2026-08-03__run03"))
        self.assertFalse(is_production_session_key("2026-08-03__model-a"))

    def test_allocate_plain_then_r2(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            key1 = allocate_session_key("META", "2026-08-10", output_dir=root)
            self.assertEqual(key1, "2026-08-10")
            p1 = session_root("META", key1, root)
            p1.mkdir(parents=True)
            (p1 / "registry").mkdir()
            key2 = allocate_session_key("META", "2026-08-10", output_dir=root)
            self.assertEqual(key2, "2026-08-10__r2")
            p2 = session_root("META", key2, root)
            p2.mkdir(parents=True)
            (p2 / "meta").mkdir()
            key3 = allocate_session_key("META", "2026-08-10", output_dir=root)
            self.assertEqual(key3, "2026-08-10__r3")

    def test_ensure_archive_tree_has_library(self):
        with tempfile.TemporaryDirectory() as td:
            dirs = ensure_archive_tree(td)
            self.assertTrue(dirs["library"].is_dir())
            self.assertEqual(library_root(td), Path(td) / "archive" / "library")

    def test_session_root_default_under_archive(self):
        with tempfile.TemporaryDirectory() as td:
            p = session_root("META", "2026-08-03", td)
            self.assertEqual(p, Path(td) / "archive" / "research" / "META" / "2026-08-03")

    def test_resolve_prefers_archive_over_legacy(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            arch = root / "archive" / "research" / "AAA" / "2026-01-01"
            leg = root / "AAA" / "2026-01-01"
            arch.mkdir(parents=True)
            leg.mkdir(parents=True)
            (arch / "registry").mkdir()
            (leg / "registry").mkdir()
            found = resolve_session("AAA", "2026-01-01", root)
            self.assertEqual(found, arch)

    def test_resolve_falls_back_to_legacy(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            leg = root / "BBB" / "2026-02-02"
            leg.mkdir(parents=True)
            (leg / "reports").mkdir()
            found = resolve_session("BBB", "2026-02-02", root)
            self.assertEqual(found, leg)

    def test_iter_sessions_archive_and_legacy(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = root / "archive" / "research" / "CCC" / "2026-03-03"
            a.mkdir(parents=True)
            (a / "registry").mkdir()
            b = root / "DDD" / "2026-04-04"
            b.mkdir(parents=True)
            (b / "reports").mkdir()
            rows = iter_research_sessions(root, include_legacy=True)
            keys = {(t, d) for t, d, _ in rows}
            self.assertIn(("CCC", "2026-03-03"), keys)
            self.assertIn(("DDD", "2026-04-04"), keys)


class ScaffoldArchiveTests(unittest.TestCase):
    def test_scaffold_writes_under_archive_research(self):
        sc = _load_scaffold()
        with tempfile.TemporaryDirectory() as td:
            root = sc.scaffold(
                "ZZARCH", "2099-06-01", output_dir=td, orchestrator_model="grok-4.5"
            )
            self.assertTrue(str(root).endswith("archive/research/ZZARCH/2099-06-01") or root.as_posix().endswith(
                "archive/research/ZZARCH/2099-06-01"
            ))
            self.assertTrue((root / "meta").is_dir())
            self.assertTrue((root / "registry" / "phase_status.json").is_file())
            self.assertTrue((root / "registry" / "session_isolation.json").is_file())
            data = json.loads((root / "registry" / "phase_status.json").read_text())
            self.assertEqual(data["ticker"], "ZZARCH")
            iso = json.loads((root / "registry" / "session_isolation.json").read_text())
            self.assertEqual(iso["mode"], "isolated")
            self.assertIs(iso["rules"]["prior_valuation_as_input"], False)
            self.assertIs(iso["rules"]["intra_session_share"], True)

    def test_scaffold_same_day_auto_r2(self):
        sc = _load_scaffold()
        with tempfile.TemporaryDirectory() as td:
            r1 = sc.scaffold(
                "ZZDUP", "2099-07-01", output_dir=td, orchestrator_model="grok-4.5"
            )
            self.assertTrue(r1.name == "2099-07-01")
            r2 = sc.scaffold(
                "ZZDUP", "2099-07-01", output_dir=td, orchestrator_model="grok-4.5"
            )
            self.assertEqual(r2.name, "2099-07-01__r2")
            self.assertTrue((r2 / "registry" / "session_isolation.json").is_file())
            man = json.loads((r2 / "meta" / "run_manifest.json").read_text())
            self.assertEqual(man["session_key"], "2099-07-01__r2")
            self.assertEqual(man["session_date"], "2099-07-01")


class OutcomesHelpersTests(unittest.TestCase):
    def test_target_and_returns(self):
        self.assertEqual(str(target_date_for("2026-08-01", "1w")), "2026-08-08")
        self.assertAlmostEqual(pct_return(100, 110), 10.0)

    def test_direction_hit_policy(self):
        self.assertEqual(direction_hit(20, 5), 1)
        self.assertEqual(direction_hit(20, -5), 0)
        self.assertEqual(direction_hit(-20, -5), 1)
        self.assertIsNone(direction_hit(1, 10))  # MoS deadband
        self.assertIsNone(direction_hit(20, 1))  # return deadband

    def test_mechanical_scorecard(self):
        fields = {
            "margin_of_safety_pct": 25.0,
            "fv_bear": 80,
            "fv_base": 100,
            "fv_bull": 130,
            "asof_price": 80,
        }
        price_path = {
            "marks": [
                {
                    "horizon": "1m",
                    "status": "ok",
                    "price": 90,
                    "total_return_pct": 12.5,
                    "excess_return_pct": 2.0,
                }
            ]
        }
        sc = mechanical_scorecard(
            run_id="research:T:2026-01-01",
            ticker="T",
            session_date="2026-01-01",
            session_key="2026-01-01",
            fields=fields,
            price_path=price_path,
            horizon_primary="1m",
        )
        self.assertEqual(sc["metrics"]["direction_vs_price"]["1m"]["value"], "correct")
        self.assertEqual(sc["overall_label"], "mostly_right")


class SnapshotBuilderTests(unittest.TestCase):
    def test_build_minimal_session(self):
        path = ROOT / "scripts" / "build_prediction_snapshot.py"
        spec = importlib.util.spec_from_file_location("snap_test", path)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as td:
            session = Path(td) / "archive" / "research" / "SNAP" / "2026-05-05"
            (session / "data").mkdir(parents=True)
            (session / "registry").mkdir(parents=True)
            (session / "reports").mkdir(parents=True)
            (session / "data" / "valuation_model.json").write_text(
                json.dumps(
                    {
                        "ticker": "SNAP",
                        "model": {"name": "dcf", "rationale": "x" * 25},
                        "fair_value": {
                            "base": 100,
                            "bear": 70,
                            "bull": 130,
                            "margin_of_safety_pct": 10,
                            "currency": "USD",
                        },
                        "assumptions": {},
                        "compute_script": "data/compute/x.py",
                        "sensitivity": {},
                    }
                )
            )
            (session / "registry" / "sector_config.json").write_text(
                json.dumps(
                    {
                        "ticker": "SNAP",
                        "session_date": "2026-05-05",
                        "primary_sector": "standard",
                        "confidence": 0.9,
                        "rationale": "test sector rationale here",
                    }
                )
            )
            (session / "registry" / "audit.json").write_text(json.dumps({"verdict": "PASS", "checks": []}))
            result = mod.build_for_session(session)
            self.assertEqual(result["run_id"], "research:SNAP:2026-05-05")
            snap = json.loads((session / "meta" / "prediction_snapshot.json").read_text())
            self.assertEqual(snap["fair_value"]["base"], 100)
            self.assertEqual(snap["audit_verdict"], "PASS")
            man = json.loads((session / "meta" / "run_manifest.json").read_text())
            self.assertTrue(man["immutable"])


if __name__ == "__main__":
    unittest.main()

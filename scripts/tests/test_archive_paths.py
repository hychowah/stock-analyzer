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
    iter_research_sessions,
    rel_to_project,
    research_root,
    resolve_session,
    run_id,
    session_root,
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
            root = sc.scaffold("ZZARCH", "2099-06-01", output_dir=td)
            self.assertTrue(str(root).endswith("archive/research/ZZARCH/2099-06-01") or root.as_posix().endswith(
                "archive/research/ZZARCH/2099-06-01"
            ))
            self.assertTrue((root / "meta").is_dir())
            self.assertTrue((root / "registry" / "phase_status.json").is_file())
            data = json.loads((root / "registry" / "phase_status.json").read_text())
            self.assertEqual(data["ticker"], "ZZARCH")


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

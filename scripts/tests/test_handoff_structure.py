"""Handoff globs (swarm aliases) and section header checks."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.kd_research.gates import (  # noqa: E402
    check_handoff_headers,
    check_phase_status_disk,
    primary_artifact_exists,
)


def _load_check_session():
    path = ROOT / "scripts" / "check_session.py"
    spec = importlib.util.spec_from_file_location("check_session_handoff_test", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GOOD_HANDOFF = """# What I did

Fetched prices and wrote technical.json.

# Data issues & gaps

None material.

# Assumptions & deviations

Used SPY as regional benchmark.

# For downstream agents & the auditor

1. Levels in registry/technical.json
2. No fundamental reads
3. Compute at data/compute/technical_indicators.py
"""


class HandoffStructureTests(unittest.TestCase):
    def test_headers_detect_missing(self):
        missing = check_handoff_headers("# What I did\n\nonly one section\n")
        self.assertIn("Data issues", missing)
        self.assertIn("For downstream", missing)

    def test_headers_all_present(self):
        self.assertEqual(check_handoff_headers(GOOD_HANDOFF), [])

    def test_phase0_alias_handoff_passes(self):
        cs = _load_check_session()
        cs.results.clear()
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        session = Path(td.name)
        d = session / "registry" / "handoffs"
        d.mkdir(parents=True)
        # only swarm + one specialist — expect FAIL for missing others but PASS phase0
        (d / "phase0_background.md").write_text(GOOD_HANDOFF * 2)
        (d / "phase25_stress.md").write_text(GOOD_HANDOFF * 2)
        for agent in ("2a", "2b", "2c", "2d", "2e", "4", "5", "12", "6", "7", "8", "11", "13"):
            (d / f"{agent}_x.md").write_text(GOOD_HANDOFF * 2)
        cs.check_handoffs(session)
        fails = [r for r in cs.results if r[0] == "FAIL"]
        self.assertEqual(fails, [], msg=fails)
        self.assertTrue(
            any(s == "PASS" and "phase0_swarm" in c for s, c, _ in cs.results)
        )
        self.assertTrue(
            any(s == "PASS" and "phase25_swarm" in c for s, c, _ in cs.results)
        )

    def test_phase_status_complete_missing_artifact_fails(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        session = Path(td.name)
        (session / "registry").mkdir(parents=True)
        data = {
            "phases": [
                {
                    "phase_id": "1c",
                    "status": "complete",
                    "agents": [
                        {
                            "agent_id": "2e",
                            "status": "complete",
                            "artifacts": [],
                            "handoff": None,
                        }
                    ],
                }
            ]
        }
        out = check_phase_status_disk(session, data)
        self.assertTrue(any(s == "FAIL" and "artifact" in c for s, c, _ in out), msg=out)

    def test_phase_status_lag_warns(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        session = Path(td.name)
        (session / "registry").mkdir(parents=True)
        (session / "registry" / "technical.json").write_text("{}")
        data = {
            "phases": [
                {
                    "phase_id": "2_parallel",
                    "status": "in_progress",
                    "agents": [
                        {
                            "agent_id": "4",
                            "status": "pending",
                            "artifacts": [],
                            "handoff": None,
                        }
                    ],
                }
            ]
        }
        out = check_phase_status_disk(session, data)
        self.assertTrue(any(s == "WARN" and c == "phase_status lag" for s, c, _ in out), msg=out)

    def test_primary_artifact_valuation(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        session = Path(td.name)
        (session / "data").mkdir(parents=True)
        self.assertFalse(primary_artifact_exists(session, "5"))
        (session / "data" / "valuation_model.json").write_text("{}")
        self.assertTrue(primary_artifact_exists(session, "5"))


if __name__ == "__main__":
    unittest.main()

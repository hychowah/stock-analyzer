"""Unit tests for Agent 4 fundamental-path isolation heuristic."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.kd_research.gates import check_agent4_isolation  # noqa: E402


class Agent4IsolationTests(unittest.TestCase):
    def _session(self, technical: dict | None, handoff: str | None) -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        session = Path(td.name) / "TEST" / "2026-08-10"
        (session / "registry" / "handoffs").mkdir(parents=True)
        if technical is not None:
            (session / "registry" / "technical.json").write_text(json.dumps(technical))
        if handoff is not None:
            (session / "registry" / "handoffs" / "4_technical.md").write_text(handoff)
        return session

    def test_clean_technical_passes(self):
        session = self._session(
            {"ticker": "TEST", "indicators": {"rsi": 50}, "levels": {}, "compute_script": "x"},
            "# What I did\n\nPrice/volume only via yfinance.\n",
        )
        out = check_agent4_isolation(session, full=True)
        self.assertEqual(out[0][0], "PASS")

    def test_valuation_path_in_handoff_fails_full(self):
        session = self._session(
            {"ticker": "TEST"},
            "I did not read data/valuation_model.json honestly I did.\n",
        )
        out = check_agent4_isolation(session, full=True)
        self.assertEqual(out[0][0], "FAIL")
        self.assertIn("valuation_model", out[0][2])

    def test_contamination_warns_without_full(self):
        session = self._session(
            {"note": "see registry/filing_deep_dive for earnings"},
            None,
        )
        out = check_agent4_isolation(session, full=False)
        self.assertEqual(out[0][0], "WARN")

    def test_street_estimates_path_fails_full(self):
        session = self._session(
            {"ticker": "TEST"},
            "I peeked at registry/street_estimates.json for FY+1 revenue.\n",
        )
        out = check_agent4_isolation(session, full=True)
        self.assertEqual(out[0][0], "FAIL")
        self.assertIn("street_estimates", out[0][2])

    def test_skipped_when_no_files(self):
        session = self._session(None, None)
        out = check_agent4_isolation(session, full=True)
        self.assertEqual(out[0][0], "SKIPPED")


if __name__ == "__main__":
    unittest.main()

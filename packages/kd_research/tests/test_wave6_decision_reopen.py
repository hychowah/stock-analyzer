"""Wave 6 decision reopen after 2.5 (harness >= 2.14.0)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.paths import PROJECT_ROOT as ROOT

from packages.kd_research.decision import (
    check_decision_packet,
    check_wave6_reopen,
)
from packages.kd_research.annuals import parse_semver
from packages.kd_research.gates import complete_checks


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj) if not isinstance(obj, str) else obj, encoding="utf-8")


class ReopenTests(unittest.TestCase):
    def _sess(self, version: str = "2.14.0") -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        _write(
            s / "meta/run_manifest.json",
            {"status": "scaffolded", "orchestrator_model": "grok-4.5", "harness_version": version},
        )
        _write(
            s / "data/valuation_model.json",
            {
                "ticker": "X",
                "model": {"name": "dcf"},
                "fair_value": {
                    "base": 100.0,
                    "bear": 80.0,
                    "bull": 120.0,
                    "decision_usefulness": "high",
                },
                "assumptions": {},
                "compute_script": "x",
                "sensitivity": {},
            },
        )
        _write(
            s / "registry/decision.json",
            {
                "ticker": "X",
                "duration": {
                    "action": "initiate",
                    "rationale": "Provisional duration from the Phase 2 DCF.",
                },
                "reopened_after_stress": False,
                "tsr_seen": False,
            },
        )
        return s

    def test_version_at_least_214(self) -> None:
        payload = json.loads((ROOT / "harness" / "VERSION").read_text(encoding="utf-8"))
        parsed = parse_semver(payload.get("harness_version"))
        self.assertGreaterEqual(parsed, (2, 14, 0))

    def test_prompt_has_5b_and_forbids_spawn_in_25(self) -> None:
        text = (ROOT / "harness" / "agent_prompts.md").read_text(encoding="utf-8")
        self.assertIn("5b — decision reopen", text)
        self.assertIn("do **not** spawn subagent 5 inside phase `2_5`", text)
        self.assertIn("reopened_after_stress: false", text)

    def test_213_skips_wave6(self) -> None:
        s = self._sess("2.13.0")
        _write(s / "registry/risk_bridge.json", {"ticker": "X", "risks": []})
        rows = check_wave6_reopen(s)
        self.assertEqual(rows[0][0], "SKIPPED", rows)

    def test_no_risk_bridge_skips_even_at_214(self) -> None:
        s = self._sess("2.14.0")
        rows = check_wave6_reopen(s)
        self.assertEqual(rows[0][0], "SKIPPED", rows)
        packet = check_decision_packet(s)
        self.assertEqual(packet[0][0], "PASS", packet)

    def test_risk_bridge_without_reopen_fails(self) -> None:
        s = self._sess("2.14.0")
        _write(s / "registry/risk_bridge.json", {"ticker": "X", "risks": []})
        rows = check_wave6_reopen(s)
        self.assertEqual(rows[0][0], "FAIL", rows)

    def test_reopen_without_tsr_file_ok(self) -> None:
        s = self._sess("2.14.0")
        _write(s / "registry/risk_bridge.json", {"ticker": "X", "risks": []})
        _write(
            s / "registry/decision.json",
            {
                "ticker": "X",
                "duration": {"action": "pass", "rationale": "Stress made the cone not a buy."},
                "reopened_after_stress": True,
                "tsr_seen": False,
            },
        )
        rows = check_wave6_reopen(s)
        self.assertEqual(rows[0][0], "PASS", rows)

    def test_tsr_file_requires_tsr_seen(self) -> None:
        s = self._sess("2.14.0")
        _write(s / "registry/risk_bridge.json", {"ticker": "X", "risks": []})
        _write(s / "registry/tsr_validation.json", {"ticker": "X", "tsr": {}, "compute_script": "x"})
        _write(
            s / "registry/decision.json",
            {
                "ticker": "X",
                "duration": {"action": "initiate", "rationale": "Reopened but ignored TSR file."},
                "reopened_after_stress": True,
                "tsr_seen": False,
            },
        )
        rows = check_wave6_reopen(s)
        self.assertEqual(rows[0][0], "FAIL", rows)
        self.assertEqual(rows[0][1], "decision_reopen.tsr")

    def test_reopen_and_tsr_seen_pass(self) -> None:
        s = self._sess("2.14.0")
        _write(s / "registry/risk_bridge.json", {"ticker": "X", "risks": []})
        _write(s / "registry/tsr_validation.json", {"ticker": "X", "tsr": {}, "compute_script": "x"})
        _write(
            s / "registry/decision.json",
            {
                "ticker": "X",
                "duration": {"action": "initiate", "rationale": "Reopened after stress and TSR."},
                "reopened_after_stress": True,
                "tsr_seen": True,
            },
        )
        rows = check_wave6_reopen(s)
        self.assertEqual(rows[0][0], "PASS", rows)

    def test_2_parallel_complete_does_not_require_reopen(self) -> None:
        s = self._sess("2.14.0")
        rows = complete_checks(s, "2_parallel")
        reopen = [r for r in rows if r[1].startswith("decision_reopen")]
        self.assertEqual(reopen, [], rows)

    def test_4_parallel_complete_requires_reopen(self) -> None:
        s = self._sess("2.14.0")
        _write(s / "registry/risk_bridge.json", {"ticker": "X", "risks": []})
        rows = complete_checks(s, "4_parallel")
        self.assertTrue(any(r[0] == "FAIL" and r[1] == "decision_reopen" for r in rows), rows)


if __name__ == "__main__":
    unittest.main()

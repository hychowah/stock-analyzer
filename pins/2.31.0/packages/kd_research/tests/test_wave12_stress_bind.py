"""Harness 2.29.0: material stress binds duration (no DCF rewrite, no override hatch)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.decision import check_stress_bind
from packages.kd_research.gates import complete_checks


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj) if not isinstance(obj, str) else obj, encoding="utf-8")


def _sess(version: str = "2.29.0") -> Path:
    td = tempfile.TemporaryDirectory()
    # Caller must keep td alive — use unittest addCleanup in tests instead.
    s = Path(td.name)
    s._td = td  # type: ignore[attr-defined]
    _write(
        s / "meta/run_manifest.json",
        {"status": "scaffolded", "orchestrator_model": "grok-4.5", "harness_version": version},
    )
    _write(
        s / "data/valuation_model.json",
        {
            "ticker": "X",
            "model": {"name": "dcf"},
            "fair_value": {"base": 100.0, "bear": 80.0, "bull": 120.0, "decision_usefulness": "high"},
            "assumptions": {},
            "compute_script": "x",
            "sensitivity": {},
        },
    )
    return s


def _rb(*scenarios: dict) -> dict:
    return {
        "ticker": "X",
        "risks": [
            {
                "risk": "demand shock",
                "probability": 0.2,
                "rationale": "Named analog year in FDD.",
                "valuation_adjustment": {"direction": "lower_growth"},
                "monitoring_trigger": "Q3 AI revenue vs EX-99.1",
            }
        ],
        "scenario_probabilities": {"bear": 0.3, "base": 0.5, "bull": 0.2},
        "stress_test": {"scenarios": list(scenarios)},
    }


MATERIAL = {
    "name": "channel destock",
    "type": "sector",
    "probability": 0.25,
    "rationale": "FY2022 analog matched this print.",
    "fair_value_haircut_pct": 0.40,
    "narrative": "WC release fades; Street duration overstates Y1.",
}

LIGHT = {
    "name": "mild FX",
    "type": "macro",
    "probability": 0.40,
    "rationale": "Translation only.",
    "fair_value_haircut_pct": 0.10,
    "narrative": "Not a book binder.",
}


class StressBindTests(unittest.TestCase):
    def _s(self, version: str = "2.29.0") -> Path:
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
        return s

    def test_228_skips(self) -> None:
        s = self._s("2.28.0")
        _write(s / "registry/risk_bridge.json", _rb(MATERIAL))
        rows = check_stress_bind(s)
        self.assertEqual(rows[0][0], "SKIPPED", rows)

    def test_material_initiate_fails(self) -> None:
        s = self._s()
        _write(s / "registry/risk_bridge.json", _rb(MATERIAL, LIGHT))
        _write(
            s / "registry/decision.json",
            {
                "ticker": "X",
                "duration": {"action": "initiate", "rationale": "Still a buy after stress theater."},
                "reopened_after_stress": True,
                "stress_bind": {
                    "material": True,
                    "binding_scenario": "channel destock",
                    "haircut_pct": 0.40,
                    "probability": 0.25,
                },
            },
        )
        rows = check_stress_bind(s)
        self.assertTrue(any(r[0] == "FAIL" and r[1] == "stress_bind.initiate" for r in rows), rows)

    def test_material_pass_ok(self) -> None:
        s = self._s()
        _write(s / "registry/risk_bridge.json", _rb(MATERIAL))
        _write(
            s / "registry/decision.json",
            {
                "ticker": "X",
                "duration": {"action": "pass", "rationale": "Material destock haircut binds the book."},
                "reopened_after_stress": True,
                "stress_bind": {
                    "material": True,
                    "binding_scenario": "channel destock",
                    "haircut_pct": 0.40,
                    "probability": 0.25,
                },
            },
        )
        rows = check_stress_bind(s)
        self.assertEqual(rows[0][0], "PASS", rows)

    def test_light_stress_initiate_ok(self) -> None:
        s = self._s()
        _write(s / "registry/risk_bridge.json", _rb(LIGHT))
        _write(
            s / "registry/decision.json",
            {
                "ticker": "X",
                "duration": {"action": "initiate", "rationale": "Haircut is not material."},
                "reopened_after_stress": True,
                "stress_bind": {"material": False},
            },
        )
        rows = check_stress_bind(s)
        self.assertEqual(rows[0][0], "PASS", rows)

    def test_missing_stress_bind_fails(self) -> None:
        s = self._s()
        _write(s / "registry/risk_bridge.json", _rb(LIGHT))
        _write(
            s / "registry/decision.json",
            {
                "ticker": "X",
                "duration": {"action": "pass", "rationale": "Reopened after stress without bind object."},
                "reopened_after_stress": True,
            },
        )
        rows = check_stress_bind(s)
        self.assertEqual(rows[0][0], "FAIL", rows)

    def test_narrative_only_material_fails(self) -> None:
        s = self._s()
        sc = dict(MATERIAL)
        sc["valuation_adjustment"] = {"direction": "narrative_only"}
        _write(s / "registry/risk_bridge.json", _rb(sc))
        _write(
            s / "registry/decision.json",
            {
                "ticker": "X",
                "duration": {"action": "pass", "rationale": "Tried to hide a 40 percent haircut."},
                "reopened_after_stress": True,
                "stress_bind": {"material": True, "binding_scenario": "channel destock"},
            },
        )
        rows = check_stress_bind(s)
        self.assertTrue(any(r[0] == "FAIL" and r[1] == "stress_bind.narrative_only" for r in rows), rows)

    def test_4_parallel_complete_runs_bind(self) -> None:
        s = self._s()
        _write(s / "registry/risk_bridge.json", _rb(MATERIAL))
        _write(
            s / "registry/decision.json",
            {
                "ticker": "X",
                "duration": {"action": "initiate", "rationale": "Should fail complete gate."},
                "reopened_after_stress": True,
                "stress_bind": {"material": True, "binding_scenario": "channel destock"},
            },
        )
        rows = complete_checks(s, "4_parallel")
        self.assertTrue(any(r[0] == "FAIL" and r[1] == "stress_bind.initiate" for r in rows), rows)


if __name__ == "__main__":
    unittest.main()

"""Wave 2 decision object + pass technical (harness >= 2.10.0)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.kd_research.decision import (  # noqa: E402
    check_decision_packet,
    check_duration_vs_ta_long,
    check_technical_pass_allowed,
    check_wave2_decision,
    extract_decision_action,
    extract_kill_triggers,
    session_is_wave2_runtime,
)
from scripts.kd_research.session_extract import extract_session_bundle  # noqa: E402


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, str):
        path.write_text(obj, encoding="utf-8")
    else:
        path.write_text(json.dumps(obj), encoding="utf-8")


def _stamp(session: Path, version: str | None) -> None:
    man: dict = {"status": "scaffolded", "orchestrator_model": "grok-4.5"}
    if version:
        man["harness_version"] = version
    _write(session / "meta" / "run_manifest.json", man)


def _vm(**fv) -> dict:
    fair = {
        "base": 100.0,
        "bear": 80.0,
        "bull": 120.0,
        "decision_usefulness": "high",
    }
    fair.update(fv)
    return {
        "ticker": "X",
        "model": {"name": "fcff_dcf", "rationale": "dcf"},
        "fair_value": fair,
        "assumptions": {},
        "compute_script": "data/compute/valuation.py",
        "sensitivity": {},
    }


class VersionFloorTests(unittest.TestCase):
    def test_29_skips_wave2(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.9.0")
            _write(s / "data/valuation_model.json", _vm())
            self.assertFalse(session_is_wave2_runtime(s))
            rows = check_wave2_decision(s)
            self.assertEqual(rows[0][0], "SKIPPED")

    def test_210_missing_decision_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.10.0")
            _write(s / "data/valuation_model.json", _vm())
            self.assertTrue(session_is_wave2_runtime(s))
            rows = check_decision_packet(s)
            self.assertEqual(rows[0][0], "FAIL")


class InitiateGateTests(unittest.TestCase):
    def test_initiate_on_low_du_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.10.0")
            _write(s / "data/valuation_model.json", _vm(decision_usefulness="low"))
            _write(
                s / "registry/decision.json",
                {
                    "ticker": "X",
                    "duration": {
                        "action": "initiate",
                        "rationale": "Looks cheap on base FV despite a useless cone.",
                    },
                },
            )
            rows = check_decision_packet(s)
            self.assertEqual(rows[0][0], "FAIL", rows)

    def test_pass_on_low_du_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.10.0")
            _write(s / "data/valuation_model.json", _vm(decision_usefulness="low", bear=0.0, bull=250.0))
            _write(
                s / "registry/decision.json",
                {
                    "ticker": "X",
                    "duration": {
                        "action": "pass",
                        "rationale": "Cone is decision-limiting; do not initiate a core long.",
                    },
                },
            )
            rows = check_decision_packet(s)
            self.assertEqual(rows[0][0], "PASS", rows)

    def test_initiate_on_wide_span_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.10.0")
            _write(s / "data/valuation_model.json", _vm(base=50.0, bear=0.0, bull=200.0))
            _write(
                s / "registry/decision.json",
                {
                    "ticker": "X",
                    "duration": {
                        "action": "initiate",
                        "rationale": "Buying the residual despite bear at zero.",
                    },
                },
            )
            rows = check_decision_packet(s)
            self.assertEqual(rows[0][0], "FAIL", rows)


class TechnicalPassTests(unittest.TestCase):
    def test_side_pass_without_entry_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.10.0")
            _write(
                s / "registry/technical.json",
                {
                    "ticker": "X",
                    "indicators": {"atr": 1.0},
                    "levels": {},
                    "side": "pass",
                    "compute_script": "data/compute/technical_indicators.py",
                },
            )
            rows = check_technical_pass_allowed(s)
            self.assertEqual(rows[0][0], "PASS", rows)

    def test_long_without_stop_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.10.0")
            _write(
                s / "registry/technical.json",
                {
                    "ticker": "X",
                    "indicators": {},
                    "side": "long",
                    "levels": {"entry": {"value": 10, "rationale": "poc"}},
                    "compute_script": "data/compute/technical_indicators.py",
                },
            )
            rows = check_technical_pass_allowed(s)
            self.assertEqual(rows[0][0], "FAIL", rows)

    def test_missing_side_without_entry_fails_on_210(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.10.0")
            _write(
                s / "registry/technical.json",
                {
                    "ticker": "X",
                    "indicators": {},
                    "levels": {},
                    "compute_script": "data/compute/t.py",
                },
            )
            rows = check_technical_pass_allowed(s)
            self.assertEqual(rows[0][0], "FAIL", rows)

    def test_legacy_shaped_technical_schema_ok(self) -> None:
        import jsonschema

        schema = json.loads(
            (ROOT / "templates" / "technical.schema.json").read_text(encoding="utf-8")
        )
        doc = {
            "ticker": "X",
            "indicators": {"atr": 1.0},
            "levels": {
                "entry": {"value": 10, "rationale": "poc"},
                "stop_loss": {"value": 9, "rationale": "atr"},
                "targets": [{"value": 12}],
            },
            "compute_script": "data/compute/technical_indicators.py",
        }
        jsonschema.validate(doc, schema)

    def test_duration_pass_with_ta_long_is_legal(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.10.0")
            _write(s / "data/valuation_model.json", _vm())
            _write(
                s / "registry/decision.json",
                {
                    "ticker": "X",
                    "duration": {
                        "action": "pass",
                        "rationale": "Priced for perfection; duration book is pass.",
                    },
                },
            )
            _write(
                s / "registry/technical.json",
                {
                    "ticker": "X",
                    "side": "long",
                    "indicators": {},
                    "levels": {
                        "entry": {"value": 360, "rationale": "pullback"},
                        "stop_loss": {"value": 344, "rationale": "atr"},
                    },
                    "compute_script": "data/compute/technical_indicators.py",
                },
            )
            rows = check_duration_vs_ta_long(s)
            self.assertEqual(rows[0][0], "PASS", rows)


class CatalogProjectionTests(unittest.TestCase):
    def test_kill_triggers_and_action(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "archive" / "research" / "DEC" / "2026-05-05"
            _stamp(root, "2.10.0")
            _write(root / "data/valuation_model.json", _vm())
            _write(root / "registry/sector_config.json", {"primary_sector": "standard"})
            _write(
                root / "registry/decision.json",
                {
                    "ticker": "DEC",
                    "duration": {
                        "action": "pass",
                        "rationale": "PFP true and bull FV still below tape.",
                    },
                },
            )
            _write(
                root / "registry/risk_bridge.json",
                {
                    "ticker": "DEC",
                    "risks": [
                        {
                            "risk": "AI miss",
                            "probability": 0.2,
                            "rationale": "guide is tight",
                            "valuation_adjustment": {"direction": "lower_growth"},
                            "monitoring_trigger": "Q3 AI < $16.0B on EX-99.1",
                        }
                    ],
                    "scenario_probabilities": {"bear": 0.3, "base": 0.5, "bull": 0.2},
                    "stress_test": {"scenarios": []},
                },
            )
            self.assertEqual(extract_decision_action(root), "pass")
            self.assertEqual(extract_kill_triggers(root), ["Q3 AI < $16.0B on EX-99.1"])
            bundle = extract_session_bundle(root)
            self.assertEqual(bundle["decision_action"], "pass")
            self.assertEqual(bundle["kill_triggers"], ["Q3 AI < $16.0B on EX-99.1"])


if __name__ == "__main__":
    unittest.main()

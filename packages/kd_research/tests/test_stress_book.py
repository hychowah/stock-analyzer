"""Harness 2.44.0: shocked-path bind, size_cap, report card."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.decision import (
    UnappliedStressError,
    check_stress_bind,
    check_stress_report_card,
    compute_stress_bind,
    format_stress_card,
    size_cap_for_el,
)
from packages.kd_research.gates import complete_checks
from packages.kd_research.stress_apply import (
    apply_one,
    apply_session,
    check_shock_surface,
    check_stress_applied,
    compute_reverse_stress,
    haircut_from_values,
    parse_under_stdout,
    restates_bear_numeric,
    run_fair_value_under,
)


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj) if not isinstance(obj, str) else obj, encoding="utf-8")


SCRIPT = (
    "import json,sys\n"
    "DIALS={'ke':0.08,'om':0.20}\n"
    "ov=json.loads(sys.argv[sys.argv.index('--under')+1]) if '--under' in sys.argv else {}\n"
    "ke=float(ov.get('ke', DIALS['ke']))\n"
    "om=float(ov.get('om', DIALS['om']))\n"
    "fv=500.0*om*(0.08/ke)\n"
    "print(json.dumps({'fair_value': fv}))\n"
)


def _vm(**extra):
    body = {
        "ticker": "X",
        "model": {"name": "dcf", "rationale": "ordinary DCF for this test fixture."},
        "fair_value": {"base": 100.0, "bear": 80.0, "bull": 120.0},
        "assumptions": {},
        "compute_script": "data/compute/valuation.py",
        "sensitivity": {},
        "shock_surface": {
            "dials": {
                "ke": {"value": 0.08, "lo": 0.05, "hi": 0.16},
                "om": {"value": 0.20, "lo": 0.08, "hi": 0.30},
            }
        },
    }
    body.update(extra)
    return body


def _rb(*scenarios: dict) -> dict:
    return {
        "ticker": "X",
        "risks": [
            {
                "risk": "demand shock",
                "probability": 0.2,
                "rationale": "Named analog year in FDD.",
                "valuation_adjustment": {"direction": "lower_growth"},
                "monitoring_trigger": "Q3 print vs EX-99.1",
            }
        ],
        "scenario_probabilities": {"bear": 0.3, "base": 0.5, "bull": 0.2},
        "stress_test": {
            "scenarios": list(scenarios),
            "reverse_stress": {
                "none": True,
                "reason": "fixture",
                "compute": "fair_value_under",
            },
        },
    }


INDEPENDENT = {
    "name": "channel destock",
    "type": "sector",
    "probability": 0.25,
    "rationale": "FY2022 analog matched this print.",
    "shock": {"om": 0.12},
    "applied": {
        "stressed_fv": 60.0,
        "fair_value_haircut_pct": 0.40,
        "restates_bear": False,
    },
    "narrative": "WC release fades.",
}

NEAR_BEAR = {
    "name": "cycle trough",
    "type": "sector",
    "probability": 0.28,
    "rationale": "Maps to DCF bear.",
    "shock": {"om": 0.16134},
    "applied": {
        "stressed_fv": 80.67,
        "fair_value_haircut_pct": 0.1933,
        "restates_bear": True,
    },
    "narrative": "Same movie as bear.",
}

LIGHT = {
    "name": "mild FX",
    "type": "macro",
    "probability": 0.10,
    "rationale": "Translation only.",
    "shock": {"ke": 0.0816},
    "applied": {
        "stressed_fv": 98.0,
        "fair_value_haircut_pct": 0.02,
        "restates_bear": False,
    },
    "narrative": "Not a book binder.",
}


class SizeCapScheduleTests(unittest.TestCase):
    def test_thresholds(self) -> None:
        self.assertEqual(size_cap_for_el(0.0), 1.0)
        self.assertEqual(size_cap_for_el(0.039), 1.0)
        self.assertEqual(size_cap_for_el(0.04), 0.5)
        self.assertEqual(size_cap_for_el(0.079), 0.5)
        self.assertEqual(size_cap_for_el(0.08), 0.25)
        self.assertEqual(size_cap_for_el(0.12), 0.0)
        self.assertEqual(size_cap_for_el(0.148), 0.0)


class ComputeBindTests(unittest.TestCase):
    def test_independent_high_el_zeros_cap(self) -> None:
        want = compute_stress_bind(_rb(INDEPENDENT, LIGHT), _vm())
        self.assertEqual(want["binding_scenario"], "channel destock")
        self.assertAlmostEqual(want["expected_loss_pct"], 0.10, places=4)
        self.assertEqual(want["size_cap"], 0.25)
        self.assertTrue(want["material"])

    def test_acgl_like_el_floor(self) -> None:
        sc = dict(INDEPENDENT)
        sc["probability"] = 0.32
        sc["applied"] = {
            "stressed_fv": 53.6,
            "fair_value_haircut_pct": 0.464,
            "restates_bear": False,
        }
        want = compute_stress_bind(_rb(sc), _vm())
        self.assertEqual(want["size_cap"], 0.0)
        self.assertTrue(want["material"])

    def test_restates_bear_cannot_bind(self) -> None:
        want = compute_stress_bind(_rb(NEAR_BEAR, LIGHT), _vm())
        self.assertEqual(want["binding_scenario"], "mild FX")
        self.assertAlmostEqual(want["expected_loss_pct"], 0.002, places=4)
        self.assertEqual(want["size_cap"], 1.0)
        self.assertFalse(want["material"])

    def test_worker_flag_cannot_hide_independent(self) -> None:
        sc = dict(INDEPENDENT)
        sc["restates_bear"] = True
        want = compute_stress_bind(_rb(sc), _vm())
        self.assertEqual(want["binding_scenario"], "channel destock")
        self.assertEqual(want["size_cap"], 0.25)

    def test_missing_fv_does_not_use_haircut(self) -> None:
        sc = {
            "name": "guessed",
            "probability": 0.40,
            "shock": {"om": 0.10},
            "fair_value_haircut_pct": 0.50,
            "narrative": "No applied FV.",
        }
        with self.assertRaises(UnappliedStressError):
            compute_stress_bind(_rb(sc), _vm())

    def test_liquidity_fail_zeros_cap(self) -> None:
        sc = dict(LIGHT)
        sc["liquidity_path"] = {"applies": True, "survival_12m": False}
        want = compute_stress_bind(_rb(sc), _vm())
        self.assertEqual(want["size_cap"], 0.0)
        self.assertTrue(want["material"])

    def test_liquidity_on_restates_bear_zeros_cap(self) -> None:
        sc = dict(NEAR_BEAR)
        sc["liquidity_path"] = {"applies": True, "survival_12m": False}
        want = compute_stress_bind(_rb(sc, LIGHT), _vm())
        self.assertEqual(want["size_cap"], 0.0)
        self.assertTrue(want["material"])
        self.assertEqual(want["binding_scenario"], "mild FX")

    def test_max_el_not_sum(self) -> None:
        a = dict(INDEPENDENT)
        a["name"] = "ad budget"
        a["probability"] = 0.20
        a["applied"] = {
            "stressed_fv": 70.0,
            "fair_value_haircut_pct": 0.30,
            "restates_bear": False,
        }
        b = dict(INDEPENDENT)
        b["name"] = "legal"
        b["probability"] = 0.20
        b["applied"] = {
            "stressed_fv": 85.0,
            "fair_value_haircut_pct": 0.15,
            "restates_bear": False,
        }
        want = compute_stress_bind(_rb(a, b), _vm())
        self.assertEqual(want["binding_scenario"], "ad budget")
        self.assertAlmostEqual(want["expected_loss_pct"], 0.06, places=4)
        self.assertNotAlmostEqual(want["expected_loss_pct"], 0.09, places=4)


class BookBindGateTests(unittest.TestCase):
    def _s(self, version: str = "2.44.0") -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        _write(
            s / "meta/run_manifest.json",
            {"status": "scaffolded", "orchestrator_model": "grok-4.5", "harness_version": version},
        )
        _write(s / "data/valuation_model.json", _vm())
        return s

    def _bind(self, rb, vm, action: str) -> dict:
        want = compute_stress_bind(rb, vm)
        return {
            "ticker": "X",
            "duration": {"action": action, "rationale": "Book bind after shocked-path apply."},
            "reopened_after_stress": True,
            "stress_bind": want,
        }

    def test_zero_cap_initiate_fails(self) -> None:
        s = self._s()
        sc = dict(INDEPENDENT)
        sc["probability"] = 0.32
        sc["applied"] = {
            "stressed_fv": 53.6,
            "fair_value_haircut_pct": 0.464,
            "restates_bear": False,
        }
        rb = _rb(sc)
        _write(s / "registry/risk_bridge.json", rb)
        _write(s / "registry/decision.json", self._bind(rb, _vm(), "initiate"))
        rows = check_stress_bind(s)
        self.assertTrue(any(r[0] == "FAIL" and "size_cap" in r[1] for r in rows), rows)

    def test_zero_cap_pass_ok(self) -> None:
        s = self._s()
        sc = dict(INDEPENDENT)
        sc["probability"] = 0.32
        sc["applied"] = {
            "stressed_fv": 53.6,
            "fair_value_haircut_pct": 0.464,
            "restates_bear": False,
        }
        rb = _rb(sc)
        _write(s / "registry/risk_bridge.json", rb)
        _write(s / "registry/decision.json", self._bind(rb, _vm(), "pass"))
        rows = check_stress_bind(s)
        self.assertEqual(rows[0][0], "PASS", rows)

    def test_half_cap_initiate_ok(self) -> None:
        s = self._s()
        sc = dict(INDEPENDENT)
        sc["probability"] = 0.20
        sc["applied"] = {
            "stressed_fv": 75.0,
            "fair_value_haircut_pct": 0.25,
            "restates_bear": False,
        }
        rb = _rb(sc, LIGHT)
        _write(s / "registry/risk_bridge.json", rb)
        _write(s / "registry/decision.json", self._bind(rb, _vm(), "initiate"))
        rows = check_stress_bind(s)
        self.assertEqual(rows[0][0], "PASS", rows)
        self.assertAlmostEqual(compute_stress_bind(rb, _vm())["size_cap"], 0.5)

    def test_restates_bear_initiate_ok(self) -> None:
        s = self._s()
        rb = _rb(NEAR_BEAR, LIGHT)
        _write(s / "registry/risk_bridge.json", rb)
        _write(s / "registry/decision.json", self._bind(rb, _vm(), "initiate"))
        rows = check_stress_bind(s)
        self.assertEqual(rows[0][0], "PASS", rows)

    def test_243_still_uses_cliff(self) -> None:
        s = self._s("2.43.0")
        sc = dict(INDEPENDENT)
        sc["fair_value_haircut_pct"] = 0.40
        rb = _rb(sc)
        _write(s / "registry/risk_bridge.json", rb)
        _write(
            s / "registry/decision.json",
            {
                "ticker": "X",
                "duration": {"action": "initiate", "rationale": "Old cliff still applies."},
                "reopened_after_stress": True,
                "stress_bind": {"material": True, "binding_scenario": "channel destock"},
            },
        )
        rows = check_stress_bind(s)
        self.assertTrue(any(r[0] == "FAIL" and r[1] == "stress_bind.initiate" for r in rows), rows)

    def test_4_parallel_complete_runs_book(self) -> None:
        s = self._s()
        sc = dict(INDEPENDENT)
        sc["probability"] = 0.32
        sc["applied"] = {
            "stressed_fv": 53.6,
            "fair_value_haircut_pct": 0.464,
            "restates_bear": False,
        }
        rb = _rb(sc)
        _write(s / "registry/risk_bridge.json", rb)
        _write(s / "registry/decision.json", self._bind(rb, _vm(), "hold"))
        rows = complete_checks(s, "4_parallel")
        self.assertTrue(any(r[0] == "FAIL" and "size_cap" in r[1] for r in rows), rows)


class ShockSurfaceTests(unittest.TestCase):
    def test_dials_required_on_244(self) -> None:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        _write(
            s / "meta/run_manifest.json",
            {"harness_version": "2.44.0", "orchestrator_model": "grok-4.5"},
        )
        vm = _vm()
        del vm["shock_surface"]
        _write(s / "data/valuation_model.json", vm)
        rows = check_shock_surface(s)
        self.assertEqual(rows[0][0], "FAIL", rows)

    def test_keys_only_fails(self) -> None:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        _write(
            s / "meta/run_manifest.json",
            {"harness_version": "2.44.0", "orchestrator_model": "grok-4.5"},
        )
        vm = _vm()
        vm["shock_surface"] = {"keys": ["ke", "om"]}
        _write(s / "data/valuation_model.json", vm)
        rows = check_shock_surface(s)
        self.assertEqual(rows[0][0], "FAIL", rows)
        self.assertIn("dials", rows[0][2])

    def test_under_empty_matches_base(self) -> None:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        _write(
            s / "meta/run_manifest.json",
            {"harness_version": "2.44.0", "orchestrator_model": "grok-4.5"},
        )
        _write(s / "data/valuation_model.json", _vm())
        script = s / "data" / "compute" / "valuation.py"
        script.parent.mkdir(parents=True)
        script.write_text(SCRIPT, encoding="utf-8")
        rows = check_shock_surface(s)
        self.assertEqual(rows[0][0], "PASS", rows)

    def test_legacy_skips(self) -> None:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        _write(
            s / "meta/run_manifest.json",
            {"harness_version": "2.43.0", "orchestrator_model": "grok-4.5"},
        )
        _write(s / "data/valuation_model.json", _vm())
        rows = check_shock_surface(s)
        self.assertEqual(rows[0][0], "SKIPPED", rows)


class ApplyEngineTests(unittest.TestCase):
    def test_parse_under_last_json(self) -> None:
        self.assertEqual(parse_under_stdout('log\n{"fair_value": 91.5}\n'), 91.5)

    def test_haircut_identity(self) -> None:
        self.assertAlmostEqual(haircut_from_values(100.0, 60.0), 0.40)

    def test_restates_bear_eps(self) -> None:
        self.assertTrue(restates_bear_numeric(80.67, 100.0, 80.0))
        self.assertFalse(restates_bear_numeric(60.0, 100.0, 80.0))

    def test_run_under_script(self) -> None:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        script = s / "data" / "compute" / "valuation.py"
        script.parent.mkdir(parents=True)
        script.write_text(SCRIPT, encoding="utf-8")
        fv = run_fair_value_under(script, {})
        self.assertAlmostEqual(fv, 100.0)
        fv2 = run_fair_value_under(script, {"om": 0.12, "ke": 0.08})
        self.assertAlmostEqual(fv2, 60.0)

    def test_apply_one_writes_derived(self) -> None:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        script = s / "data" / "compute" / "valuation.py"
        script.parent.mkdir(parents=True)
        script.write_text(SCRIPT, encoding="utf-8")
        vm = _vm()
        raw = {"name": "om shock", "shock": {"om": 0.12}, "probability": 0.2}
        applied = apply_one(s, raw, vm)
        self.assertAlmostEqual(applied["stressed_fv"], 60.0)
        self.assertAlmostEqual(applied["fair_value_haircut_pct"], 0.40)
        self.assertFalse(applied["restates_bear"])

    def test_apply_session_requires_bridge_and_stamps(self) -> None:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        _write(s / "data/valuation_model.json", _vm())
        script = s / "data" / "compute" / "valuation.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text(SCRIPT, encoding="utf-8")
        raw = {
            "name": "channel destock",
            "shock": {"om": 0.12},
            "probability": 0.25,
            "type": "sector",
            "rationale": "analog",
            "narrative": "path",
        }
        _write(s / "registry/raw/stress_destock.json", raw)
        with self.assertRaises(FileNotFoundError):
            apply_session(s)
        sc = dict(INDEPENDENT)
        sc.pop("applied", None)
        rb = _rb(sc)
        _write(s / "registry/risk_bridge.json", rb)
        _write(s / "data/price_snapshot.json", {"close": 90.0})
        apply_session(s)
        from packages.kd_research.check_core import load_json as _load

        stamped, _ = _load(s / "registry" / "risk_bridge.json")
        sc0 = stamped["stress_test"]["scenarios"][0]
        self.assertAlmostEqual(sc0["applied"]["stressed_fv"], 60.0)
        self.assertNotIn("stressed_fv", sc0)
        raw_doc, _ = _load(s / "registry" / "raw" / "stress_destock.json")
        self.assertNotIn("applied", raw_doc)
        self.assertEqual(stamped["stress_test"]["reverse_stress"]["compute"], "fair_value_under")

    def test_reverse_stress_uses_under_not_grid(self) -> None:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        script = s / "data" / "compute" / "valuation.py"
        script.parent.mkdir(parents=True)
        script.write_text(SCRIPT, encoding="utf-8")
        _write(s / "data/valuation_model.json", _vm())
        _write(s / "data/price_snapshot.json", {"close": 90.0})
        row = compute_reverse_stress(s, _vm())
        self.assertEqual(row.get("compute"), "fair_value_under")
        self.assertFalse(row.get("none"))
        self.assertTrue(row.get("dials"))
        self.assertLessEqual(row.get("stressed_fv"), 90.0)


class ReportCardTests(unittest.TestCase):
    def test_heading_and_projector(self) -> None:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        _write(
            s / "meta/run_manifest.json",
            {"harness_version": "2.44.0", "orchestrator_model": "grok-4.5"},
        )
        vm = _vm()
        sc = dict(INDEPENDENT)
        sc["probability"] = 0.20
        sc["applied"] = {
            "stressed_fv": 75.0,
            "fair_value_haircut_pct": 0.25,
            "restates_bear": False,
        }
        rb = _rb(sc)
        want = compute_stress_bind(rb, vm)
        _write(s / "data/valuation_model.json", vm)
        _write(s / "registry/risk_bridge.json", rb)
        _write(
            s / "registry/decision.json",
            {
                "ticker": "X",
                "duration": {"action": "initiate", "rationale": "Sized initiate after stress."},
                "stress_bind": want,
            },
        )
        card = "## Unstressed vs stressed\n\n" + format_stress_card(want, 100.0) + "\n"
        _write(s / "reports/00_X_README.md", "Do not initiate.\n\n" + card)
        _write(s / "reports/01_X_fundamental.md", "Hold.\n\n" + card)
        rows = check_stress_report_card(s)
        self.assertTrue(all(r[0] == "PASS" for r in rows), rows)

    def test_number_in_wrong_sentence_fails(self) -> None:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        _write(
            s / "meta/run_manifest.json",
            {"harness_version": "2.44.0", "orchestrator_model": "grok-4.5"},
        )
        vm = _vm()
        sc = dict(INDEPENDENT)
        sc["probability"] = 0.20
        sc["applied"] = {
            "stressed_fv": 75.0,
            "fair_value_haircut_pct": 0.25,
            "restates_bear": False,
        }
        rb = _rb(sc)
        want = compute_stress_bind(rb, vm)
        _write(s / "data/valuation_model.json", vm)
        _write(s / "registry/risk_bridge.json", rb)
        _write(
            s / "registry/decision.json",
            {
                "ticker": "X",
                "duration": {"action": "initiate", "rationale": "Sized initiate after stress."},
                "stress_bind": want,
            },
        )
        fake = (
            "## Unstressed vs stressed\n\n"
            f"Peers trade at {want['stressed_fv']:.2f}. Size thoughts elsewhere.\n"
        )
        _write(s / "reports/00_X_README.md", "Initiate.\n\n" + fake)
        _write(s / "reports/01_X_fundamental.md", "Initiate.\n\n" + fake)
        rows = check_stress_report_card(s)
        self.assertTrue(all(r[0] == "FAIL" for r in rows), rows)

    def test_missing_heading_fails(self) -> None:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        _write(
            s / "meta/run_manifest.json",
            {"harness_version": "2.44.0", "orchestrator_model": "grok-4.5"},
        )
        vm = _vm()
        rb = _rb(LIGHT)
        want = compute_stress_bind(rb, vm)
        _write(s / "data/valuation_model.json", vm)
        _write(s / "registry/risk_bridge.json", rb)
        _write(
            s / "registry/decision.json",
            {
                "ticker": "X",
                "duration": {"action": "initiate", "rationale": "No card."},
                "stress_bind": want,
            },
        )
        _write(s / "reports/00_X_README.md", "Initiate. Fair value vs price as context.\n")
        _write(s / "reports/01_X_fundamental.md", "Initiate.\n")
        rows = check_stress_report_card(s)
        self.assertTrue(any(r[0] == "FAIL" for r in rows), rows)


class AppliedGateTests(unittest.TestCase):
    def test_guessed_haircut_without_shock_fails(self) -> None:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        _write(
            s / "meta/run_manifest.json",
            {"harness_version": "2.44.0", "orchestrator_model": "grok-4.5"},
        )
        _write(s / "data/valuation_model.json", _vm())
        sc = dict(INDEPENDENT)
        del sc["shock"]
        rb = _rb(sc, LIGHT, NEAR_BEAR, dict(LIGHT, name="m2"), dict(LIGHT, name="m3"))
        _write(s / "registry/risk_bridge.json", rb)
        rows = check_stress_applied(s)
        self.assertTrue(any(r[0] == "FAIL" and "shock" in r[1] for r in rows), rows)


if __name__ == "__main__":
    unittest.main()

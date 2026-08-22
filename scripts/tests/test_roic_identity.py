"""ROIC identity gates: same-script NOPAT/IC vs WACC (harness >= 2.8.0)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.kd_research.gates import complete_checks  # noqa: E402
from scripts.kd_research.roic_identity import (  # noqa: E402
    check_roic_identity,
    session_is_roic_runtime,
    thin_roic_from_valuation,
    thin_roic_metrics,
)


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, str):
        path.write_text(obj, encoding="utf-8")
    else:
        path.write_text(json.dumps(obj), encoding="utf-8")


def _stamp(session: Path, version: str | None) -> None:
    man: dict = {
        "status": "scaffolded",
        "orchestrator_model": "grok-4.5",
        "default_subagent_model": "grok-4.5",
    }
    if version:
        man["harness_version"] = version
    _write(session / "meta" / "run_manifest.json", man)


def _identity(**extra) -> dict:
    d = {
        "applies": True,
        "nopat": {"value": 900.0, "definition": "SOI minus corporate other minus cash tax", "rationale": "Same stack as FCFF.", "basis": "compute"},
        "invested_capital": {"value": 10000.0, "definition": "notes+LT+equity-cash", "vintage": "FY2025", "rationale": "Book capital.", "basis": "10-K"},
        "leases": "opex_and_out_of_ic",
        "wacc": 0.09,
        "ttc_roic": {"value": 0.03, "rationale": "Four-year average on the same definition.", "basis": "financials"},
        "mid_cycle_roic": {"value": 0.09, "rationale": "900/10000.", "basis": "script"},
        "spread_mid_cycle": 0.0,
        "quality_bucket": "approx_wacc",
        "column_a": {"method": "residual_claim_fcff", "ev": 10000.0, "equity_fv": 12.0},
        "column_b": {"method": "residual_income", "ev": 10000.0, "ic": 10000.0, "equity_fv": 12.0},
        "delta_ev_pct": 0.0,
        "g0_counterfactual": {"ev": 8500.0, "equity_fv": 7.0, "note": "same engine, g=0"},
        "reinvestment_identity": {
            "g": 0.015,
            "implied_reinvestment_if_roc_eq_wacc": 0.167,
            "modeled_reinvestment_of_nopat": 0.0,
            "mismatch": True,
        },
        "gate": {
            "response": "reconciled_to_ic",
            "rationale": "A equals IC within NWC noise; this DCF is equity near book, not a franchise.",
        },
        "cheap_claim": {
            "class": "equity_near_book",
            "rationale": "Price vs DCF is price vs book after debt.",
        },
    }
    d.update(extra)
    return d


def _vm(identity: dict | None = None, **kwargs) -> dict:
    d: dict = {
        "ticker": "X",
        "model": {"name": "through_cycle_fcff_dcf", "rationale": "fixture manufacturing cyclical FCFF"},
        "fair_value": {"base": 12.0, "bear": 0.0, "bull": 20.0},
        "assumptions": {
            "wacc": {"value": 0.09, "rationale": "Named buildup.", "basis": "script"},
            "terminal_growth": {"value": 0.015, "rationale": "Nominal mix.", "basis": "module"},
        },
        "compute_script": "data/compute/valuation.py",
        "sensitivity": {"grid": {}},
    }
    if identity is not None:
        d["roic_identity"] = identity
    d.update(kwargs)
    return d


class VersionFloorTests(unittest.TestCase):
    def test_legacy_version_skips(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.7.1")
            _write(s / "data/valuation_model.json", _vm(identity=None))
            self.assertFalse(session_is_roic_runtime(s))
            rows = check_roic_identity(s)
            self.assertEqual(rows[0][0], "SKIPPED")

    def test_missing_version_is_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, None)
            _write(s / "data/valuation_model.json", _vm(identity=None))
            self.assertFalse(session_is_roic_runtime(s))
            rows = check_roic_identity(s)
            self.assertEqual(rows[0][0], "SKIPPED")

    def test_new_runtime_omits_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.8.0")
            _write(s / "data/valuation_model.json", _vm(identity=None))
            self.assertTrue(session_is_roic_runtime(s))
            rows = check_roic_identity(s)
            self.assertEqual(rows[0][0], "FAIL")
            self.assertEqual(rows[0][1], "roic_identity")


class IdentityTests(unittest.TestCase):
    def _sess(self, vm: dict, version: str | None = "2.8.0") -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        _stamp(s, version)
        _write(s / "data/valuation_model.json", vm)
        return s

    def test_reconciled_to_ic_passes(self) -> None:
        s = self._sess(_vm(_identity()))
        rows = check_roic_identity(s)
        fails = [r for r in rows if r[0] == "FAIL"]
        self.assertEqual(fails, [], fails)

    def test_applies_false_needs_reason(self) -> None:
        ident = {"applies": False, "native_analog": "roe_vs_ke"}
        s = self._sess(_vm(ident, model={"name": "excess_return", "rationale": "bank"}))
        rows = check_roic_identity(s)
        self.assertTrue(any(r[0] == "FAIL" and "not_applicable" in r[1] for r in rows), rows)

    def test_bank_na_passes(self) -> None:
        ident = {
            "applies": False,
            "native_analog": "roe_vs_ke",
            "not_applicable_reason": (
                "Lead model is excess-return / residual income on tangible book; "
                "industrial invested capital is not the capital base."
            ),
        }
        s = self._sess(_vm(ident, model={"name": "excess_return", "rationale": "bank residual income"}))
        rows = check_roic_identity(s)
        fails = [r for r in rows if r[0] == "FAIL"]
        self.assertEqual(fails, [], fails)

    def test_growth_negative_ic_na_passes(self) -> None:
        ident = {
            "applies": False,
            "native_analog": "burn_ltv_cac",
            "not_applicable_reason": (
                "Negative earnings and negative invested capital make industrial ROIC "
                "meaningless; burn multiple and LTV/CAC replace it."
            ),
        }
        s = self._sess(_vm(ident, model={"name": "path_to_profit", "rationale": "pre-profit growth"}))
        rows = check_roic_identity(s)
        self.assertFalse(any(r[0] == "FAIL" for r in rows), rows)

    def test_arithmetic_mismatch_fails(self) -> None:
        ident = _identity(mid_cycle_roic={"value": 0.15, "rationale": "wrong", "basis": "x"})
        s = self._sess(_vm(ident))
        rows = check_roic_identity(s)
        self.assertTrue(any(r[0] == "FAIL" and r[1] == "roic_identity.mid_cycle_roic" for r in rows), rows)

    def test_mixed_leases_fail(self) -> None:
        ident = _identity(leases="mixed")
        s = self._sess(_vm(ident))
        rows = check_roic_identity(s)
        self.assertTrue(any(r[0] == "FAIL" and r[1] == "roic_identity.leases" for r in rows), rows)

    def test_franchise_mos_on_approx_fails(self) -> None:
        ident = _identity(
            cheap_claim={"class": "franchise_mos", "rationale": "MoS vs DCF looks wide."}
        )
        s = self._sess(_vm(ident))
        rows = check_roic_identity(s)
        self.assertTrue(any(r[0] == "FAIL" and "cheap_claim" in r[1] for r in rows), rows)

    def test_g_zero_with_g_nonzero_fails(self) -> None:
        ident = _identity(
            gate={"response": "g_zero", "rationale": "Force no-growth terminal because ROIC is not above WACC."}
        )
        s = self._sess(_vm(ident))
        rows = check_roic_identity(s)
        self.assertTrue(any(r[0] == "FAIL" and r[1] == "roic_identity.gate" for r in rows), rows)

    def test_g_zero_passes_when_g_is_zero(self) -> None:
        ident = _identity(
            reinvestment_identity={
                "g": 0.0,
                "implied_reinvestment_if_roc_eq_wacc": 0.0,
                "modeled_reinvestment_of_nopat": 0.0,
                "mismatch": False,
            },
            gate={"response": "g_zero", "rationale": "No-growth terminal; TV cannot drive posture."},
        )
        vm = _vm(ident)
        vm["assumptions"]["terminal_growth"] = {
            "value": 0.0,
            "rationale": "g=0 legal exit.",
            "basis": "gate",
        }
        s = self._sess(vm)
        rows = check_roic_identity(s)
        fails = [r for r in rows if r[0] == "FAIL"]
        self.assertEqual(fails, [], fails)

    def test_gordon_plug_exceeds_ic_fails(self) -> None:
        ident = _identity(
            column_a={"method": "residual_claim_fcff", "ev": 13000.0, "equity_fv": 18.0},
            gate={
                "response": "reconciled_to_ic",
                "rationale": "Claiming equity near book while Gordon TV inflates EV.",
            },
        )
        s = self._sess(_vm(ident))
        rows = check_roic_identity(s)
        self.assertTrue(any(r[0] == "FAIL" and r[1] == "roic_identity.gate" for r in rows), rows)

    def test_below_wacc_without_gate_fails(self) -> None:
        ident = _identity(
            nopat={"value": 700.0, "definition": "x", "rationale": "low", "basis": "x"},
            mid_cycle_roic={"value": 0.07, "rationale": "700/10000", "basis": "x"},
            spread_mid_cycle=-0.02,
            quality_bucket="below_wacc",
            gate={"response": "keep_gordon", "rationale": "disclosed mismatch only"},
        )
        s = self._sess(_vm(ident))
        rows = check_roic_identity(s)
        self.assertTrue(any(r[0] == "FAIL" and r[1] == "roic_identity.gate" for r in rows), rows)

    def test_wacc_must_match_assumptions(self) -> None:
        ident = _identity(wacc=0.15)
        ident["spread_mid_cycle"] = 0.09 - 0.15
        ident["quality_bucket"] = "below_wacc"
        s = self._sess(_vm(ident))
        rows = check_roic_identity(s)
        self.assertTrue(any(r[0] == "FAIL" and r[1] == "roic_identity.wacc" for r in rows), rows)

    def test_above_wacc_allows_gordon(self) -> None:
        ident = _identity(
            nopat={"value": 1500.0, "definition": "x", "rationale": "high", "basis": "x"},
            mid_cycle_roic={"value": 0.15, "rationale": "1500/10000", "basis": "x"},
            spread_mid_cycle=0.06,
            quality_bucket="above_wacc",
            cheap_claim={"class": "franchise_mos", "rationale": "Capital earns above WACC."},
            reinvestment_identity={
                "g": 0.015,
                "implied_reinvestment_if_roc_eq_wacc": 0.10,
                "modeled_reinvestment_of_nopat": 0.10,
                "mismatch": False,
            },
            gate={"response": "reinvestment_in_engine", "rationale": "Reinvestment in FCFF."},
        )
        s = self._sess(_vm(ident))
        rows = check_roic_identity(s)
        fails = [r for r in rows if r[0] == "FAIL"]
        self.assertEqual(fails, [], fails)

    def test_present_on_legacy_still_validates(self) -> None:
        s = self._sess(_vm(_identity()), version="2.7.1")
        rows = check_roic_identity(s)
        fails = [r for r in rows if r[0] == "FAIL"]
        self.assertEqual(fails, [], fails)

    def test_column_a_matches_result_ev(self) -> None:
        s = self._sess(_vm(_identity()))
        _write(
            s / "data/compute/valuation_result.json",
            {"dcf": {"base": {"ev": 10000.0, "fv": 12.0}}},
        )
        rows = check_roic_identity(s)
        self.assertTrue(any(r[0] == "PASS" and r[1] == "roic_identity.column_a" for r in rows), rows)

    def test_column_a_mismatch_result_ev_fails(self) -> None:
        s = self._sess(_vm(_identity()))
        _write(
            s / "data/compute/valuation_result.json",
            {"dcf": {"base": {"ev": 8000.0, "fv": 8.0}}},
        )
        rows = check_roic_identity(s)
        self.assertTrue(any(r[0] == "FAIL" and r[1] == "roic_identity.column_a" for r in rows), rows)

    def test_2_parallel_complete_includes_roic_on_new_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.8.0")
            _write(s / "registry/technical.json", {"ticker": "X"})
            _write(s / "data/valuation_model.json", _vm(identity=None))
            _write(s / "registry/tsr_validation.json", {"ticker": "X", "tsr": {}, "compute_script": "x.py"})
            rows = complete_checks(s, "2_parallel")
            self.assertTrue(any(r[0] == "FAIL" and r[1] == "roic_identity" for r in rows), rows)
            _write(s / "data/valuation_model.json", _vm(_identity()))
            rows = complete_checks(s, "2_parallel")
            self.assertFalse(any(r[0] == "FAIL" and r[1] == "roic_identity" for r in rows), rows)


class LookbackTests(unittest.TestCase):
    def test_lookback_extract_bundle_omits_when_absent(self) -> None:
        from scripts.kd_research.session_extract import extract_session_bundle

        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name) / "archive" / "research" / "X" / "2026-01-01"
        s.mkdir(parents=True)
        _stamp(s, "2.8.0")
        _write(s / "data/valuation_model.json", _vm(identity=None))
        bundle = extract_session_bundle(s)
        self.assertIsNone(bundle.get("roic_identity"))

    def test_lookback_extract_bundle_projects(self) -> None:
        from scripts.kd_research.session_extract import extract_session_bundle

        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name) / "archive" / "research" / "X" / "2026-01-01"
        s.mkdir(parents=True)
        _stamp(s, "2.8.0")
        _write(s / "data/valuation_model.json", _vm(_identity()))
        bundle = extract_session_bundle(s)
        ident = bundle.get("roic_identity")
        assert isinstance(ident, dict)
        self.assertEqual(ident["cheap_claim"], "equity_near_book")
        metrics = thin_roic_metrics(bundle)
        self.assertEqual(metrics["roic_wacc"], 0.09)
        self.assertNotIn("posture", metrics)

    def test_lookback_thin_projection(self) -> None:
        thin = thin_roic_from_valuation(_vm(_identity()))
        assert thin is not None
        self.assertTrue(thin["applies"])
        self.assertEqual(thin["mid_cycle_roic"], 0.09)
        self.assertEqual(thin["cheap_claim"], "equity_near_book")
        self.assertEqual(thin["wacc"], 0.09)
        metrics = thin_roic_metrics({"roic_identity": thin})
        self.assertEqual(metrics["roic_applies"], 1.0)
        self.assertEqual(metrics["roic_wacc"], 0.09)
        self.assertEqual(metrics["cheap_claim"], "equity_near_book")
        self.assertNotIn("posture", metrics)

    def test_lookback_omit_when_absent(self) -> None:
        self.assertIsNone(thin_roic_from_valuation(_vm(identity=None)))
        self.assertEqual(thin_roic_metrics({}), {})

    def test_lookback_export_metrics_tempfile(self) -> None:
        from scripts.export_compare_db import export_session
        from scripts.kd_research.compare_db import open_db

        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        s = root / "archive" / "research" / "X" / "2026-01-01"
        s.mkdir(parents=True)
        _stamp(s, "2.8.0")
        _write(s / "data/valuation_model.json", _vm(_identity()))
        conn = open_db(root, rebuild=True)
        try:
            export_session(s, conn, refresh_snapshot=False)
            keys = {
                r[0]: (r[1], r[2])
                for r in conn.execute(
                    "SELECT metric_key, metric_value, metric_text FROM run_metrics"
                )
            }
            self.assertIn("roic_wacc", keys)
            self.assertAlmostEqual(keys["roic_wacc"][0], 0.09)
            self.assertEqual(keys["cheap_claim"][1], "equity_near_book")
            if "posture" in keys:
                self.assertIn(keys["posture"][1], ("cheap", "fair", "expensive"))
            self.assertNotEqual(keys.get("posture", (None, None))[1], "equity_near_book")
        finally:
            conn.close()

    def test_lookback_applies_false(self) -> None:
        ident = {
            "applies": False,
            "native_analog": "roe_vs_ke",
            "not_applicable_reason": "Bank excess-return model already is residual income on equity.",
        }
        thin = thin_roic_from_valuation(_vm(ident))
        assert thin is not None
        self.assertFalse(thin["applies"])
        metrics = thin_roic_metrics({"roic_identity": thin})
        self.assertEqual(metrics["roic_applies"], 0.0)
        self.assertEqual(metrics["roic_native_analog"], "roe_vs_ke")


if __name__ == "__main__":
    unittest.main()

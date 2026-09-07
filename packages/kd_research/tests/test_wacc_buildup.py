"""WACC-buildup identity gates (harness >= 2.40.0)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.wacc_buildup import (
    check_wacc_buildup,
    session_is_wacc_runtime,
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


def _ident(**extra) -> dict:
    rf = 0.04784
    beta_erp = 0.811656 * 0.05
    ke = rf + beta_erp + 0.0025
    kd_pre = 0.06284  # rf + 150 bp
    tax = 0.23
    kd_at = kd_pre * (1.0 - tax)
    we = 0.65
    wd = 0.35
    wacc = we * ke + wd * kd_at
    d = {
        "applies": True,
        "rf": rf,
        "ke": ke,
        "kd_pretax": kd_pre,
        "kd_aftertax": kd_at,
        "tax": tax,
        "we": we,
        "wd": wd,
        "wacc": wacc,
        "kd_source": "rf_plus_spread",
        "spread_bp": 150,
        "weight_policy": "target",
        "current_market_wd": 0.49,
        "implied_wacc_gap_bp": 200.0,
        "wacc_gap_rationale": (
            "Tape-implied WACC sits near Ke; remaining gap is leverage "
            "weights vs target, not coupon Kd."
        ),
    }
    d.update(extra)
    return d


def _vm(ident: dict | None = None, **kwargs) -> dict:
    ident = ident if ident is not None else _ident()
    wacc = ident.get("wacc", 0.08)
    d: dict = {
        "ticker": "X",
        "model": {"name": "dcf_fcff", "rationale": "ordinary FCFF"},
        "fair_value": {"base": 40.0, "bear": 20.0, "bull": 55.0},
        "assumptions": {
            "wacc": {"value": wacc, "rationale": "Named buildup.", "basis": "script"},
        },
        "wacc_buildup": ident,
        "reverse_engineering": {
            "implied": {"wacc_on_base_path": wacc + 0.02},
            "priced_for_perfection": False,
            "rationale": "Price matches a higher WACC or lower terminal OM.",
        },
        "roic_identity": {
            "applies": True,
            "wacc": wacc,
            "quality_bucket": "approx_wacc",
            "cheap_claim": {"class": "not_cheap", "rationale": "Not a franchise claim."},
        },
    }
    d.update(kwargs)
    return d


class WaccBuildupTests(unittest.TestCase):
    def _session(self, version: str, vm: dict | None) -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        _stamp(s, version)
        if vm is not None:
            _write(s / "data" / "valuation_model.json", vm)
        return s

    def test_legacy_skip_when_absent(self) -> None:
        s = self._session("2.39.0", {"ticker": "X", "assumptions": {}})
        rows = check_wacc_buildup(s)
        self.assertTrue(any(r[0] == "SKIPPED" and r[1] == "wacc_buildup" for r in rows), rows)
        self.assertFalse(session_is_wacc_runtime(s))

    def test_missing_fails_on_240(self) -> None:
        s = self._session("2.40.0", {"ticker": "X", "assumptions": {}})
        rows = check_wacc_buildup(s)
        self.assertTrue(any(r[0] == "FAIL" and r[1] == "wacc_buildup" for r in rows), rows)
        self.assertTrue(session_is_wacc_runtime(s))

    def test_applies_false_needs_reason(self) -> None:
        s = self._session("2.40.0", _vm({"applies": False, "not_applicable_reason": "short"}))
        rows = check_wacc_buildup(s)
        self.assertTrue(
            any(r[0] == "FAIL" and r[1] == "wacc_buildup.not_applicable_reason" for r in rows),
            rows,
        )

    def test_applies_false_bank_passes(self) -> None:
        ident = {
            "applies": False,
            "not_applicable_reason": (
                "Banking native hurdle is ROE vs cost of equity / NIM, not industrial WACC."
            ),
            "native_analog": "roe_vs_ke",
        }
        s = self._session("2.40.0", _vm(ident))
        rows = check_wacc_buildup(s)
        self.assertFalse(any(r[0] == "FAIL" for r in rows), rows)
        self.assertTrue(any(r[0] == "PASS" and r[1] == "wacc_buildup" for r in rows), rows)

    def test_coupon_source_fails(self) -> None:
        s = self._session("2.40.0", _vm(_ident(kd_source="coupon")))
        rows = check_wacc_buildup(s)
        self.assertTrue(any(r[0] == "FAIL" and r[1] == "wacc_buildup.kd_source" for r in rows), rows)

    def test_kd_below_rf_fails(self) -> None:
        ident = _ident(kd_pretax=0.04, kd_aftertax=0.04 * 0.77, kd_source="current_yield")
        ident["wacc"] = ident["we"] * ident["ke"] + ident["wd"] * ident["kd_aftertax"]
        s = self._session("2.40.0", _vm(ident))
        rows = check_wacc_buildup(s)
        self.assertTrue(any(r[0] == "FAIL" and r[1] == "wacc_buildup.kd_vs_rf" for r in rows), rows)

    def test_kd_below_rf_japan_hatch_passes(self) -> None:
        ident = _ident(
            kd_pretax=0.01,
            kd_aftertax=0.01 * 0.77,
            rf=0.012,
            ke=0.052,
            kd_source="current_yield",
            kd_below_rf_gate="negative_rate_market",
            kd_below_rf_rationale=(
                "Local JGB 10Y is the cash-flow currency Rf; quoted JPY industrial YTM "
                "sits 20 bp through the local curve on this print."
            ),
            implied_wacc_gap_bp=100.0,
        )
        ident["wacc"] = ident["we"] * ident["ke"] + ident["wd"] * ident["kd_aftertax"]
        vm = _vm(ident)
        vm["assumptions"]["wacc"]["value"] = ident["wacc"]
        vm["roic_identity"]["wacc"] = ident["wacc"]
        vm["reverse_engineering"]["implied"]["wacc_on_base_path"] = ident["wacc"] + 0.01
        s = self._session("2.40.0", vm)
        rows = check_wacc_buildup(s)
        self.assertFalse(any(r[0] == "FAIL" for r in rows), rows)

    def test_zero_spread_fails(self) -> None:
        rf = 0.04784
        ident = _ident(
            kd_source="rf_plus_spread",
            spread_bp=0,
            kd_pretax=rf,
            kd_aftertax=rf * 0.77,
        )
        ident["wacc"] = ident["we"] * ident["ke"] + ident["wd"] * ident["kd_aftertax"]
        vm = _vm(ident)
        vm["assumptions"]["wacc"]["value"] = ident["wacc"]
        vm["roic_identity"]["wacc"] = ident["wacc"]
        s = self._session("2.40.0", vm)
        rows = check_wacc_buildup(s)
        self.assertTrue(any(r[0] == "FAIL" and r[1] == "wacc_buildup.spread_bp" for r in rows), rows)

    def test_zero_spread_gov_hatch_passes(self) -> None:
        rf = 0.04784
        ident = _ident(
            kd_source="rf_plus_spread",
            spread_bp=0,
            kd_spread_hatch="gov_or_aaa",
            kd_pretax=rf,
            kd_aftertax=rf * 0.77,
            wd=0.10,
            we=0.90,
            current_market_wd=0.10,
            weight_policy="current_market",
        )
        ident["wacc"] = ident["we"] * ident["ke"] + ident["wd"] * ident["kd_aftertax"]
        ident["implied_wacc_gap_bp"] = 50.0
        vm = _vm(ident)
        vm["assumptions"]["wacc"]["value"] = ident["wacc"]
        vm["roic_identity"]["wacc"] = ident["wacc"]
        vm["reverse_engineering"]["implied"]["wacc_on_base_path"] = ident["wacc"] + 0.005
        s = self._session("2.40.0", vm)
        rows = check_wacc_buildup(s)
        self.assertFalse(any(r[0] == "FAIL" for r in rows), rows)

    def test_cmcsa_shaped_coupon_and_trough_weights_fail(self) -> None:
        rf = 0.04784
        ke = 0.090923
        kd_pre = 0.04
        tax = 0.23
        kd_at = kd_pre * (1.0 - tax)
        we, wd = 0.51, 0.49
        wacc = we * ke + wd * kd_at
        ident = _ident(
            rf=rf,
            ke=ke,
            kd_pretax=kd_pre,
            kd_aftertax=kd_at,
            tax=tax,
            we=we,
            wd=wd,
            wacc=wacc,
            kd_source="current_yield",
            weight_policy="current_market",
            current_market_wd=0.49,
            implied_wacc_gap_bp=299.0,
        )
        vm = _vm(ident)
        vm["assumptions"]["wacc"]["value"] = wacc
        vm["roic_identity"]["wacc"] = wacc
        vm["roic_identity"]["cheap_claim"] = {
            "class": "franchise_mos",
            "rationale": "ROIC 10% vs WACC 6% is a franchise.",
        }
        vm["reverse_engineering"]["implied"]["wacc_on_base_path"] = 0.0913
        s = self._session("2.40.0", vm)
        rows = check_wacc_buildup(s)
        self.assertTrue(any(r[0] == "FAIL" and r[1] == "wacc_buildup.kd_vs_rf" for r in rows), rows)

    def test_current_market_distressed_fails(self) -> None:
        ident = _ident(
            we=0.51,
            wd=0.49,
            weight_policy="current_market",
            current_market_wd=0.49,
        )
        ident["wacc"] = ident["we"] * ident["ke"] + ident["wd"] * ident["kd_aftertax"]
        ident["implied_wacc_gap_bp"] = 280.0
        vm = _vm(ident)
        vm["assumptions"]["wacc"]["value"] = ident["wacc"]
        vm["roic_identity"]["wacc"] = ident["wacc"]
        vm["reverse_engineering"]["implied"]["wacc_on_base_path"] = ident["wacc"] + 0.028
        s = self._session("2.40.0", vm)
        rows = check_wacc_buildup(s)
        self.assertTrue(
            any(r[0] == "FAIL" and r[1] == "wacc_buildup.weight_policy" for r in rows),
            rows,
        )

    def test_target_copy_trough_fails(self) -> None:
        ident = _ident(
            we=0.51,
            wd=0.49,
            weight_policy="target",
            current_market_wd=0.49,
        )
        ident["wacc"] = ident["we"] * ident["ke"] + ident["wd"] * ident["kd_aftertax"]
        ident["implied_wacc_gap_bp"] = 280.0
        vm = _vm(ident)
        vm["assumptions"]["wacc"]["value"] = ident["wacc"]
        vm["roic_identity"]["wacc"] = ident["wacc"]
        vm["reverse_engineering"]["implied"]["wacc_on_base_path"] = ident["wacc"] + 0.028
        s = self._session("2.40.0", vm)
        rows = check_wacc_buildup(s)
        self.assertTrue(
            any(r[0] == "FAIL" and r[1] == "wacc_buildup.target_wd_copy" for r in rows),
            rows,
        )

    def test_target_material_diff_passes(self) -> None:
        ident = _ident(
            we=0.62,
            wd=0.38,
            weight_policy="target",
            current_market_wd=0.49,
            implied_wacc_gap_bp=250.0,
            wacc_gap_rationale=(
                "Implied WACC is near Ke; model uses target 38% debt vs trough 49% "
                "and Rf+150bp cost of debt, not the coupon mix."
            ),
        )
        ident["wacc"] = ident["we"] * ident["ke"] + ident["wd"] * ident["kd_aftertax"]
        vm = _vm(ident)
        vm["assumptions"]["wacc"]["value"] = ident["wacc"]
        vm["roic_identity"]["wacc"] = ident["wacc"]
        vm["reverse_engineering"]["implied"]["wacc_on_base_path"] = ident["wacc"] + 0.025
        s = self._session("2.40.0", vm)
        rows = check_wacc_buildup(s)
        self.assertFalse(any(r[0] == "FAIL" for r in rows), rows)

    def test_arithmetic_fail(self) -> None:
        ident = _ident(wacc=0.12)
        s = self._session("2.40.0", _vm(ident, assumptions={"wacc": {"value": 0.12, "rationale": "x" * 12, "basis": "x"}}))
        rows = check_wacc_buildup(s)
        self.assertTrue(any(r[0] == "FAIL" and r[1] == "wacc_buildup.wacc" for r in rows), rows)

    def test_net_cash_skips_kd_vs_rf(self) -> None:
        ident = _ident(
            we=0.98,
            wd=0.02,
            kd_pretax=0.0,
            kd_aftertax=0.0,
            kd_source="current_yield",
            weight_policy="current_market",
            current_market_wd=0.02,
        )
        ident["wacc"] = ident["we"] * ident["ke"] + ident["wd"] * ident["kd_aftertax"]
        ident["implied_wacc_gap_bp"] = 10.0
        vm = _vm(ident)
        vm["assumptions"]["wacc"]["value"] = ident["wacc"]
        vm["roic_identity"]["wacc"] = ident["wacc"]
        vm["reverse_engineering"]["implied"]["wacc_on_base_path"] = ident["wacc"] + 0.001
        s = self._session("2.40.0", vm)
        rows = check_wacc_buildup(s)
        self.assertFalse(any(r[0] == "FAIL" for r in rows), rows)
        self.assertTrue(any(r[1] == "wacc_buildup.kd_skip" for r in rows), rows)

    def test_gap_rationale_tape_only_fails(self) -> None:
        ident = _ident(
            implied_wacc_gap_bp=250.0,
            wacc_gap_rationale="Tape is cheap so franchise margin of safety applies here.",
        )
        ident["wacc"] = ident["we"] * ident["ke"] + ident["wd"] * ident["kd_aftertax"]
        vm = _vm(ident)
        vm["assumptions"]["wacc"]["value"] = ident["wacc"]
        vm["roic_identity"]["wacc"] = ident["wacc"]
        vm["reverse_engineering"]["implied"]["wacc_on_base_path"] = ident["wacc"] + 0.025
        s = self._session("2.40.0", vm)
        rows = check_wacc_buildup(s)
        self.assertTrue(
            any(r[0] == "FAIL" and r[1] == "wacc_buildup.wacc_gap_rationale" for r in rows),
            rows,
        )

    def test_omit_implied_with_high_wd_fails(self) -> None:
        ident = _ident(we=0.51, wd=0.49, weight_policy="target", current_market_wd=0.49)
        ident["wacc"] = ident["we"] * ident["ke"] + ident["wd"] * ident["kd_aftertax"]
        vm = _vm(ident)
        vm["assumptions"]["wacc"]["value"] = ident["wacc"]
        vm["roic_identity"]["wacc"] = ident["wacc"]
        vm["reverse_engineering"] = {"priced_for_perfection": False, "rationale": "omitted inversion"}
        s = self._session("2.40.0", vm)
        rows = check_wacc_buildup(s)
        self.assertTrue(
            any(r[0] == "FAIL" and r[1] == "wacc_buildup.implied_wacc" for r in rows),
            rows,
        )

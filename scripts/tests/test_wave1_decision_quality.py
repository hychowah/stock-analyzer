"""Wave 1 decision-quality gates (harness >= 2.9.0) on synthetic sessions."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.kd_research.decision_quality import (  # noqa: E402
    check_decision_usefulness,
    check_growth_cash_identity,
    check_priced_for_perfection,
    check_readme_audit_disclaimer,
    check_roc_screen_vs_cheap_claim,
    check_sector_identity_tripwire,
    check_template_masses,
    check_wave1_decision_quality,
    extract_priced_for_perfection,
    session_is_wave1_runtime,
)
from scripts.kd_research.outcomes import mechanical_scorecard  # noqa: E402
from scripts.kd_research.roic_identity import check_roic_identity  # noqa: E402
from scripts.kd_research.session_extract import (  # noqa: E402
    extract_key_risks,
    extract_session_bundle,
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


def _vm(**kwargs) -> dict:
    d = {
        "ticker": "X",
        "model": {"name": "fcff_dcf", "rationale": "ordinary DCF"},
        "fair_value": {
            "base": 100.0,
            "bear": 80.0,
            "bull": 120.0,
            "margin_of_safety": 0.2,
            "margin_of_safety_pct": 20.0,
            "scenario_probabilities": {"bear": 0.28, "base": 0.47, "bull": 0.25},
            "probability_method": "Hit-rate 7/12 plus destock analog → bear 0.28; counterfactual clean-SOM 0.22/0.48/0.30.",
        },
        "assumptions": {
            "wacc": {"value": 0.09, "rationale": "buildup", "basis": "script"},
        },
        "compute_script": "data/compute/valuation.py",
        "sensitivity": {"grid": {}},
        "reverse_engineering": {
            "implied": {"or_wacc": "base path needs WACC ~7.1% vs model 9.0%"},
            "priced_for_perfection": True,
            "rationale": "Matching tape on the base volume path needs WACC 7.1% vs 9.0% or terminal OM at bull 22%.",
        },
    }
    fv_over = kwargs.pop("fair_value", None)
    if isinstance(fv_over, dict):
        d["fair_value"].update(fv_over)
    d.update(kwargs)
    return d


class VersionFloorTests(unittest.TestCase):
    def test_legacy_skips_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.8.0")
            _write(s / "data/valuation_model.json", _vm())
            self.assertFalse(session_is_wave1_runtime(s))
            rows = check_wave1_decision_quality(s)
            self.assertEqual(rows[0][0], "SKIPPED")
            self.assertEqual(rows[0][1], "wave1_decision_quality")

    def test_missing_version_skips(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, None)
            _write(s / "data/valuation_model.json", _vm())
            self.assertFalse(session_is_wave1_runtime(s))
            self.assertEqual(check_wave1_decision_quality(s)[0][0], "SKIPPED")

    def test_290_enforces(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.9.0")
            _write(s / "data/valuation_model.json", _vm())
            self.assertTrue(session_is_wave1_runtime(s))
            rows = check_wave1_decision_quality(s, include_reports=False)
            self.assertTrue(any(r[1] == "template_masses" for r in rows), rows)


class TemplateMassTests(unittest.TestCase):
    def _sess(self, vm: dict, version: str = "2.9.0") -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        _stamp(s, version)
        _write(s / "data/valuation_model.json", vm)
        return s

    def test_304525_without_method_fails(self) -> None:
        vm = _vm(
            fair_value={
                "scenario_probabilities": {"bear": 0.30, "base": 0.45, "bull": 0.25},
                "probability_method": "",
            }
        )
        rows = check_template_masses(self._sess(vm))
        self.assertEqual(rows[0][0], "FAIL")

    def test_304525_with_counterfactual_passes(self) -> None:
        vm = _vm(
            fair_value={
                "scenario_probabilities": {"bear": 0.30, "base": 0.45, "bull": 0.25},
                "probability_method": (
                    "Late-cycle DC book is 60% of sales. Counterfactual if bookings "
                    "roll over: 0.38/0.42/0.20."
                ),
            }
        )
        rows = check_template_masses(self._sess(vm))
        self.assertEqual(rows[0][0], "PASS", rows)

    def test_non_template_passes(self) -> None:
        rows = check_template_masses(self._sess(_vm()))
        self.assertEqual(rows[0][0], "PASS", rows)

    def test_28_does_not_fail_via_bundle(self) -> None:
        s = self._sess(_vm(fair_value={
            "scenario_probabilities": {"bear": 0.30, "base": 0.45, "bull": 0.25},
            "probability_method": "",
        }), version="2.8.0")
        rows = check_wave1_decision_quality(s)
        self.assertEqual(rows[0][0], "SKIPPED")


class PfpTests(unittest.TestCase):
    def test_extracts_reverse_engineering(self) -> None:
        vm = _vm()
        flag, rationale = extract_priced_for_perfection(vm)
        self.assertIs(flag, True)
        self.assertIn("WACC", rationale)

    def test_mechanical_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.9.0")
            vm = _vm()
            vm["reverse_engineering"] = {
                "priced_for_perfection": True,
                "rationale": "Base FV is below current price therefore priced for perfection.",
            }
            _write(s / "data/valuation_model.json", vm)
            rows = check_priced_for_perfection(s)
            self.assertEqual(rows[0][0], "FAIL", rows)

    def test_named_dial_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.9.0")
            _write(s / "data/valuation_model.json", _vm())
            rows = check_priced_for_perfection(s)
            self.assertEqual(rows[0][0], "PASS", rows)


class DecisionUsefulnessTests(unittest.TestCase):
    def test_wide_cone_without_du_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.9.0")
            vm = _vm(fair_value={"base": 50.0, "bear": 0.0, "bull": 200.0})
            _write(s / "data/valuation_model.json", vm)
            rows = check_decision_usefulness(s)
            self.assertEqual(rows[0][0], "FAIL", rows)

    def test_wide_cone_with_low_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.9.0")
            vm = _vm(
                fair_value={
                    "base": 50.0,
                    "bear": 0.0,
                    "bull": 200.0,
                    "decision_usefulness": "low",
                }
            )
            _write(s / "data/valuation_model.json", vm)
            rows = check_decision_usefulness(s)
            self.assertEqual(rows[0][0], "PASS", rows)

    def test_tight_cone_no_du_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.9.0")
            _write(s / "data/valuation_model.json", _vm())
            rows = check_decision_usefulness(s)
            self.assertEqual(rows[0][0], "PASS", rows)


class RocBindTests(unittest.TestCase):
    def _tsr(self, session: Path) -> None:
        _write(
            session / "registry/tsr_validation.json",
            {
                "ticker": "X",
                "tsr": {},
                "compute_script": "data/compute/tsr.py",
                "value_trap_flags": [
                    {
                        "flag": "roc_vs_cost_of_capital",
                        "status": "fail",
                        "evidence": "historical GAAP ROIC below a floor",
                    }
                ],
            },
        )

    def test_below_wacc_franchise_is_roic_not_this_gate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.9.0")
            vm = _vm()
            vm["roic_identity"] = {
                "applies": True,
                "quality_bucket": "below_wacc",
                "cheap_claim": {"class": "franchise_mos"},
            }
            _write(s / "data/valuation_model.json", vm)
            self._tsr(s)
            rows = check_roc_screen_vs_cheap_claim(s)
            self.assertEqual(rows[0][0], "PASS", rows)

    def test_above_wacc_franchise_without_rebuttal_warns(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.9.0")
            vm = _vm()
            vm["roic_identity"] = {
                "applies": True,
                "quality_bucket": "above_wacc",
                "cheap_claim": {"class": "franchise_mos"},
            }
            _write(s / "data/valuation_model.json", vm)
            self._tsr(s)
            rows = check_roc_screen_vs_cheap_claim(s)
            self.assertEqual(rows[0][0], "WARN", rows)

    def test_above_wacc_with_rebuttal_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.9.0")
            vm = _vm()
            vm["roic_identity"] = {
                "applies": True,
                "quality_bucket": "above_wacc",
                "cheap_claim": {"class": "franchise_mos"},
                "roc_screen_rebuttal": (
                    "Historical GAAP ROC is trough-year; mid-cycle owner-earnings "
                    "NOPAT/IC on the DCF stack is 12% vs WACC 9%."
                ),
            }
            _write(s / "data/valuation_model.json", vm)
            self._tsr(s)
            rows = check_roc_screen_vs_cheap_claim(s)
            self.assertEqual(rows[0][0], "PASS", rows)


class SectorTripwireTests(unittest.TestCase):
    def test_branded_staple_cyclical_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.9.0")
            _write(
                s / "registry/sector_config.json",
                {
                    "primary_sector": "cyclical",
                    "signals": ["GICS Consumer Defensive", "Farm Products", "branded retail eggs"],
                    "rationale": "Q2 trough so cyclical despite branded CPG mix",
                },
            )
            rows = check_sector_identity_tripwire(s)
            self.assertEqual(rows[0][0], "FAIL", rows)

    def test_mixed_branded_and_spot_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.9.0")
            _write(
                s / "registry/sector_config.json",
                {
                    "primary_sector": "cyclical",
                    "signals": [
                        "GICS Consumer Defensive",
                        "branded retail",
                        "majority of revenue realized at spot",
                    ],
                },
            )
            rows = check_sector_identity_tripwire(s)
            self.assertEqual(rows[0][0], "SKIPPED", rows)

    def test_unbranded_spot_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.9.0")
            _write(
                s / "registry/sector_config.json",
                {
                    "primary_sector": "cyclical",
                    "signals": [
                        "Farm Products",
                        "unbranded posted-price shell eggs",
                        "majority of revenue realized at spot",
                    ],
                    "rationale": "spot-realized protein",
                },
            )
            rows = check_sector_identity_tripwire(s)
            self.assertEqual(rows[0][0], "PASS", rows)


class GrowthCashTests(unittest.TestCase):
    def test_branded_cpg_as_growth_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.9.0")
            _write(
                s / "registry/sector_config.json",
                {
                    "primary_sector": "growth",
                    "signals": ["GICS Consumer Defensive", "branded CPG beverage"],
                    "rationale": "fast growth so growth module",
                },
            )
            rows = check_growth_cash_identity(s)
            self.assertEqual(rows[0][0], "FAIL", rows)

    def test_saas_growth_without_staple_language_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.9.0")
            _write(
                s / "registry/sector_config.json",
                {
                    "primary_sector": "growth",
                    "signals": ["negative FCF SaaS", "SBC dilution is the identity"],
                },
            )
            rows = check_growth_cash_identity(s)
            self.assertEqual(rows[0][0], "SKIPPED", rows)

    def test_28_f21_combo_skipped_via_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.8.0")
            _write(s / "data/valuation_model.json", _vm(fair_value={
                "base": 50.0,
                "bear": 0.0,
                "bull": 200.0,
                "scenario_probabilities": {"bear": 0.30, "base": 0.45, "bull": 0.25},
                "probability_method": "",
            }))
            _write(
                s / "registry/sector_config.json",
                {
                    "primary_sector": "cyclical",
                    "signals": ["GICS Consumer Defensive", "branded retail eggs"],
                },
            )
            rows = check_wave1_decision_quality(s)
            self.assertEqual(rows[0][0], "SKIPPED")
            self.assertEqual(rows[0][1], "wave1_decision_quality")


class ReadmeDisclaimerTests(unittest.TestCase):
    def test_pass_without_disclaimer_warns(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.9.0")
            _write(s / "reports/00_X_README.md", "# X\n\nAudit verdict: PASS\nMoS 45%.\n")
            rows = check_readme_audit_disclaimer(s)
            self.assertEqual(rows[0][0], "WARN", rows)

    def test_disclaimer_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.9.0")
            _write(
                s / "reports/00_X_README.md",
                "# X\n\nAudit verdict: PASS (process completeness, not an investment recommendation).\n",
            )
            rows = check_readme_audit_disclaimer(s)
            self.assertEqual(rows[0][0], "PASS", rows)


class SnapshotExtractTests(unittest.TestCase):
    def test_bundle_projects_pfp_du_cheap_claim_and_string_risks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "archive" / "research" / "SNAP" / "2026-05-05"
            _stamp(root, "2.9.0")
            vm = _vm(
                fair_value={"decision_usefulness": "medium"},
            )
            vm["roic_identity"] = {
                "applies": True,
                "cheap_claim": {"class": "not_cheap"},
                "quality_bucket": "above_wacc",
                "mid_cycle_roic": 0.12,
                "wacc": 0.09,
            }
            _write(root / "data/valuation_model.json", vm)
            _write(root / "registry/sector_config.json", {"primary_sector": "standard", "ticker": "SNAP"})
            _write(
                root / "registry/latest_quarter.json",
                {
                    "ticker": "SNAP",
                    "fiscal_period": "2026-Q1",
                    "filing_date": "2026-04-01",
                    "currency": "USD",
                    "sources": ["10-Q"],
                    "risks": [
                        {"risk": "AI capex ROI", "severity": "high"},
                        {"foo": 1, "bar": 2},
                    ],
                },
            )
            _write(
                root / "registry/risk_bridge.json",
                {
                    "top_risks": ["litigation"],
                    "scenario_probabilities": {"bear": 0.3, "base": 0.5, "bull": 0.2},
                },
            )
            bundle = extract_session_bundle(root)
            self.assertIs(bundle["priced_for_perfection"], True)
            self.assertEqual(bundle["decision_usefulness"], "medium")
            self.assertEqual(bundle["roic_identity"]["cheap_claim"], "not_cheap")
            risks = extract_key_risks(root)
            self.assertTrue(all(isinstance(r, str) for r in risks), risks)
            self.assertNotIn(str({"foo": 1, "bar": 2}), risks)
            self.assertIn("AI capex ROI", risks)


class OutcomesPolicyTests(unittest.TestCase):
    def test_overall_ignores_1d_when_primary_3m_pending(self) -> None:
        fields = {
            "margin_of_safety_pct": 25.0,
            "fv_bear": 80,
            "fv_base": 100,
            "fv_bull": 130,
        }
        price_path = {
            "marks": [
                {
                    "horizon": "1d",
                    "status": "ok",
                    "price": 90,
                    "total_return_pct": 12.5,
                    "excess_return_pct": 2.0,
                },
                {"horizon": "3m", "status": "pending", "price": None},
            ]
        }
        sc = mechanical_scorecard(
            run_id="research:T:2026-01-01",
            ticker="T",
            session_date="2026-01-01",
            session_key="2026-01-01",
            fields=fields,
            price_path=price_path,
            horizon_primary="3m",
        )
        self.assertEqual(sc["metrics"]["direction_vs_price"]["1d"]["value"], "correct")
        self.assertEqual(sc["overall_label"], "too_early")

    def test_wide_band_ineligible(self) -> None:
        fields = {
            "margin_of_safety_pct": -17.0,
            "fv_bear": 149.0,
            "fv_base": 494.0,
            "fv_bull": 961.0,
        }
        price_path = {
            "marks": [
                {
                    "horizon": "1d",
                    "status": "ok",
                    "price": 588.0,
                    "total_return_pct": 1.2,
                    "excess_return_pct": 0.0,
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
            horizon_primary="3m",
        )
        self.assertEqual(sc["metrics"]["fv_band_at_mark"]["1d"]["value"], "ineligible")


class CheckSessionCheapClaimTests(unittest.TestCase):
    """Verification: check_session entry on omit cheap_claim / legacy skip."""

    def test_new_runtime_omit_fails_via_check_roic(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.9.0")
            _write(s / "data/valuation_model.json", _vm())
            rows = check_roic_identity(s)
            fails = [r for r in rows if r[0] == "FAIL" and r[1] == "roic_identity"]
            self.assertTrue(fails, rows)

    def test_legacy_omit_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, None)
            _write(s / "data/valuation_model.json", _vm())
            rows = check_roic_identity(s)
            self.assertEqual(rows[0][0], "SKIPPED")


class RoicStillFailsOmitOnNewRuntime(unittest.TestCase):
    def test_290_omit_roic_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.9.0")
            _write(s / "data/valuation_model.json", _vm())
            rows = check_roic_identity(s)
            self.assertEqual(rows[0][0], "FAIL")
            self.assertEqual(rows[0][1], "roic_identity")


if __name__ == "__main__":
    unittest.main()

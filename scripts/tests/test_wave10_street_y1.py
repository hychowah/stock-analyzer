"""Wave 10 / harness 2.18.0: Street FY+1 is base Y1; destock analog in bear."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.kd_research.epistemology import (  # noqa: E402
    check_destock_default,
    check_destock_not_silent_duration,
    check_tv_share_duration,
)
from scripts.kd_research.street_bind import check_street_bind  # noqa: E402


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj) if not isinstance(obj, str) else obj, encoding="utf-8")


def _stamp(session: Path, version: str) -> None:
    _write(
        session / "meta" / "run_manifest.json",
        {"status": "scaffolded", "orchestrator_model": "grok-4.5", "harness_version": version},
    )


def _street(*, revenue=254.2, n=55) -> dict:
    return {
        "ticker": "X",
        "session_date": "2026-01-01",
        "source": "yfinance.revenue_estimate",
        "fiscal_convention": "company_fy",
        "years": [
            {"label": "0y", "revenue": 180.0, "eps": 28.0, "n_revenue": n},
            {"label": "+1y", "revenue": revenue, "eps": 31.72, "n_revenue": n, "eps_basis": "unknown"},
        ],
    }


def _brief(status: str = "unresolved") -> dict:
    return {
        "ticker": "X",
        "session_date": "2026-01-01",
        "sources": {"workers": ["a", "b", "c"]},
        "conflicts": [
            {
                "id": "flatten_vs_destock",
                "claim_a": "flatten mid-cycle",
                "claim_b": "destock analog FY2022",
                "status": status,
            }
        ],
        "rejected_shapes": [],
        "verify_rechecks": [{"path": "x", "value": 1}, {"path": "y", "value": 2}, {"path": "z", "value": 3}],
        "analog_class": "advertiser_budget",
        "current_print_is_destock": False,
    }


BEAR_HOOK = {
    "from": "conflicts.flatten_vs_destock",
    "action": "used_as:bear_only",
    "applies_in": "bear_only",
    "reason": "destock analog lives in bear; Street FY+1 is the Y1 baseline",
    "new": "Y1 Street duration; destock analog lives in bear only",
}

BASE_HOOK = {
    "from": "conflicts.flatten_vs_destock",
    "action": "used_as:base",
    "applies_in": "base",
    "reason": "Y1 destock/quality-reset on the base path",
    "new": "Y1 destock/quality-reset on the base path (run-rate ex destock); duration only in bull",
}


def _dials() -> list[dict]:
    keys = ("volume_vs_guide", "gaap_om_vs_guide", "sbc_in_fcff", "wacc_vs_buildup")
    return [{"key": k, "applies_in": "none"} for k in keys]


def _vm(*, base: float, street: float, destock_hook: dict | None, hook_action: str = "used_as:fy1_baseline", response: str | None = None) -> dict:
    delta = (base - street) / street
    bind = {
        "guide": 252.7,
        "street": street,
        "base": base,
        "delta_pct": delta,
        "independent_construction": {
            "rationale": "Base Y1 starts from Street FY+1 vendor mean; remaining-period box is the cross-check; destock analog is bear-only."
        },
    }
    if response:
        bind["response"] = response
        if response != "street_baseline":
            bind["divergence_rationale"] = (
                "Street FY+1 marked unusable because coverage n is too small or the "
                "fiscal map is unclear; Y1 falls back to the printed remaining-year box."
            )
    hooks = []
    if destock_hook is not None:
        hooks.append(destock_hook)
    return {
        "ticker": "X",
        "model": {"name": "dcf", "rationale": "ordinary FCFF"},
        "fair_value": {"base": 100, "bear": 80, "bull": 120, "decision_usefulness": "medium"},
        "assumptions": {},
        "compute_script": "data/compute/v.py",
        "sensitivity": {},
        "operating_path_hooks": hooks,
        "street_bind": bind,
        "street_hooks": [
            {
                "from": "street_estimates.years[+1y].revenue",
                "action": hook_action,
                "reason": "Street FY+1 revenue is the required base Y1 starting point on harness 2.18.",
            }
        ],
        "conservatism_dials": _dials(),
    }


class StreetY1BandTests(unittest.TestCase):
    def test_base_equals_street_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.18.0")
            _write(s / "registry/street_estimates.json", _street())
            _write(s / "data/valuation_model.json", _vm(base=254.2, street=254.2, destock_hook=BEAR_HOOK))
            rows = check_street_bind(s)
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertEqual(fails, [], fails)

    def test_minus_7pct_destock_y1_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.18.0")
            _write(s / "registry/street_estimates.json", _street())
            vm = _vm(base=236.0, street=254.2, destock_hook=BASE_HOOK)
            vm["street_bind"]["response"] = "keep_independent_vs_street"
            vm["street_bind"]["divergence_rationale"] = (
                "Keep independent destock Y1 because |delta| is inside 20 percent."
            )
            _write(s / "data/valuation_model.json", vm)
            rows = check_street_bind(s)
            self.assertTrue(any(r[0] == "FAIL" and r[1] == "street_bind.y1_band" for r in rows), rows)
            self.assertTrue(any(r[0] == "FAIL" and r[1] == "street_bind.response" for r in rows), rows)

    def test_minus_7pct_still_warn_only_on_217(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.17.0")
            _write(s / "registry/street_estimates.json", _street())
            vm = _vm(
                base=236.0,
                street=254.2,
                destock_hook=BASE_HOOK,
                hook_action="used_as:calibration_check",
            )
            _write(s / "data/valuation_model.json", vm)
            rows = check_street_bind(s)
            self.assertFalse(any(r[0] == "FAIL" and "y1_band" in r[1] for r in rows), rows)
            self.assertFalse(any(r[0] == "FAIL" and r[1] == "street_hooks copy" for r in rows), rows)

    def test_fy1_baseline_hook_required(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.18.0")
            _write(s / "registry/street_estimates.json", _street())
            vm = _vm(base=254.2, street=254.2, destock_hook=BEAR_HOOK, hook_action="used_as:calibration_check")
            _write(s / "data/valuation_model.json", vm)
            rows = check_street_bind(s)
            self.assertTrue(any(r[0] == "FAIL" and "fy1_baseline" in r[1] for r in rows), rows)

    def test_revenue_path_hook_legal_on_218(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.18.0")
            _write(s / "registry/street_estimates.json", _street())
            vm = _vm(base=254.2, street=254.2, destock_hook=BEAR_HOOK, hook_action="used_as:revenue_path")
            _write(s / "data/valuation_model.json", vm)
            rows = check_street_bind(s)
            self.assertFalse(any(r[0] == "FAIL" and "copy" in r[1] for r in rows), rows)
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertEqual(fails, [], fails)

    def test_revenue_path_hook_fails_on_217(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.17.0")
            _write(s / "registry/street_estimates.json", _street())
            vm = _vm(base=254.2, street=254.2, destock_hook=BEAR_HOOK, hook_action="used_as:revenue_path")
            _write(s / "data/valuation_model.json", vm)
            rows = check_street_bind(s)
            self.assertTrue(any(r[0] == "FAIL" and "copy" in r[1] for r in rows), rows)

    def test_street_unusable_escapes_band(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.18.0")
            _write(s / "registry/street_estimates.json", _street())
            vm = _vm(base=236.0, street=254.2, destock_hook=BASE_HOOK, response="street_unusable")
            _write(s / "data/valuation_model.json", vm)
            rows = check_street_bind(s)
            self.assertFalse(any(r[0] == "FAIL" and r[1] == "street_bind.y1_band" for r in rows), rows)


class DestockInvertTests(unittest.TestCase):
    def test_218_destock_in_bear_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.18.0")
            _write(s / "registry/street_estimates.json", _street())
            _write(s / "registry/operating_path_brief.json", _brief("unresolved"))
            _write(s / "data/valuation_model.json", _vm(base=254.2, street=254.2, destock_hook=BEAR_HOOK))
            _write(
                s / "registry/decision.json",
                {"ticker": "X", "duration": {"action": "initiate", "rationale": "Street Y1 duration in base."}},
            )
            w3 = check_destock_not_silent_duration(s)
            w4 = check_destock_default(s)
            self.assertEqual(w3[0][0], "PASS", w3)
            self.assertEqual(w4[0][0], "PASS", w4)

    def test_218_destock_in_base_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.18.0")
            _write(s / "registry/street_estimates.json", _street())
            _write(s / "registry/operating_path_brief.json", _brief("unresolved"))
            _write(s / "data/valuation_model.json", _vm(base=254.2, street=254.2, destock_hook=BASE_HOOK))
            _write(
                s / "registry/decision.json",
                {"ticker": "X", "duration": {"action": "initiate", "rationale": "Destock in base."}},
            )
            w3 = check_destock_not_silent_duration(s)
            w4 = check_destock_default(s)
            self.assertEqual(w3[0][0], "FAIL", w3)
            self.assertEqual(w4[0][0], "FAIL", w4)

    def test_218_du_low_does_not_allow_destock_in_base(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.18.0")
            _write(s / "registry/street_estimates.json", _street())
            _write(s / "registry/operating_path_brief.json", _brief("resolved"))
            vm = _vm(base=254.2, street=254.2, destock_hook=BASE_HOOK)
            vm["fair_value"]["decision_usefulness"] = "low"
            _write(s / "data/valuation_model.json", vm)
            _write(
                s / "registry/decision.json",
                {"ticker": "X", "duration": {"action": "pass", "rationale": "Cone is decision-useless."}},
            )
            w4 = check_destock_default(s)
            self.assertEqual(w4[0][0], "FAIL", w4)

    def test_212_destock_in_bear_still_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.12.0")
            _write(s / "registry/operating_path_brief.json", _brief("resolved"))
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf"},
                    "fair_value": {"base": 100, "decision_usefulness": "high"},
                    "assumptions": {},
                    "compute_script": "data/compute/v.py",
                    "sensitivity": {},
                    "operating_path_hooks": [BEAR_HOOK],
                },
            )
            _write(
                s / "registry/decision.json",
                {"ticker": "X", "duration": {"action": "initiate", "rationale": "Duration in base."}},
            )
            w4 = check_destock_default(s)
            self.assertEqual(w4[0][0], "FAIL", w4)

    def test_218_street_unusable_keeps_destock_in_base(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.18.0")
            street = _street()
            street["unavailable"] = True
            street["years"] = []
            _write(s / "registry/street_estimates.json", street)
            _write(s / "registry/operating_path_brief.json", _brief("unresolved"))
            vm = {
                "ticker": "X",
                "model": {"name": "dcf", "rationale": "ordinary FCFF"},
                "fair_value": {"base": 100, "decision_usefulness": "high"},
                "assumptions": {},
                "compute_script": "data/compute/v.py",
                "sensitivity": {},
                "operating_path_hooks": [BASE_HOOK],
                "street_hooks": [
                    {
                        "from": "street_estimates",
                        "action": "rejected",
                        "reason": "Street fetch unavailable; widen range; destock analog matches this print.",
                    }
                ],
                "conservatism_dials": _dials(),
            }
            _write(s / "data/valuation_model.json", vm)
            _write(
                s / "registry/decision.json",
                {"ticker": "X", "duration": {"action": "initiate", "rationale": "Destock print with no Street."}},
            )
            w4 = check_destock_default(s)
            self.assertEqual(w4[0][0], "PASS", w4)


class BoxFloorTests(unittest.TestCase):
    def test_q3_below_box_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.18.0")
            _write(s / "registry/street_estimates.json", _street())
            _write(
                s / "registry/latest_quarter.json",
                {
                    "ticker": "X",
                    "fiscal_period": "2026-Q2",
                    "filing_date": "2026-07-30",
                    "currency": "USD",
                    "sources": ["8-K"],
                    "guidance": {"revenue_box_low": 61.0, "revenue_box_high": 64.0, "revenue_box_period": "Q3"},
                },
            )
            vm = _vm(base=254.2, street=254.2, destock_hook=BEAR_HOOK)
            vm["street_bind"]["intra_year"] = [{"period": "Q3", "revenue": 57.5}]
            _write(s / "data/valuation_model.json", vm)
            rows = check_street_bind(s)
            self.assertTrue(any(r[0] == "FAIL" and r[1] == "guide_floor" for r in rows), rows)

    def test_untyped_guidance_does_not_false_fail(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.18.0")
            _write(s / "registry/street_estimates.json", _street())
            _write(
                s / "registry/latest_quarter.json",
                {
                    "ticker": "X",
                    "fiscal_period": "2026-Q2",
                    "filing_date": "2026-07-30",
                    "currency": "USD",
                    "sources": ["8-K"],
                    "guidance": {"narrative": "Q3 revenue $61-64B"},
                },
            )
            _write(s / "data/valuation_model.json", _vm(base=254.2, street=254.2, destock_hook=BEAR_HOOK))
            rows = check_street_bind(s)
            self.assertFalse(any(r[0] == "FAIL" and r[1] == "guide_floor" for r in rows), rows)


class StackingPairTests(unittest.TestCase):
    def test_volume_and_sbc_off_street_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.18.0")
            _write(s / "registry/street_estimates.json", _street())
            vm = _vm(base=236.0, street=254.2, destock_hook=BEAR_HOOK)
            vm["conservatism_dials"] = [
                {"key": "volume_vs_guide", "applies_in": "base"},
                {"key": "gaap_om_vs_guide", "applies_in": "none"},
                {"key": "sbc_in_fcff", "applies_in": "base"},
                {"key": "wacc_vs_buildup", "applies_in": "none"},
            ]
            _write(s / "data/valuation_model.json", vm)
            rows = check_street_bind(s)
            self.assertTrue(any(r[0] == "FAIL" and "stacking_pair" in r[1] for r in rows), rows)

    def test_volume_and_sbc_on_street_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.18.0")
            _write(s / "registry/street_estimates.json", _street())
            vm = _vm(base=254.2, street=254.2, destock_hook=BEAR_HOOK)
            vm["conservatism_dials"] = [
                {"key": "volume_vs_guide", "applies_in": "base"},
                {"key": "gaap_om_vs_guide", "applies_in": "none"},
                {"key": "sbc_in_fcff", "applies_in": "base"},
                {"key": "wacc_vs_buildup", "applies_in": "none"},
            ]
            _write(s / "data/valuation_model.json", vm)
            rows = check_street_bind(s)
            self.assertFalse(any(r[0] == "FAIL" and "stacking_pair" in r[1] for r in rows), rows)


class TvShareTests(unittest.TestCase):
    def test_base_tv_75_without_du_low_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.18.0")
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf"},
                    "fair_value": {"base": 100, "decision_usefulness": "medium"},
                    "assumptions": {"y8_growth": 0.035, "explicit_years": 8},
                    "compute_script": "data/compute/v.py",
                    "terminal_consistency": {"tv_share_of_ev_base": 0.885, "y8_growth": 0.035},
                },
            )
            rows = check_tv_share_duration(s)
            self.assertTrue(any(r[0] == "FAIL" and r[1] == "tv_share_75" for r in rows), rows)

    def test_bear_tv_over_one_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.18.0")
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf"},
                    "fair_value": {"base": 100, "decision_usefulness": "low"},
                    "assumptions": {"y8_growth": 0.035, "explicit_years": 8},
                    "compute_script": "data/compute/v.py",
                    "terminal_consistency": {
                        "tv_share_of_ev_base": 0.885,
                        "tv_share_of_ev_bear": 1.76,
                        "y8_growth": 0.035,
                    },
                },
            )
            rows = check_tv_share_duration(s)
            self.assertTrue(any(r[0] == "FAIL" and r[1] == "bear_tv_share" for r in rows), rows)

    def test_bear_tv_stress_only_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.18.0")
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf"},
                    "fair_value": {"base": 100, "decision_usefulness": "low"},
                    "assumptions": {"y8_growth": 0.035, "explicit_years": 8},
                    "compute_script": "data/compute/v.py",
                    "terminal_consistency": {
                        "tv_share_of_ev_base": 0.885,
                        "tv_share_of_ev_bear": 1.76,
                        "bear_tv_role": "stress_only",
                        "y8_growth": 0.035,
                    },
                },
            )
            rows = check_tv_share_duration(s)
            self.assertFalse(any(r[0] == "FAIL" for r in rows), rows)


class PromptLawTests(unittest.TestCase):
    def test_1d_merge_teaches_street_y1_destock_in_bear(self) -> None:
        text = (ROOT / "harness" / "agent_prompts.md").read_text(encoding="utf-8")
        self.assertIn("Street FY+1", text)
        self.assertIn("destock analog in **bear**", text)
        self.assertNotIn("4d wins 4e", text)
        self.assertNotIn("default destock/quality-reset in **base**, duration **only in bull**", text)

    def test_pair0_good_is_street_y1_destock_in_bear(self) -> None:
        text = (ROOT / "harness" / "exemplars" / "hooks_quality.md").read_text(encoding="utf-8")
        good_idx = text.find("### GOOD")
        self.assertGreater(good_idx, 0)
        good = text[good_idx : good_idx + 2200]
        self.assertIn('"applies_in": "bear_only"', good)
        self.assertIn("Street", good)

    def test_version_at_least_218(self) -> None:
        from scripts.kd_research.annuals import parse_semver

        payload = json.loads((ROOT / "harness" / "VERSION").read_text(encoding="utf-8"))
        parsed = parse_semver(payload.get("harness_version"))
        self.assertIsNotNone(parsed)
        self.assertGreaterEqual(parsed, (2, 18, 0))


if __name__ == "__main__":
    unittest.main()

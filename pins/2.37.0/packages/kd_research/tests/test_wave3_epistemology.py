"""Wave 3 epistemology gates (harness >= 2.11.0)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.epistemology import (
    check_changelog_isolation,
    check_destock_not_silent_duration,
    check_related_party_intensity,
    check_trust_guides_more,
    check_tv_share_duration,
    check_two_quarter_wc,
    check_wave3_epistemology,
)
from packages.kd_research.street_bind import check_street_bind


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj) if not isinstance(obj, str) else obj, encoding="utf-8")


def _stamp(session: Path, version: str | None) -> None:
    man: dict = {"status": "scaffolded", "orchestrator_model": "grok-4.5"}
    if version:
        man["harness_version"] = version
    _write(session / "meta" / "run_manifest.json", man)


class DestockTests(unittest.TestCase):
    def test_unresolved_destock_as_base_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.11.0")
            _write(
                s / "registry/operating_path_brief.json",
                {
                    "ticker": "X",
                    "session_date": "2026-01-01",
                    "sources": {"workers": ["a", "b", "c"]},
                    "conflicts": [
                        {
                            "id": "flatten_vs_destock",
                            "claim_a": "flatten mid-cycle",
                            "claim_b": "destock analog FY2024",
                            "status": "unresolved",
                        }
                    ],
                    "rejected_shapes": [],
                    "verify_rechecks": [{"path": "x", "value": 1}, {"path": "y", "value": 2}, {"path": "z", "value": 3}],
                },
            )
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf"},
                    "fair_value": {"base": 100, "bear": 80, "bull": 120, "decision_usefulness": "high"},
                    "assumptions": {},
                    "compute_script": "data/compute/v.py",
                    "sensitivity": {},
                    "operating_path_hooks": [
                        {"from": "conflicts.flatten", "action": "used_as:growth_path", "reason": "base is duration"}
                    ],
                },
            )
            rows = check_destock_not_silent_duration(s)
            self.assertEqual(rows[0][0], "FAIL", rows)

    def test_destock_only_in_bear_rationale_fails(self) -> None:
        """Destock mentioned on fair_value (always has key 'base') is not destock-in-base."""
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.11.0")
            _write(
                s / "registry/operating_path_brief.json",
                {
                    "ticker": "X",
                    "session_date": "2026-01-01",
                    "sources": {"workers": ["a", "b", "c"]},
                    "conflicts": [
                        {
                            "id": "flatten_vs_destock",
                            "claim_a": "flatten",
                            "claim_b": "destock",
                            "status": "unresolved",
                        }
                    ],
                    "rejected_shapes": [],
                    "verify_rechecks": [
                        {"path": "x", "value": 1},
                        {"path": "y", "value": 2},
                        {"path": "z", "value": 3},
                    ],
                },
            )
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf"},
                    "fair_value": {
                        "base": 100,
                        "bear": 80,
                        "bull": 120,
                        "decision_usefulness": "high",
                        "posture": "destock analog lives in the bear path only",
                    },
                    "assumptions": {},
                    "compute_script": "data/compute/v.py",
                    "sensitivity": {},
                    "operating_path_hooks": [
                        {
                            "from": "conflicts.flatten_vs_destock",
                            "action": "used_as:bear_only",
                            "applies_in": "bear_only",
                            "reason": "destock encoded in bear mass 0.32, not base",
                        }
                    ],
                },
            )
            _write(
                s / "registry/decision.json",
                {
                    "ticker": "X",
                    "duration": {
                        "action": "initiate",
                        "rationale": "Buying the duration story at a 46 percent MoS.",
                    },
                },
            )
            rows = check_destock_not_silent_duration(s)
            self.assertEqual(rows[0][0], "FAIL", rows)

    def test_unresolved_destock_with_pass_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.11.0")
            _write(
                s / "registry/operating_path_brief.json",
                {
                    "ticker": "X",
                    "session_date": "2026-01-01",
                    "sources": {"workers": ["a", "b", "c"]},
                    "conflicts": [
                        {
                            "id": "destock",
                            "claim_a": "destock",
                            "claim_b": "flatten",
                            "status": "unresolved",
                        }
                    ],
                    "rejected_shapes": [],
                    "verify_rechecks": [{"path": "x", "value": 1}, {"path": "y", "value": 2}, {"path": "z", "value": 3}],
                },
            )
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "fair_value": {"base": 10, "bear": 0, "bull": 30, "decision_usefulness": "low"},
                    "assumptions": {},
                    "compute_script": "x",
                    "sensitivity": {},
                    "model": {"name": "dcf"},
                },
            )
            _write(
                s / "registry/decision.json",
                {"ticker": "X", "duration": {"action": "pass", "rationale": "Unresolved destock is not a buy."}},
            )
            rows = check_destock_not_silent_duration(s)
            self.assertEqual(rows[0][0], "PASS", rows)

    def test_210_skips_wave3(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.10.0")
            rows = check_wave3_epistemology(s)
            self.assertEqual(rows[0][0], "SKIPPED")


class TvShareTests(unittest.TestCase):
    def test_high_tv_high_g_without_response_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.11.0")
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf"},
                    "fair_value": {"base": 1},
                    "assumptions": {"y8_growth": 0.08},
                    "compute_script": "x",
                    "sensitivity": {},
                    "terminal_consistency": {"tv_share_of_ev_base": 0.68, "y8_growth": 0.08},
                },
            )
            rows = check_tv_share_duration(s)
            self.assertEqual(rows[0][0], "FAIL", rows)

    def test_extend_years_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.11.0")
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf"},
                    "fair_value": {"base": 1},
                    "assumptions": {},
                    "compute_script": "x",
                    "sensitivity": {},
                    "terminal_consistency": {
                        "tv_share_of_ev_base": 0.68,
                        "y8_growth": 0.08,
                        "response": "extend_years",
                    },
                },
            )
            rows = check_tv_share_duration(s)
            self.assertEqual(rows[0][0], "PASS", rows)


class RpIntensityTests(unittest.TestCase):
    def test_low_intensity_high_rp_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.11.0")
            _write(s / "registry/market_context.json", {"primary_region": "us", "intensity": "low"})
            _write(
                s / "registry/filing_deep_dive.json",
                {
                    "footnotes": {
                        "related_party_dual_class": {
                            "excerpt": "Pepsi related-party revenue 60.2% of Q2; two board seats."
                        }
                    }
                },
            )
            rows = check_related_party_intensity(s)
            self.assertEqual(rows[0][0], "FAIL", rows)


class ChangelogTests(unittest.TestCase):
    def test_update_without_changelog_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.11.0")
            _write(
                s / "registry/research_brief.json",
                {
                    "ticker": "X",
                    "session_date": "2026-01-02",
                    "company_name": "X Inc",
                    "investment_objective": "Update the living file after the print.",
                    "must_answer_questions": ["q1 question", "q2 question", "q3 question"],
                    "peers": ["Y"],
                    "benchmarks": {"regional": "SPY", "sector": "XLY"},
                    "currency": "USD",
                    "research_depth": "standard",
                    "rationale": "update after earnings",
                    "mode": "update",
                    "prior_session_key": "2026-01-01",
                },
            )
            rows = check_changelog_isolation(s)
            self.assertEqual(rows[0][0], "FAIL", rows)

    def test_changelog_with_prior_fv_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.11.0")
            _write(
                s / "registry/research_brief.json",
                {"mode": "update", "prior_session_key": "2026-01-01", "investment_objective": "update living position"},
            )
            _write(
                s / "registry/earning_power_changelog.json",
                {"prior_fair_value": 975.0, "facts": {"nopat": 10}},
            )
            rows = check_changelog_isolation(s)
            self.assertEqual(rows[0][0], "FAIL", rows)
            self.assertIn("isolation", rows[0][1])

    def test_nested_facts_fair_value_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.11.0")
            _write(
                s / "registry/research_brief.json",
                {
                    "mode": "update",
                    "prior_session_key": "2026-01-01",
                    "investment_objective": "update living position",
                },
            )
            _write(
                s / "registry/earning_power_changelog.json",
                {"facts": {"nopat": 10, "fair_value": 975, "wacc": 0.09}},
            )
            rows = check_changelog_isolation(s)
            self.assertEqual(rows[0][0], "FAIL", rows)
            self.assertIn("isolation", rows[0][1])

    def test_facts_only_changelog_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.11.0")
            _write(
                s / "registry/research_brief.json",
                {"mode": "update", "prior_session_key": "2026-01-01", "investment_objective": "update living position"},
            )
            _write(
                s / "registry/earning_power_changelog.json",
                {
                    "facts": {
                        "nopat": {"old": 8.0, "new": 9.1, "rationale": "H1 run-rate"},
                        "share_count": {"old": 100, "new": 102},
                    }
                },
            )
            rows = check_changelog_isolation(s)
            self.assertEqual(rows[0][0], "PASS", rows)


class TrustGuidesTests(unittest.TestCase):
    def test_trust_guides_more_without_split_warns(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.11.0")
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf"},
                    "fair_value": {"base": 1},
                    "assumptions": {},
                    "compute_script": "x",
                    "sensitivity": {},
                    "filing_deep_dive_hooks": [
                        {
                            "from": "management_scorecard",
                            "action": "used_as:scenario_probabilities",
                            "reason": "hit-rate 0.94 → trust_guides_more in base",
                        }
                    ],
                },
            )
            _write(
                s / "registry/filing_deep_dive.json",
                {
                    "management_scorecard": {
                        "hit_rate": 0.941,
                        "valuation_implication": "trust_guides_more",
                    }
                },
            )
            rows = check_trust_guides_more(s)
            self.assertEqual(rows[0][0], "WARN", rows)

    def test_trust_guides_with_met_only_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.11.0")
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf"},
                    "fair_value": {"base": 1},
                    "assumptions": {},
                    "compute_script": "x",
                    "sensitivity": {},
                },
            )
            _write(
                s / "registry/filing_deep_dive.json",
                {
                    "management_scorecard": {
                        "hit_rate": 0.94,
                        "met_only_hit_rate": 0.55,
                        "valuation_implication": "trust_guides_more",
                    }
                },
            )
            rows = check_trust_guides_more(s)
            self.assertEqual(rows[0][0], "PASS", rows)


class TwoQuarterWcTests(unittest.TestCase):
    def test_two_quarter_raise_with_wc_deterioration_warns(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.11.0")
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf"},
                    "fair_value": {"base": 1},
                    "assumptions": {},
                    "compute_script": "x",
                    "sensitivity": {},
                    "overrides_applied": [
                        {
                            "rule": "two_quarter_rule",
                            "old_assumption": "Y1 growth 0.188",
                            "new_assumption": "Y1 growth 0.2078",
                            "reason": "three consecutive >20% prints",
                        }
                    ],
                },
            )
            _write(
                s / "registry/latest_quarter.json",
                {
                    "ticker": "X",
                    "fiscal_period": "2026-Q2",
                    "filing_date": "2026-08-01",
                    "currency": "USD",
                    "sources": ["10-Q"],
                    "cash_flow": {"fcf": -0.6},
                    "balance_sheet": {"accounts_receivable": 8.4},
                    "evidence_log": [
                        {
                            "metric": "inventory",
                            "observation": "inventories +79.5% YoY",
                            "materiality": "high",
                            "suggested_rule": "two_quarter_rule",
                        }
                    ],
                },
            )
            rows = check_two_quarter_wc(s)
            self.assertEqual(rows[0][0], "WARN", rows)


class StreetSofteningTests(unittest.TestCase):
    def test_large_gap_without_response_warns_not_fail(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.7.0")
            _write(
                s / "registry/street_estimates.json",
                {
                    "ticker": "X",
                    "session_date": "2026-01-01",
                    "source": "yfinance",
                    "fiscal_convention": "company_fy",
                    "years": [
                        {"label": "0y", "revenue": 100.0},
                        {"label": "+1y", "revenue": 174.0},
                    ],
                },
            )
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf"},
                    "fair_value": {"base": 1},
                    "assumptions": {},
                    "compute_script": "x",
                    "sensitivity": {},
                    "street_bind": {
                        "guide": 154.0,
                        "street": 174.0,
                        "base": 100.0,
                        "delta_pct": (100.0 - 174.0) / 174.0,
                        "independent_construction": {
                            "rationale": "FY+1 base from company AI floor plus software run-rate plus non-AI sequential, not consensus mean."
                        },
                    },
                    "street_hooks": [
                        {
                            "from": "street_estimates.years[+1y].revenue",
                            "action": "used_as:calibration_check",
                            "reason": "Independent stack vs Street FY+1 used as calibration after the path was built.",
                        }
                    ],
                    "conservatism_dials": [
                        {"key": "volume_vs_guide", "applies_in": "none"},
                        {"key": "gaap_om_vs_guide", "applies_in": "none"},
                        {"key": "sbc_in_fcff", "applies_in": "none"},
                        {"key": "wacc_vs_buildup", "applies_in": "none"},
                    ],
                },
            )
            rows = check_street_bind(s)
            fails = [r for r in rows if r[0] == "FAIL" and "divergence" in r[1] or (r[0] == "FAIL" and r[1].endswith("response"))]
            warns = [r for r in rows if r[0] == "WARN" and "20%" in r[2] or (r[0] == "WARN" and "delta" in r[1])]
            self.assertFalse(fails, rows)
            self.assertTrue(any(r[0] == "WARN" for r in rows), rows)


if __name__ == "__main__":
    unittest.main()

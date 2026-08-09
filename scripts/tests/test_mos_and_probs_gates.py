"""Unit tests for MoS unit and scenario_probability key gates (synthetic fixtures)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.kd_research.gates import (  # noqa: E402
    check_mos_units,
    check_scenario_probability_keys,
    extract_scenario_prob_mass,
)


class ScenarioProbabilityKeysTest(unittest.TestCase):
    def test_clean_bare_floats_pass(self) -> None:
        rows = check_scenario_probability_keys({"bear": 0.3, "base": 0.45, "bull": 0.25})
        statuses = {r[1]: r[0] for r in rows}
        self.assertEqual(statuses["scenario_probabilities_sum"], "PASS")
        self.assertEqual(statuses["scenario_probabilities_keys"], "PASS")

    def test_nested_value_objects_sum(self) -> None:
        probs = {
            "bear": {"value": 0.2, "rationale": "x", "basis": "y"},
            "base": {"value": 0.55, "rationale": "x", "basis": "y"},
            "bull": {"value": 0.25, "rationale": "x", "basis": "y"},
        }
        total, issues = extract_scenario_prob_mass(probs)
        self.assertEqual(issues, [])
        self.assertAlmostEqual(total or 0.0, 1.0, places=5)

    def test_extra_meta_keys_warn_not_fail_sum(self) -> None:
        """META-style _sum must not double-count; extra keys WARN."""
        probs = {"bear": 0.3, "base": 0.45, "bull": 0.25, "_sum": 1.0, "_note": "x"}
        # _note is string — still "extra key"
        rows = check_scenario_probability_keys(probs, extra_key_severity="WARN")
        by_id = {r[1]: r for r in rows}
        self.assertEqual(by_id["scenario_probabilities_sum"][0], "PASS")
        self.assertEqual(by_id["scenario_probabilities_keys"][0], "WARN")
        self.assertIn("_sum", by_id["scenario_probabilities_keys"][2])

    def test_sum_ignores_meta_numeric_keys(self) -> None:
        # Old bug: sum all numerics → 2.0 when _sum=1.0
        probs = {"bear": 0.3, "base": 0.45, "bull": 0.25, "_sum": 1.0}
        total, _ = extract_scenario_prob_mass(probs)
        self.assertAlmostEqual(total or 0.0, 1.0, places=5)

    def test_string_value_under_leg_fails(self) -> None:
        probs = {"bear": "high", "base": 0.5, "bull": 0.5}
        rows = check_scenario_probability_keys(probs)
        self.assertTrue(any(r[0] == "FAIL" for r in rows))

    def test_missing_probs_fail(self) -> None:
        rows = check_scenario_probability_keys(None)
        self.assertEqual(rows[0][0], "FAIL")


class MosUnitsTest(unittest.TestCase):
    def test_dual_consistent_pass(self) -> None:
        rows = check_mos_units({"margin_of_safety": 0.292, "margin_of_safety_pct": 29.2})
        self.assertEqual(rows[0][0], "PASS")
        self.assertEqual(rows[0][1], "mos_units_dual")

    def test_dual_inconsistent_fail(self) -> None:
        rows = check_mos_units({"margin_of_safety": 0.292, "margin_of_safety_pct": 0.292})
        self.assertEqual(rows[0][0], "FAIL")
        self.assertIn("100*fraction", rows[0][2])

    def test_fraction_in_pct_field_warn(self) -> None:
        rows = check_mos_units({"margin_of_safety_pct": 0.0349})
        self.assertEqual(rows[0][0], "WARN")
        self.assertEqual(rows[0][1], "mos_units_pct_field")

    def test_true_percent_no_warn(self) -> None:
        rows = check_mos_units({"margin_of_safety_pct": 36.9})
        self.assertEqual(rows[0][0], "PASS")

    def test_negative_percent_pass(self) -> None:
        rows = check_mos_units({"margin_of_safety_pct": -29.9})
        self.assertEqual(rows[0][0], "PASS")

    def test_legacy_missing_both_skipped(self) -> None:
        rows = check_mos_units({"base": 100.0, "bear": 70.0, "bull": 130.0})
        self.assertEqual(rows[0][0], "SKIPPED")

    def test_fraction_only_warn(self) -> None:
        rows = check_mos_units({"margin_of_safety": -0.299})
        self.assertEqual(rows[0][0], "WARN")
        self.assertEqual(rows[0][1], "mos_units_fraction_only")


if __name__ == "__main__":
    unittest.main()

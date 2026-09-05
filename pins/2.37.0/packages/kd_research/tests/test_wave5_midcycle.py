"""Wave 5 mid-cycle construction (harness >= 2.13.0)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.paths import PROJECT_ROOT as ROOT

from packages.kd_research.roic_identity import (
    check_roic_identity,
)
from packages.kd_research.tests.test_roic_identity import (
    _identity,
    _stamp,
    _vm,
    _write,
)


def _windowed_franchise() -> dict:
    return _identity(
        nopat={"value": 1100.0, "definition": "windowed", "rationale": "avg", "basis": "script"},
        mid_cycle_roic={"value": 0.11, "rationale": "1100/10000", "basis": "script"},
        spread_mid_cycle=0.02,
        quality_bucket="above_wacc",
        cheap_claim={"class": "franchise_mos", "rationale": "Windowed ROIC above WACC."},
        reinvestment_identity={
            "g": 0.015,
            "implied_reinvestment_if_roc_eq_wacc": 0.167,
            "modeled_reinvestment_of_nopat": 0.14,
            "mismatch": False,
        },
        gate={"response": "reinvestment_in_engine", "rationale": "Reinvestment in the engine."},
        mid_cycle_construction={
            "window_kind": "multi_year_avg",
            "years_used": [2018, 2019, 2020, 2021, 2022, 2023],
            "print_vs_midcycle": "FY2024 print OM is 18%; mid-cycle NOPAT is the 2018-2023 average.",
        },
    )


class PromptLawTests(unittest.TestCase):
    def test_version_at_least_213(self) -> None:
        from packages.kd_research.annuals import parse_semver

        payload = json.loads((ROOT / "harness" / "VERSION").read_text(encoding="utf-8"))
        parsed = parse_semver(payload.get("harness_version"))
        self.assertIsNotNone(parsed)
        self.assertGreaterEqual(parsed, (2, 13, 0))

    def test_agent5_requires_construction(self) -> None:
        text = (ROOT / "harness" / "agent_prompts.md").read_text(encoding="utf-8")
        self.assertIn("mid_cycle_construction", text)
        self.assertIn("peak SOI cannot license", text)

    def test_pair8_good_is_not_peak_as_midcycle(self) -> None:
        text = (ROOT / "harness" / "exemplars" / "valuation_decision_quality.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("## Pair 8", text)
        self.assertIn('"window_kind": "multi_year_avg"', text)
        self.assertIn('"window_kind": "last_year"', text)


class MidcycleGateTests(unittest.TestCase):
    def _sess(self, vm: dict, version: str = "2.13.0") -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        _stamp(s, version)
        _write(s / "data/valuation_model.json", vm)
        return s

    def test_212_omits_construction_passes(self) -> None:
        s = self._sess(_vm(_identity()), version="2.12.0")
        rows = check_roic_identity(s)
        fails = [r for r in rows if r[0] == "FAIL"]
        self.assertEqual(fails, [], fails)

    def test_213_omits_construction_fails(self) -> None:
        s = self._sess(_vm(_identity()), version="2.13.0")
        rows = check_roic_identity(s)
        self.assertTrue(any(r[0] == "FAIL" and r[1] == "mid_cycle_construction" for r in rows), rows)

    def test_applies_false_no_construction_ok(self) -> None:
        ident = {
            "applies": False,
            "not_applicable_reason": "Bank: industrial invested capital does not apply; use roe vs ke analog.",
            "native_analog": "roe_vs_ke",
        }
        s = self._sess(_vm(ident), version="2.13.0")
        rows = check_roic_identity(s)
        fails = [r for r in rows if r[0] == "FAIL"]
        self.assertEqual(fails, [], fails)

    def test_trough_ttc_with_window_ok(self) -> None:
        ident = _identity(
            mid_cycle_construction={
                "window_kind": "ttc_cycle",
                "years_used": {"start": 2016, "end": 2024},
                "print_vs_midcycle": "TTC ROIC 3% at trough; mid-cycle is the cycle average not this year.",
            }
        )
        s = self._sess(_vm(ident))
        rows = check_roic_identity(s)
        fails = [r for r in rows if r[0] == "FAIL"]
        self.assertEqual(fails, [], fails)

    def test_last_year_above_wacc_fails(self) -> None:
        ident = _identity(
            nopat={"value": 1800.0, "definition": "x", "rationale": "peak", "basis": "x"},
            mid_cycle_roic={"value": 0.18, "rationale": "1800/10000", "basis": "x"},
            spread_mid_cycle=0.09,
            quality_bucket="above_wacc",
            cheap_claim={"class": "franchise_mos", "rationale": "Peak year looks cheap."},
            reinvestment_identity={
                "g": 0.015,
                "implied_reinvestment_if_roc_eq_wacc": 0.167,
                "modeled_reinvestment_of_nopat": 0.08,
                "mismatch": False,
            },
            gate={"response": "reinvestment_in_engine", "rationale": "Reinvestment in FCFF."},
            mid_cycle_construction={
                "window_kind": "last_year",
                "years_used": [2024],
                "print_vs_midcycle": "Used FY2024 SOI as mid-cycle because it is latest.",
            },
        )
        s = self._sess(_vm(ident))
        rows = check_roic_identity(s)
        self.assertTrue(
            any(r[0] == "FAIL" and r[1] == "mid_cycle_construction.license" for r in rows),
            rows,
        )

    def test_last_year_approx_book_ok(self) -> None:
        ident = _identity(
            mid_cycle_construction={
                "window_kind": "last_year",
                "years_used": [2024],
                "print_vs_midcycle": "Only one clean year; equity near book not a franchise.",
            }
        )
        s = self._sess(_vm(ident))
        rows = check_roic_identity(s)
        fails = [r for r in rows if r[0] == "FAIL"]
        self.assertEqual(fails, [], fails)

    def test_start_end_span_franchise_ok(self) -> None:
        ident = _windowed_franchise()
        ident["mid_cycle_construction"] = {
            "window_kind": "ttc_cycle",
            "years_used": {"start": 2019, "end": 2024},
            "print_vs_midcycle": "Six-year inclusive span; mid-cycle not the peak print.",
        }
        s = self._sess(_vm(ident))
        rows = check_roic_identity(s)
        fails = [r for r in rows if r[0] == "FAIL"]
        self.assertEqual(fails, [], fails)

    def test_multi_year_avg_one_year_above_wacc_fails(self) -> None:
        ident = _windowed_franchise()
        ident["mid_cycle_construction"] = {
            "window_kind": "multi_year_avg",
            "years_used": [2024],
            "print_vs_midcycle": "Called it an average but only one year is in the window.",
        }
        s = self._sess(_vm(ident))
        rows = check_roic_identity(s)
        self.assertTrue(
            any(r[0] == "FAIL" and r[1] == "mid_cycle_construction.license" for r in rows),
            rows,
        )

    def test_windowed_franchise_ok(self) -> None:
        s = self._sess(_vm(_windowed_franchise()))
        rows = check_roic_identity(s)
        fails = [r for r in rows if r[0] == "FAIL"]
        self.assertEqual(fails, [], fails)


if __name__ == "__main__":
    unittest.main()

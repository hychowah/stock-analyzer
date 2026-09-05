"""Harness 2.28.0: Street is default Y1; independent_y1 needs a resolved evidence gate."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.epistemology import (
    check_destock_default,
    check_destock_not_silent_duration,
)
from packages.kd_research.street_bind import check_street_bind
from packages.kd_research.tests.test_wave10_street_y1 import (
    BASE_HOOK,
    BEAR_HOOK,
    _brief,
    _dials,
    _stamp,
    _street,
    _vm,
    _write,
)


def _brief_destock_print() -> dict:
    brief = _brief("unresolved")
    brief["analog_class"] = "inventory_channel"
    brief["current_print_is_destock"] = True
    return brief


class GatedY1BandTests(unittest.TestCase):
    def test_228_street_baseline_inside_band_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.28.0")
            _write(s / "registry/street_estimates.json", _street())
            vm = _vm(base=254.2, street=254.2, destock_hook=BEAR_HOOK, response="street_baseline")
            _write(s / "data/valuation_model.json", vm)
            rows = check_street_bind(s)
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertEqual(fails, [], fails)

    def test_228_street_baseline_8pct_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.28.0")
            _write(s / "registry/street_estimates.json", _street())
            vm = _vm(base=236.0, street=254.2, destock_hook=BEAR_HOOK, response="street_baseline")
            _write(s / "data/valuation_model.json", vm)
            rows = check_street_bind(s)
            self.assertTrue(any(r[0] == "FAIL" and r[1] == "street_bind.y1_band" for r in rows), rows)

    def test_228_keep_independent_still_illegal(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.28.0")
            _write(s / "registry/street_estimates.json", _street())
            vm = _vm(base=236.0, street=254.2, destock_hook=BASE_HOOK)
            vm["street_bind"]["response"] = "keep_independent_vs_street"
            _write(s / "data/valuation_model.json", vm)
            rows = check_street_bind(s)
            self.assertTrue(any(r[0] == "FAIL" and r[1] == "street_bind.response" for r in rows), rows)

    def test_228_independent_y1_destock_print_12pct_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.28.0")
            _write(s / "registry/street_estimates.json", _street())
            _write(s / "registry/operating_path_brief.json", _brief_destock_print())
            vm = _vm(base=223.7, street=254.2, destock_hook=BASE_HOOK, response="independent_y1")
            vm["street_bind"]["independence_gate"] = "destock_this_print"
            vm["street_bind"]["y1_construction"] = {
                "rationale": "This print matches the inventory-channel destock analog; Y1 starts from run-rate not Street duration."
            }
            vm["street_hooks"] = [
                {
                    "from": "street_estimates.years[+1y].revenue",
                    "action": "used_as:calibration_check",
                    "reason": "Street FY+1 is the calibration; destock_this_print licenses independent Y1.",
                }
            ]
            _write(s / "data/valuation_model.json", vm)
            rows = check_street_bind(s)
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertEqual(fails, [], fails)
            self.assertTrue(any(r[0] == "WARN" and r[1] == "street_bind.y1_band" for r in rows), rows)

    def test_228_independent_y1_without_gate_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.28.0")
            _write(s / "registry/street_estimates.json", _street())
            vm = _vm(base=223.7, street=254.2, destock_hook=BASE_HOOK, response="independent_y1")
            _write(s / "data/valuation_model.json", vm)
            rows = check_street_bind(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "street_bind.independence_gate" for r in rows),
                rows,
            )

    def test_228_ttc_midcycle_is_not_a_legal_gate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.28.0")
            _write(s / "registry/street_estimates.json", _street())
            vm = _vm(base=223.7, street=254.2, destock_hook=BEAR_HOOK, response="independent_y1")
            vm["street_bind"]["independence_gate"] = "ttc_midcycle"
            _write(s / "data/valuation_model.json", vm)
            rows = check_street_bind(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "street_bind.independence_gate" for r in rows),
                rows,
            )

    def test_228_definition_mismatch_requires_class_pair(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.28.0")
            _write(s / "registry/street_estimates.json", _street())
            vm = _vm(base=223.7, street=254.2, destock_hook=BEAR_HOOK, response="independent_y1")
            vm["street_bind"]["independence_gate"] = "definition_mismatch"
            _write(s / "data/valuation_model.json", vm)
            rows = check_street_bind(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "street_bind.independence_gate" for r in rows),
                rows,
            )

    def test_228_native_kpi_banking_skips_revenue_band(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.28.0")
            _write(s / "registry/street_estimates.json", _street())
            _write(
                s / "registry/sector_config.json",
                {"primary_sector": "banking", "confidence": 0.9, "module_file": "sector_banking.md"},
            )
            vm = _vm(base=216.0, street=254.2, destock_hook=BEAR_HOOK, response="independent_y1")
            vm["street_bind"]["independence_gate"] = "native_kpi"
            vm["street_bind"]["y1_construction"] = {
                "rationale": "Primary sector is banking; Y1 binds NII not vendor total revenue."
            }
            vm["street_bind"]["divergence_rationale"] = (
                "Vendor total revenue is a different object than NII; native KPI bind skips the revenue 5% band."
            )
            vm["street_hooks"] = [
                {
                    "from": "street_estimates.years[+1y].revenue",
                    "action": "rejected",
                    "reason": "Revenue consensus is the wrong object for a bank NII model.",
                }
            ]
            _write(s / "data/valuation_model.json", vm)
            rows = check_street_bind(s)
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertEqual(fails, [], fails)

    def test_228_average_destock_street_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.28.0")
            _write(s / "registry/street_estimates.json", _street())
            _write(s / "registry/operating_path_brief.json", _brief_destock_print())
            vm = _vm(base=223.7, street=254.2, destock_hook=BASE_HOOK, response="independent_y1")
            vm["street_bind"]["independence_gate"] = "destock_this_print"
            vm["street_bind"]["y1_construction"] = {
                "rationale": "Average destock analog with Street consensus into one CAGR called base."
            }
            vm["street_hooks"] = [
                {
                    "from": "street_estimates.years[+1y].revenue",
                    "action": "used_as:calibration_check",
                    "reason": "Calibration only.",
                }
            ]
            _write(s / "data/valuation_model.json", vm)
            rows = check_street_bind(s)
            self.assertTrue(any(r[0] == "FAIL" and r[1] == "street_bind.average" for r in rows), rows)

    def test_228_rehydrate_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.28.0")
            _write(s / "registry/street_estimates.json", _street())
            vm = _vm(base=254.2, street=254.2, destock_hook=BEAR_HOOK, response="street_baseline")
            _write(s / "data/valuation_model.json", vm)
            _write(s / "data/compute/valuation_result.json", {"y1_revenue": 200.0})
            rows = check_street_bind(s)
            self.assertTrue(any(r[0] == "FAIL" and r[1] == "street_bind.rehydrate" for r in rows), rows)

    def test_218_stamp_still_fails_8pct(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.18.0")
            _write(s / "registry/street_estimates.json", _street())
            vm = _vm(base=236.0, street=254.2, destock_hook=BEAR_HOOK, response="street_baseline")
            _write(s / "data/valuation_model.json", vm)
            rows = check_street_bind(s)
            self.assertTrue(any(r[0] == "FAIL" and r[1] == "street_bind.y1_band" for r in rows), rows)


class GatedDestockTests(unittest.TestCase):
    def test_228_destock_in_base_with_this_print_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.28.0")
            _write(s / "registry/street_estimates.json", _street())
            _write(s / "registry/operating_path_brief.json", _brief_destock_print())
            vm = _vm(base=223.7, street=254.2, destock_hook=BASE_HOOK, response="independent_y1")
            vm["street_bind"]["independence_gate"] = "destock_this_print"
            vm["street_bind"]["y1_construction"] = {
                "rationale": "This print is destock; analog years set base Y1 off Street duration."
            }
            vm["street_hooks"] = [
                {
                    "from": "street_estimates.years[+1y].revenue",
                    "action": "used_as:calibration_check",
                    "reason": "Street is calibration under destock_this_print.",
                }
            ]
            _write(s / "data/valuation_model.json", vm)
            _write(
                s / "registry/decision.json",
                {"ticker": "X", "duration": {"action": "pass", "rationale": "Destock print; cone first."}},
            )
            w3 = check_destock_not_silent_duration(s)
            w4 = check_destock_default(s)
            self.assertEqual(w3[0][0], "PASS", w3)
            self.assertEqual(w4[0][0], "PASS", w4)

    def test_228_destock_in_base_without_this_print_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.28.0")
            _write(s / "registry/street_estimates.json", _street())
            _write(s / "registry/operating_path_brief.json", _brief("unresolved"))
            vm = _vm(base=254.2, street=254.2, destock_hook=BASE_HOOK, response="street_baseline")
            _write(s / "data/valuation_model.json", vm)
            _write(
                s / "registry/decision.json",
                {"ticker": "X", "duration": {"action": "initiate", "rationale": "Street Y1 duration in base."}},
            )
            w3 = check_destock_not_silent_duration(s)
            w4 = check_destock_default(s)
            self.assertEqual(w3[0][0], "FAIL", w3)
            self.assertEqual(w4[0][0], "FAIL", w4)

    def test_218_destock_in_base_still_fails_even_if_print_matches(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.18.0")
            _write(s / "registry/street_estimates.json", _street())
            _write(s / "registry/operating_path_brief.json", _brief_destock_print())
            _write(s / "data/valuation_model.json", _vm(base=254.2, street=254.2, destock_hook=BASE_HOOK))
            _write(
                s / "registry/decision.json",
                {"ticker": "X", "duration": {"action": "initiate", "rationale": "Destock in base."}},
            )
            w4 = check_destock_default(s)
            self.assertEqual(w4[0][0], "FAIL", w4)


if __name__ == "__main__":
    unittest.main()

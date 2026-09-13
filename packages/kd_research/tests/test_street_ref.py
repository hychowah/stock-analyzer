"""Harness 3.0.1: Street is the default Y1 forecast; independent_y1 needs a named gate."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.street_bind import check_street_bind
from packages.kd_research.tests.test_wave10_street_y1 import (
    BASE_HOOK,
    BEAR_HOOK,
    _stamp,
    _street,
    _vm,
    _write,
)


def _indep_vm(*, base: float = 223.7, street: float = 254.2, gate: str | None = None) -> dict:
    vm = _vm(base=base, street=street, destock_hook=BASE_HOOK, response="independent_y1")
    vm["street_bind"]["y1_construction"] = {
        "rationale": "Independent Y1 from company evidence; Street is the calibration prior."
    }
    vm["street_hooks"] = [
        {
            "from": "street_estimates.years[+1y].revenue",
            "action": "used_as:calibration_check",
            "reason": "Street FY+1 is the forecast reference; Y1 is independent under a named gate.",
        }
    ]
    if gate:
        vm["street_bind"]["independence_gate"] = gate
    return vm


class StreetRefTests(unittest.TestCase):
    def test_301_independent_without_gate_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.0.1")
            _write(s / "registry/street_estimates.json", _street())
            _write(s / "data/valuation_model.json", _indep_vm())
            rows = check_street_bind(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "street_bind.independence_gate" for r in rows),
                rows,
            )

    def test_300_independent_without_gate_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.0.0")
            _write(s / "registry/street_estimates.json", _street())
            _write(s / "data/valuation_model.json", _indep_vm())
            rows = check_street_bind(s)
            self.assertFalse(
                any(r[0] == "FAIL" and r[1] == "street_bind.independence_gate" for r in rows),
                rows,
            )

    def test_301_street_baseline_inside_band_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.0.1")
            _write(s / "registry/street_estimates.json", _street())
            vm = _vm(
                base=254.2, street=254.2, destock_hook=BEAR_HOOK, response="street_baseline"
            )
            _write(s / "data/valuation_model.json", vm)
            rows = check_street_bind(s)
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertEqual(fails, [], fails)

    def test_301_story_fail_requires_will_own_false(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.0.1")
            _write(s / "registry/street_estimates.json", _street())
            vm = _indep_vm(gate="story_fail")
            _write(s / "data/valuation_model.json", vm)
            _write(
                s / "registry/narrative_bind.json",
                {
                    "ticker": "X",
                    "status": "locked",
                    "street_restory": {
                        "implied_story": "Street implies duration ads growth we will not own as base.",
                    },
                },
            )
            rows = check_street_bind(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "street_bind.independence_gate" for r in rows),
                rows,
            )
            _write(
                s / "registry/narrative_bind.json",
                {
                    "ticker": "X",
                    "status": "locked",
                    "street_restory": {
                        "will_own": False,
                        "implied_story": "Street implies duration ads growth we will not own as base.",
                    },
                },
            )
            rows2 = check_street_bind(s)
            self.assertFalse(
                any(r[0] == "FAIL" and r[1] == "street_bind.independence_gate" for r in rows2),
                rows2,
            )

    def test_300_story_fail_rationale_still_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.0.0")
            _write(s / "registry/street_estimates.json", _street())
            vm = _indep_vm(gate="story_fail")
            vm["street_bind"]["divergence_rationale"] = (
                "Street implies a duration ads story this print's destock analog rejects."
            )
            _write(s / "data/valuation_model.json", vm)
            rows = check_street_bind(s)
            self.assertFalse(
                any(r[0] == "FAIL" and r[1] == "street_bind.independence_gate" for r in rows),
                rows,
            )

    def test_301_ttc_midcycle_accepts_cyclical_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.0.1")
            _write(s / "registry/street_estimates.json", _street())
            _write(s / "registry/sector_config.json", {"primary_sector": "standard"})
            _write(
                s / "registry/narrative_bind.json",
                {
                    "ticker": "X",
                    "status": "locked",
                    "overlays": ["cyclical"],
                },
            )
            vm = _indep_vm(gate="ttc_midcycle")
            _write(s / "data/valuation_model.json", vm)
            rows = check_street_bind(s)
            self.assertFalse(
                any(r[0] == "FAIL" and r[1] == "street_bind.independence_gate" for r in rows),
                rows,
            )


if __name__ == "__main__":
    unittest.main()

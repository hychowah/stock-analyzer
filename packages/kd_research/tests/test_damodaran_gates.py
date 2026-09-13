"""v3 Damodaran catalog identities."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.damodaran_gates import check_damodaran_v3


def _stamp(session: Path, version: str) -> None:
    (session / "meta").mkdir(parents=True, exist_ok=True)
    (session / "meta" / "run_manifest.json").write_text(
        json.dumps({"harness_version": version, "ticker": "X", "session_date": "2026-01-01"})
        + "\n",
        encoding="utf-8",
    )


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


class DamodaranGateTests(unittest.TestCase):
    def test_skipped_on_244(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.44.0")
            _write(s / "data/valuation_model.json", {"ticker": "X", "fair_value": {"base": 1, "bear": 1, "bull": 1}})
            rows = check_damodaran_v3(s)
            self.assertTrue(any(r[0] == "SKIPPED" for r in rows), rows)

    def test_narrative_locked_required(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.0.0")
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf", "rationale": "mature operating fcff model"},
                    "fair_value": {"base": 10, "bear": 8, "bull": 12},
                },
            )
            rows = check_damodaran_v3(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "damodaran.narrative_locked" for r in rows),
                rows,
            )
            _write(s / "registry/narrative_bind.json", {"ticker": "X", "status": "locked"})
            rows2 = check_damodaran_v3(s)
            self.assertFalse(
                any(r[0] == "FAIL" and r[1] == "damodaran.narrative_locked" for r in rows2),
                rows2,
            )

    def test_bank_engine_rejects_industrial_wacc(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.0.0")
            _write(s / "registry/narrative_bind.json", {"ticker": "X", "status": "locked"})
            _write(s / "registry/sector_config.json", {"primary_sector": "banking"})
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf", "rationale": "oops fcff bank"},
                    "fair_value": {"base": 10, "bear": 8, "bull": 12},
                    "wacc_buildup": {"applies": True, "wacc": 0.09},
                },
            )
            rows = check_damodaran_v3(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "damodaran.bank_engine" for r in rows),
                rows,
            )

    def test_exit_multiple_tv_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.0.0")
            _write(s / "registry/narrative_bind.json", {"ticker": "X", "status": "locked"})
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf", "rationale": "gordon then exit"},
                    "fair_value": {"base": 10, "bear": 8, "bull": 12},
                    "terminal_consistency": {"method": "exit_multiple"},
                },
            )
            rows = check_damodaran_v3(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "damodaran.tv_method" for r in rows),
                rows,
            )

    def test_truncation_writes_base(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.0.0")
            _write(s / "registry/narrative_bind.json", {"ticker": "X", "status": "locked"})
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf", "rationale": "young with p_fail"},
                    "fair_value": {"base": 10, "bear": 4, "bull": 12},
                    "truncation": {
                        "material": True,
                        "p": 0.4,
                        "going_concern_upper_bound": 10,
                        "failure_payoff": 1,
                    },
                },
            )
            rows = check_damodaran_v3(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "damodaran.truncation_base" for r in rows),
                rows,
            )
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf", "rationale": "young with p_fail"},
                    "fair_value": {"base": 6.4, "bear": 4, "bull": 12},
                    "truncation": {
                        "material": True,
                        "p": 0.4,
                        "going_concern_upper_bound": 10,
                        "failure_payoff": 1,
                    },
                },
            )
            rows2 = check_damodaran_v3(s)
            self.assertFalse(
                any(r[0] == "FAIL" and r[1] == "damodaran.truncation_base" for r in rows2),
                rows2,
            )

    def test_301_omit_tv_still_skips(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.0.1")
            _write(s / "registry/narrative_bind.json", {"ticker": "X", "status": "locked"})
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf", "rationale": "omit tv"},
                    "fair_value": {"base": 10, "bear": 8, "bull": 12},
                },
            )
            rows = check_damodaran_v3(s)
            self.assertFalse(
                any(r[0] == "FAIL" and r[1] == "damodaran.tv_method" for r in rows),
                rows,
            )
            self.assertFalse(
                any(r[0] == "FAIL" and r[1] == "damodaran.iv_playbook" for r in rows),
                rows,
            )

    def test_31_omit_tv_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.1.0")
            _write(
                s / "registry/narrative_bind.json",
                {"ticker": "X", "status": "locked", "iv_playbook": "mature_operating"},
            )
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf", "rationale": "omit tv"},
                    "fair_value": {"base": 10, "bear": 8, "bull": 12},
                },
            )
            rows = check_damodaran_v3(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "damodaran.tv_method" for r in rows),
                rows,
            )

    def test_31_exit_multiple_space_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.1.0")
            _write(
                s / "registry/narrative_bind.json",
                {"ticker": "X", "status": "locked", "iv_playbook": "mature_operating"},
            )
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf", "rationale": "exit tv"},
                    "fair_value": {"base": 10, "bear": 8, "bull": 12},
                    "terminal_consistency": {"method": "exit multiple"},
                },
            )
            rows = check_damodaran_v3(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "damodaran.tv_method" for r in rows),
                rows,
            )

    def test_31_gordon_playbook_passes_tv(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.1.0")
            _write(
                s / "registry/narrative_bind.json",
                {"ticker": "X", "status": "locked", "iv_playbook": "mature_operating"},
            )
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf", "rationale": "operating fcff"},
                    "fair_value": {"base": 10, "bear": 8, "bull": 12},
                    "terminal_consistency": {
                        "method": "gordon",
                        "g_n": 0.03,
                        "reinvestment_rate": 0.5,
                        "roc_n": 0.06,
                    },
                },
            )
            rows = check_damodaran_v3(s)
            self.assertFalse(any(r[0] == "FAIL" for r in rows), rows)

    def test_31_playbook_required(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.1.0")
            _write(s / "registry/narrative_bind.json", {"ticker": "X", "status": "locked"})
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf", "rationale": "no playbook"},
                    "fair_value": {"base": 10, "bear": 8, "bull": 12},
                    "terminal_consistency": {"method": "gordon"},
                },
            )
            rows = check_damodaran_v3(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "damodaran.iv_playbook" for r in rows),
                rows,
            )

    def test_31_bank_sector_requires_financial_playbook(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.1.0")
            _write(
                s / "registry/narrative_bind.json",
                {"ticker": "X", "status": "locked", "iv_playbook": "mature_operating"},
            )
            _write(s / "registry/sector_config.json", {"primary_sector": "banking"})
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf", "rationale": "wrong playbook"},
                    "fair_value": {"base": 10, "bear": 8, "bull": 12},
                    "terminal_consistency": {"method": "excess_return"},
                    "wacc_buildup": {"applies": False},
                },
            )
            rows = check_damodaran_v3(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "damodaran.iv_playbook" for r in rows),
                rows,
            )

    def test_31_broker_playbook_rejects_fcff(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.1.0")
            _write(
                s / "registry/narrative_bind.json",
                {"ticker": "X", "status": "locked", "iv_playbook": "financial_service"},
            )
            _write(s / "registry/sector_config.json", {"primary_sector": "standard"})
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "fcff", "rationale": "broker industrial"},
                    "fair_value": {"base": 10, "bear": 8, "bull": 12},
                    "terminal_consistency": {"method": "gordon"},
                    "wacc_buildup": {"applies": False},
                },
            )
            rows = check_damodaran_v3(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "damodaran.bank_engine" for r in rows),
                rows,
            )

    def test_31_reit_nav_model_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.1.0")
            _write(
                s / "registry/narrative_bind.json",
                {"ticker": "X", "status": "locked", "iv_playbook": "real_estate"},
            )
            _write(s / "registry/sector_config.json", {"primary_sector": "reit"})
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "nav", "rationale": "NAV primary"},
                    "fair_value": {"base": 10, "bear": 8, "bull": 12},
                    "terminal_consistency": {"method": "gordon"},
                    "wacc_buildup": {"applies": True, "wacc": 0.07},
                },
            )
            rows = check_damodaran_v3(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "damodaran.reit_engine" for r in rows),
                rows,
            )

    def test_31_reit_wacc_skip_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.1.0")
            _write(
                s / "registry/narrative_bind.json",
                {"ticker": "X", "status": "locked", "iv_playbook": "real_estate"},
            )
            _write(s / "registry/sector_config.json", {"primary_sector": "reit"})
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf", "rationale": "after-tax dcf"},
                    "fair_value": {"base": 10, "bear": 8, "bull": 12},
                    "terminal_consistency": {"method": "gordon"},
                    "wacc_buildup": {
                        "applies": False,
                        "not_applicable_reason": "REIT NAV/AFFO skip " + "x" * 40,
                    },
                },
            )
            rows = check_damodaran_v3(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "damodaran.reit_engine" for r in rows),
                rows,
            )

    def test_31_pricing_used_as_value_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.1.0")
            _write(
                s / "registry/narrative_bind.json",
                {"ticker": "X", "status": "locked", "iv_playbook": "mature_operating"},
            )
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf", "rationale": "dcf name but pricing as value"},
                    "fair_value": {"base": 10, "bear": 8, "bull": 12},
                    "terminal_consistency": {"method": "gordon"},
                    "pricing": {"used_as": "fair_value", "method": "nav"},
                },
            )
            rows = check_damodaran_v3(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "damodaran.price_as_value" for r in rows),
                rows,
            )

    def test_31_distressed_is_overlay_not_playbook(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.1.0")
            _write(
                s / "registry/narrative_bind.json",
                {"ticker": "X", "status": "locked", "iv_playbook": "distressed"},
            )
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf", "rationale": "distress as primary"},
                    "fair_value": {"base": 10, "bear": 8, "bull": 12},
                    "terminal_consistency": {"method": "gordon"},
                },
            )
            rows = check_damodaran_v3(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "damodaran.iv_playbook" for r in rows),
                rows,
            )

    def test_31_price_model_name_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.1.0")
            _write(
                s / "registry/narrative_bind.json",
                {"ticker": "X", "status": "locked", "iv_playbook": "young_startup"},
            )
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "arr_multiple", "rationale": "ARR as value"},
                    "fair_value": {"base": 10, "bear": 8, "bull": 12},
                    "terminal_consistency": {"method": "gordon"},
                },
            )
            rows = check_damodaran_v3(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "damodaran.price_as_value" for r in rows),
                rows,
            )


if __name__ == "__main__":
    unittest.main()

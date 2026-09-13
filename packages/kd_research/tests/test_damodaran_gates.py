"""v3 Damodaran catalog identities."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.damodaran_gates import check_damodaran_v3
from packages.kd_research.paths import PROJECT_ROOT as ROOT


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

    def _full_narrative(self) -> dict:
        return {
            "ticker": "X",
            "status": "locked",
            "iv_playbook": "mature_operating",
            "story": {"paragraph": "Scale advantage in a stable market drives steady cash flows."},
            "map": {"revenue_growth": "share gains", "operating_margin": "mix and pricing"},
            "3p": {
                "possible": [{"strand": "adjacent entry", "revenue_in_dcf": 0}],
                "plausible": [{"strand": "share gains continue"}],
                "probable": [{"strand": "current mix holds"}],
            },
        }

    def _legal_vm(self) -> dict:
        return {
            "ticker": "X",
            "model": {"name": "dcf", "rationale": "operating fcff"},
            "fair_value": {"base": 10, "bear": 8, "bull": 12},
            "assumptions": {
                "revenue_growth": {"value": 0.04, "rationale": "history", "basis": "10-K"},
                "operating_margin": {"value": 0.22, "rationale": "mix", "basis": "history"},
            },
            "terminal_consistency": {
                "method": "gordon",
                "g_n": 0.03,
                "reinvestment_rate": 0.5,
                "roc_n": 0.06,
            },
        }

    def test_32_blank_narrative_substance_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.2.0")
            _write(
                s / "registry/narrative_bind.json",
                {"ticker": "X", "status": "locked", "iv_playbook": "mature_operating"},
            )
            _write(s / "data/valuation_model.json", self._legal_vm())
            rows = check_damodaran_v3(s)
            ids = {r[1] for r in rows if r[0] == "FAIL"}
            self.assertIn("damodaran.narrative_story", ids, rows)
            self.assertIn("damodaran.narrative_map", ids, rows)
            self.assertIn("damodaran.narrative_3p", ids, rows)

    def test_32_full_narrative_substance_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.2.0")
            _write(s / "registry/narrative_bind.json", self._full_narrative())
            _write(s / "data/valuation_model.json", self._legal_vm())
            rows = check_damodaran_v3(s)
            self.assertFalse(any(r[0] == "FAIL" for r in rows), rows)

    def test_32_map_key_must_name_a_model_input(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.2.0")
            bind = self._full_narrative()
            bind["map"] = {"synergy_unicorn": "a story with no input behind it"}
            _write(s / "registry/narrative_bind.json", bind)
            _write(s / "data/valuation_model.json", self._legal_vm())
            rows = check_damodaran_v3(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "damodaran.narrative_map" for r in rows),
                rows,
            )

    def test_32_empty_3p_bucket_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.2.0")
            bind = self._full_narrative()
            bind["3p"] = {"possible": [], "plausible": [], "probable": []}
            _write(s / "registry/narrative_bind.json", bind)
            _write(s / "data/valuation_model.json", self._legal_vm())
            rows = check_damodaran_v3(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "damodaran.narrative_3p" for r in rows),
                rows,
            )

    def test_32_possible_not_list_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.2.0")
            bind = self._full_narrative()
            bind["3p"] = {"possible": "n/a", "plausible": [], "probable": []}
            _write(s / "registry/narrative_bind.json", bind)
            _write(s / "data/valuation_model.json", self._legal_vm())
            rows = check_damodaran_v3(s)
            ids = {r[1] for r in rows if r[0] == "FAIL"}
            self.assertIn("damodaran.narrative_3p", ids, rows)
            self.assertIn("damodaran.possible_in_base", ids, rows)

    def test_32_truncation_p_requires_weighted_base(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.2.0")
            _write(s / "registry/narrative_bind.json", self._full_narrative())
            vm = self._legal_vm()
            vm["truncation"] = {
                "p": 0.3,
                "going_concern_upper_bound": 10,
                "failure_payoff": 1,
            }
            _write(s / "data/valuation_model.json", vm)
            rows = check_damodaran_v3(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "damodaran.truncation_base" for r in rows),
                rows,
            )

    def test_32_truncation_weighted_base_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.2.0")
            _write(s / "registry/narrative_bind.json", self._full_narrative())
            vm = self._legal_vm()
            vm["fair_value"] = {"base": 7.3, "bear": 4, "bull": 12}
            vm["truncation"] = {
                "p": 0.3,
                "going_concern_upper_bound": 10,
                "failure_payoff": 1,
            }
            _write(s / "data/valuation_model.json", vm)
            rows = check_damodaran_v3(s)
            self.assertFalse(
                any(r[0] == "FAIL" and r[1] == "damodaran.truncation_base" for r in rows),
                rows,
            )

    def test_32_truncation_material_false_cannot_bypass(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.2.0")
            _write(s / "registry/narrative_bind.json", self._full_narrative())
            vm = self._legal_vm()
            vm["truncation"] = {
                "material": False,
                "p": 0.3,
                "going_concern_upper_bound": 10,
                "failure_payoff": 1,
                "why_not_material": "p is already inside the cash-flow path",
            }
            _write(s / "data/valuation_model.json", vm)
            rows = check_damodaran_v3(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "damodaran.truncation_base" for r in rows),
                rows,
            )

    def test_32_truncation_non_numeric_p_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.2.0")
            _write(s / "registry/narrative_bind.json", self._full_narrative())
            vm = self._legal_vm()
            vm["truncation"] = {
                "p": "30%",
                "going_concern_upper_bound": 10,
                "failure_payoff": 1,
            }
            _write(s / "data/valuation_model.json", vm)
            rows = check_damodaran_v3(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "damodaran.truncation_base" for r in rows),
                rows,
            )

    def test_32_pricing_used_as_variants_fail(self) -> None:
        for variant in ("Fair Value", "fv", "base", "decision_value"):
            with self.subTest(variant=variant):
                with tempfile.TemporaryDirectory() as td:
                    s = Path(td)
                    _stamp(s, "3.2.0")
                    _write(s / "registry/narrative_bind.json", self._full_narrative())
                    vm = self._legal_vm()
                    vm["pricing"] = {"used_as": variant, "method": "nav"}
                    _write(s / "data/valuation_model.json", vm)
                    rows = check_damodaran_v3(s)
                    self.assertTrue(
                        any(
                            r[0] == "FAIL" and r[1] == "damodaran.price_as_value"
                            for r in rows
                        ),
                        (variant, rows),
                    )

    def test_32_pricing_role_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.2.0")
            _write(s / "registry/narrative_bind.json", self._full_narrative())
            vm = self._legal_vm()
            vm["pricing"] = {"used_as": "cross_check", "method": "nav"}
            _write(s / "data/valuation_model.json", vm)
            rows = check_damodaran_v3(s)
            self.assertFalse(
                any(r[0] == "FAIL" and r[1] == "damodaran.price_as_value" for r in rows),
                rows,
            )

    def test_32_v3_model_without_version_is_root_of_trust_fail(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            (s / "meta").mkdir(parents=True, exist_ok=True)
            (s / "meta" / "run_manifest.json").write_text(
                json.dumps({"harness_spec": "v3", "ticker": "X"}) + "\n",
                encoding="utf-8",
            )
            _write(s / "registry/narrative_bind.json", self._full_narrative())
            _write(s / "data/valuation_model.json", self._legal_vm())
            rows = check_damodaran_v3(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "damodaran.version_root" for r in rows),
                rows,
            )

    def test_legacy_v2_without_version_skips(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            (s / "meta").mkdir(parents=True, exist_ok=True)
            (s / "meta" / "run_manifest.json").write_text(
                json.dumps({"harness_spec": "v2", "ticker": "X"}) + "\n",
                encoding="utf-8",
            )
            _write(s / "data/valuation_model.json", self._legal_vm())
            rows = check_damodaran_v3(s)
            self.assertTrue(any(r[0] == "SKIPPED" for r in rows), rows)
            self.assertFalse(any(r[0] == "FAIL" for r in rows), rows)

    def test_31_blank_narrative_substance_skips(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.1.0")
            _write(
                s / "registry/narrative_bind.json",
                {"ticker": "X", "status": "locked", "iv_playbook": "mature_operating"},
            )
            _write(s / "data/valuation_model.json", self._legal_vm())
            rows = check_damodaran_v3(s)
            ids = {r[1] for r in rows if r[0] == "FAIL"}
            self.assertNotIn("damodaran.narrative_story", ids, rows)
            self.assertNotIn("damodaran.narrative_map", ids, rows)
            self.assertNotIn("damodaran.narrative_3p", ids, rows)

    # ---- 3.3.0 Tier-1 gates: life cycle, buyer, option, truncation, ----------
    # ---- market-neutral inputs, per-share bridge ----------------------------

    def _tier1_narrative(self) -> dict:
        bind = self._full_narrative()
        bind.update(
            {
                "life_cycle_stage": "mature",
                "who_leads": "numbers",
                "stage_fit": "Mature cash-cow with stable share; numbers lead the story.",
                "buyer": {
                    "class": "public_diversified",
                    "rationale": "Widely held NYSE large-cap; the marginal investor is diversified.",
                    "illiquidity_discount": 0.0,
                },
                "market_contest": {
                    "accept": ["session rf", "implied ERP", "market D/E weights"],
                    "contest": ["company cash flows", "reinvestment", "margins"],
                    "rationale": "Accept market prices of risk; contest the company operating path.",
                },
            }
        )
        return bind

    def _tier1_vm(self) -> dict:
        vm = self._legal_vm()
        vm["truncation"] = {
            "p": 0,
            "why_not_material": "Large cash-rich mature firm; failure is not material to value.",
        }
        vm["wacc_buildup"] = {
            "applies": True,
            "rf": 0.04,
            "erp_method": "implied",
            "beta_method": "bottom_up",
            "discount_currency": "USD",
            "cash_flow_currency": "USD",
        }
        vm["per_share_bridge"] = {
            "shares_used": 100.0,
            "net_debt_subtracted": 0.0,
            "cash_added": 0.0,
            "rationale": "Enterprise value less net debt, plus cash, over primary shares.",
        }
        return vm

    def _tier1_session(self, bind=None, vm=None) -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        _stamp(s, "3.3.0")
        _write(
            s / "registry/narrative_bind.json",
            bind if bind is not None else self._tier1_narrative(),
        )
        _write(
            s / "data/valuation_model.json",
            vm if vm is not None else self._tier1_vm(),
        )
        return s

    def test_33_tier1_compliant_passes(self) -> None:
        rows = check_damodaran_v3(self._tier1_session())
        fails = [r for r in rows if r[0] == "FAIL"]
        self.assertEqual(fails, [], msg=fails)

    def test_33_life_cycle_stage_required(self) -> None:
        bind = self._tier1_narrative()
        bind.pop("life_cycle_stage")
        rows = check_damodaran_v3(self._tier1_session(bind=bind))
        self.assertTrue(
            any(r[0] == "FAIL" and r[1] == "damodaran.life_cycle_stage" for r in rows), rows
        )

    def test_33_stage_fit_required(self) -> None:
        bind = self._tier1_narrative()
        bind["stage_fit"] = "short"
        rows = check_damodaran_v3(self._tier1_session(bind=bind))
        self.assertTrue(any(r[0] == "FAIL" and r[1] == "damodaran.stage_fit" for r in rows), rows)

    def test_33_buyer_required(self) -> None:
        bind = self._tier1_narrative()
        bind.pop("buyer")
        rows = check_damodaran_v3(self._tier1_session(bind=bind))
        self.assertTrue(
            any(r[0] == "FAIL" and r[1] == "damodaran.buyer_identity" for r in rows), rows
        )

    def test_33_private_buyer_needs_total_beta(self) -> None:
        bind = self._tier1_narrative()
        bind["buyer"] = {
            "class": "private_undiversified",
            "rationale": "Founder-owned; the owner holds an undiversified stake.",
        }
        rows = check_damodaran_v3(self._tier1_session(bind=bind))
        self.assertTrue(
            any(r[0] == "FAIL" and r[1] == "damodaran.buyer_identity" for r in rows), rows
        )

    def test_33_market_contest_required(self) -> None:
        bind = self._tier1_narrative()
        bind.pop("market_contest")
        rows = check_damodaran_v3(self._tier1_session(bind=bind))
        self.assertTrue(
            any(r[0] == "FAIL" and r[1] == "damodaran.market_contest" for r in rows), rows
        )

    def test_33_option_screens_required(self) -> None:
        bind = self._tier1_narrative()
        bind["overlays"] = ["real_options"]
        rows = check_damodaran_v3(self._tier1_session(bind=bind))
        self.assertTrue(
            any(r[0] == "FAIL" and r[1] == "damodaran.option_screens" for r in rows), rows
        )

    def test_33_option_screens_present_passes(self) -> None:
        bind = self._tier1_narrative()
        bind["overlays"] = ["real_options"]
        bind["option_screens"] = {
            "exclusivity": True,
            "materiality": True,
            "no_double_count": True,
            "rationale": "Exclusive license, material at this firm, no double count with DCF growth.",
        }
        rows = check_damodaran_v3(self._tier1_session(bind=bind))
        self.assertFalse(
            any(r[0] == "FAIL" and r[1] == "damodaran.option_screens" for r in rows), rows
        )

    def test_33_distressed_call_replaces_equity(self) -> None:
        bind = self._tier1_narrative()
        bind["overlays"] = ["distressed_call"]
        bind["distressed_call"] = {"dcf_equity_near_zero": True, "replaces_dcf_equity": False}
        vm = self._tier1_vm()
        vm["model"] = {"name": "liquidation_call", "rationale": "option on assets in place"}
        rows = check_damodaran_v3(self._tier1_session(bind=bind, vm=vm))
        self.assertTrue(
            any(r[0] == "FAIL" and r[1] == "damodaran.distressed_call" for r in rows), rows
        )

    def test_33_truncation_assessment_required(self) -> None:
        vm = self._tier1_vm()
        vm.pop("truncation")
        rows = check_damodaran_v3(self._tier1_session(vm=vm))
        self.assertTrue(
            any(r[0] == "FAIL" and r[1] == "damodaran.truncation_assessed" for r in rows), rows
        )

    def test_33_truncation_p0_needs_reason(self) -> None:
        vm = self._tier1_vm()
        vm["truncation"] = {"p": 0}
        rows = check_damodaran_v3(self._tier1_session(vm=vm))
        self.assertTrue(
            any(r[0] == "FAIL" and r[1] == "damodaran.truncation_assessed" for r in rows), rows
        )

    def test_33_erp_method_required(self) -> None:
        vm = self._tier1_vm()
        vm["wacc_buildup"].pop("erp_method")
        rows = check_damodaran_v3(self._tier1_session(vm=vm))
        self.assertTrue(
            any(r[0] == "FAIL" and r[1] == "damodaran.erp_method" for r in rows), rows
        )

    def test_33_historical_erp_needs_reject_reason(self) -> None:
        vm = self._tier1_vm()
        vm["wacc_buildup"]["erp_method"] = "historical"
        rows = check_damodaran_v3(self._tier1_session(vm=vm))
        self.assertTrue(
            any(r[0] == "FAIL" and r[1] == "damodaran.erp_method" for r in rows), rows
        )

    def test_33_currency_mismatch_needs_fx_policy(self) -> None:
        vm = self._tier1_vm()
        vm["wacc_buildup"]["cash_flow_currency"] = "EUR"
        rows = check_damodaran_v3(self._tier1_session(vm=vm))
        self.assertTrue(
            any(r[0] == "FAIL" and r[1] == "damodaran.currency_match" for r in rows), rows
        )

    def test_33_per_share_bridge_required(self) -> None:
        vm = self._tier1_vm()
        vm.pop("per_share_bridge")
        rows = check_damodaran_v3(self._tier1_session(vm=vm))
        self.assertTrue(
            any(r[0] == "FAIL" and r[1] == "damodaran.per_share_bridge" for r in rows), rows
        )

    def test_33_contingent_claim_playbook_allowed(self) -> None:
        bind = self._tier1_narrative()
        bind["iv_playbook"] = "contingent_claim"
        bind["overlays"] = ["real_options"]
        bind["option_screens"] = {
            "exclusivity": True,
            "materiality": True,
            "no_double_count": True,
            "rationale": "Exclusive patent right; material at this firm; not in the DCF base.",
        }
        rows = check_damodaran_v3(self._tier1_session(bind=bind))
        self.assertFalse(
            any(r[0] == "FAIL" and r[1] == "damodaran.iv_playbook" for r in rows), rows
        )

    def test_33_public_buyer_discount_must_be_zero(self) -> None:
        bind = self._tier1_narrative()
        bind["buyer"] = {
            "class": "public_diversified",
            "rationale": "Widely held; diversified marginal investor.",
            "illiquidity_discount": 0.15,
        }
        rows = check_damodaran_v3(self._tier1_session(bind=bind))
        self.assertTrue(
            any(r[0] == "FAIL" and r[1] == "damodaran.buyer_identity" for r in rows), rows
        )

    def test_33_public_buyer_needs_numeric_zero_discount(self) -> None:
        bind = self._tier1_narrative()
        bind["buyer"] = {
            "class": "public_diversified",
            "rationale": "Widely held; diversified marginal investor.",
            "illiquidity_treatment": "none",
        }
        rows = check_damodaran_v3(self._tier1_session(bind=bind))
        self.assertTrue(
            any(r[0] == "FAIL" and r[1] == "damodaran.buyer_identity" for r in rows), rows
        )

    def test_33_vc_pe_needs_ke_stepdown(self) -> None:
        bind = self._tier1_narrative()
        bind["buyer"] = {
            "class": "vc_pe",
            "rationale": "Late-stage VC stake; cost of equity steps down at IPO.",
        }
        rows = check_damodaran_v3(self._tier1_session(bind=bind))
        self.assertTrue(
            any(r[0] == "FAIL" and r[1] == "damodaran.buyer_identity" for r in rows), rows
        )

    def test_33_erp_not_applicable_illegal_when_wacc_applies(self) -> None:
        vm = self._tier1_vm()
        vm["wacc_buildup"]["erp_method"] = "not_applicable"
        rows = check_damodaran_v3(self._tier1_session(vm=vm))
        self.assertTrue(any(r[0] == "FAIL" and r[1] == "damodaran.erp_method" for r in rows), rows)

    def test_33_beta_not_applicable_illegal_when_wacc_applies(self) -> None:
        vm = self._tier1_vm()
        vm["wacc_buildup"]["beta_method"] = "not_applicable"
        rows = check_damodaran_v3(self._tier1_session(vm=vm))
        self.assertTrue(
            any(r[0] == "FAIL" and r[1] == "damodaran.beta_method" for r in rows), rows
        )

    def test_32_does_not_run_tier1_gates(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.2.0")
            _write(s / "registry/narrative_bind.json", self._full_narrative())
            _write(s / "data/valuation_model.json", self._legal_vm())
            rows = check_damodaran_v3(s)
            tier1_ids = {
                "damodaran.life_cycle_stage",
                "damodaran.stage_fit",
                "damodaran.buyer_identity",
                "damodaran.market_contest",
                "damodaran.truncation_assessed",
                "damodaran.market_neutral",
                "damodaran.per_share_bridge",
                "damodaran.erp_method",
                "damodaran.beta_method",
                "damodaran.currency_match",
                "damodaran.option_screens",
                "damodaran.distressed_call",
            }
            fired = {r[1] for r in rows if r[0] == "FAIL"} & tier1_ids
            self.assertEqual(fired, set(), rows)


class ValuationRouterRefRecipeTests(unittest.TestCase):
    """Every primary id and overlay in the overlay list must have a ref recipe
    row, and each ref path it names must exist."""

    PRIMARY_IDS = (
        "mature_operating",
        "financial_service",
        "real_estate",
        "young_startup",
        "contingent_claim",
        "asset_based",
    )
    OVERLAY_IDS = (
        "cyclical",
        "distressed",
        "intangibles_sbc",
        "em",
        "truncation",
        "sotp_users",
        "growth_assets",
        "macro_neutral",
        "real_options",
        "distressed_call",
        "asset_based_floor",
        "private_buyer",
        "value_enhancement",
    )

    def _recipe_rows(self) -> dict:
        text = (ROOT / "harness" / "modules" / "valuation_router.md").read_text(
            encoding="utf-8"
        )
        rows: dict = {}
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("|"):
                continue
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if not cells:
                continue
            rows[cells[0].strip().strip("`")] = line
        return rows

    def test_every_id_has_a_ref_recipe_row(self) -> None:
        import re

        rows = self._recipe_rows()
        for ident in self.PRIMARY_IDS + self.OVERLAY_IDS:
            with self.subTest(ident=ident):
                self.assertIn(ident, rows, f"no ref recipe row for {ident}")
                paths = re.findall(r"`(knowledge-hub[^`]+\.md)`", rows[ident])
                self.assertTrue(paths, f"{ident} row names no knowledge-hub ref path")

    def test_ref_recipe_paths_exist_when_library_present(self) -> None:
        import re

        ref_root = ROOT / "ref" / "Investment Valuation"
        if not ref_root.is_dir():
            self.skipTest("local ref/ library absent (gitignored; not a ship dependency)")
        rows = self._recipe_rows()
        for ident in self.PRIMARY_IDS + self.OVERLAY_IDS:
            with self.subTest(ident=ident):
                for rel in re.findall(r"`(knowledge-hub[^`]+\.md)`", rows[ident]):
                    self.assertTrue((ref_root / rel).is_file(), f"{ident}: missing {rel}")


if __name__ == "__main__":
    unittest.main()

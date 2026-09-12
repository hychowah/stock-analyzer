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


if __name__ == "__main__":
    unittest.main()

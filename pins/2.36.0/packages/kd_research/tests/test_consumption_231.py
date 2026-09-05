"""Harness 2.31.0 consumption gates."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.consumption import (
    check_1d_ind_background,
    check_2d_street_cite,
    check_fdd_material_hooks,
    check_stress_legal_dollar,
)


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj) if not isinstance(obj, str) else obj, encoding="utf-8")


class ConsumptionTests(unittest.TestCase):
    def _s(self, version: str = "2.31.0") -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        _write(
            s / "meta/run_manifest.json",
            {"status": "scaffolded", "orchestrator_model": "grok-4.5", "harness_version": version},
        )
        return s

    def test_extracted_sbc_noted_only_fails(self) -> None:
        s = self._s()
        _write(
            s / "registry/filing_deep_dive.json",
            {
                "ticker": "X",
                "footnotes": {
                    "items": {
                        "sbc_unrecognized": {
                            "status": "extracted",
                            "value": "2.1B",
                        }
                    }
                },
            },
        )
        _write(
            s / "data/valuation_model.json",
            {
                "ticker": "X",
                "filing_deep_dive_hooks": [
                    {
                        "from": "footnotes.sbc_unrecognized",
                        "action": "noted_only",
                        "reason": "Noted SBC without changing the path.",
                    }
                ],
            },
        )
        rows = check_fdd_material_hooks(s)
        self.assertEqual(rows[0][0], "FAIL", rows)

    def test_extracted_sbc_rejected_passes(self) -> None:
        s = self._s()
        _write(
            s / "registry/filing_deep_dive.json",
            {
                "ticker": "X",
                "footnotes": {
                    "items": {
                        "sbc_unrecognized": {"status": "extracted", "value": "2.1B"}
                    }
                },
            },
        )
        _write(
            s / "data/valuation_model.json",
            {
                "ticker": "X",
                "filing_deep_dive_hooks": [
                    {
                        "from": "footnotes.sbc_unrecognized",
                        "action": "rejected",
                        "reason": "Already in the FCFF SBC convention; no second subtract.",
                    }
                ],
            },
        )
        rows = check_fdd_material_hooks(s)
        self.assertEqual(rows[0][0], "PASS", rows)

    def test_230_skips_material_hooks(self) -> None:
        s = self._s("2.30.0")
        rows = check_fdd_material_hooks(s)
        self.assertEqual(rows[0][0], "SKIPPED", rows)

    def test_2d_consensus_without_street_file_cite_fails(self) -> None:
        s = self._s()
        _write(s / "registry/street_estimates.json", {"ticker": "X", "years": [{"revenue": 1}]})
        _write(
            s / "registry/latest_quarter.json",
            {"ticker": "X", "revenue": {"value": 10, "vs_consensus": "beat"}},
        )
        rows = check_2d_street_cite(s)
        self.assertEqual(rows[0][0], "FAIL", rows)

    def test_2d_cites_street_estimates_passes(self) -> None:
        s = self._s()
        _write(s / "registry/street_estimates.json", {"ticker": "X", "years": [{"revenue": 1}]})
        _write(
            s / "registry/latest_quarter.json",
            {
                "ticker": "X",
                "revenue": {
                    "value": 10,
                    "vs_consensus": "beat",
                    "source": "registry/street_estimates.json",
                },
            },
        )
        rows = check_2d_street_cite(s)
        self.assertEqual(rows[0][0], "PASS", rows)

    def test_1d_ind_needs_background_or_gaps(self) -> None:
        s = self._s()
        _write(
            s / "registry/raw/oppath_ind.json",
            {"ticker": "X", "session_date": "2026-01-01", "lens": "industry_trend", "findings": ["units up"]},
        )
        rows = check_1d_ind_background(s)
        self.assertEqual(rows[0][0], "FAIL", rows)

    def test_1d_ind_named_gaps_pass(self) -> None:
        s = self._s()
        _write(
            s / "registry/raw/oppath_ind.json",
            {
                "ticker": "X",
                "session_date": "2026-01-01",
                "lens": "industry_trend",
                "findings": ["utilization missing in background"],
                "named_gaps": ["industry utilization vs history"],
            },
        )
        rows = check_1d_ind_background(s)
        self.assertEqual(rows[0][0], "PASS", rows)

    def test_legal_dollar_without_fdd_cite_fails(self) -> None:
        s = self._s()
        _write(
            s / "registry/risk_bridge.json",
            {
                "ticker": "X",
                "risks": [],
                "scenario_probabilities": {"bear": 0.3, "base": 0.5, "bull": 0.2},
                "stress_test": {
                    "scenarios": [
                        {
                            "name": "litigation",
                            "probability": 0.2,
                            "fair_value_haircut_pct": 0.1,
                            "narrative": "A $400 million lawsuit from a blog.",
                        }
                    ]
                },
            },
        )
        rows = check_stress_legal_dollar(s)
        self.assertEqual(rows[0][0], "FAIL", rows)


if __name__ == "__main__":
    unittest.main()

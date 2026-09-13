"""StreetY1Policy table: 2.7 / 2.18 / 2.28 / 3.0.0 / 3.0.1 version floors."""

from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from packages.kd_research.street_bind import check_street_bind
from packages.kd_research.street_y1 import (
    CALIB,
    GATED,
    GATES_228,
    GATES_300,
    INDEPENDENT,
    STREET_REF,
    Y1,
    StreetY1Policy,
    Y1_BAND,
)


def _stamp(session: Path, version: str) -> None:
    (session / "meta").mkdir(parents=True, exist_ok=True)
    (session / "meta" / "run_manifest.json").write_text(
        json.dumps({"harness_version": version, "ticker": "X", "session_date": "2026-01-01"})
        + "\n",
        encoding="utf-8",
    )


class StreetY1PolicyTests(unittest.TestCase):
    def test_version_floors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.6.0")
            self.assertFalse(StreetY1Policy.for_session(s).y1)
            _stamp(s, "2.7.0")
            p = StreetY1Policy.for_session(s)
            self.assertEqual(p, CALIB)
            self.assertIn("keep_independent_vs_street", p.responses)
            self.assertIsNone(p.fail_band)
            _stamp(s, "2.18.0")
            p = StreetY1Policy.for_session(s)
            self.assertEqual(p, Y1)
            self.assertTrue(p.keep_independent_illegal)
            self.assertEqual(p.fail_band, Y1_BAND)
            self.assertFalse(p.independent_y1_ok)
            _stamp(s, "2.28.0")
            p = StreetY1Policy.for_session(s)
            self.assertEqual(p, GATED)
            self.assertTrue(p.independent_y1_ok)
            self.assertIn("independent_y1", p.responses)
            self.assertTrue(p.rehydrate)
            self.assertEqual(p.legal_gates, GATES_228)
            self.assertFalse(p.story_fail_requires_will_own)
            _stamp(s, "3.0.0")
            p = StreetY1Policy.for_session(s)
            self.assertEqual(p, INDEPENDENT)
            self.assertTrue(p.gate_optional)
            self.assertFalse(p.fy1_baseline_required)
            self.assertEqual(p.legal_gates, GATES_300)
            self.assertFalse(p.story_fail_requires_will_own)
            _stamp(s, "3.0.1")
            p = StreetY1Policy.for_session(s)
            self.assertEqual(p, STREET_REF)
            self.assertFalse(p.gate_optional)
            self.assertTrue(p.fy1_baseline_required)
            self.assertTrue(p.independent_y1_ok)
            self.assertEqual(p.legal_gates, GATES_300)
            self.assertTrue(p.story_fail_requires_will_own)
            self.assertNotEqual(STREET_REF, GATED)

    def test_injected_fail_band_is_not_hardcoded_five_pct(self) -> None:
        """A second copy of 0.05 in bind would still FAIL at 7% under a 10% band."""
        street = 254.2
        base = 236.0  # ~7.2% below Street
        wide = replace(Y1, fail_band=0.10, warn_band=0.08)

        def _vm() -> dict:
            delta = (base - street) / street
            return {
                "ticker": "X",
                "model": {"name": "dcf", "rationale": "ordinary FCFF"},
                "fair_value": {"base": 100, "bear": 80, "bull": 120},
                "assumptions": {},
                "compute_script": "data/compute/v.py",
                "sensitivity": {},
                "street_bind": {
                    "guide": 252.7,
                    "street": street,
                    "base": base,
                    "delta_pct": delta,
                    "response": "street_baseline",
                    "independent_construction": {
                        "rationale": "Base Y1 starts from Street FY+1 vendor mean; overlay documented here."
                    },
                },
                "street_hooks": [
                    {
                        "from": "street_estimates.years[+1y].revenue",
                        "action": "used_as:fy1_baseline",
                        "reason": "Street FY+1 revenue is the required base Y1 starting point.",
                    }
                ],
                "conservatism_dials": [
                    {"key": k, "applies_in": "none"}
                    for k in (
                        "volume_vs_guide",
                        "gaap_om_vs_guide",
                        "sbc_in_fcff",
                        "wacc_vs_buildup",
                    )
                ],
            }

        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.18.0")
            (s / "registry").mkdir(parents=True, exist_ok=True)
            (s / "data").mkdir(parents=True, exist_ok=True)
            (s / "registry" / "street_estimates.json").write_text(
                json.dumps(
                    {
                        "ticker": "X",
                        "session_date": "2026-01-01",
                        "source": "yfinance.revenue_estimate",
                        "fiscal_convention": "company_fy",
                        "years": [
                            {"label": "0y", "revenue": 180.0, "n_revenue": 55},
                            {"label": "+1y", "revenue": street, "n_revenue": 55},
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (s / "data" / "valuation_model.json").write_text(
                json.dumps(_vm()) + "\n", encoding="utf-8"
            )
            native = check_street_bind(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "street_bind.y1_band" for r in native),
                native,
            )
            with patch.object(StreetY1Policy, "for_session", return_value=wide):
                injected = check_street_bind(s)
            self.assertFalse(
                any(r[0] == "FAIL" and r[1] == "street_bind.y1_band" for r in injected),
                injected,
            )

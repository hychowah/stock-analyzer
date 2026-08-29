"""Unit tests for filing_deep_dive_hooks machine gate (F8)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.gates import (
    check_filing_deep_dive_hooks,
    check_market_context_hooks_intensity,
    validate_hooks_list,
)


def _vm_with_hooks(fdd_hooks=None, mc_hooks=None):
    d = {
        "ticker": "TEST",
        "model": {"name": "dcf", "rationale": "fixture"},
        "fair_value": {"base": 100.0},
        "compute_script": "data/compute/valuation.py",
    }
    if fdd_hooks is not None:
        d["filing_deep_dive_hooks"] = fdd_hooks
    if mc_hooks is not None:
        d["market_context_hooks"] = mc_hooks
    return d


class FddHooksTests(unittest.TestCase):
    def _session(self, *, fdd: bool, vm: dict | None) -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        session = Path(td.name) / "TEST" / "2026-08-10"
        (session / "registry").mkdir(parents=True)
        (session / "data").mkdir(parents=True)
        if fdd:
            (session / "registry" / "filing_deep_dive.json").write_text(
                json.dumps({"ticker": "TEST", "footnotes": {"items": []}})
            )
        if vm is not None:
            (session / "data" / "valuation_model.json").write_text(json.dumps(vm))
        return session

    def test_skipped_when_no_fdd(self):
        session = self._session(fdd=False, vm=_vm_with_hooks(fdd_hooks=[]))
        out = check_filing_deep_dive_hooks(session)
        self.assertEqual(out[0][0], "SKIPPED")

    def test_fail_when_fdd_without_hooks(self):
        session = self._session(fdd=True, vm=_vm_with_hooks(fdd_hooks=[]))
        out = check_filing_deep_dive_hooks(session)
        self.assertEqual(out[0][0], "FAIL")
        self.assertEqual(out[0][1], "filing_deep_dive_hooks")

    def test_fail_when_hooks_key_missing(self):
        session = self._session(fdd=True, vm=_vm_with_hooks())
        out = check_filing_deep_dive_hooks(session)
        self.assertEqual(out[0][0], "FAIL")

    def test_pass_with_valid_hooks(self):
        hooks = [
            {
                "from": "footnotes.lease",
                "action": "use",
                "reason": "Lease obligations raise net debt in FCFF bridge for base case.",
            }
        ]
        session = self._session(fdd=True, vm=_vm_with_hooks(fdd_hooks=hooks))
        out = check_filing_deep_dive_hooks(session)
        self.assertEqual(out[0][0], "PASS")

    def test_validate_hooks_reason_too_short(self):
        out = validate_hooks_list(
            [{"from": "x", "action": "use", "reason": "short"}],
            check_id="filing_deep_dive_hooks",
            empty_detail="empty",
        )
        self.assertEqual(out[0][0], "FAIL")
        self.assertIn("shape", out[0][1])

    def test_intensity_all_noted_only_fails(self):
        hooks = [
            {"from": "intensity", "action": "noted_only", "reason": "enough characters here"},
            {"from": "ownership", "action": "noted_only", "reason": "also enough characters"},
        ]
        out = check_market_context_hooks_intensity(hooks, "high")
        self.assertEqual(out[0][0], "FAIL")

    def test_intensity_low_allows_noted_only(self):
        hooks = [
            {"from": "intensity", "action": "noted_only", "reason": "enough characters here"},
        ]
        out = check_market_context_hooks_intensity(hooks, "low")
        self.assertEqual(out, [])


if __name__ == "__main__":
    unittest.main()

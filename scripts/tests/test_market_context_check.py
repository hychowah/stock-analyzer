"""Unit tests for market_context structural checks in check_session (no network)."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def _load_check_session():
    path = ROOT / "scripts" / "check_session.py"
    spec = importlib.util.spec_from_file_location("check_session_under_test", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _valid_market_context(**overrides):
    base = {
        "ticker": "TEST",
        "session_date": "2026-08-03",
        "primary_region": "us",
        "intensity": "low",
        "confidence": 0.95,
        "module_file": "region_us.md",
        "signals": ["NYSE listing", "US GAAP", "USD"],
        "rationale": "Primary US listing with widely held ownership and US GAAP reporting.",
        "requires_manual_review": False,
        "listing": {
            "exchange": "NYSE",
            "market_region": "US",
            "reporting_currency": "USD",
            "primary_filing_source": "sec_edgar",
            "regional_benchmark": "SPY",
        },
        "accounting_regime": {"basis": "us_gaap", "rationale": "10-K US GAAP"},
        "cost_of_capital_flags": {
            "use_local_rf": True,
            "country_risk_overlay": False,
            "fx_in_cash_flows": False,
        },
        "ownership": {"control_type": "widely_held", "complexity": "low", "signals": []},
    }
    base.update(overrides)
    return base


def _minimal_valuation_with_hooks(hooks):
    return {
        "ticker": "TEST",
        "model": {"name": "dcf", "rationale": "Standard DCF for test fixture company only."},
        "fair_value": {"base": 100.0, "bear": 70.0, "bull": 130.0},
        "assumptions": {
            "wacc": {
                "value": 0.09,
                "rationale": "Test fixture WACC only.",
                "basis": "unit test",
            }
        },
        "compute_script": "data/compute/valuation.py",
        "sensitivity": {"grid": {}, "note": "fixture"},
        "market_context_hooks": hooks,
    }


class MarketContextCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cs = _load_check_session()
        self.cs.results.clear()

    def _session(self, with_mc=None, with_vm=None) -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        # Fake ticker/date layout not required for check_market_context alone
        session = root / "TEST" / "2026-08-03"
        (session / "registry").mkdir(parents=True)
        (session / "data").mkdir(parents=True)
        if with_mc is not None:
            (session / "registry" / "market_context.json").write_text(json.dumps(with_mc))
        if with_vm is not None:
            (session / "data" / "valuation_model.json").write_text(json.dumps(with_vm))
        return session

    def test_absent_market_context_is_skipped_not_fail(self):
        session = self._session()
        self.cs.check_market_context(session)
        statuses = [s for s, c, _ in self.cs.results if c == "market_context"]
        self.assertEqual(statuses, ["SKIPPED"])
        self.assertFalse(any(s == "FAIL" for s, _, _ in self.cs.results))

    def test_valid_low_intensity_with_noted_only_hook_passes(self):
        hooks = [
            {
                "from": "intensity",
                "action": "noted_only",
                "reason": "US widely held large-cap; no country-risk or control overlay applied.",
            }
        ]
        session = self._session(
            with_mc=_valid_market_context(),
            with_vm=_minimal_valuation_with_hooks(hooks),
        )
        self.cs.check_market_context(session)
        fails = [r for r in self.cs.results if r[0] == "FAIL"]
        self.assertEqual(fails, [], msg=fails)
        self.assertTrue(any(s == "PASS" and c == "market_context_hooks" for s, c, _ in self.cs.results))

    def test_high_intensity_all_noted_only_fails(self):
        hooks = [
            {
                "from": "intensity",
                "action": "noted_only",
                "reason": "Pretend high intensity needs no treatment at all.",
            }
        ]
        session = self._session(
            with_mc=_valid_market_context(primary_region="hk_china", intensity="high"),
            with_vm=_minimal_valuation_with_hooks(hooks),
        )
        self.cs.check_market_context(session)
        self.assertTrue(
            any(s == "FAIL" and "intensity" in c for s, c, _ in self.cs.results),
            msg=self.cs.results,
        )

    def test_present_without_hooks_fails(self):
        session = self._session(
            with_mc=_valid_market_context(primary_region="hk_china", intensity="high"),
            with_vm=_minimal_valuation_with_hooks([]),
        )
        self.cs.check_market_context(session)
        hook_fails = [r for r in self.cs.results if r[0] == "FAIL" and "market_context_hooks" in r[1]]
        self.assertTrue(hook_fails, msg=self.cs.results)

    def test_invalid_intensity_fails(self):
        session = self._session(with_mc=_valid_market_context(intensity="extreme"))
        self.cs.check_market_context(session)
        self.assertTrue(
            any(s == "FAIL" and "intensity" in c for s, c, _ in self.cs.results),
            msg=self.cs.results,
        )

    def test_short_rationale_fails(self):
        session = self._session(with_mc=_valid_market_context(rationale="too short"))
        self.cs.check_market_context(session)
        self.assertTrue(
            any(s == "FAIL" and "rationale" in c for s, c, _ in self.cs.results),
            msg=self.cs.results,
        )

    def test_schema_file_exists_and_loads(self):
        schema_path = ROOT / "templates" / "market_context.schema.json"
        self.assertTrue(schema_path.is_file())
        schema = json.loads(schema_path.read_text())
        self.assertIn("primary_region", schema["properties"])
        self.assertIn("intensity", schema["properties"])
        self.assertIn("market_context", (ROOT / "templates" / "valuation_model.schema.json").read_text())

    def test_region_modules_referenced_from_normative_spec(self):
        # Mode A law lives in RESEARCH_AGENTS.md; root AGENTS.md is router-only.
        agents = (ROOT / "harness" / "RESEARCH_AGENTS.md").read_text()
        self.assertIn("§5b", agents)
        self.assertIn("market_context.json", agents)
        self.assertIn("region_hk_china.md", agents)
        self.assertIn("market_context_hooks", agents)
        prompts = (ROOT / "harness" / "agent_prompts.md").read_text()
        self.assertIn("market_context_hooks", prompts)
        self.assertIn("no always-on region agent", prompts.lower())
        decision = (ROOT / "harness" / "region_integration.md").read_text()
        self.assertIn("Reject", decision)
        self.assertIn("No Agent 2f", decision)

    def test_check_session_help_exits_zero(self):
        import subprocess

        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check_session.py"), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("check_session", proc.stdout.lower() + proc.stderr.lower() or "usage")


if __name__ == "__main__":
    unittest.main()

"""Tests for phase evidence gates and preflight helpers."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.kd_research.gates import (  # noqa: E402
    check_phase0_coverage,
    check_stress_coverage,
    entry_checks,
)
from scripts.kd_research.url_health import classify_source, check_url  # noqa: E402


def _write(p: Path, obj: object) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, (dict, list)):
        p.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    else:
        p.write_text(str(obj), encoding="utf-8")


class GatesTest(unittest.TestCase):
    def test_entry_2_parallel_fails_without_deep_dive(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            for rel in (
                "registry/sector_config.json",
                "registry/market_context.json",
                "registry/sec_filings.json",
                "registry/latest_quarter.json",
            ):
                _write(s / rel, {"ticker": "X", "session_date": "2026-01-01"})
            _write(s / "data/sp_financials.csv", "ticker,item\nX,1\n")
            rows = entry_checks(s, "2_parallel", ticker="X")
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertTrue(any("filing_deep_dive" in r[1] for r in fails), fails)

    def test_entry_2_parallel_passes_minimal(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            for rel in (
                "registry/sector_config.json",
                "registry/market_context.json",
                "registry/sec_filings.json",
                "registry/latest_quarter.json",
                "registry/filing_deep_dive.json",
            ):
                _write(s / rel, {"ticker": "X", "session_date": "2026-01-01"})
            _write(s / "data/sp_financials.csv", "ticker,item\nX,1\n")
            rows = entry_checks(s, "2_parallel", ticker="X")
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertEqual(fails, [], fails)

    def test_phase0_coverage_requires_downstream_relevance(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _write(
                s / "registry/background.json",
                {"ticker": "X", "rounds": [{"topic": "t", "findings": ["a"], "sources": ["u"]}]},
            )
            _write(
                s / "registry/raw/phase0_round1.json",
                {"topic": "t", "findings": ["a"], "sources": ["u"]},  # missing relevance
            )
            rows = check_phase0_coverage(s)
            # all missing relevance → FAIL
            self.assertTrue(any(r[0] == "FAIL" and "downstream_relevance" in r[1] for r in rows), rows)

    def test_stress_coverage_min_five(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            raw = s / "registry/raw"
            raw.mkdir(parents=True)
            for i in range(3):
                _write(raw / f"stress_{i}.json", {"name": f"s{i}", "probability": 0.1})
            _write(
                s / "registry/risk_bridge.json",
                {
                    "scenario_probabilities": {"bear": 0.2, "base": 0.5, "bull": 0.3},
                    "stress_test": {"scenarios": [{"name": "a"}, {"name": "b"}]},
                    "risks": [],
                },
            )
            rows = check_stress_coverage(s)
            self.assertTrue(any(r[0] == "FAIL" and "stress_raw" in r[1] for r in rows), rows)

    def test_url_classify_and_not_url(self) -> None:
        self.assertEqual(classify_source("https://a.com"), "url")
        self.assertEqual(classify_source("Bloomberg"), "not_url")
        r = check_url("plain-text-source")
        self.assertEqual(r["status"], "not_url")


class PreflightCLITest(unittest.TestCase):
    def test_cli_unknown_phase(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/preflight_phase.py"), "--session-dir", str(ROOT), "--phase", "nope"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 2)


class ResearchBriefSchemaTest(unittest.TestCase):
    def test_schema_file_exists_and_validates_example(self) -> None:
        schema_path = ROOT / "templates/research_brief.schema.json"
        self.assertTrue(schema_path.exists())
        try:
            import jsonschema  # type: ignore
        except ImportError:
            self.skipTest("jsonschema not installed")
        schema = json.loads(schema_path.read_text())
        sample = {
            "ticker": "X",
            "session_date": "2026-08-09",
            "company_name": "Example Co",
            "investment_objective": "Initiate coverage with focus on unit economics and capital returns.",
            "must_answer_questions": [
                "What drives revenue growth?",
                "How levered is the balance sheet?",
                "What is the key bear case?",
            ],
            "peers": ["A", "B"],
            "benchmarks": {"regional": "^GSPC", "sector": "XLK"},
            "currency": "USD",
            "research_depth": "standard",
            "rationale": "US widely held large-cap with clean US GAAP disclosure and low intensity.",
        }
        jsonschema.Draft7Validator(schema).validate(sample)


if __name__ == "__main__":
    unittest.main()

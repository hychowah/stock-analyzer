"""Wave 7 gather: cash_quality + prompt-file tests (harness >= 2.15.0)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.paths import PROJECT_ROOT as ROOT

from packages.kd_research.annuals import parse_semver
from packages.kd_research.cash_quality import check_cash_quality
from packages.kd_research.gates import entry_checks


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj) if not isinstance(obj, str) else obj, encoding="utf-8")


class GatherTests(unittest.TestCase):
    def _sess(self, version: str = "2.15.0", lq: dict | None = None) -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        _write(
            s / "meta/run_manifest.json",
            {"status": "scaffolded", "orchestrator_model": "grok-4.5", "harness_version": version},
        )
        if lq is not None:
            _write(s / "registry/latest_quarter.json", lq)
        return s

    def test_version_at_least_215(self) -> None:
        payload = json.loads((ROOT / "harness" / "VERSION").read_text(encoding="utf-8"))
        self.assertGreaterEqual(parse_semver(payload.get("harness_version")), (2, 15, 0))

    def test_prompts_require_mechanism_and_1d_ind_units(self) -> None:
        text = (ROOT / "harness" / "agent_prompts.md").read_text(encoding="utf-8")
        self.assertIn("`mechanism` (switching_cost|network|cost|scale|brand_price|license|none)", text)
        self.assertIn("dated **units**", text)
        self.assertIn("cash_quality", text)
        self.assertNotIn(
            "Re-read Phase 0 + primary industry sources (dated TAM/units, node ramp vs destock, architecture vs dollars, share).",
            text,
        )

    def test_214_skips(self) -> None:
        s = self._sess(
            "2.14.0",
            {"ticker": "X", "fiscal_period": "2026-Q1", "filing_date": "2026-01-01", "currency": "USD", "sources": ["x"]},
        )
        rows = check_cash_quality(s)
        self.assertEqual(rows[0][0], "SKIPPED", rows)

    def test_missing_lq_skips(self) -> None:
        s = self._sess("2.15.0", lq=None)
        rows = check_cash_quality(s)
        self.assertEqual(rows[0][0], "SKIPPED", rows)

    def test_missing_cash_quality_fails(self) -> None:
        s = self._sess(
            "2.15.0",
            {"ticker": "X", "fiscal_period": "2026-Q1", "filing_date": "2026-01-01", "currency": "USD", "sources": ["x"]},
        )
        rows = check_cash_quality(s)
        self.assertEqual(rows[0][0], "FAIL", rows)

    def test_nested_fcf_passes(self) -> None:
        s = self._sess(
            "2.15.0",
            {
                "ticker": "X",
                "fiscal_period": "2026-Q1",
                "filing_date": "2026-01-01",
                "currency": "USD",
                "sources": ["x"],
                "cash_quality": {"fcf": {"value": 400.0}, "dso": 42},
            },
        )
        rows = check_cash_quality(s)
        self.assertEqual(rows[0][0], "PASS", rows)

    def test_2_parallel_entry_includes_cash_quality(self) -> None:
        s = self._sess(
            "2.15.0",
            {"ticker": "X", "fiscal_period": "2026-Q1", "filing_date": "2026-01-01", "currency": "USD", "sources": ["x"]},
        )
        rows = entry_checks(s, "2_parallel")
        self.assertTrue(any(r[1] == "cash_quality" and r[0] == "FAIL" for r in rows), rows)


if __name__ == "__main__":
    unittest.main()

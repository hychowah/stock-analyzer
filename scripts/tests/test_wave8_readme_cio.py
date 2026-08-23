"""Wave 8 README CIO lead (harness >= 2.16.0)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.kd_research.annuals import parse_semver  # noqa: E402
from scripts.kd_research.decision import check_readme_quotes_decision  # noqa: E402


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, str):
        path.write_text(obj, encoding="utf-8")
    else:
        path.write_text(json.dumps(obj), encoding="utf-8")


class ReadmeCioTests(unittest.TestCase):
    def _sess(self, version: str, readme: str, action: str = "pass") -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        _write(
            s / "meta/run_manifest.json",
            {"status": "scaffolded", "orchestrator_model": "grok-4.5", "harness_version": version},
        )
        _write(
            s / "registry/decision.json",
            {
                "ticker": "X",
                "duration": {"action": action, "rationale": "Pass because destock is unresolved."},
            },
        )
        _write(s / "reports/00_X_README.md", readme)
        return s

    def test_version_at_least_216(self) -> None:
        payload = json.loads((ROOT / "harness" / "VERSION").read_text(encoding="utf-8"))
        self.assertGreaterEqual(parse_semver(payload.get("harness_version")), (2, 16, 0))

    def test_agent11_cover_starts_with_duration(self) -> None:
        text = (ROOT / "harness" / "agent_prompts.md").read_text(encoding="utf-8")
        self.assertIn("quote** `duration.action` first", text)
        self.assertIn("lead with the **cone + pass**", text)

    def test_215_unquoted_is_warn(self) -> None:
        s = self._sess("2.15.0", "# README\nFair value vs price: 10 vs 12.\nAudit PASS.\n")
        rows = check_readme_quotes_decision(s)
        self.assertEqual(rows[0][0], "WARN", rows)

    def test_216_unquoted_is_fail(self) -> None:
        s = self._sess("2.16.0", "# README\nFair value vs price: 10 vs 12.\nAudit PASS.\n")
        rows = check_readme_quotes_decision(s)
        self.assertEqual(rows[0][0], "FAIL", rows)

    def test_audit_pass_is_not_duration_pass(self) -> None:
        s = self._sess("2.16.0", "# README\nFair value vs price + margin of safety 20%.\nAudit PASS.\n")
        rows = check_readme_quotes_decision(s)
        self.assertEqual(rows[0][0], "FAIL", rows)

    def test_duration_before_mos_passes(self) -> None:
        s = self._sess(
            "2.16.0",
            "# README\nDuration action: pass — destock unresolved.\nCheap claim: not_cheap.\nThen fair value vs price as context.\n",
        )
        rows = check_readme_quotes_decision(s)
        self.assertEqual(rows[0][0], "PASS", rows)

    def test_mos_before_duration_fails(self) -> None:
        s = self._sess(
            "2.16.0",
            "# README\nFair value vs price 10 vs 14; margin of safety 28%.\nDuration action: pass.\n",
        )
        rows = check_readme_quotes_decision(s)
        self.assertEqual(rows[0][0], "FAIL", rows)
        self.assertEqual(rows[0][1], "readme_cio_lead")


if __name__ == "__main__":
    unittest.main()

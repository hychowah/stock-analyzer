"""Wave 9 stop teaching the plug (harness >= 2.17.0)."""

from __future__ import annotations

import json
import unittest

from packages.kd_research.paths import PROJECT_ROOT as ROOT

from packages.kd_research.annuals import parse_semver


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class StopPlugTests(unittest.TestCase):
    def test_version_at_least_217(self) -> None:
        payload = json.loads((ROOT / "harness" / "VERSION").read_text(encoding="utf-8"))
        self.assertGreaterEqual(parse_semver(payload.get("harness_version")), (2, 17, 0))

    def test_growth_module_has_no_decay_paste_path(self) -> None:
        text = _read("harness/modules/sector_growth.md")
        self.assertNotIn("Project revenue using growth rate decay curve", text)
        self.assertNotIn("60% → 45% → 35%", text)
        self.assertNotIn("Base growth on: TAM penetration", text)
        self.assertIn("unit demand × share × price", text)
        self.assertIn("do **not** set `primary_sector` from this matrix", text)

    def test_s5_s12_do_not_shrug_to_standard(self) -> None:
        text = _read("harness/RESEARCH_AGENTS.md")
        self.assertNotIn("Confidence < 0.70 → use `standard`, set `requires_manual_review: true`", text)
        self.assertNotIn("Sector confidence < 0.70 → `standard` + manual-review flag.", text)
        self.assertIn("Do **not** auto-fallback to ordinary DCF", text)
        self.assertIn("Demand staple vs supply shock", text)
        self.assertIn("branded CPG", text)

    def test_agent5_not_unconditional_ordinary_dcf(self) -> None:
        text = _read("harness/agent_prompts.md")
        self.assertNotIn("Empty `module_file` → ordinary DCF; still honor", text)
        self.assertIn("only when §5 already chose `standard`", text)
        self.assertIn("lead module vs identity", text)
        self.assertIn("Do not PASS on schema-valid `sector_fit`", text)

    def test_check_session_header_not_force_standard(self) -> None:
        text = _read("scripts/check_session.py")
        self.assertIn("≥2.17.0 does not force standard", text)
        self.assertIn("(2, 17, 0)", text)


if __name__ == "__main__":
    unittest.main()

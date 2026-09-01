"""Harness 2.18.1: current destock/Street law-surface freeze (no machine change)."""

from __future__ import annotations

import json
import unittest

from packages.kd_research.paths import PROJECT_ROOT as ROOT

from packages.kd_research.annuals import parse_semver


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class LawSurfaceFreezeTests(unittest.TestCase):
    def test_version_at_least_2181(self) -> None:
        payload = json.loads((ROOT / "harness" / "VERSION").read_text(encoding="utf-8"))
        parsed = parse_semver(payload.get("harness_version"))
        self.assertIsNotNone(parsed)
        self.assertGreaterEqual(parsed, (2, 18, 1))

    def test_copying_street_fail_is_upper_bounded(self) -> None:
        text = _read("harness/RESEARCH_AGENTS.md")
        hits = [ln for ln in text.splitlines() if "copying Street still FAIL" in ln]
        self.assertTrue(hits, "expected historical Street-copy FAIL somewhere")
        for ln in hits:
            self.assertIn("< 2.18", ln, ln)

    def test_unbounded_211_keeps_tv_rp_changelog(self) -> None:
        text = _read("harness/RESEARCH_AGENTS.md")
        rows = [
            ln
            for ln in text.splitlines()
            if ln.startswith("| Harness ≥ 2.11.0:") and "< 2.18" not in ln
        ]
        self.assertTrue(rows, "expected unbounded ≥2.11.0 quality-gate row")
        blob = "\n".join(rows)
        self.assertIn("TV share", blob)
        self.assertIn("related-party", blob)
        self.assertIn("earning_power_changelog", blob)
        self.assertNotIn("copying Street still FAIL", blob)
        self.assertNotIn("destock is in base, DU=low", blob)

    def test_agent5_4e_no_file_existence_slash(self) -> None:
        prompts = _read("harness/agent_prompts.md")
        e_lines = [ln for ln in prompts.splitlines() if ln.strip().startswith("4e.")]
        self.assertTrue(e_lines)
        for ln in e_lines:
            self.assertNotIn("/ when street_estimates.json exists", ln)

    def test_agent5_fence_is_current_only(self) -> None:
        prompts = _read("harness/agent_prompts.md")
        self.assertNotIn("this prompt is 2.18", prompts)
        self.assertNotIn("4d wins 4e", prompts)
        self.assertIn("destock analog", prompts)
        self.assertIn("bear", prompts)
        self.assertIn("used_as:fy1_baseline", prompts)
        self.assertIn("4d` does **not** win `4e", prompts)
        self.assertIn("On 2.7–2.17 sessions", prompts)

    def test_independent_base_path_gone_from_current_law(self) -> None:
        self.assertNotIn("independent base path", _read("harness/RESEARCH_AGENTS.md"))
        self.assertNotIn("independent base path", _read("harness/filing_deep_dive.md"))

    def test_failure_catalog_f28_historical_f30_current(self) -> None:
        text = _read("eng/eval/failure_catalog.md")
        f28 = [ln for ln in text.splitlines() if ln.startswith("| F28 |")]
        self.assertTrue(f28)
        self.assertTrue(
            any("2.11" in ln or "2.12" in ln for ln in f28),
            f28,
        )
        f30 = [ln for ln in text.splitlines() if ln.startswith("| F30 |")]
        self.assertTrue(f30)
        blob = "\n".join(f30)
        self.assertIn("Destock", blob)
        self.assertIn("base", blob)
        self.assertIn("Street", blob)

    def test_harness_map_no_4d_wins_4e(self) -> None:
        text = _read("harness/HARNESS_MAP.md")
        self.assertNotIn("4d wins 4e", text)
        self.assertIn("4d` does **not** win `4e", text)
        self.assertIn("RESEARCH_AGENTS.md` §13", text)
        self.assertIn("§5 identity; modules advisory", text)

    def test_pair0_bad_reason_is_not_212_current_law(self) -> None:
        text = _read("harness/exemplars/hooks_quality.md")
        self.assertIn('"reason": "Y1 destock while Street FY+1 is usable."', text)
        bad = text.split("### GOOD")[0]
        self.assertNotIn(
            '"reason": "Unresolved flatten-vs-destock; destock default is base until cash/channel prove demand."',
            bad,
        )


if __name__ == "__main__":
    unittest.main()

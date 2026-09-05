"""Live Mode A operator files are current-only; history lives in law_history.md."""

from __future__ import annotations

import json
import unittest

from packages.kd_research.paths import PROJECT_ROOT as ROOT

from packages.kd_research.annuals import parse_semver


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


_LIVE_OPERATOR = (
    "AGENTS.md",
    "harness/RESEARCH_AGENTS.md",
    "harness/HARNESS_MAP.md",
    "harness/orchestrator_runbook.md",
    "harness/agent_prompts.md",
)


class LawSurfaceFreezeTests(unittest.TestCase):
    def test_version_at_least_2370(self) -> None:
        payload = json.loads((ROOT / "harness" / "VERSION").read_text(encoding="utf-8"))
        parsed = parse_semver(payload.get("harness_version"))
        self.assertIsNotNone(parsed)
        self.assertGreaterEqual(parsed, (2, 37, 0))

    def test_copying_street_fail_is_historical(self) -> None:
        for rel in _LIVE_OPERATOR:
            self.assertNotIn("copying Street still FAIL", _read(rel), rel)
        hist = _read("harness/law_history.md")
        hits = [ln for ln in hist.splitlines() if "copying Street still FAIL" in ln]
        self.assertTrue(hits, "expected historical Street-copy FAIL in law_history.md")
        for ln in hits:
            self.assertTrue("2.11" in ln or "< 2.18" in ln or "2.11.0" in hist, ln)

    def test_tv_rp_changelog_are_current_unbanded(self) -> None:
        text = _read("harness/RESEARCH_AGENTS.md")
        self.assertIn("TV share", text)
        self.assertIn("related-party", text)
        self.assertIn("earning_power_changelog", text)
        self.assertNotIn("copying Street still FAIL", text)
        self.assertFalse(
            any(
                ln.startswith("| Harness ≥ 2.11.0")
                for ln in text.splitlines()
            ),
            "changelog-style Harness ≥ 2.11.0 rows must not live in RESEARCH_AGENTS.md",
        )

    def test_218_street_row_is_not_live_operator(self) -> None:
        for rel in (
            "harness/RESEARCH_AGENTS.md",
            "harness/HARNESS_MAP.md",
            "harness/orchestrator_runbook.md",
        ):
            text = _read(rel)
            self.assertNotIn("| Harness ≥ 2.18.0 and < 2.28.0", text, rel)
            self.assertNotIn("On ≥ **2.18.0** and < **2.28.0**", text, rel)
        hist = _read("harness/law_history.md")
        self.assertIn("2.18.0–2.27.x", hist)
        self.assertIn("4d` does **not** win `4e", hist)

    def test_current_street_row(self) -> None:
        text = _read("harness/RESEARCH_AGENTS.md")
        self.assertIn("independent_y1", text)
        self.assertIn("destock_this_print", text)
        self.assertIn("street_baseline", text)
        self.assertFalse(
            any(ln.startswith("| Harness ≥ 2.28.0:") for ln in text.splitlines())
        )

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
        self.assertIn("independence_gate", prompts)
        self.assertIn("independent_y1", prompts)
        self.assertIn("destock_this_print", prompts)
        self.assertIn("used_as:fy1_baseline", prompts)
        agent5 = prompts.split("### Agent 5")[1].split("### Agent 12")[0]
        self.assertNotIn("4d` does **not** win `4e", agent5)
        self.assertNotIn("On 2.7–2.17 sessions", agent5)
        self.assertIn("do not load ROOT/harness/law_history.md", agent5)

    def test_independent_base_path_gone_from_current_law(self) -> None:
        self.assertNotIn("independent base path", _read("harness/RESEARCH_AGENTS.md"))
        self.assertNotIn("independent base path", _read("harness/filing_deep_dive.md"))

    def test_failure_catalog_f28_historical_f30_bounded_f34_current(self) -> None:
        text = _read("eng/eval/failure_catalog.md")
        f28 = [ln for ln in text.splitlines() if ln.startswith("| F28 |")]
        self.assertTrue(f28)
        self.assertTrue(
            any("2.11" in ln or "2.12" in ln for ln in f28),
            f28,
        )
        f30 = [ln for ln in text.splitlines() if ln.startswith("| F30 |")]
        self.assertTrue(f30)
        blob30 = "\n".join(f30)
        self.assertIn("Destock", blob30)
        self.assertIn("2.18", blob30)
        f34 = [ln for ln in text.splitlines() if ln.startswith("| F34 |")]
        self.assertTrue(f34)
        blob34 = "\n".join(f34)
        self.assertIn("2.28", blob34)
        self.assertIn("destock_this_print", blob34)

    def test_harness_map_current_street(self) -> None:
        text = _read("harness/HARNESS_MAP.md")
        self.assertNotIn("4d wins 4e", text)
        self.assertNotIn("< **2.28.0**", text)
        self.assertNotIn("4d` does **not** win `4e", text)
        self.assertIn("independent_y1", text)
        self.assertIn("destock_this_print", text)
        self.assertIn("RESEARCH_AGENTS.md` §10c", text)
        self.assertIn("§5 identity; modules advisory", text)

    def test_one_orch_bind_before_classify(self) -> None:
        ra = _read("harness/RESEARCH_AGENTS.md")
        self.assertIn("stamp `quote_symbol` + `verify_listing.py` → `bind_library.py`", ra)
        self.assertNotIn(
            "classify sector + market_context → write `registry/research_brief.json` → `bind_library.py`",
            ra,
        )
        runbook = _read("harness/orchestrator_runbook.md")
        self.assertIn("Finalize **copies** scaffold-time", runbook)
        self.assertNotIn("Finalize refreshes `harness_version`", runbook)
        prompts = _read("harness/agent_prompts.md")
        self.assertIn("`bind_library.py` **before** `sector_config`", prompts)
        self.assertNotIn("After research_brief (may overlap Phase 0), run", prompts)
        router = _read("AGENTS.md")
        self.assertIn("`bind_library.py` (before `sector_config`)", router)
        self.assertNotIn(
            "`research_brief` → `bind_library.py` (before 2b)",
            router,
        )

    def test_1d_waits_on_phase0_and_charts_after_25(self) -> None:
        ra = _read("harness/RESEARCH_AGENTS.md")
        self.assertIn("Phase 0 + 1b + 1c", ra)
        self.assertIn("Charts (phase 3) and reports (phase 4) start after 2.5", ra)
        design = _read("harness/design_phase_status_and_exemplars.md")
        self.assertIn("0 + 1b + 1c → 1d", design)
        self.assertNotIn("\n1b + 1c → 1d", design)
        self.assertIn("start **after 2_5**", design)
        self.assertNotIn("as soon as phase `2_parallel` is complete", design)

    def test_pair0_bad_reason_is_not_212_current_law(self) -> None:
        text = _read("harness/exemplars/hooks_quality.md")
        self.assertIn('"reason": "Y1 destock while Street FY+1 is usable."', text)
        bad = text.split("### GOOD")[0]
        self.assertNotIn(
            '"reason": "Unresolved flatten-vs-destock; destock default is base until cash/channel prove demand."',
            bad,
        )

    def test_law_history_exists_and_is_not_current(self) -> None:
        text = _read("harness/law_history.md")
        self.assertIn("Not current law", text)
        self.assertIn("2.18.0–2.27.x", text)
        prompts = _read("harness/agent_prompts.md")
        agent5 = prompts.split("### Agent 5")[1].split("### Agent 12")[0]
        self.assertIn("do not load ROOT/harness/law_history.md", agent5)


if __name__ == "__main__":
    unittest.main()

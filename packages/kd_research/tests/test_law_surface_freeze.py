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
        self.assertIn("default Y1 forecast", text)
        self.assertNotIn("no gate required", text)
        self.assertFalse(
            any(ln.startswith("| Harness ≥ 2.28.0:") for ln in text.splitlines())
        )
        hist = _read("harness/law_history.md")
        self.assertIn("no gate required", hist)
        self.assertIn("## 3.0.0 — independent Y1 default", hist)

    def test_agent5_4e_no_file_existence_slash(self) -> None:
        prompts = _read("harness/agent_prompts.md")
        e_lines = [ln for ln in prompts.splitlines() if ln.strip().startswith("4e.")]
        self.assertTrue(e_lines)
        for ln in e_lines:
            self.assertNotIn("/ when street_estimates.json exists", ln)

    def test_agent5_fence_loads_law_does_not_restate(self) -> None:
        prompts = _read("harness/agent_prompts.md")
        self.assertNotIn("this prompt is 2.18", prompts)
        self.assertNotIn("4d wins 4e", prompts)
        agent5 = prompts.split("### Agent 5")[1].split("### Agent 12")[0]
        self.assertIn("§10c", agent5)
        self.assertIn("§10d", agent5)
        self.assertIn("§10e", agent5)
        self.assertIn("§10f", agent5)
        self.assertIn("Do not load ROOT/harness/law_history.md", agent5)
        self.assertNotIn("Y1 LAW", agent5)
        self.assertNotIn("STREET IS THE DEFAULT Y1 START", agent5)
        self.assertNotIn("4d` does **not** win `4e", agent5)
        self.assertNotIn("On 2.7–2.17 sessions", agent5)
        self.assertNotIn("|delta|>5% FAIL", agent5)
        self.assertNotIn("Independent Y1 is default", agent5)
        self.assertNotIn("banks never FCFF/WACC", agent5)
        self.assertIn("§8 **5b**", agent5)
        ra = _read("harness/RESEARCH_AGENTS.md")
        eight = ra.split("## 8.")[1].split("## 9.")[0]
        self.assertIn("stress_bind", eight)
        self.assertIn("roc_screen_rebuttal", eight)
        self.assertIn("size_cap", eight)
        self.assertIn("compute_stress_bind", eight)

    def test_section1_stress_book_is_derived(self) -> None:
        one = _read("harness/RESEARCH_AGENTS.md").split("## 1.")[1].split("## 2.")[0]
        self.assertNotIn("stress haircuts, position sizing", one)
        self.assertIn("fair_value_under", one)
        self.assertIn("compute_stress_bind", one)
        self.assertIn("§10f", one)
        self.assertNotIn("required_mos_addon", _read("harness/agent_prompts.md"))

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

    def test_harness_map_points_at_law_homes(self) -> None:
        text = _read("harness/HARNESS_MAP.md")
        self.assertNotIn("4d wins 4e", text)
        self.assertNotIn("< **2.28.0**", text)
        self.assertNotIn("4d` does **not** win `4e", text)
        self.assertNotIn("independent_y1", text)
        self.assertNotIn("destock_this_print", text)
        self.assertIn("§10c", text)
        self.assertIn("§10d", text)
        self.assertIn("§10e", text)
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

    def test_1d_waits_on_phase0_and_charts_after_valuation(self) -> None:
        ra = _read("harness/RESEARCH_AGENTS.md")
        self.assertIn("Phase 0 + 1b (**not** 1c)", ra)
        self.assertIn("Charts (phase 3) start after Agent 5", ra)
        self.assertNotIn("Charts (phase 3) and reports (phase 4) start after 2.5", ra)
        design = _read("harness/design_phase_status_and_exemplars.md")
        self.assertIn("0 + 1b → 1d", design)
        self.assertNotIn("0 + 1b + 1c → 1d", design)
        self.assertIn("0 + 1b + 1c + 1d → 1e", design)
        ra = _read("harness/RESEARCH_AGENTS.md")
        self.assertIn("registry/classification.json", ra)
        self.assertIn("**1e** (harness ≥ 3.4.0)", ra)
        self.assertIn("start after Agent 5", design)
        self.assertNotIn("start **after 2_5**, same as reports", design)
        self.assertNotIn("as soon as phase `2_parallel` is complete", design)
        hist = _read("harness/law_history.md")
        self.assertIn("2.44.x graph joins", hist)
        runbook = _read("harness/orchestrator_runbook.md")
        self.assertIn("after Phase 0 + 1b, not 1c", runbook)
        self.assertNotIn("Phase 1d (after Phase 0 + 1b + 1c)", runbook)
        self.assertNotIn("both wait on 2.5", runbook)

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
        self.assertIn("Do not load ROOT/harness/law_history.md", agent5)

    def test_no_restated_y1_roic_wacc_essays_outside_homes(self) -> None:
        """Maps, Agent 5/13, and schema descriptions point; they do not restate §10c–e."""
        ra = _read("harness/RESEARCH_AGENTS.md")
        self.assertIn("## 10c.", ra)
        self.assertIn("## 10d.", ra)
        self.assertIn("## 10e.", ra)
        self.assertIn("independent_y1", ra)
        self.assertIn("destock_this_print", ra)
        prompts = _read("harness/agent_prompts.md")
        agent5 = prompts.split("### Agent 5")[1].split("### Agent 12")[0]
        agent13 = prompts.split("### Agent 13")[1]
        for blob, name in ((agent5, "agent5"), (agent13, "agent13")):
            self.assertNotIn("keep_independent_vs_street is illegal", blob, name)
            self.assertNotIn("coupon is not Kd", blob, name)
        schema = _read("harness/schemas/valuation_model.schema.json")
        self.assertNotIn("On 2.7-2.17", schema)
        self.assertNotIn("On 2.18-2.27", schema)
        self.assertIn("RESEARCH_AGENTS.md §10c", schema)


if __name__ == "__main__":
    unittest.main()

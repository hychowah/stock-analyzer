"""Law/prompt regressions: sector modules do not classify (W1 2.7.1)."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BANNER = "signals/sub-type after identity"
SECTOR_FILES = (
    "sector_cyclical.md",
    "sector_growth.md",
    "sector_banking.md",
    "sector_insurance.md",
    "sector_reit.md",
    "sector_utility.md",
)


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class SectorClassificationLawTests(unittest.TestCase):
    def test_cyclical_has_no_any_of_mandate(self):
        text = _read("sector_cyclical.md")
        self.assertNotIn("classified as cyclical if ANY", text)
        self.assertNotIn("classified as **cyclical** if ANY", text)
        self.assertNotIn("Automatic Detection Logic", text)
        self.assertIn("Do not set `primary_sector`", text)
        self.assertIn("realized at", text.lower())
        self.assertIn("branded retail", text.lower())
        self.assertIn("Unbranded protein", text)

    def test_research_agents_s5_s9(self):
        text = _read("harness/RESEARCH_AGENTS.md")
        self.assertIn("no scoring algorithm", text.lower())
        self.assertIn("Sector modules do not classify", text)
        self.assertIn("Demand staple vs supply shock", text)
        self.assertIn("branded CPG", text)
        self.assertIn("posted-price", text.lower())
        self.assertIn("this section wins", text.lower())
        self.assertIn("diagnostic only", text.lower())
        self.assertIn("Empty `module_file` is valid for `standard`", text)

    def test_other_modules_diagnostic_banner(self):
        for name in SECTOR_FILES:
            text = _read(name)
            self.assertIn(
                BANNER,
                text,
                msg=f"{name} missing §1 diagnostic banner ({BANNER!r})",
            )

    def test_growth_matrix_is_not_a_classifier(self):
        text = _read("sector_growth.md")
        self.assertNotIn("A company qualifies for \"growth company modified analysis\" if", text)
        self.assertIn("do **not** set `primary_sector` from this matrix", text)

    def test_banking_signals_not_return_true(self):
        text = _read("sector_banking.md")
        # Detection pseudocode must not assign identity with return True
        self.assertNotIn("return True, \"industry_code\"", text)
        self.assertIn("def banking_signals", text)

    def test_agent13_challenges_lead_module_identity(self):
        text = _read("harness/agent_prompts.md")
        self.assertIn("lead module vs identity", text)
        self.assertIn("Do not PASS on schema-valid `sector_fit`", text)
        self.assertIn("when `sector_config.module_file` is empty", text.lower())

    def test_phase25_empty_module_stress(self):
        text = _read("harness/agent_prompts.md")
        self.assertIn("must_cover_risks", text)
        self.assertIn("module_file` is empty", text)

    def test_orchestrator_classifies_from_s5(self):
        runbook = _read("harness/orchestrator_runbook.md")
        self.assertIn("§5 first", runbook)
        prompts = _read("harness/agent_prompts.md")
        self.assertIn("Classify from `ROOT/harness/RESEARCH_AGENTS.md` §5 first", prompts)

    def test_harness_map_orch_clause(self):
        text = _read("harness/HARNESS_MAP.md")
        self.assertIn("§5 identity; modules advisory", text)


if __name__ == "__main__":
    unittest.main()

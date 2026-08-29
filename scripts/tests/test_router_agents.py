"""Root AGENTS.md is a short dual-mode router; research law is nested."""

from __future__ import annotations

import unittest
from pathlib import Path

from packages.kd_research.paths import PROJECT_ROOT as ROOT


class RouterAgentsTests(unittest.TestCase):
    def test_router_short_and_points(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        lines = agents.splitlines()
        self.assertLessEqual(len(lines), 150, msg=f"router too long: {len(lines)} lines")
        self.assertIn("harness/RESEARCH_AGENTS.md", agents)
        self.assertIn("eng/AGENTS.md", agents)
        self.assertIn("Mode A", agents)
        self.assertIn("Mode B", agents)

    def test_research_agents_exists_and_has_pipeline(self):
        path = ROOT / "harness" / "RESEARCH_AGENTS.md"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn("justification contract", text.lower())
        self.assertIn("phase", text.lower())
        self.assertGreater(len(text.splitlines()), 100)


if __name__ == "__main__":
    unittest.main()

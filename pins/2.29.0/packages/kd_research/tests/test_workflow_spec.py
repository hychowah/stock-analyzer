"""workflow_spec dump and agent_prompts heading parser."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest

from packages.kd_research.library import BIND_REL, LIBRARY_SINCE
from packages.kd_research.operating_path import BRIEF_REL, OPPATH_SINCE
from packages.kd_research.paths import PROJECT_ROOT as ROOT
from packages.kd_research.phase_status import PHASE_AGENTS
from packages.kd_research.provenance import load_harness_identity
from packages.kd_research.spawn_gate import SPECIALIST_ARTIFACTS
from packages.kd_research.workflow_spec import (
    AGENT_HEADING_RE,
    agent_prompt_payload,
    build_workflow_spec,
    missing_prompt_ids,
    parse_agent_prompts,
)


class WorkflowSpecTests(unittest.TestCase):
    def test_every_phase_agent_has_heading(self) -> None:
        missing = missing_prompt_ids()
        self.assertEqual(missing, [], missing)

    def test_parse_longest_id(self) -> None:
        text = (
            "conventions here\n\n"
            "### Agent orchestrator\nlead\n"
            "### Agent 2e-year — single annual\nyear body\n"
            "### Agent 2e — merger\nmerge body\n"
        )
        parsed = parse_agent_prompts(text)
        self.assertIn("2e-year", parsed)
        self.assertIn("2e", parsed)
        self.assertIn("year body", parsed["2e-year"]["body"])
        self.assertIn("merge body", parsed["2e"]["body"])
        self.assertNotIn("merge body", parsed["2e-year"]["body"])
        self.assertIn("conventions here", parsed["_conventions"]["body"])

    def test_heading_regex(self) -> None:
        self.assertIsNotNone(AGENT_HEADING_RE.match("### Agent 5 — valuation (`coder`)"))
        self.assertIsNotNone(AGENT_HEADING_RE.match("### Agent phase0_swarm"))
        self.assertIsNone(AGENT_HEADING_RE.match("## Phase 0 — Background"))

    def test_spec_shape(self) -> None:
        spec = build_workflow_spec()
        ident = load_harness_identity(ROOT)
        self.assertEqual(spec["harness_version"], ident["harness_version"])
        ids = [p["id"] for p in spec["phases"]]
        self.assertEqual(ids, [pid for pid, _ in PHASE_AGENTS])
        self.assertTrue(spec["conventions_present"])
        self.assertEqual(spec["missing_prompt_ids"], [])
        self.assertTrue(any(e.get("kind") == "write" for e in spec["edges"]))
        self.assertTrue(any(e.get("kind") == "entry" for e in spec["edges"]))
        p2 = next(p for p in spec["phases"] if p["id"] == "2_parallel")
        paths = {row["path"] for row in p2["entry"]}
        self.assertIn(BRIEF_REL, paths)
        self.assertIn("registry/filing_deep_dive.json", paths)
        self.assertIn("data/price_snapshot.json", paths)
        p1 = next(p for p in spec["phases"] if p["id"] == "1_parallel")
        self.assertIn(BIND_REL, {row["path"] for row in p1["entry"]})
        a4 = next(a for a in p2["agents"] if a["id"] == "4")
        self.assertIn("registry/technical.json", a4["writes"])
        self.assertNotIn("registry/filing_deep_dive.json", a4["writes"])
        self.assertIn("technical.json", SPECIALIST_ARTIFACTS["4"][0])
        _ = LIBRARY_SINCE, OPPATH_SINCE

    def test_agent_5_slice(self) -> None:
        payload = agent_prompt_payload("5")
        self.assertTrue(payload["found"])
        self.assertIn("### Agent 5", payload["title"] or "")
        self.assertIn("valuation", payload["body"].lower())
        self.assertNotIn("### Agent 12", payload["body"])
        self.assertTrue(payload["conventions"])

    def test_subprocess_matches_inprocess(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "packages.kd_research.workflow_spec"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        dumped = json.loads(proc.stdout)
        spec = build_workflow_spec()
        self.assertEqual(dumped["harness_version"], spec["harness_version"])
        self.assertEqual(len(dumped["phases"]), len(spec["phases"]))


if __name__ == "__main__":
    unittest.main()

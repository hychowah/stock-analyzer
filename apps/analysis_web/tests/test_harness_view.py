"""Unit tests for the /harness page model."""

from __future__ import annotations

import unittest

from apps.analysis_web.services.harness_view import (
    convention_items,
    file_chip,
    harness_page_model,
    parse_agent_title,
    structure_prompt,
    structure_prompt_payload,
)

_PREAMBLE = """# Subagent Prompt Templates

| Variable | Example |
|---|---|
| `TICKER` | `JPM` |

Every template already carries the justification contract — do not strip it.

**Conventions for all agents:**
- **Yahoo listing**: yfinance uses quote_symbol
- **Hermetic scripts**: read session cache
  continuation line
"""

_SPEC = {
    "harness_version": "2.32.0",
    "harness_spec": "test",
    "phases": [
        {
            "id": "orch",
            "agents": [
                {
                    "id": "orchestrator",
                    "title": "### Agent orchestrator",
                    "writes": [],
                    "prompt_present": True,
                }
            ],
            "entry": [],
        },
        {
            "id": "1_parallel",
            "agents": [
                {
                    "id": "2b",
                    "title": "### Agent 2b — SEC filings (`coder`)",
                    "writes": ["registry/sec_filings.json"],
                    "prompt_present": True,
                }
            ],
            "entry": [
                {"path": "registry/library_bind.json", "required": True, "since": "2.19.0"},
                {"path": "registry/sec_filings.json", "required": True},
            ],
        },
        {
            "id": "2_parallel",
            "agents": [
                {
                    "id": "5",
                    "title": "### Agent 5 — valuation (`coder`)",
                    "writes": ["data/valuation_model.json"],
                    "prompt_present": True,
                },
                {
                    "id": "6",
                    "title": "### Agent 6",
                    "writes": ["charts/*.png"],
                    "prompt_present": True,
                },
            ],
            "entry": [{"path": "data/price_snapshot.json", "required": True}],
        },
        {"id": "mystery", "agents": [], "entry": []},
    ],
    "edges": [{"from": "5", "to": "data/valuation_model.json", "kind": "write"}],
    "annotations": [
        {
            "id": "bind_library",
            "before": "2b",
            "path": "registry/library_bind.json",
            "since": "2.19.0",
        },
        {
            "id": "price_snapshot",
            "before": "2_parallel",
            "path": "data/price_snapshot.json",
            "note": "Orchestrator freeze before Phase 2.",
        },
        {
            "id": "spawn_or_abandon",
            "since": "2.20.0",
            "note": "Specialists must be spawn_subagent.",
        },
        {
            "id": "5b",
            "phase": "2_5",
            "agent": "orchestrator",
            "note": "Do not spawn subagent 5 in 2_5.",
        },
    ],
}


def _phases(model: dict) -> dict:
    out = {}
    for stage in model["stages"]:
        for phase in stage["phases"]:
            out[phase["id"]] = (stage["id"], phase)
    return out


class FileChipTests(unittest.TestCase):
    def test_basename(self):
        chip = file_chip("registry/background.json")
        self.assertEqual(chip["name"], "background.json")
        self.assertEqual(chip["label"], "background.json")
        self.assertEqual(chip["folder"], "registry")
        self.assertEqual(chip["path"], "registry/background.json")

    def test_glob_keeps_full_path_as_label(self):
        chip = file_chip("charts/*.png")
        self.assertEqual(chip["label"], "charts/*.png")
        self.assertEqual(chip["name"], "*.png")


class ParseTitleTests(unittest.TestCase):
    def test_em_dash_and_spawn_role(self):
        parsed = parse_agent_title("### Agent 5 — valuation (`coder`)", "5")
        self.assertEqual(parsed["label"], "Valuation")
        self.assertEqual(parsed["spawn_role"], "coder")

    def test_untitled_uses_label_table(self):
        parsed = parse_agent_title("### Agent orchestrator", "orchestrator")
        self.assertEqual(parsed["label"], "Orchestrator")
        self.assertIsNone(parsed["spawn_role"])

    def test_untitled_2d(self):
        parsed = parse_agent_title("### Agent 2d", "2d")
        self.assertEqual(parsed["label"], "Latest quarter")


class PromptStructureTests(unittest.TestCase):
    def test_fence_split(self):
        body = (
            "### Agent 5 — valuation (`coder`)\n\n"
            "**Anti-anchoring:** stay in session.\n\n"
            "```text\nRole: model designer\nWrite the DCF.\n```\n\n"
            "**5b — decision reopen:** orchestrator lead.\n"
        )
        structured = structure_prompt(body)
        ids = [s["id"] for s in structured["sections"]]
        self.assertEqual(ids, ["briefing", "template", "follow_on"])
        self.assertIn("model designer", structured["role_line"])
        self.assertTrue(structured["summary"].startswith("Anti-anchoring"))

    def test_payload_keeps_found_title_body(self):
        payload = structure_prompt_payload(
            {
                "id": "5",
                "found": True,
                "title": "### Agent 5 — valuation (`coder`)",
                "body": "### Agent 5 — valuation (`coder`)\n\n```text\nDo the DCF.\n```\n",
                "conventions": _PREAMBLE,
            }
        )
        self.assertTrue(payload["found"])
        self.assertIn("### Agent 5", payload["title"])
        self.assertIn("Do the DCF", payload["body"])
        self.assertEqual(payload["label"], "Valuation")
        self.assertEqual(payload["spawn_role"], "coder")
        self.assertTrue(any(s["id"] == "template" for s in payload["sections"]))
        titles = [i["title"] for i in payload["conventions_items"]]
        self.assertEqual(titles, ["Yahoo listing", "Hermetic scripts"])


class ConventionItemsTests(unittest.TestCase):
    def test_skips_variable_table(self):
        items = convention_items(_PREAMBLE)
        titles = [i["title"] for i in items]
        self.assertEqual(titles, ["Yahoo listing", "Hermetic scripts"])
        self.assertNotIn("Variable", titles)
        self.assertNotIn("TICKER", " ".join(titles))
        self.assertIn("continuation", items[1]["html"])

    def test_empty_falls_back_to_caller(self):
        self.assertEqual(convention_items(""), [])
        self.assertEqual(convention_items("# Intro only\n\nNo bullets.\n"), [])


class PageModelTests(unittest.TestCase):
    def test_display_only_keys(self):
        model = harness_page_model(_SPEC, conventions=_PREAMBLE)
        self.assertNotIn("edges", model)
        self.assertNotIn("agent_index", model)
        self.assertNotIn("phase_index", model)
        self.assertNotIn("phases", model)
        self.assertEqual(model["harness_version"], "2.32.0")
        self.assertEqual(model["agent_count"], 4)
        self.assertEqual(model["phase_count"], 4)
        conv_titles = [i["title"] for i in model["conventions"]["cards"]]
        self.assertEqual(conv_titles, ["Yahoo listing", "Hermetic scripts"])

    def test_stages_and_labels(self):
        model = harness_page_model(_SPEC)
        by = _phases(model)
        self.assertEqual(by["orch"][0], "setup")
        self.assertEqual(by["orch"][1]["label"], "Classify & brief")
        self.assertEqual(by["1_parallel"][0], "gather")
        self.assertEqual(by["1_parallel"][1]["label"], "Source facts")
        self.assertEqual(by["2_parallel"][0], "decide")
        self.assertEqual(by["2_parallel"][1]["label"], "Valuation")
        self.assertEqual(by["mystery"][0], "other")
        self.assertEqual(by["mystery"][1]["label"], "mystery")
        self.assertEqual(by["mystery"][1]["purpose"], "")

    def test_agents_are_new_dicts(self):
        model = harness_page_model(_SPEC)
        phase = _phases(model)["2_parallel"][1]
        agent5 = next(a for a in phase["agents"] if a["id"] == "5")
        self.assertEqual(agent5["label"], "Valuation")
        self.assertEqual(agent5["spawn_role"], "coder")
        self.assertNotIn("title", agent5)
        self.assertNotIn("writes", agent5)
        self.assertEqual(agent5["primary_write"]["label"], "valuation_model.json")
        agent6 = next(a for a in phase["agents"] if a["id"] == "6")
        self.assertEqual(agent6["label"], "Charts")
        self.assertEqual(agent6["write_chips"][0]["label"], "charts/*.png")

    def test_bind_library_lands_on_agent_2b(self):
        model = harness_page_model(_SPEC)
        phase = _phases(model)["1_parallel"][1]
        agent = phase["agents"][0]
        self.assertEqual(agent["id"], "2b")
        ids = [n["id"] for n in agent["notes"]]
        self.assertIn("bind_library", ids)
        self.assertFalse(any(n["id"] == "bind_library" for n in phase["notes"]))
        self.assertNotIn("2b", _phases(model))

    def test_price_snapshot_on_phase_and_spawn_on_page(self):
        model = harness_page_model(_SPEC)
        phase = _phases(model)["2_parallel"][1]
        self.assertTrue(any(n["id"] == "price_snapshot" for n in phase["notes"]))
        page_ids = [n["id"] for n in model["notes"]]
        self.assertIn("spawn_or_abandon", page_ids)
        # 2_5 is not in this spec, so 5b cannot attach to a missing phase
        self.assertIn("5b", page_ids)

    def test_producer_only_on_exact_write_match(self):
        model = harness_page_model(_SPEC)
        facts = _phases(model)["1_parallel"][1]
        by_path = {n["path"]: n for n in facts["needs"]}
        self.assertNotIn("producer", by_path["registry/library_bind.json"])
        self.assertEqual(by_path["registry/sec_filings.json"]["producer"], "2b")
        self.assertEqual(by_path["registry/sec_filings.json"]["producer_label"], "SEC filings")
        val = _phases(model)["2_parallel"][1]
        snap = val["needs"][0]
        self.assertEqual(snap["path"], "data/price_snapshot.json")
        self.assertNotIn("producer", snap)


if __name__ == "__main__":
    unittest.main()

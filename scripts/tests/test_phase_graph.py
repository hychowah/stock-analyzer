"""Phase graph + subagent binding tests."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.kd_research.phase_graph import (  # noqa: E402
    check_phase_graph_entry,
    check_phase_status_graph,
    normalize_subagent_id,
    subagent_allowed_in_phase,
)
from scripts.kd_research.phase_status import build_phase_status_skeleton  # noqa: E402
from scripts.kd_research.gates import entry_checks  # noqa: E402


def _write_status(session: Path, data: dict) -> None:
    p = session / "registry" / "phase_status.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _set_phase(data: dict, phase_id: str, status: str) -> None:
    for ph in data["phases"]:
        if ph["phase_id"] == phase_id:
            ph["status"] = status
            for ag in ph.get("agents") or []:
                if status == "complete":
                    ag["status"] = "complete"
            return


class SubagentNamingTests(unittest.TestCase):
    def test_normalize_subagent_aliases(self):
        self.assertEqual(normalize_subagent_id("5"), "5")
        self.assertEqual(normalize_subagent_id("valuation"), "5")
        self.assertEqual(normalize_subagent_id("Agent 5"), "5")
        self.assertEqual(normalize_subagent_id("subagent_2e"), "2e")

    def test_subagent_phase_binding(self):
        ok, _ = subagent_allowed_in_phase("5", "2_parallel")
        self.assertTrue(ok)
        ok, detail = subagent_allowed_in_phase("5", "0")
        self.assertFalse(ok)
        self.assertIn("2_parallel", detail)
        ok, _ = subagent_allowed_in_phase("orchestrator", "5")
        self.assertTrue(ok)


class PhaseGraphEntryTests(unittest.TestCase):
    def test_prereq_blocks_jump_to_2_parallel(self):
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            data = build_phase_status_skeleton("META", "2026-08-10")
            # only orch complete
            _set_phase(data, "orch", "complete")
            data["current_phase"] = "0"
            _write_status(s, data)
            rows = check_phase_graph_entry(s, "2_parallel", subagent_id="5")
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertTrue(any("prereq" in r[1] for r in fails), fails)
            self.assertTrue(
                any(r[1] == "phase_graph.subagent_phase" and r[0] == "PASS" for r in rows),
                rows,
            )

    def test_wrong_subagent_fails(self):
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            data = build_phase_status_skeleton("META", "2026-08-10")
            for pid in ("orch", "0", "1_parallel", "1b", "1c"):
                _set_phase(data, pid, "complete")
            data["current_phase"] = "2_parallel"
            _write_status(s, data)
            rows = check_phase_graph_entry(s, "2_parallel", subagent_id="13")
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertTrue(any("subagent_phase" in r[1] for r in fails), fails)

    def test_entry_checks_includes_subagent_gate(self):
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            data = build_phase_status_skeleton("X", "2026-01-01")
            for pid in ("orch", "0", "1_parallel", "1b", "1c"):
                _set_phase(data, pid, "complete")
            data["current_phase"] = "2_parallel"
            _write_status(s, data)
            for rel in (
                "registry/sector_config.json",
                "registry/market_context.json",
                "registry/sec_filings.json",
                "registry/latest_quarter.json",
                "registry/filing_deep_dive.json",
            ):
                p = s / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(json.dumps({"ticker": "X", "session_date": "2026-01-01"}), encoding="utf-8")
            (s / "data").mkdir(parents=True, exist_ok=True)
            (s / "data" / "sp_financials.csv").write_text("ticker,item\nX,1\n", encoding="utf-8")
            man = s / "meta" / "run_manifest.json"
            man.parent.mkdir(parents=True, exist_ok=True)
            man.write_text(
                json.dumps(
                    {
                        "status": "scaffolded",
                        "orchestrator_model": "grok-4.5",
                        "default_subagent_model": "grok-4.5",
                    }
                ),
                encoding="utf-8",
            )
            rows = entry_checks(s, "2_parallel", ticker="X", subagent_id="5")
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertEqual(fails, [], fails)

    def test_order_integrity(self):
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            data = build_phase_status_skeleton("X", "2026-01-01")
            _set_phase(data, "5", "complete")  # later complete while orch pending
            _write_status(s, data)
            rows = check_phase_status_graph(s)
            self.assertTrue(any(r[0] == "FAIL" and "order_integrity" in r[1] for r in rows), rows)


if __name__ == "__main__":
    unittest.main()

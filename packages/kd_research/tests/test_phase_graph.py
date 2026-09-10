"""Phase graph + subagent binding tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.gates import entry_checks
from packages.kd_research.paths import PROJECT_ROOT
from packages.kd_research.phase_graph import (
    PHASE_ANNOTATIONS,
    PHASE_GRAPH,
    PHASE_IDS,
    check_phase_graph_entry,
    check_phase_status_graph,
    check_phase_status_order_integrity,
    normalize_subagent_id,
    phase_status_map,
    subagent_allowed_in_phase,
)
from packages.kd_research.phase_status import build_phase_status_skeleton


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
        self.assertEqual(normalize_subagent_id("revenue_growth"), "1d_rev")
        self.assertEqual(normalize_subagent_id("oppath"), "1d_merge")

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

    def test_price_snapshot_required_since_242(self):
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            data = build_phase_status_skeleton("X", "2026-01-01")
            for pid in ("orch", "0", "1_parallel", "1b", "1c", "1d"):
                _set_phase(data, pid, "complete")
            data["current_phase"] = "2_parallel"
            _write_status(s, data)
            for rel in (
                "registry/sector_config.json",
                "registry/market_context.json",
                "registry/sec_filings.json",
                "registry/latest_quarter.json",
                "registry/filing_deep_dive.json",
                "registry/operating_path_brief.json",
            ):
                p = s / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(
                    json.dumps({"ticker": "X", "session_date": "2026-01-01"}),
                    encoding="utf-8",
                )
            (s / "data").mkdir(parents=True, exist_ok=True)
            (s / "data" / "sp_financials.csv").write_text(
                "ticker,item\nX,1\n", encoding="utf-8"
            )
            man = s / "meta" / "run_manifest.json"
            man.parent.mkdir(parents=True, exist_ok=True)
            man.write_text(
                json.dumps(
                    {
                        "status": "scaffolded",
                        "orchestrator_model": "grok-4.5",
                        "default_subagent_model": "grok-4.5",
                        "harness_version": "2.42.0",
                    }
                ),
                encoding="utf-8",
            )
            rows = entry_checks(s, "2_parallel", ticker="X")
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertTrue(
                any("price_snapshot" in r[1] for r in fails),
                fails,
            )
            (s / "data" / "price_snapshot.json").write_text("{}\n", encoding="utf-8")
            rows2 = entry_checks(s, "2_parallel", ticker="X")
            snap_fails = [
                r for r in rows2 if r[0] == "FAIL" and "price_snapshot" in r[1]
            ]
            self.assertEqual(snap_fails, [], rows2)

    def test_order_integrity(self):
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            data = build_phase_status_skeleton("X", "2026-01-01")
            _set_phase(data, "5", "complete")  # later complete while orch pending
            _write_status(s, data)
            rows = check_phase_status_graph(s)
            self.assertTrue(any(r[0] == "FAIL" and "order_integrity" in r[1] for r in rows), rows)


class Phase0ParallelTests(unittest.TestCase):
    def test_230_1_parallel_does_not_wait_on_phase0(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            (s / "meta").mkdir(parents=True)
            (s / "meta" / "run_manifest.json").write_text(
                json.dumps(
                    {
                        "status": "scaffolded",
                        "orchestrator_model": "grok-4.5",
                        "harness_version": "2.30.0",
                    }
                ),
                encoding="utf-8",
            )
            data = build_phase_status_skeleton("X", "2026-01-01")
            _set_phase(data, "orch", "complete")
            data["current_phase"] = "1_parallel"
            _write_status(s, data)
            rows = check_phase_graph_entry(s, "1_parallel", subagent_id="2a")
            fails = [r for r in rows if r[0] == "FAIL" and "prereq.0" in r[1]]
            self.assertEqual(fails, [], rows)

    def test_229_1_parallel_still_waits_on_phase0(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            (s / "meta").mkdir(parents=True)
            (s / "meta" / "run_manifest.json").write_text(
                json.dumps(
                    {
                        "status": "scaffolded",
                        "orchestrator_model": "grok-4.5",
                        "harness_version": "2.29.0",
                    }
                ),
                encoding="utf-8",
            )
            data = build_phase_status_skeleton("X", "2026-01-01")
            _set_phase(data, "orch", "complete")
            data["current_phase"] = "1_parallel"
            _write_status(s, data)
            rows = check_phase_graph_entry(s, "1_parallel", subagent_id="2a")
            self.assertTrue(
                any(r[0] == "FAIL" and "prereq.0" in r[1] for r in rows),
                rows,
            )

    def test_230_1d_still_waits_on_phase0(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            (s / "meta").mkdir(parents=True)
            (s / "meta" / "run_manifest.json").write_text(
                json.dumps(
                    {
                        "status": "scaffolded",
                        "orchestrator_model": "grok-4.5",
                        "harness_version": "2.30.0",
                    }
                ),
                encoding="utf-8",
            )
            data = build_phase_status_skeleton("X", "2026-01-01")
            for pid in ("orch", "1_parallel", "1b", "1c"):
                _set_phase(data, pid, "complete")
            data["current_phase"] = "1d"
            _write_status(s, data)
            rows = check_phase_graph_entry(s, "1d", subagent_id="1d_rev")
            self.assertTrue(
                any(r[0] == "FAIL" and "prereq.0" in r[1] for r in rows),
                rows,
            )


class GraphContractTests(unittest.TestCase):
    def test_graph_ids_match_schema_and_skeleton(self) -> None:
        schema_path = PROJECT_ROOT / "harness" / "schemas" / "phase_status.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        enum = schema["definitions"]["phase_id"]["enum"]
        self.assertEqual(list(PHASE_IDS), enum)
        skeleton = build_phase_status_skeleton("X", "2026-01-01")
        self.assertEqual([p["phase_id"] for p in skeleton["phases"]], list(PHASE_IDS))

    def test_spawn_subset_of_subagents(self) -> None:
        for node in PHASE_GRAPH:
            self.assertTrue(
                set(node.spawn_ids) <= set(node.subagents),
                f"{node.phase_id}: spawn {node.spawn_ids} not in {node.subagents}",
            )

    def test_5b_is_annotation_not_phase_id(self) -> None:
        self.assertNotIn("5b", PHASE_IDS)
        self.assertIn("5b", PHASE_ANNOTATIONS)

    def test_230_1_parallel_complete_while_0_pending_is_legal(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            (s / "meta").mkdir(parents=True)
            (s / "meta" / "run_manifest.json").write_text(
                json.dumps(
                    {
                        "status": "scaffolded",
                        "orchestrator_model": "grok-4.5",
                        "harness_version": "2.30.0",
                    }
                ),
                encoding="utf-8",
            )
            data = build_phase_status_skeleton("X", "2026-01-01")
            _set_phase(data, "orch", "complete")
            _set_phase(data, "1_parallel", "complete")
            _write_status(s, data)
            rows = check_phase_status_graph(s)
            fails = [r for r in rows if r[0] == "FAIL" and "order_integrity" in r[1]]
            self.assertEqual(fails, [], rows)

    def test_229_1_parallel_complete_while_0_pending_is_illegal(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            (s / "meta").mkdir(parents=True)
            (s / "meta" / "run_manifest.json").write_text(
                json.dumps(
                    {
                        "status": "scaffolded",
                        "orchestrator_model": "grok-4.5",
                        "harness_version": "2.29.0",
                    }
                ),
                encoding="utf-8",
            )
            data = build_phase_status_skeleton("X", "2026-01-01")
            _set_phase(data, "orch", "complete")
            _set_phase(data, "1_parallel", "complete")
            _write_status(s, data)
            rows = check_phase_status_graph(s)
            self.assertTrue(
                any(r[0] == "FAIL" and "order_integrity" in r[1] for r in rows),
                rows,
            )

    def test_charts_and_reports_are_siblings_after_2_5(self) -> None:
        data = build_phase_status_skeleton("X", "2026-01-01")
        for pid in (
            "orch",
            "0",
            "1_parallel",
            "1b",
            "1c",
            "1d",
            "2_parallel",
            "2_5",
            "3",
        ):
            _set_phase(data, pid, "complete")
        smap = phase_status_map(data)
        rows = check_phase_status_order_integrity(smap)
        self.assertEqual([r for r in rows if r[0] == "FAIL"], [], rows)
        _set_phase(data, "3", "pending")
        _set_phase(data, "4_parallel", "complete")
        smap = phase_status_map(data)
        rows = check_phase_status_order_integrity(smap)
        self.assertEqual([r for r in rows if r[0] == "FAIL"], [], rows)


if __name__ == "__main__":
    unittest.main()

"""Specialist spawn discipline (harness >= 2.20.0) and abandon path."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.kd_research.gates import complete_checks, entry_checks  # noqa: E402
from scripts.kd_research.phase_graph import (  # noqa: E402
    check_phase_status_graph,
    home_phase_for_subagent,
    normalize_subagent_id,
    subagent_allowed_in_phase,
)
from scripts.kd_research.phase_status import build_phase_status_skeleton  # noqa: E402
from scripts.kd_research.spawn_gate import (  # noqa: E402
    check_spawn_discipline,
    record_spawn_event,
    session_enforces_spawn,
    session_is_abandoned,
    write_abandon,
)
from scripts.record_spawn import main as record_spawn_main  # noqa: E402
from scripts.abandon_session import main as abandon_main  # noqa: E402
from scripts.finalize_session import main as finalize_main  # noqa: E402


def _write(p: Path, obj: object) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, (dict, list)):
        p.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    else:
        p.write_text(str(obj), encoding="utf-8")


def _stamp(session: Path, version: str = "2.20.0") -> None:
    _write(
        session / "meta" / "run_manifest.json",
        {
            "schema_version": 2,
            "run_id": "research:X:2026-01-01",
            "ticker": "X",
            "session_date": "2026-01-01",
            "status": "scaffolded",
            "harness_version": version,
            "orchestrator_model": "grok-4.5",
            "default_subagent_model": "grok-4.5",
        },
    )


def _status(session: Path) -> None:
    data = build_phase_status_skeleton("X", "2026-01-01", updated_at="2026-01-01T00:00:00Z")
    _write(session / "registry" / "phase_status.json", data)


class YearReaderBindingTests(unittest.TestCase):
    def test_normalize_year_reader(self) -> None:
        self.assertEqual(normalize_subagent_id("2e_fy2023"), "2e_fy2023")
        self.assertEqual(normalize_subagent_id("year_reader_FY2024"), "2e_fy2024")
        self.assertEqual(normalize_subagent_id("phase0_r3"), "phase0_r3")
        self.assertEqual(home_phase_for_subagent("2e_fy2022"), "1c")
        self.assertEqual(home_phase_for_subagent("phase0_r3"), "0")

    def test_year_reader_allowed_in_1c_only(self) -> None:
        ok, _ = subagent_allowed_in_phase("2e_fy2022", "1c")
        self.assertTrue(ok)
        ok, detail = subagent_allowed_in_phase("2e_fy2022", "2_parallel")
        self.assertFalse(ok)
        self.assertIn("1c", detail)


class SpawnGateTests(unittest.TestCase):
    def test_legacy_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.19.0")
            _write(s / "data" / "valuation_model.json", {"ticker": "X"})
            rows = check_spawn_discipline(s)
            self.assertEqual(rows[0][0], "SKIPPED")
            self.assertFalse(session_enforces_spawn(s))

    def test_new_runtime_idle_pass(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s)
            _status(s)
            rows = check_spawn_discipline(s)
            self.assertTrue(any(r[0] == "PASS" and r[1] == "spawn.idle" for r in rows), rows)

    def test_valuation_without_spawn_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s)
            _write(s / "data" / "valuation_model.json", {"ticker": "X"})
            rows = check_spawn_discipline(s)
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertTrue(any("spawn.missing:5" in r[1] or r[1] == "registry/spawns.json" for r in fails), fails)

    def test_returned_spawn_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s)
            _write(s / "data" / "valuation_model.json", {"ticker": "X"})
            record_spawn_event(s, subagent_id="5", phase_id="2_parallel", event="launch", subagent_type="coder")
            record_spawn_event(s, subagent_id="5", phase_id="2_parallel", event="return")
            rows = check_spawn_discipline(s)
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertEqual(fails, [], rows)
            self.assertTrue(any(r[1] == "spawn.returned:5" for r in rows), rows)

    def test_inline_execution_fails_even_with_spawn(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s)
            data = build_phase_status_skeleton("X", "2026-01-01", updated_at="2026-01-01T00:00:00Z")
            for ph in data["phases"]:
                if ph["phase_id"] == "2_parallel":
                    for ag in ph["agents"]:
                        if ag["agent_id"] == "5":
                            ag["status"] = "complete"
                            ag["execution"] = "orchestrator_inline"
            _write(s / "registry" / "phase_status.json", data)
            _write(s / "data" / "valuation_model.json", {"ticker": "X"})
            record_spawn_event(s, subagent_id="5", phase_id="2_parallel", event="launch")
            record_spawn_event(s, subagent_id="5", phase_id="2_parallel", event="return")
            rows = check_spawn_discipline(s)
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertTrue(any(r[1] == "spawn.inline:5" for r in fails), rows)

    def test_spawn_fail_abandons_and_blocks_entry(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s)
            _status(s)
            record_spawn_event(
                s,
                subagent_id="5",
                phase_id="2_parallel",
                event="fail",
                fail_reason="spawn_subagent unavailable",
            )
            self.assertTrue(session_is_abandoned(s))
            self.assertTrue((s / "registry" / "abandon.json").is_file())
            rows = entry_checks(s, "2_5", ticker="X")
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertTrue(any(r[1] == "spawn.abandoned" for r in fails), rows)

    def test_complete_phase0_requires_swarm_spawn(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s)
            _write(s / "registry" / "background.json", {"ticker": "X"})
            _write(s / "registry" / "raw" / "phase0_r1.json", {"round": 1})
            rows = complete_checks(s, "0")
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertTrue(
                any("phase0_swarm" in r[1] or r[1] == "registry/spawns.json" for r in fails),
                rows,
            )

    def test_year_file_requires_year_reader_spawn(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s)
            _write(s / "registry" / "raw" / "fdd_year_FY2023.json", {"fiscal_year": 2023})
            record_spawn_event(s, subagent_id="2e", phase_id="1c", event="launch")
            record_spawn_event(s, subagent_id="2e", phase_id="1c", event="return")
            rows = check_spawn_discipline(s)
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertTrue(any("2e_fy2023" in r[1] for r in fails), rows)
            record_spawn_event(s, subagent_id="2e_fy2023", phase_id="1c", event="launch")
            record_spawn_event(s, subagent_id="2e_fy2023", phase_id="1c", event="return")
            rows = check_spawn_discipline(s)
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertEqual(fails, [], rows)

    def test_record_spawn_cli_and_abandon_cli(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s)
            _status(s)
            rc = record_spawn_main(
                [
                    "--session-dir",
                    str(s),
                    "--subagent",
                    "2a",
                    "--phase",
                    "1_parallel",
                    "--event",
                    "launch",
                    "--subagent-type",
                    "coder",
                ]
            )
            self.assertEqual(rc, 0)
            rc = record_spawn_main(
                [
                    "--session-dir",
                    str(s),
                    "--subagent",
                    "2b",
                    "--phase",
                    "1_parallel",
                    "--event",
                    "fail",
                    "--reason",
                    "spawn_subagent unavailable",
                ]
            )
            self.assertEqual(rc, 1)
            self.assertTrue(session_is_abandoned(s))

            s2 = Path(td) / "other"
            _stamp(s2)
            _status(s2)
            rc = abandon_main(
                [
                    "--session-dir",
                    str(s2),
                    "--reason",
                    "spawn_failed",
                    "--phase",
                    "0",
                    "--subagent",
                    "phase0_swarm",
                    "--detail",
                    "tool missing",
                ]
            )
            self.assertEqual(rc, 1)
            self.assertTrue(session_is_abandoned(s2))

    def test_finalize_refuses_abandoned(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td) / "archive" / "research" / "X" / "2026-01-01"
            _stamp(s)
            _status(s)
            write_abandon(
                s,
                reason="spawn_failed",
                phase_id="2_parallel",
                subagent_id="5",
                detail="unavailable",
            )
            rc = finalize_main(["--session-dir", str(s)])
            self.assertEqual(rc, 2)

    def test_return_without_launch_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s)
            with self.assertRaises(ValueError):
                record_spawn_event(s, subagent_id="5", phase_id="2_parallel", event="return")
            rc = record_spawn_main(
                [
                    "--session-dir",
                    str(s),
                    "--subagent",
                    "5",
                    "--phase",
                    "2_parallel",
                    "--event",
                    "return",
                ]
            )
            self.assertEqual(rc, 2)

    def test_wrong_phase_spawn_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s)
            with self.assertRaises(ValueError):
                record_spawn_event(s, subagent_id="5", phase_id="0", event="launch")

    def test_agent5_stays_subagent_after_5b(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s)
            data = build_phase_status_skeleton("X", "2026-01-01", updated_at="2026-01-01T00:00:00Z")
            for ph in data["phases"]:
                if ph["phase_id"] == "2_parallel":
                    for ag in ph["agents"]:
                        if ag["agent_id"] == "5":
                            ag["status"] = "complete"
                            ag["execution"] = "subagent"
                if ph["phase_id"] == "orch":
                    for ag in ph["agents"]:
                        if ag["agent_id"] == "orchestrator":
                            ag["execution"] = "orchestrator_lead"
            _write(s / "registry" / "phase_status.json", data)
            _write(s / "data" / "valuation_model.json", {"ticker": "X"})
            record_spawn_event(s, subagent_id="5", phase_id="2_parallel", event="launch")
            record_spawn_event(s, subagent_id="5", phase_id="2_parallel", event="return")
            rows = check_spawn_discipline(s)
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertEqual(fails, [], rows)

    def test_retag_agent5_orchestrator_lead_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s)
            data = build_phase_status_skeleton("X", "2026-01-01", updated_at="2026-01-01T00:00:00Z")
            for ph in data["phases"]:
                if ph["phase_id"] == "2_parallel":
                    for ag in ph["agents"]:
                        if ag["agent_id"] == "5":
                            ag["status"] = "complete"
                            ag["execution"] = "orchestrator_lead"
            _write(s / "registry" / "phase_status.json", data)
            _write(s / "data" / "valuation_model.json", {"ticker": "X"})
            record_spawn_event(s, subagent_id="5", phase_id="2_parallel", event="launch")
            record_spawn_event(s, subagent_id="5", phase_id="2_parallel", event="return")
            rows = check_spawn_discipline(s)
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertTrue(any(r[1] == "spawn.retag:5" for r in fails), rows)

    def test_phase0_raws_need_round_spawns(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s)
            _write(s / "registry" / "background.json", {"ticker": "X"})
            _write(s / "registry" / "raw" / "phase0_r1.json", {"round": 1})
            _write(s / "registry" / "raw" / "phase0_r2.json", {"round": 2})
            record_spawn_event(s, subagent_id="phase0_swarm", phase_id="0", event="launch")
            record_spawn_event(s, subagent_id="phase0_swarm", phase_id="0", event="return")
            rows = check_spawn_discipline(s)
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertTrue(any("phase0_r1" in r[1] for r in fails), rows)
            record_spawn_event(s, subagent_id="phase0_r1", phase_id="0", event="launch")
            record_spawn_event(s, subagent_id="phase0_r1", phase_id="0", event="return")
            record_spawn_event(s, subagent_id="phase0_r2", phase_id="0", event="launch")
            record_spawn_event(s, subagent_id="phase0_r2", phase_id="0", event="return")
            rows = check_spawn_discipline(s)
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertEqual(fails, [], rows)

    def test_year_reader_listed_under_wrong_phase_fails_graph(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            data = build_phase_status_skeleton("X", "2026-01-01", updated_at="2026-01-01T00:00:00Z")
            for ph in data["phases"]:
                if ph["phase_id"] == "2_parallel":
                    ph["agents"].append(
                        {"agent_id": "2e_fy2023", "status": "complete", "artifacts": [], "handoff": None}
                    )
            _write(s / "registry" / "phase_status.json", data)
            rows = check_phase_status_graph(s)
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertTrue(any("2e_fy2023" in r[2] for r in fails), rows)


if __name__ == "__main__":
    unittest.main()

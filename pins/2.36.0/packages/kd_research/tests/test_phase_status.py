"""Unit tests for phase_status skeleton + check_session optional check (no network)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.phase_status import (
    PHASE_AGENTS,
    PHASE_IDS,
    SCHEMA_VERSION,
    build_phase_status_skeleton,
    check_phase_status_session,
    write_phase_status_skeleton,
)
from packages.kd_research.scaffold import scaffold


class BuildSkeletonTests(unittest.TestCase):
    def test_all_phase_ids_and_pending_agents(self):
        data = build_phase_status_skeleton("meta", "2026-08-04", updated_at="2026-08-04T12:00:00Z")
        self.assertEqual(data["ticker"], "META")
        self.assertEqual(data["session_date"], "2026-08-04")
        self.assertEqual(data["schema_version"], SCHEMA_VERSION)
        self.assertEqual(data["updated_at"], "2026-08-04T12:00:00Z")
        self.assertEqual(data["current_phase"], "orch")
        self.assertIsInstance(data["resume_hint"], str)
        self.assertTrue(data["resume_hint"])
        self.assertEqual(data["failures"], [])
        self.assertEqual(data["waivers"], [])

        by_id = {p["phase_id"]: p for p in data["phases"]}
        self.assertEqual(list(by_id.keys()), PHASE_IDS)
        for phase_id, agent_ids in PHASE_AGENTS:
            ph = by_id[phase_id]
            self.assertEqual(ph["status"], "pending")
            self.assertIsNone(ph["started_at"])
            self.assertIsNone(ph["finished_at"])
            got_agents = [a["agent_id"] for a in ph["agents"]]
            self.assertEqual(got_agents, agent_ids)
            for a in ph["agents"]:
                self.assertEqual(a["status"], "pending")
                self.assertEqual(a["artifacts"], [])
                self.assertIsNone(a["handoff"])

    def test_write_skeleton_to_disk(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "T" / "2026-01-01"
            (root / "registry").mkdir(parents=True)
            path = write_phase_status_skeleton(root, "t", "2026-01-01", updated_at="2026-01-01T00:00:00Z")
            self.assertTrue(path.is_file())
            loaded = json.loads(path.read_text())
            self.assertEqual(loaded["ticker"], "T")
            self.assertEqual(len(loaded["phases"]), len(PHASE_IDS))


class ScaffoldWritesPhaseStatusTests(unittest.TestCase):
    def test_scaffold_creates_valid_phase_status(self):
        with tempfile.TemporaryDirectory() as td:
            root = scaffold(
                "ZZTEST", "2099-01-02", output_dir=td, orchestrator_model="grok-4.5"
            )
            ps = root / "registry" / "phase_status.json"
            self.assertTrue(ps.is_file(), f"missing {ps}")
            data = json.loads(ps.read_text())
            self.assertEqual(data["ticker"], "ZZTEST")
            self.assertEqual(data["session_date"], "2099-01-02")
            self.assertEqual({p["phase_id"] for p in data["phases"]}, set(PHASE_IDS))
            # all agents pending
            for p in data["phases"]:
                self.assertEqual(p["status"], "pending")
                for a in p["agents"]:
                    self.assertEqual(a["status"], "pending")


class PhaseStatusCheckTests(unittest.TestCase):
    def _session_dir(self) -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name) / "TEST" / "2026-08-04"
        root.mkdir(parents=True)
        (root / "registry").mkdir()
        return root

    def test_absent_is_skipped(self):
        session = self._session_dir()
        rows = check_phase_status_session(session)
        skipped = [r for r in rows if r[0] == "SKIPPED" and r[1] == "phase_status"]
        fails = [r for r in rows if r[0] == "FAIL"]
        self.assertEqual(len(skipped), 1, rows)
        self.assertEqual(fails, [], rows)

    def test_present_valid_passes(self):
        session = self._session_dir()
        write_phase_status_skeleton(session, "TEST", "2026-08-04", updated_at="2026-08-04T00:00:00Z")
        rows = check_phase_status_session(session)
        fails = [r for r in rows if r[0] == "FAIL"]
        self.assertEqual(fails, [], rows)
        passes = [r for r in rows if r[0] == "PASS" and "phase_status" in r[1]]
        self.assertTrue(any("content" in r[1] for r in passes), rows)

    def test_present_invalid_fails(self):
        session = self._session_dir()
        bad = {"ticker": "TEST"}  # missing required keys
        (session / "registry" / "phase_status.json").write_text(json.dumps(bad))
        rows = check_phase_status_session(session)
        fails = [r for r in rows if r[0] == "FAIL"]
        self.assertTrue(fails, rows)
        self.assertTrue(any("keys" in r[1] or "parse" in r[1] for r in fails), fails)

    def test_missing_phase_id_fails(self):
        session = self._session_dir()
        data = build_phase_status_skeleton("TEST", "2026-08-04", updated_at="2026-08-04T00:00:00Z")
        data["phases"] = [p for p in data["phases"] if p["phase_id"] != "2_5"]
        (session / "registry" / "phase_status.json").write_text(json.dumps(data))
        rows = check_phase_status_session(session)
        fails = [r for r in rows if r[0] == "FAIL"]
        self.assertTrue(any("coverage" in r[1] for r in fails), rows)

    def test_invalid_status_fails(self):
        session = self._session_dir()
        data = build_phase_status_skeleton("TEST", "2026-08-04", updated_at="2026-08-04T00:00:00Z")
        data["phases"][0]["status"] = "done_wrong"
        (session / "registry" / "phase_status.json").write_text(json.dumps(data))
        rows = check_phase_status_session(session)
        fails = [r for r in rows if r[0] == "FAIL"]
        self.assertTrue(any("status" in r[1] for r in fails), rows)


if __name__ == "__main__":
    unittest.main()

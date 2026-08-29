"""CLI wrappers for spawn/abandon/finalize (library cases live in kd_research tests)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.phase_status import build_phase_status_skeleton
from packages.kd_research.spawn_gate import session_is_abandoned, write_abandon
from scripts.abandon_session import main as abandon_main
from scripts.finalize_session import main as finalize_main
from scripts.record_spawn import main as record_spawn_main


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


class SpawnGateCliTests(unittest.TestCase):
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

    def test_return_without_launch_cli_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s)
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


if __name__ == "__main__":
    unittest.main()

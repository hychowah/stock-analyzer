"""Completed-session predicate and insert-only export."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.session_state import session_is_completed


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


class SessionCompletedTests(unittest.TestCase):
    def test_empty_and_in_progress(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            self.assertFalse(session_is_completed(s))
            _write(s / "meta" / "run_manifest.json", {"status": "scaffolded"})
            self.assertFalse(session_is_completed(s))

    def test_snapshot_or_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _write(s / "meta" / "prediction_snapshot.json", {})
            self.assertTrue(session_is_completed(s))
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _write(s / "meta" / "run_manifest.json", {"immutable": True})
            self.assertTrue(session_is_completed(s))
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _write(s / "meta" / "run_manifest.json", {"status": "completed"})
            self.assertTrue(session_is_completed(s))


class ExportInsertOnlyTests(unittest.TestCase):
    def test_export_module_does_not_refresh_snapshots(self) -> None:
        src = (
            Path(__file__).resolve().parents[3]
            / "scripts"
            / "export_compare_db.py"
        )
        text = src.read_text(encoding="utf-8")
        self.assertNotIn("build_for_session", text)
        self.assertNotIn("refresh_snapshot", text)
        self.assertNotIn("no-refresh-snapshot", text)

    def test_export_does_not_write_snapshot(self) -> None:
        from packages.kd_research.compare_db import open_db
        from scripts.export_compare_db import export_session

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            s = root / "archive" / "research" / "X" / "2026-01-01"
            s.mkdir(parents=True)
            _write(
                s / "meta" / "run_manifest.json",
                {
                    "ticker": "X",
                    "session_date": "2026-01-01",
                    "session_key": "2026-01-01",
                    "status": "scaffolded",
                    "orchestrator_model": "grok-4.5",
                    "default_subagent_model": "grok-4.5",
                    "harness_version": "2.42.0",
                },
            )
            snap = s / "meta" / "prediction_snapshot.json"
            self.assertFalse(snap.is_file())
            conn = open_db(root, rebuild=True)
            export_session(s, conn)
            conn.close()
            self.assertFalse(snap.is_file())

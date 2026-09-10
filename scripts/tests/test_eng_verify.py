"""eng_verify completed-session dirty check (git union, not wallpaper)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.eng_verify import check_completed_session_dirty, _research_session_from_rel


class CompletedDirtyTests(unittest.TestCase):
    def test_parse_research_path(self) -> None:
        self.assertEqual(
            _research_session_from_rel("archive/research/META/2026-09-01/meta/run_manifest.json"),
            ("archive/research", "META", "2026-09-01"),
        )
        self.assertEqual(
            _research_session_from_rel(
                "eng/fixtures/archive/research/X/2026-01-01/data/valuation_model.json"
            ),
            ("eng/fixtures/archive/research", "X", "2026-01-01"),
        )
        self.assertIsNone(_research_session_from_rel("packages/kd_research/library.py"))

    def test_outcomes_always_fail(self) -> None:
        errs = check_completed_session_dirty(
            Path("."),
            changed=["archive/outcomes/META/2026-09-01.json"],
        )
        self.assertTrue(any("outcomes" in e for e in errs), errs)

    def test_in_progress_scaffold_legal(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            s = root / "archive" / "research" / "X" / "2026-01-01"
            s.mkdir(parents=True)
            (s / "meta").mkdir()
            (s / "meta" / "run_manifest.json").write_text(
                json.dumps({"status": "scaffolded"}) + "\n", encoding="utf-8"
            )
            errs = check_completed_session_dirty(
                root,
                changed=["archive/research/X/2026-01-01/meta/run_manifest.json"],
            )
            self.assertEqual(errs, [])

    def test_snapshot_path_fails(self) -> None:
        errs = check_completed_session_dirty(
            Path("."),
            changed=["archive/research/X/2026-01-01/meta/prediction_snapshot.json"],
        )
        self.assertTrue(any("completed research" in e for e in errs), errs)

    def test_completed_on_disk_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            s = root / "archive" / "research" / "X" / "2026-01-01"
            (s / "meta").mkdir(parents=True)
            (s / "meta" / "prediction_snapshot.json").write_text("{}\n", encoding="utf-8")
            errs = check_completed_session_dirty(
                root,
                changed=["archive/research/X/2026-01-01/reports/00_X_README.md"],
            )
            self.assertTrue(any("completed research" in e for e in errs), errs)

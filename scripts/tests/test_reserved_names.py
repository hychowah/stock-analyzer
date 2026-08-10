"""ROOT_RESERVED_NAMES must include product platform dirs."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.kd_research.paths import (  # noqa: E402
    ROOT_RESERVED_NAMES,
    iter_research_sessions,
)


class ReservedNamesTests(unittest.TestCase):
    def test_product_roots_reserved(self):
        for name in ("eng", "packages", "apps", "programs", "docs", "build", "dist"):
            self.assertIn(name, ROOT_RESERVED_NAMES, msg=f"missing reserved {name}")

    def test_eng_sessions_not_scanned_as_research(self):
        """Legacy root scan must skip eng/ even if date-shaped folders exist."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # Fake eng work session that looks date-like under a reserved parent
            eng = root / "eng" / "sessions" / "2026-08-10-slug"
            eng.mkdir(parents=True)
            (eng / "registry").mkdir()
            # Real research session under archive
            real = root / "archive" / "research" / "META" / "2026-08-03"
            real.mkdir(parents=True)
            (real / "registry").mkdir()
            # Poison: apps/FOO/2026-08-10 as if ticker FOO
            poison = root / "apps" / "FOO" / "2026-08-10"
            poison.mkdir(parents=True)
            (poison / "reports").mkdir()

            rows = iter_research_sessions(root, include_legacy=True)
            keys = {(t, d) for t, d, _ in rows}
            self.assertIn(("META", "2026-08-03"), keys)
            self.assertNotIn(("FOO", "2026-08-10"), keys)
            # eng is reserved parent — nothing under eng/sessions should appear as ticker eng
            self.assertFalse(any(t == "ENG" for t, _, _ in rows))


if __name__ == "__main__":
    unittest.main()

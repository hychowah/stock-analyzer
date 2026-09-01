"""TICKER_BLOCKLIST covers product nouns; root dirs are not sessions."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from packages.kd_research.paths import TICKER_BLOCKLIST, iter_research_sessions
from packages.kd_research.ticker_lookup import is_reserved


class TickerBlocklistTests(unittest.TestCase):
    def test_product_roots_blocked(self):
        for name in ("eng", "packages", "apps", "programs", "docs", "build", "dist", "library", "vendor", "pins"):
            self.assertIn(name, TICKER_BLOCKLIST, msg=f"missing blocked {name}")
            self.assertTrue(is_reserved(name.upper()))

    def test_root_dirs_are_not_sessions(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            eng = root / "eng" / "sessions" / "2026-08-10-slug"
            eng.mkdir(parents=True)
            (eng / "registry").mkdir()
            real = root / "archive" / "research" / "META" / "2026-08-03"
            real.mkdir(parents=True)
            (real / "registry").mkdir()
            poison = root / "apps" / "FOO" / "2026-08-10"
            poison.mkdir(parents=True)
            (poison / "reports").mkdir()
            legacy = root / "DDD" / "2026-04-04"
            legacy.mkdir(parents=True)
            (legacy / "reports").mkdir()

            rows = iter_research_sessions(root)
            keys = {(t, d) for t, d, _ in rows}
            self.assertIn(("META", "2026-08-03"), keys)
            self.assertNotIn(("FOO", "2026-08-10"), keys)
            self.assertNotIn(("DDD", "2026-04-04"), keys)
            self.assertFalse(any(t == "ENG" for t, _, _ in rows))


if __name__ == "__main__":
    unittest.main()

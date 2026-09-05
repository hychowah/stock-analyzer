"""StreetY1Policy table: 2.7 / 2.18 / 2.28 enums and bands."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.street_y1 import (
    CALIB,
    GATED,
    Y1,
    StreetY1Policy,
    Y1_BAND,
)


def _stamp(session: Path, version: str) -> None:
    (session / "meta").mkdir(parents=True, exist_ok=True)
    (session / "meta" / "run_manifest.json").write_text(
        json.dumps({"harness_version": version, "ticker": "X", "session_date": "2026-01-01"})
        + "\n",
        encoding="utf-8",
    )


class StreetY1PolicyTests(unittest.TestCase):
    def test_version_floors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.6.0")
            self.assertFalse(StreetY1Policy.for_session(s).y1)
            _stamp(s, "2.7.0")
            p = StreetY1Policy.for_session(s)
            self.assertEqual(p, CALIB)
            self.assertIn("keep_independent_vs_street", p.responses)
            self.assertIsNone(p.fail_band)
            _stamp(s, "2.18.0")
            p = StreetY1Policy.for_session(s)
            self.assertEqual(p, Y1)
            self.assertTrue(p.keep_independent_illegal)
            self.assertEqual(p.fail_band, Y1_BAND)
            self.assertFalse(p.independent_y1_ok)
            _stamp(s, "2.28.0")
            p = StreetY1Policy.for_session(s)
            self.assertEqual(p, GATED)
            self.assertTrue(p.independent_y1_ok)
            self.assertIn("independent_y1", p.responses)
            self.assertTrue(p.rehydrate)

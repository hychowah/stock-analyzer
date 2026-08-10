"""Cross-session isolation checks in check_session."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def _load_check_session():
    path = ROOT / "scripts" / "check_session.py"
    spec = importlib.util.spec_from_file_location("check_session_iso_test", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CrossSessionIsolationTests(unittest.TestCase):
    def setUp(self):
        self.mod = _load_check_session()
        self.mod.results.clear()

    def test_flags_foreign_session_path_in_valuation(self):
        with tempfile.TemporaryDirectory() as td:
            session = Path(td) / "archive" / "research" / "META" / "2026-08-10__r2"
            (session / "data").mkdir(parents=True)
            (session / "registry").mkdir(parents=True)
            (session / "registry" / "session_isolation.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "mode": "isolated",
                        "session_key": "2026-08-10__r2",
                        "rules": {
                            "intra_session_share": True,
                            "prior_valuation_as_input": False,
                        },
                    }
                ),
                encoding="utf-8",
            )
            (session / "data" / "valuation_model.json").write_text(
                json.dumps(
                    {
                        "ticker": "META",
                        "note": "see archive/research/META/2026-08-03/data/valuation_model.json",
                    }
                ),
                encoding="utf-8",
            )
            self.mod.check_session_isolation(session, full=False)
            statuses = {c: s for s, c, _ in self.mod.results}
            self.assertEqual(statuses.get("session_isolation policy"), "PASS")
            self.assertEqual(statuses.get("cross-session valuation isolation"), "WARN")

    def test_full_mode_fails(self):
        with tempfile.TemporaryDirectory() as td:
            session = Path(td) / "archive" / "research" / "META" / "2026-08-10"
            (session / "data").mkdir(parents=True)
            (session / "registry").mkdir(parents=True)
            (session / "data" / "valuation_model.json").write_text(
                "prior archive/research/META/2026-07-30/meta/prediction_snapshot.json\n",
                encoding="utf-8",
            )
            self.mod.check_session_isolation(session, full=True)
            statuses = {c: s for s, c, _ in self.mod.results}
            self.assertEqual(statuses.get("cross-session valuation isolation"), "FAIL")

    def test_clean_session_passes(self):
        with tempfile.TemporaryDirectory() as td:
            session = Path(td) / "archive" / "research" / "META" / "2026-08-10"
            (session / "data").mkdir(parents=True)
            (session / "registry").mkdir(parents=True)
            (session / "registry" / "session_isolation.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "mode": "isolated",
                        "session_key": "2026-08-10",
                        "rules": {
                            "intra_session_share": True,
                            "prior_valuation_as_input": False,
                        },
                    }
                ),
                encoding="utf-8",
            )
            (session / "data" / "valuation_model.json").write_text(
                json.dumps({"ticker": "META", "fair_value": {"base": 1}}),
                encoding="utf-8",
            )
            self.mod.check_session_isolation(session, full=True)
            statuses = {c: s for s, c, _ in self.mod.results}
            self.assertEqual(statuses.get("cross-session valuation isolation"), "PASS")


if __name__ == "__main__":
    unittest.main()

"""Cross-session isolation checks in check_session."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.isolation import check_session_isolation


class CrossSessionIsolationTests(unittest.TestCase):

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
            rows = check_session_isolation(session, full=False)
            statuses = {c: s for s, c, _ in rows}
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
            rows = check_session_isolation(session, full=True)
            statuses = {c: s for s, c, _ in rows}
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
            rows = check_session_isolation(session, full=True)
            statuses = {c: s for s, c, _ in rows}
            self.assertEqual(statuses.get("cross-session valuation isolation"), "PASS")


if __name__ == "__main__":
    unittest.main()

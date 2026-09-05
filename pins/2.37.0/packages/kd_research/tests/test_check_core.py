"""Unit tests for check_core I/O and version compare."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.check_core import (
    Check,
    load_json,
    session_since,
    validate_hooks_list,
)


def _stamp(session: Path, version: str | None) -> None:
    meta = session / "meta"
    meta.mkdir(parents=True, exist_ok=True)
    payload: dict = {
        "schema_version": 2,
        "run_id": "research:X:2026-01-01",
        "ticker": "X",
        "session_date": "2026-01-01",
    }
    if version is not None:
        payload["harness_version"] = version
    (meta / "run_manifest.json").write_text(json.dumps(payload) + "\n", encoding="utf-8")


class CheckCoreTests(unittest.TestCase):
    def test_check_unpacks_like_tuple(self) -> None:
        row = Check("PASS", "foo", "ok")
        status, cid, detail = row
        self.assertEqual((status, cid, detail), ("PASS", "foo", "ok"))
        self.assertEqual(row[1], "foo")

    def test_load_json_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            data, err = load_json(Path(td) / "nope.json")
            self.assertIsNone(data)
            self.assertEqual(err, "missing")

    def test_load_json_unparseable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.json"
            p.write_text("{not json", encoding="utf-8")
            data, err = load_json(p)
            self.assertIsNone(data)
            self.assertIsNotNone(err)
            self.assertTrue(str(err).startswith("unparseable:"), err)

    def test_load_json_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "ok.json"
            p.write_text('{"a": 1}\n', encoding="utf-8")
            data, err = load_json(p)
            self.assertIsNone(err)
            self.assertEqual(data, {"a": 1})

    def test_session_since(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.18.0")
            self.assertTrue(session_since(s, (2, 18, 0)))
            self.assertTrue(session_since(s, (2, 7, 0)))
            self.assertFalse(session_since(s, (2, 28, 0)))
            _stamp(s, None)
            self.assertFalse(session_since(s, (2, 7, 0)))
            _stamp(s, "not-a-version")
            self.assertFalse(session_since(s, (2, 7, 0)))

    def test_validate_hooks_empty_fails(self) -> None:
        rows = validate_hooks_list([], check_id="hooks", empty_detail="need hooks")
        self.assertEqual(rows[0][0], "FAIL")
        self.assertEqual(rows[0][1], "hooks")

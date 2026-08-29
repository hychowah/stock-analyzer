"""Compare job runner (fake spawn; never calls Grok)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.compare_jobs.jobs import (
    CompareBusy,
    CompareValidationError,
    cancel_compare,
    get_compare,
    start_compare,
)
from packages.compare_jobs.spawn import FakeSpawnBackend


def _session(archive: Path, ticker: str, key: str, *, fv: float, model: bool = True, snap: bool = True) -> Path:
    root = archive / "research" / ticker / key
    (root / "data").mkdir(parents=True)
    (root / "meta").mkdir(parents=True)
    if model:
        (root / "data" / "valuation_model.json").write_text(
            json.dumps({"name": "dcf", "fair_value": {"base": fv}}),
            encoding="utf-8",
        )
    if snap:
        (root / "meta" / "prediction_snapshot.json").write_text(
            json.dumps(
                {
                    "asof_price": fv * 0.8,
                    "fair_value": {"base": fv, "bear": fv * 0.7, "bull": fv * 1.3},
                    "margin_of_safety_pct": 20.0,
                    "audit_verdict": "PASS",
                    "primary_sector": "growth",
                    "region": "us",
                    "verdict_line": "pass",
                    "key_risks": ["ads"],
                }
            ),
            encoding="utf-8",
        )
    return root


class CompareJobsTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.archive = Path(self._td.name) / "archive"
        self.archive.mkdir()
        _session(self.archive, "META", "2026-08-03", fv=500.0)
        _session(self.archive, "META", "2026-08-10", fv=600.0)
        _session(self.archive, "JPM", "2026-07-25", fv=200.0)
        self.fake = FakeSpawnBackend(write_synthesis=True)

    def tearDown(self):
        self._td.cleanup()

    def test_start_same_ticker_completes_fake(self):
        job = start_compare(
            self.archive,
            "research:META:2026-08-03",
            "research:META:2026-08-10",
            spawn=self.fake,
        )
        self.assertEqual(job["status"], "complete")
        self.assertEqual(job["session_a"], "2026-08-03")
        self.assertEqual(job["session_b"], "2026-08-10")
        out = Path(job["out_dir"])
        self.assertTrue((out / "99_synthesis.md").is_file())
        self.assertTrue((out / "README.md").is_file())
        self.assertTrue((out / "headline.json").is_file())
        self.assertTrue((out / "job.json").is_file())
        headline = json.loads((out / "headline.json").read_text(encoding="utf-8"))
        self.assertEqual(headline["fields"][1]["values"]["2026-08-03"], 500.0)
        # Did not write research tmp
        self.assertFalse((self.archive / "research" / "META" / "tmp").exists())

    def test_different_tickers_rejected(self):
        with self.assertRaises(CompareValidationError):
            start_compare(
                self.archive,
                "research:META:2026-08-03",
                "research:JPM:2026-07-25",
                spawn=self.fake,
            )

    def test_missing_valuation_model_rejected(self):
        _session(self.archive, "META", "2026-08-20", fv=1.0, model=False)
        with self.assertRaises(CompareValidationError) as ctx:
            start_compare(
                self.archive,
                "research:META:2026-08-03",
                "research:META:2026-08-20",
                spawn=self.fake,
            )
        self.assertIn("valuation_model.json", str(ctx.exception))

    def test_duplicate_complete_returns_same(self):
        a = start_compare(
            self.archive,
            "research:META:2026-08-10",
            "research:META:2026-08-03",
            spawn=self.fake,
        )
        b = start_compare(
            self.archive,
            "research:META:2026-08-03",
            "research:META:2026-08-10",
            spawn=self.fake,
        )
        self.assertEqual(a["compare_id"], b["compare_id"])

    def test_duplicate_running_returns_same(self):
        running = FakeSpawnBackend(write_synthesis=False)
        a = start_compare(
            self.archive,
            "research:META:2026-08-03",
            "research:META:2026-08-10",
            spawn=running,
        )
        self.assertEqual(a["status"], "running")
        b = start_compare(
            self.archive,
            "research:META:2026-08-03",
            "research:META:2026-08-10",
            spawn=running,
        )
        self.assertEqual(a["compare_id"], b["compare_id"])

    def test_busy_blocks_other_pair(self):
        running = FakeSpawnBackend(write_synthesis=False)
        start_compare(
            self.archive,
            "research:META:2026-08-03",
            "research:META:2026-08-10",
            spawn=running,
        )
        _session(self.archive, "JPM", "2026-07-30", fv=210.0)
        with self.assertRaises(CompareBusy):
            start_compare(
                self.archive,
                "research:JPM:2026-07-25",
                "research:JPM:2026-07-30",
                spawn=self.fake,
            )

    def test_force_after_complete_allocates_r2(self):
        a = start_compare(
            self.archive,
            "research:META:2026-08-03",
            "research:META:2026-08-10",
            spawn=self.fake,
        )
        b = start_compare(
            self.archive,
            "research:META:2026-08-03",
            "research:META:2026-08-10",
            spawn=self.fake,
            force=True,
        )
        self.assertNotEqual(a["compare_id"], b["compare_id"])
        self.assertIn("__r2", b["packet_key"])

    def test_cancel(self):
        running = FakeSpawnBackend(write_synthesis=False)
        job = start_compare(
            self.archive,
            "research:META:2026-08-03",
            "research:META:2026-08-10",
            spawn=running,
        )
        out = cancel_compare(self.archive, job["compare_id"])
        self.assertEqual(out["status"], "cancelled")
        again = get_compare(self.archive, job["compare_id"])
        self.assertEqual(again["status"], "cancelled")


if __name__ == "__main__":
    unittest.main()

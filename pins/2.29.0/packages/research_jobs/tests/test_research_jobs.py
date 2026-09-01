"""Analyze job runner (fake spawn; never calls Grok or Yahoo)."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from packages.kd_research.paths import PROJECT_ROOT as ROOT

from packages.agent_jobs.spawn import GrokSpawnBackend
from packages.research_jobs.jobs import (
    AnalyzeBusy,
    AnalyzeDiscardRefused,
    AnalyzeRunbookMissing,
    AnalyzeTickerError,
    AnalyzeValidationError,
    FakeAnalyzeSpawnBackend,
    cancel_analyze,
    discard_analyze,
    get_analyze,
    list_analyzes,
    reconcile_analyze_jobs,
    refresh_analyze,
    resume_analyze,
    start_analyze,
)
from packages.research_jobs.prompt import (
    ABANDON_IF_UNREAL,
    ALREADY_SCAFFOLDED,
    LISTING_JUDGE,
    LISTING_VERIFY,
    NO_LIST_SIBLINGS,
    NO_RE_SCAFFOLD,
    R2_WARNING,
    build_prompt,
)
from packages.kd_research.ticker_lookup import FakeBackend, Quote


def _q(sym: str) -> Quote:
    return Quote(symbol=sym, quote_type="EQUITY", name=sym, n_fields=80, price=1.0)


def write_stub_snapshot(session: Path, *, audit_verdict: str = "FAIL") -> None:
    """Tmp-only helper. Labeled stub — not a Mode A result."""
    meta = session / "meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "prediction_snapshot.json").write_text(
        json.dumps(
            {
                "stub": True,
                "audit_verdict": audit_verdict,
                "fair_value": {"base": None},
            }
        ),
        encoding="utf-8",
    )


class ResearchJobsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env = {k: os.environ.get(k) for k in ("ARCHIVE_ROOT", "AGENT_SPAWN")}
        os.environ.pop("ARCHIVE_ROOT", None)
        os.environ["AGENT_SPAWN"] = "fake"
        self._td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.archive = Path(self._td.name) / "archive"
        self.archive.mkdir()
        self.be = FakeBackend(
            quotes={"COHR": _q("COHR"), "META": _q("META")},
            search_hits={"ZZZNOPE": [], "APPL": [_q("AAPL")]},
        )
        self.fake = FakeAnalyzeSpawnBackend()
        self._fixture_mtimes = self._fixture_research_mtimes()

    def tearDown(self) -> None:
        self._td.cleanup()
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.assertEqual(self._fixture_research_mtimes(), self._fixture_mtimes)

    def _fixture_research_mtimes(self) -> dict[str, float]:
        root = ROOT / "eng" / "fixtures" / "archive" / "research"
        if not root.is_dir():
            return {}
        out: dict[str, float] = {}
        for p in root.rglob("*"):
            if p.is_file():
                out[str(p.relative_to(root))] = p.stat().st_mtime
        return out

    def _start(self, ticker: str = "COHR", **kw: object) -> dict:
        return start_analyze(
            self.archive,
            ticker,
            orchestrator_model="grok-4.5",
            spawn=self.fake,
            ticker_backend=self.be,
            **kw,  # type: ignore[arg-type]
        )

    def test_start_ok_does_not_write_session_from_fake(self) -> None:
        job = self._start()
        self.assertEqual(job["status"], "running")
        self.assertEqual(job["ticker"], "COHR")
        session = Path(job["session_root"])
        self.assertTrue((session / "registry" / "phase_status.json").is_file())
        self.assertFalse((session / "data" / "valuation_model.json").is_file())
        self.assertFalse((session / "meta" / "prediction_snapshot.json").is_file())
        job_dir = Path(job["job_dir"])
        self.assertTrue((job_dir / "fake_spawn.txt").is_file())
        self.assertTrue((job_dir / "prompt.md").is_file())
        prompt = (job_dir / "prompt.md").read_text(encoding="utf-8")
        self.assertIn(ALREADY_SCAFFOLDED, prompt)
        self.assertIn(NO_RE_SCAFFOLD, prompt)
        self.assertIn(NO_LIST_SIBLINGS, prompt)
        self.assertIn(R2_WARNING, prompt)
        self.assertIsNone(job.get("quote_symbol"))
        self.assertNotIn("yahoo_search_hits", job)
        self.assertIn("YAHOO_QUOTE_SYMBOL: unset", prompt)
        self.assertIn(LISTING_JUDGE, prompt)
        self.assertIn(LISTING_VERIFY, prompt)
        self.assertIn(ABANDON_IF_UNREAL, prompt)
        man = json.loads(
            (Path(job["session_root"]) / "meta" / "run_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIsNone(man.get("quote_symbol"))

    def test_start_sends_typed_ticker_when_only_search_hits(self) -> None:
        be = FakeBackend(
            quotes={"ADYEN.AS": _q("ADYEN.AS")},
            search_hits={"ADYEN": [_q("ADYEN.AS")]},
        )
        job = start_analyze(
            self.archive,
            "ADYEN",
            orchestrator_model="grok-4.5",
            spawn=self.fake,
            ticker_backend=be,
        )
        self.assertEqual(job["ticker"], "ADYEN")
        self.assertIsNone(job.get("quote_symbol"))
        self.assertNotIn("yahoo_search_hits", job)
        man = json.loads(
            (Path(job["session_root"]) / "meta" / "run_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIsNone(man.get("quote_symbol"))
        prompt = (Path(job["job_dir"]) / "prompt.md").read_text(encoding="utf-8")
        self.assertNotIn("ADYEN.AS", prompt)
        self.assertIn(LISTING_JUDGE, prompt)
        self.assertIn(LISTING_VERIFY, prompt)
        self.assertIn("session folder and catalog ticker stay TICKER", prompt)

    def test_refresh_copies_quote_symbol_from_manifest(self) -> None:
        job = self._start()
        man_path = Path(job["session_root"]) / "meta" / "run_manifest.json"
        man = json.loads(man_path.read_text(encoding="utf-8"))
        man["quote_symbol"] = "COHR"
        man_path.write_text(json.dumps(man) + "\n", encoding="utf-8")
        refreshed = get_analyze(self.archive, job["analyze_id"])
        self.assertEqual(refreshed["quote_symbol"], "COHR")

    def test_resume_prompt_repeats_listing_when_unstamped(self) -> None:
        text = build_prompt(
            {
                "ticker": "ADYEN",
                "quote_symbol": None,
                "session_key": "2026-08-29",
                "session_root": "/tmp/S",
                "project_root": "/tmp",
                "orchestrator_model": "grok-4.5",
                "subagent_model": "grok-4.5",
                "session_date": "2026-08-29",
            },
            resume=True,
        )
        self.assertIn(LISTING_JUDGE, text)
        self.assertIn("NOT stamped", text)

    def test_ticker_unknown(self) -> None:
        with self.assertRaises(AnalyzeTickerError) as ctx:
            self._start("ZZZNOPE")
        self.assertEqual(ctx.exception.status, "abort_unknown")

    def test_search_evidence_still_starts_typed(self) -> None:
        job = self._start("APPL")
        self.assertEqual(job["ticker"], "APPL")
        self.assertIsNone(job.get("quote_symbol"))
        self.assertNotIn("AAPL", (Path(job["job_dir"]) / "prompt.md").read_text(encoding="utf-8"))

    def test_ticker_reserved(self) -> None:
        with self.assertRaises(AnalyzeTickerError) as ctx:
            self._start("ENG")
        self.assertEqual(ctx.exception.status, "abort_reserved")

    def test_same_day_second_run_allocates_r2(self) -> None:
        a = self._start()
        cancel_analyze(self.archive, a["analyze_id"])
        b = self._start()
        self.assertNotEqual(a["session_key"], b["session_key"])
        self.assertTrue(
            b["session_key"].endswith("__r2") or a["session_key"].endswith("__r2")
        )

    def test_cancel_does_not_abandon(self) -> None:
        job = self._start()
        out = cancel_analyze(self.archive, job["analyze_id"])
        self.assertEqual(out["status"], "cancelled")
        session = Path(job["session_root"])
        self.assertFalse((session / "registry" / "abandon.json").is_file())

    def test_discard_empty_writes_abandon(self) -> None:
        job = self._start()
        out = discard_analyze(self.archive, job["analyze_id"])
        self.assertTrue(out["abandoned"])
        self.assertEqual(out["status"], "failed")
        self.assertTrue((Path(job["session_root"]) / "registry" / "abandon.json").is_file())

    def test_stub_snapshot_blocks_discard_and_cancel_abandon(self) -> None:
        job = self._start()
        session = Path(job["session_root"])
        write_stub_snapshot(session)
        with self.assertRaises(AnalyzeDiscardRefused):
            discard_analyze(self.archive, job["analyze_id"])
        self.assertFalse((session / "registry" / "abandon.json").is_file())
        cancel_analyze(self.archive, job["analyze_id"])
        self.assertFalse((session / "registry" / "abandon.json").is_file())

    def test_snapshot_after_cancelled_is_complete(self) -> None:
        job = self._start()
        cancel_analyze(self.archive, job["analyze_id"])
        write_stub_snapshot(Path(job["session_root"]), audit_verdict="FAIL")
        refreshed = get_analyze(self.archive, job["analyze_id"])
        self.assertEqual(refreshed["status"], "complete")
        self.assertTrue(refreshed["snapshot_ready"])
        self.assertEqual(refreshed["audit_verdict"], "FAIL")
        self.assertFalse(refreshed.get("abandoned"))

    def test_pid_dead_running_failed_no_abandon_resume_ok(self) -> None:
        job = self._start()
        job_path = Path(job["job_dir"]) / "job.json"
        data = json.loads(job_path.read_text(encoding="utf-8"))
        data["pid"] = 999_999_999
        data["status"] = "running"
        data["spawned_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        job_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        refreshed = get_analyze(self.archive, job["analyze_id"])
        self.assertEqual(refreshed["status"], "failed")
        self.assertFalse(refreshed.get("abandoned"))
        self.assertFalse((Path(job["session_root"]) / "registry" / "abandon.json").is_file())
        resumed = resume_analyze(self.archive, job["analyze_id"], spawn=self.fake)
        self.assertEqual(resumed["status"], "running")
        self.assertEqual(resumed["mode"], "resume")
        self.assertEqual(resumed["session_key"], job["session_key"])

    def test_queued_stale_failed_resume_no_new_scaffold(self) -> None:
        job = self._start()
        key = job["session_key"]
        job_path = Path(job["job_dir"]) / "job.json"
        data = json.loads(job_path.read_text(encoding="utf-8"))
        data["status"] = "queued"
        data["pid"] = None
        data["updated_at"] = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        job_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        refreshed = get_analyze(self.archive, job["analyze_id"])
        self.assertEqual(refreshed["status"], "failed")
        resume_analyze(self.archive, job["analyze_id"], spawn=self.fake)
        sessions = list((self.archive / "research" / "COHR").iterdir())
        self.assertEqual(len([p for p in sessions if p.is_dir()]), 1)
        self.assertEqual(sessions[0].name, key)

    def test_missing_session_root_not_resumable(self) -> None:
        job = self._start()
        import shutil

        shutil.rmtree(job["session_root"])
        refreshed = get_analyze(self.archive, job["analyze_id"])
        self.assertEqual(refreshed["status"], "failed")
        self.assertIn("session_root missing", str(refreshed.get("error")))
        with self.assertRaises(AnalyzeValidationError):
            resume_analyze(self.archive, job["analyze_id"], spawn=self.fake)

    def test_corrupt_phase_status_does_not_crash(self) -> None:
        job = self._start()
        phase = Path(job["session_root"]) / "registry" / "phase_status.json"
        phase.write_text("{not-json", encoding="utf-8")
        refreshed = get_analyze(self.archive, job["analyze_id"])
        self.assertEqual(refreshed.get("phase_current"), "unknown")
        rows = list_analyzes(self.archive)
        self.assertEqual(len(rows), 1)

    def test_three_running_analyzes_block_fourth(self) -> None:
        started = []
        for i in range(3):
            job = self._start(session_date="2026-08-29", slug=f"slot{i}")
            self.assertEqual(job["status"], "running")
            started.append(job["analyze_id"])
        with self.assertRaises(AnalyzeBusy) as ctx:
            self._start(session_date="2026-08-29", slug="slot3")
        self.assertIn("ANALYZE_MAX", str(ctx.exception))
        self.assertEqual(len(started), 3)

    def test_reconcile_dead_pid_frees_slot(self) -> None:
        job = self._start()
        job_path = Path(job["job_dir"]) / "job.json"
        data = json.loads(job_path.read_text(encoding="utf-8"))
        data["pid"] = 999_999_998
        data["status"] = "running"
        data["spawned_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        job_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        reconcile_analyze_jobs(self.archive)
        second = self._start()
        self.assertEqual(second["status"], "running")
        self.assertNotEqual(second["analyze_id"], job["analyze_id"])

    def test_real_grok_without_heading_refuses(self) -> None:
        with self.assertRaises(AnalyzeRunbookMissing):
            start_analyze(
                self.archive,
                "COHR",
                orchestrator_model="grok-4.5",
                spawn=GrokSpawnBackend(),
                ticker_backend=self.be,
                project_root=Path(self._td.name),
            )

    def test_fake_without_heading_allowed(self) -> None:
        job = start_analyze(
            self.archive,
            "COHR",
            orchestrator_model="grok-4.5",
            spawn=self.fake,
            ticker_backend=self.be,
            project_root=Path(self._td.name),
        )
        self.assertEqual(job["status"], "running")

    def test_unknown_harness_version(self) -> None:
        with self.assertRaises(AnalyzeValidationError) as ctx:
            self._start(harness_version="9.9.9")
        self.assertIn("pins", str(ctx.exception).lower())

    def test_job_records_live_pin_and_pythonpath(self) -> None:
        job = self._start()
        self.assertEqual(job["pin"]["version"], "live")
        self.assertEqual(job["spawn_env"]["PYTHONPATH"], str(ROOT))
        self.assertEqual(job["spawn_cwd"], str(ROOT))
        prompt = Path(job["job_dir"]).joinpath("prompt.md").read_text(encoding="utf-8")
        self.assertNotIn("bind_library.py", prompt)
        self.assertNotIn("preflight_phase.py", prompt)
        self.assertIn("ROOT:", prompt)

    def test_published_pin_sets_pythonpath_to_pin_root(self) -> None:
        pin_root = ROOT / "pins" / "2.27.0"
        if not (pin_root / "PIN.json").is_file():
            self.skipTest("pins/2.27.0 not published")
        job = self._start(
            harness_version="2.27.0",
            session_date="2026-08-29",
            slug="pin227",
        )
        self.assertEqual(job["pin"]["version"], "2.27.0")
        self.assertEqual(Path(job["spawn_env"]["PYTHONPATH"]), pin_root)
        prompt = Path(job["job_dir"]).joinpath("prompt.md").read_text(encoding="utf-8")
        self.assertIn(str(pin_root), prompt)
        live = self._start(session_date="2026-08-29", slug="livejob")
        self.assertNotEqual(live["spawn_env"]["PYTHONPATH"], job["spawn_env"]["PYTHONPATH"])

    def test_two_starts_do_not_share_process_global_harness(self) -> None:
        a = self._start(session_date="2026-08-29", slug="a")
        b = self._start(session_date="2026-08-29", slug="b")
        self.assertEqual(a["pin"]["version"], "live")
        self.assertEqual(b["pin"]["version"], "live")
        self.assertNotEqual(a["analyze_id"], b["analyze_id"])
        os.environ.pop("HARNESS_ROOT", None)
        self.assertNotIn("HARNESS_ROOT", os.environ)

    def test_prompt_build_contains_frozen_strings(self) -> None:
        text = build_prompt(
            {
                "ticker": "COHR",
                "session_key": "2026-08-29",
                "session_root": "/tmp/S",
                "project_root": "/tmp",
                "orchestrator_model": "grok-4.5",
                "subagent_model": "grok-4.5",
                "session_date": "2026-08-29",
            }
        )
        self.assertIn("UI-scheduled runs (read this first)", text)
        self.assertIn("YAHOO_QUOTE_SYMBOL: unset", text)
        self.assertIn(LISTING_JUDGE, text)
        self.assertIn(LISTING_VERIFY, text)

    def test_runbook_ui_scheduled_heading_before_new_run(self) -> None:
        text = (ROOT / "harness" / "orchestrator_runbook.md").read_text(encoding="utf-8")
        heading = "## UI-scheduled runs (read this first)"
        new_run = "## New run vs resume (read first)"
        self.assertIn(heading, text)
        self.assertLess(text.index(heading), text.index(new_run))
        self.assertIn("already scaffolded", text.lower())
        self.assertIn("__r2", text)


if __name__ == "__main__":
    unittest.main()

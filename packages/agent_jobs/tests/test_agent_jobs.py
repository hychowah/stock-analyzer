"""Shared Grok job runtime (spawn/PID/capacity). Never calls Grok."""

from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

from packages.agent_jobs.capacity import (
    JobsBusy,
    Limits,
    check_slots,
    limits,
    running_by_kind,
)
from packages.agent_jobs.spawn import (
    pid_alive,
    pid_alive_for_job,
    process_create_time,
)


class PidTests(unittest.TestCase):
    def test_pid_alive_rejects_none_and_zero(self) -> None:
        self.assertFalse(pid_alive(None))
        self.assertFalse(pid_alive(0))
        self.assertFalse(pid_alive(-1))

    def test_current_pid_is_alive(self) -> None:
        self.assertTrue(pid_alive(os.getpid()))

    def test_missing_pid_is_dead(self) -> None:
        self.assertFalse(pid_alive(999_999_999))

    def test_pid_alive_for_job_without_spawned_at_falls_back(self) -> None:
        self.assertTrue(pid_alive_for_job(os.getpid(), None))
        self.assertFalse(pid_alive_for_job(None, "2026-08-29T00:00:00Z"))

    def test_pid_reuse_when_process_started_after_spawned_at(self) -> None:
        if process_create_time(os.getpid()) is None:
            self.skipTest("process birth time unavailable on this OS")
        spawned = (datetime.now(timezone.utc) - timedelta(days=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        # This interpreter started today — after yesterday's spawned_at.
        self.assertFalse(pid_alive_for_job(os.getpid(), spawned))

    def test_pid_alive_for_job_when_spawned_just_now(self) -> None:
        spawned = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.assertTrue(pid_alive_for_job(os.getpid(), spawned))


class CapacityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env = {
            k: os.environ.get(k)
            for k in ("ANALYZE_MAX", "COMPARE_MAX", "GROK_JOBS_MAX")
        }

    def tearDown(self) -> None:
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_default_limits(self) -> None:
        for k in ("ANALYZE_MAX", "COMPARE_MAX", "GROK_JOBS_MAX"):
            os.environ.pop(k, None)
        self.assertEqual(limits(), Limits(analyze=3, compare=1, grok=4))
        self.assertEqual(limits().analyze_slots, 3)

    def test_unset_grok_derives_from_kind_slots(self) -> None:
        os.environ["ANALYZE_MAX"] = "5"
        os.environ["COMPARE_MAX"] = "2"
        os.environ.pop("GROK_JOBS_MAX", None)
        self.assertEqual(limits(), Limits(analyze=5, compare=2, grok=7))

    def test_analyze_slots_follows_tighter_global(self) -> None:
        os.environ.pop("ANALYZE_MAX", None)
        os.environ.pop("COMPARE_MAX", None)
        os.environ["GROK_JOBS_MAX"] = "2"
        self.assertEqual(limits().analyze_slots, 2)

    def test_compare_slot_full(self) -> None:
        os.environ.pop("COMPARE_MAX", None)
        os.environ.pop("GROK_JOBS_MAX", None)
        with self.assertRaises(JobsBusy) as ctx:
            check_slots("compare", {"compare": 1, "analyze": 0})
        self.assertIn("COMPARE_MAX", str(ctx.exception))

    def test_compare_slot_free(self) -> None:
        check_slots("compare", {"compare": 0, "analyze": 0})

    def test_analyze_slot_full(self) -> None:
        for k in ("ANALYZE_MAX", "COMPARE_MAX", "GROK_JOBS_MAX"):
            os.environ.pop(k, None)
        check_slots("analyze", {"compare": 0, "analyze": 2})
        with self.assertRaises(JobsBusy) as ctx:
            check_slots("analyze", {"compare": 0, "analyze": 3})
        self.assertIn("ANALYZE_MAX", str(ctx.exception))

    def test_global_cap_blocks_second_kind(self) -> None:
        os.environ["GROK_JOBS_MAX"] = "1"
        os.environ["COMPARE_MAX"] = "1"
        os.environ["ANALYZE_MAX"] = "1"
        with self.assertRaises(JobsBusy) as ctx:
            check_slots("analyze", {"compare": 1, "analyze": 0})
        self.assertIn("GROK_JOBS_MAX", str(ctx.exception))

    def test_global_cap_two_allows_one_each(self) -> None:
        os.environ["GROK_JOBS_MAX"] = "2"
        os.environ["COMPARE_MAX"] = "1"
        os.environ["ANALYZE_MAX"] = "1"
        check_slots("analyze", {"compare": 1, "analyze": 0})
        check_slots("compare", {"compare": 0, "analyze": 1})

    def test_unknown_kind(self) -> None:
        with self.assertRaises(JobsBusy):
            check_slots("audit", {"compare": 0, "analyze": 0})

    def test_env_override(self) -> None:
        os.environ["ANALYZE_MAX"] = "5"
        os.environ["COMPARE_MAX"] = "2"
        os.environ["GROK_JOBS_MAX"] = "6"
        self.assertEqual(limits(), Limits(analyze=5, compare=2, grok=6))

    def test_three_analyze_plus_one_compare_fits(self) -> None:
        for k in ("ANALYZE_MAX", "COMPARE_MAX", "GROK_JOBS_MAX"):
            os.environ.pop(k, None)
        check_slots("analyze", {"compare": 0, "analyze": 2})
        check_slots("compare", {"compare": 0, "analyze": 3})
        check_slots("analyze", {"compare": 1, "analyze": 2})
        with self.assertRaises(JobsBusy):
            check_slots("analyze", {"compare": 1, "analyze": 3})

    def test_running_by_kind_empty_archive(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(
                running_by_kind(Path(td)),
                {"analyze": 0, "compare": 0},
            )


class CompareReexportTests(unittest.TestCase):
    def test_compare_spawn_reexports_shared_helpers(self) -> None:
        from packages.compare_jobs import spawn as cs

        self.assertIs(cs.pid_alive, pid_alive)
        self.assertIs(cs.pid_alive_for_job, pid_alive_for_job)

    def test_compare_fake_still_writes_synthesis(self) -> None:
        import tempfile

        from packages.compare_jobs.spawn import FakeSpawnBackend

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "packet"
            job = {
                "out_dir": str(out),
                "ticker": "META",
                "session_a": "2026-08-03",
                "session_b": "2026-08-10",
            }
            FakeSpawnBackend(write_synthesis=True).spawn(job)
            self.assertTrue((out / "99_synthesis.md").is_file())
            self.assertTrue((out / "README.md").is_file())


class DetachFlagTests(unittest.TestCase):
    def test_windows_creationflags_include_detached(self) -> None:
        import subprocess

        from packages.agent_jobs.spawn import GrokSpawnBackend

        captured: dict[str, Any] = {}

        class FakePopen:
            def __init__(self, cmd, **kwargs):  # noqa: ANN003
                captured["cmd"] = cmd
                captured["kwargs"] = kwargs
                self.pid = 4242

        with (
            patch("packages.agent_jobs.spawn.grok_binary", return_value="grok"),
            patch("packages.agent_jobs.spawn.subprocess.Popen", FakePopen),
            patch("packages.agent_jobs.spawn.sys.platform", "win32"),
            tempfile_job() as job,
        ):
            GrokSpawnBackend().spawn(job)
        flags = int(captured["kwargs"].get("creationflags") or 0)
        self.assertTrue(flags & int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200)))
        self.assertTrue(flags & int(getattr(subprocess, "DETACHED_PROCESS", 0x8)))
        self.assertEqual(captured["kwargs"].get("stdin"), subprocess.DEVNULL)


class tempfile_job:
    def __enter__(self) -> dict:
        import tempfile

        self._td = tempfile.TemporaryDirectory()
        out = Path(self._td.name)
        (out / "prompt.md").write_text("hi\n", encoding="utf-8")
        return {"out_dir": str(out), "project_root": str(out)}

    def __exit__(self, *args: object) -> None:
        self._td.cleanup()


if __name__ == "__main__":
    unittest.main()

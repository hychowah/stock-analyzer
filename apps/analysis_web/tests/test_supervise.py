"""Unit tests for the git-SHA UI supervisor (no live port bind)."""

from __future__ import annotations

import subprocess
import unittest
from unittest import mock

from apps.analysis_web.supervise import child_argv, head_changed, stop_child


class HeadChangedTests(unittest.TestCase):
    def test_equal(self):
        self.assertFalse(head_changed("aaa", "aaa"))

    def test_different(self):
        self.assertTrue(head_changed("aaa", "bbb"))

    def test_any_none_is_not_a_change(self):
        self.assertFalse(head_changed(None, None))
        self.assertFalse(head_changed("aaa", None))
        self.assertFalse(head_changed(None, "aaa"))


class ChildArgvTests(unittest.TestCase):
    def test_one_shot_child_not_nested_supervisor(self):
        argv = child_argv("127.0.0.1", 8765)
        self.assertEqual(argv[1:3], ["-m", "apps.analysis_web"])
        self.assertIn("--no-auto-restart", argv)
        self.assertEqual(argv[argv.index("--host") + 1], "127.0.0.1")
        self.assertEqual(argv[argv.index("--port") + 1], "8765")


class StopChildTests(unittest.TestCase):
    def test_source_never_tree_kills(self):
        from pathlib import Path

        src = (Path(__file__).resolve().parents[1] / "supervise.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("from packages.agent_jobs", src)
        self.assertNotIn("kill_pid(", src)
        self.assertNotIn("taskkill /T", src)
        self.assertNotIn('["taskkill"', src)

    def test_stop_uses_pid_kill_not_taskkill(self):
        class FakeProc:
            def __init__(self):
                self.returncode = None
                self.signals: list[object] = []
                self.killed = False

            def poll(self):
                return self.returncode

            def send_signal(self, sig):
                self.signals.append(sig)

            def terminate(self):
                self.signals.append("TERM")

            def kill(self):
                self.killed = True
                self.returncode = 1

            def wait(self, timeout=None):
                if self.returncode is not None:
                    return self.returncode
                raise subprocess.TimeoutExpired(cmd="fake", timeout=timeout)

        proc = FakeProc()
        code = stop_child(proc)  # type: ignore[arg-type]
        self.assertTrue(proc.killed)
        self.assertEqual(code, 1)
        self.assertTrue(proc.signals)


class ServeTests(unittest.TestCase):
    def test_no_auto_restart_is_run_server(self):
        from apps.analysis_web import supervise as s

        with mock.patch.object(s, "run_server", return_value=0) as run:
            with mock.patch.object(s, "_supervise") as sup:
                self.assertEqual(s.serve("127.0.0.1", 8765, auto_restart=False), 0)
                run.assert_called_once_with("127.0.0.1", 8765)
                sup.assert_not_called()

    def test_supervise_replaces_child_on_sha_change(self):
        from apps.analysis_web import supervise as s

        calls = {"spawn": 0, "stop": 0}
        shas = ["a" * 40, "a" * 40, "b" * 40]

        class Child:
            def __init__(self):
                self.returncode = None

            def poll(self):
                return self.returncode

        def fake_git():
            return shas.pop(0) if len(shas) > 1 else shas[0]

        def fake_spawn(host, port):
            calls["spawn"] += 1
            c = Child()
            if calls["spawn"] >= 2:
                c.returncode = 0
            return c

        def fake_stop(proc):
            calls["stop"] += 1
            proc.returncode = 0
            return 0

        with mock.patch.object(s, "git_head_sha", fake_git):
            with mock.patch.object(s, "spawn_child", fake_spawn):
                with mock.patch.object(s, "stop_child", fake_stop):
                    with mock.patch.object(s, "wait_port_free", lambda *a, **k: True):
                        with mock.patch.object(s, "POLL_S", 0):
                            code = s._supervise("127.0.0.1", 8765)
        self.assertEqual(calls["spawn"], 2)
        self.assertEqual(calls["stop"], 1)
        self.assertEqual(code, 0)

    def test_supervise_none_sha_does_not_replace(self):
        from apps.analysis_web import supervise as s

        calls = {"stop": 0}

        class Child:
            def __init__(self):
                self.ticks = 0
                self.returncode = None

            def poll(self):
                self.ticks += 1
                if self.ticks > 3:
                    self.returncode = 7
                return self.returncode

        seq = ["a" * 40, None, None, None, None]

        def fake_git():
            return seq.pop(0) if seq else None

        def fake_stop(proc):
            calls["stop"] += 1
            return 0

        with mock.patch.object(s, "git_head_sha", fake_git):
            with mock.patch.object(s, "spawn_child", lambda *a, **k: Child()):
                with mock.patch.object(s, "stop_child", fake_stop):
                    with mock.patch.object(s, "POLL_S", 0):
                        code = s._supervise("127.0.0.1", 8765)
        self.assertEqual(code, 7)
        self.assertEqual(calls["stop"], 0)

    def test_supervise_none_boot_never_arms(self):
        from apps.analysis_web import supervise as s

        calls = {"stop": 0}

        class Child:
            def __init__(self):
                self.ticks = 0
                self.returncode = None

            def poll(self):
                self.ticks += 1
                if self.ticks > 4:
                    self.returncode = 0
                return self.returncode

        seq = [None, "a" * 40, "b" * 40, "b" * 40, "b" * 40]

        def fake_git():
            return seq.pop(0) if seq else "b" * 40

        def fake_stop(proc):
            calls["stop"] += 1
            return 0

        with mock.patch.object(s, "git_head_sha", fake_git):
            with mock.patch.object(s, "spawn_child", lambda *a, **k: Child()):
                with mock.patch.object(s, "stop_child", fake_stop):
                    with mock.patch.object(s, "POLL_S", 0):
                        code = s._supervise("127.0.0.1", 8765)
        self.assertEqual(code, 0)
        self.assertEqual(calls["stop"], 0)


if __name__ == "__main__":
    unittest.main()


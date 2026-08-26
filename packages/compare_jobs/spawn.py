"""Spawn backends for session-valuation-audit (real Grok or test fake)."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass
class SpawnResult:
    pid: int | None
    grok_session_id: str | None
    command: list[str]


class SpawnBackend(Protocol):
    def spawn(self, job: dict[str, Any]) -> SpawnResult: ...


def grok_binary() -> str | None:
    raw = os.environ.get("GROK_BIN")
    if raw and raw.strip():
        return raw.strip()
    return shutil.which("grok")


def pid_alive(pid: int | None) -> bool:
    if not pid or int(pid) <= 0:
        return False
    pid = int(pid)
    if sys.platform == "win32":
        try:
            import ctypes

            still_active = 259
            query = 0x1000  # PROCESS_QUERY_LIMITED_INFORMATION
            handle = ctypes.windll.kernel32.OpenProcess(query, False, pid)
            if not handle:
                return False
            try:
                code = ctypes.c_ulong()
                ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
                if ok == 0:
                    return False
                return int(code.value) == still_active
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def kill_pid(pid: int | None) -> None:
    if not pid or int(pid) <= 0:
        return
    pid = int(pid)
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass


class FakeSpawnBackend:
    """Writes README + synthesis so tests never call Grok."""

    def __init__(self, *, write_synthesis: bool = True) -> None:
        self.write_synthesis = write_synthesis

    def spawn(self, job: dict[str, Any]) -> SpawnResult:
        out = Path(str(job["out_dir"]))
        out.mkdir(parents=True, exist_ok=True)
        a = job.get("session_a")
        b = job.get("session_b")
        ticker = job.get("ticker")
        (out / "README.md").write_text(
            f"# Compare {ticker} {a} vs {b}\n\n"
            f"Read [99_synthesis.md](99_synthesis.md) first.\n",
            encoding="utf-8",
        )
        if self.write_synthesis:
            (out / "99_synthesis.md").write_text(
                f"# Synthesis\n\n"
                f"Fake audit complete for **{ticker}** `{a}` vs `{b}`.\n\n"
                "Do not average the two base FVs.\n",
                encoding="utf-8",
            )
        return SpawnResult(pid=None, grok_session_id="fake", command=["fake-compare"])


class GrokSpawnBackend:
    def spawn(self, job: dict[str, Any]) -> SpawnResult:
        binary = grok_binary()
        if not binary:
            raise FileNotFoundError(
                "Grok CLI not found. Install grok or set GROK_BIN. "
                "Headless compare needs a logged-in grok or XAI_API_KEY."
            )
        out = Path(str(job["out_dir"]))
        prompt_path = out / "prompt.md"
        session_uuid = str(uuid.uuid4())
        cwd = str(job.get("project_root") or Path.cwd())
        log_path = out / "grok.log"
        cmd = [
            binary,
            "--prompt-file",
            str(prompt_path),
            "--cwd",
            cwd,
            "--yolo",
            "--no-plan",
            "--output-format",
            "json",
            "--session-id",
            session_uuid,
        ]
        log_handle = open(log_path, "ab")  # noqa: SIM115 — kept for process lifetime
        kwargs: dict[str, Any] = {
            "stdout": log_handle,
            "stderr": subprocess.STDOUT,
            "cwd": cwd,
            "stdin": subprocess.DEVNULL,
        }
        if sys.platform == "win32":
            flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            kwargs["creationflags"] = flags
        else:
            kwargs["start_new_session"] = True
        proc = subprocess.Popen(cmd, **kwargs)  # noqa: S603 — grok binary + fixed flags
        # Parent must not keep the log fd; child inherited it.
        try:
            log_handle.close()
        except OSError:
            pass
        return SpawnResult(
            pid=int(proc.pid),
            grok_session_id=session_uuid,
            command=cmd,
        )


def default_spawn_backend() -> SpawnBackend:
    mode = (os.environ.get("COMPARE_SPAWN") or "grok").strip().lower()
    if mode in {"fake", "test"}:
        write = os.environ.get("COMPARE_SPAWN_SYNTHESIS", "1") not in (
            "0",
            "false",
            "False",
            "",
        )
        return FakeSpawnBackend(write_synthesis=write)
    return GrokSpawnBackend()

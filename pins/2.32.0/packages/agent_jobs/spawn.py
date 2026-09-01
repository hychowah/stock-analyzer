"""Shared Grok spawn / PID helpers.

Grok is a detached child: killing the FastAPI UI must not kill the worker.
Cancel is best-effort on the orchestrator pid tree, not a proof that
spawn_subagent children are gone.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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


def _parse_spawned_at(value: str | None) -> datetime | None:
    if not value or not str(value).strip():
        return None
    raw = str(value).strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _filetime_to_utc(high: int, low: int) -> datetime | None:
    ticks = (int(high) << 32) | int(low)
    if ticks <= 0:
        return None
    unix = ticks / 10_000_000 - 11_644_473_600
    try:
        return datetime.fromtimestamp(unix, tz=timezone.utc)
    except (OSError, OverflowError, ValueError):
        return None


def process_create_time(pid: int) -> datetime | None:
    """Birth time of a live process, or None if unknown."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            query = 0x1000  # PROCESS_QUERY_LIMITED_INFORMATION
            handle = ctypes.windll.kernel32.OpenProcess(query, False, int(pid))
            if not handle:
                return None
            try:
                ctime = wintypes.FILETIME()
                etime = wintypes.FILETIME()
                ktime = wintypes.FILETIME()
                utime = wintypes.FILETIME()
                ok = ctypes.windll.kernel32.GetProcessTimes(
                    handle,
                    ctypes.byref(ctime),
                    ctypes.byref(etime),
                    ctypes.byref(ktime),
                    ctypes.byref(utime),
                )
                if ok == 0:
                    return None
                return _filetime_to_utc(ctime.dwHighDateTime, ctime.dwLowDateTime)
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            return None
    proc = Path("/proc") / str(int(pid))
    try:
        st = proc.stat()
    except OSError:
        return None
    birth = getattr(st, "st_birthtime", None)
    if birth:
        try:
            return datetime.fromtimestamp(float(birth), tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None
    return None


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


def pid_alive_for_job(pid: int | None, spawned_at: str | None) -> bool:
    """True only if pid is live *and* not an obvious PID reuse.

    If the live process was created more than 60s after ``spawned_at``, it
    cannot be the Grok we spawned (overnight Analyze PID reuse).
    """
    if not pid_alive(pid):
        return False
    spawned = _parse_spawned_at(spawned_at)
    if spawned is None:
        return True
    created = process_create_time(int(pid))
    if created is None:
        return True
    if created > spawned + timedelta(seconds=60):
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
        os.killpg(pid, signal.SIGTERM)
        return
    except OSError:
        pass
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass


def _job_dir(job: dict[str, Any]) -> Path:
    raw = job.get("out_dir") or job.get("job_dir") or ""
    return Path(str(raw))


class GrokSpawnBackend:
    def spawn(self, job: dict[str, Any]) -> SpawnResult:
        binary = grok_binary()
        if not binary:
            raise FileNotFoundError(
                "Grok CLI not found. Install grok or set GROK_BIN. "
                "Headless jobs need a logged-in grok or XAI_API_KEY."
            )
        out = _job_dir(job)
        out.mkdir(parents=True, exist_ok=True)
        prompt_path = out / "prompt.md"
        session_uuid = str(uuid.uuid4())
        cwd = str(job.get("spawn_cwd") or job.get("project_root") or Path.cwd())
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
        env = os.environ.copy()
        extra = job.get("spawn_env")
        if isinstance(extra, dict):
            if extra.get("PYTHONPATH"):
                env["PYTHONPATH"] = str(extra["PYTHONPATH"])
            if extra.get("ARCHIVE_ROOT"):
                env["ARCHIVE_ROOT"] = str(extra["ARCHIVE_ROOT"])
        archive = job.get("archive_root")
        if archive and "ARCHIVE_ROOT" not in (extra or {}):
            env["ARCHIVE_ROOT"] = str(archive)
        kwargs: dict[str, Any] = {
            "stdout": log_handle,
            "stderr": subprocess.STDOUT,
            "cwd": cwd,
            "stdin": subprocess.DEVNULL,
            "env": env,
        }
        if sys.platform == "win32":
            new_group = int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200))
            detached = int(getattr(subprocess, "DETACHED_PROCESS", 0x00000008))
            kwargs["creationflags"] = new_group | detached
        else:
            kwargs["start_new_session"] = True
        proc = subprocess.Popen(cmd, **kwargs)  # noqa: S603 — grok binary + fixed flags
        try:
            log_handle.close()
        except OSError:
            pass
        return SpawnResult(
            pid=int(proc.pid),
            grok_session_id=session_uuid,
            command=cmd,
        )

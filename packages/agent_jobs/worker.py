"""SpawnBackend.spawn is a durable worker handle, not "Popen and hope".

Before spawn returns, callers write job.json running with pid + grok_session_id
via record_spawn. orchestrator_alive(job): recorded pid (reuse-guarded) or a
process still carrying grok_session_id. session_busy(job, work_root):
orchestrator_alive OR any process whose command line or cwd names this
session/packet. refresh must not use PID death alone as job death.

kill(job) is best-effort on the recorded orchestrator pid tree.
It does not prove specialists are gone (product law).
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from packages.agent_jobs.spawn import (
    SpawnResult,
    kill_pid,
    pid_alive_for_job,
)
from packages.agent_jobs.store import write_job

SLOT_STATUSES = frozenset({"starting", "queued", "running"})
FAKE_SESSION_IDS = frozenset({"fake", "fake-analyze", "fake-compare"})


@dataclass(frozen=True)
class ProcInfo:
    pid: int
    cmdline: str
    cwd: str | None = None


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_fake_spawn(job: dict[str, Any]) -> bool:
    """True when tests used a fake backend (no OS process).

    A recorded pid means we use OS liveness even if the session id was 'fake'.
    """
    if job.get("pid"):
        return False
    sid = str(job.get("grok_session_id") or "").strip().lower()
    if sid in FAKE_SESSION_IDS:
        return True
    cmd = job.get("command")
    if isinstance(cmd, list) and cmd:
        first = str(cmd[0]).lower()
        if first.startswith("fake"):
            return True
    return False


def work_root(job: dict[str, Any]) -> Path | None:
    raw = job.get("session_root") or job.get("out_dir") or job.get("job_dir") or ""
    if not raw or str(raw).strip() in {".", ""}:
        return None
    return Path(str(raw))


def record_spawn(job: dict[str, Any], result: SpawnResult, path: Path) -> None:
    """Write running + pid + grok_session_id before the start call returns."""
    job["pid"] = result.pid
    job["grok_session_id"] = result.grok_session_id
    job["command"] = result.command
    job["status"] = "running"
    job["error"] = None
    job["pid_missing"] = False
    job["spawned_at"] = _utc_stamp()
    job["updated_at"] = job["spawned_at"]
    write_job(path, job)


def orchestrator_alive(
    job: dict[str, Any],
    *,
    processes: Iterable[ProcInfo] | None = None,
) -> bool:
    """True if the recorded orchestrator pid is still this job's process."""
    if is_fake_spawn(job) and not job.get("pid"):
        return False
    pid = job.get("pid")
    spawned = job.get("spawned_at")
    if pid_alive_for_job(
        int(pid) if pid else None,
        spawned if isinstance(spawned, str) else None,
    ):
        return True
    sid = str(job.get("grok_session_id") or "").strip()
    if not sid or sid.lower() in FAKE_SESSION_IDS:
        return False
    try:
        procs = list(processes) if processes is not None else list(iter_processes())
    except Exception:
        return False
    for proc in procs:
        if sid in (proc.cmdline or ""):
            return True
    return False


def session_busy(
    job: dict[str, Any],
    work: Path | None = None,
    *,
    processes: Iterable[ProcInfo] | None = None,
) -> bool:
    """True if this job's work is still present on the machine.

    If process listing fails, return True (do not treat the job as dead).
    """
    if is_fake_spawn(job):
        return False
    if orchestrator_alive(job, processes=processes):
        return True
    root = work if work is not None else work_root(job)
    if root is None:
        return False
    try:
        marker = str(root.resolve())
    except OSError:
        marker = str(root)
    if processes is not None:
        procs = list(processes)
    else:
        try:
            procs = list(iter_processes())
        except Exception:
            return True
    needles = {marker.lower(), marker.replace("\\", "/").lower(), marker.replace("/", "\\").lower()}
    for proc in procs:
        blob = f"{proc.cmdline} {proc.cwd or ''}".lower()
        blob_slash = blob.replace("\\", "/")
        blob_bslash = blob.replace("/", "\\")
        for n in needles:
            if n and (n in blob or n in blob_slash or n in blob_bslash):
                return True
    return False


def apply_liveness(
    job: dict[str, Any],
    *,
    processes: Iterable[ProcInfo] | None = None,
) -> bool:
    """Update starting/queued/running from worker evidence. Return True if changed.

    Fake spawn (pid None) stays running until the caller sees snapshot/synthesis.
    PID death alone is not a status transition. Failed means no worker evidence.
    """
    status = str(job.get("status") or "")
    if status not in SLOT_STATUSES:
        return False
    if is_fake_spawn(job):
        if job.get("pid_missing"):
            job["pid_missing"] = False
            return True
        return False
    if orchestrator_alive(job, processes=processes):
        changed = False
        if status != "running":
            job["status"] = "running"
            changed = True
        if job.get("pid_missing"):
            job["pid_missing"] = False
            changed = True
        return changed
    if session_busy(job, processes=processes):
        changed = False
        if status != "running":
            job["status"] = "running"
            changed = True
        if not job.get("pid_missing"):
            job["pid_missing"] = True
            changed = True
        return changed
    if status == "running" and job.get("pid"):
        job["status"] = "failed"
        job["error"] = "Grok process exited before finalize"
        job["abandoned"] = False
        job["pid_missing"] = False
        return True
    # starting/queued with no worker: leave for reconcile (not a death timer).
    return False


def kill(job: dict[str, Any]) -> None:
    """Best-effort kill of the recorded orchestrator pid tree."""
    pid = job.get("pid")
    spawned = job.get("spawned_at")
    if not pid_alive_for_job(
        int(pid) if pid else None,
        spawned if isinstance(spawned, str) else None,
    ):
        return
    kill_pid(pid)


_PROC_CACHE: tuple[float, list[ProcInfo]] | None = None
_PROC_CACHE_S = 2.0


def iter_processes() -> list[ProcInfo]:
    """Best-effort process list. Raises on total failure so session_busy can stay busy."""
    import time

    global _PROC_CACHE
    now = time.monotonic()
    if _PROC_CACHE is not None and now - _PROC_CACHE[0] < _PROC_CACHE_S:
        return list(_PROC_CACHE[1])
    if sys.platform == "win32":
        rows = _iter_processes_win()
    else:
        rows = _iter_processes_posix()
    _PROC_CACHE = (now, rows)
    return list(rows)


def _iter_processes_posix() -> list[ProcInfo]:
    proc = Path("/proc")
    if not proc.is_dir():
        raise FileNotFoundError("/proc")
    out: list[ProcInfo] = []
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        if not raw:
            continue
        cmdline = raw.replace(b"\x00", b" ").decode("utf-8", "replace").strip()
        cwd: str | None = None
        try:
            cwd = os.readlink(entry / "cwd")
        except OSError:
            cwd = None
        out.append(ProcInfo(pid=int(entry.name), cmdline=cmdline, cwd=cwd))
    return out


def _iter_processes_win() -> list[ProcInfo]:
    from packages.agent_jobs.spawn import grok_binary

    if not grok_binary():
        return []
    # Filter to grok so we do not CIM-dump the whole machine on every refresh.
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Get-CimInstance Win32_Process -Filter \"Name = 'grok.exe'\" "
        "| Select-Object ProcessId,CommandLine | ConvertTo-Csv -NoTypeInformation",
    ]
    proc = subprocess.run(  # noqa: S603
        cmd,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or "process list failed")
    lines = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    if len(lines) < 2:
        return []
    out: list[ProcInfo] = []
    for line in lines[1:]:
        # CSV: "ProcessId","CommandLine"
        parts = _split_csv_line(line)
        if len(parts) < 1:
            continue
        try:
            pid = int(parts[0].strip())
        except ValueError:
            continue
        cmdline = parts[1] if len(parts) > 1 else ""
        out.append(ProcInfo(pid=pid, cmdline=cmdline, cwd=None))
    return out


def _split_csv_line(line: str) -> list[str]:
    out: list[str] = []
    cur: list[str] = []
    in_q = False
    i = 0
    while i < len(line):
        ch = line[i]
        if in_q:
            if ch == '"' and i + 1 < len(line) and line[i + 1] == '"':
                cur.append('"')
                i += 2
                continue
            if ch == '"':
                in_q = False
                i += 1
                continue
            cur.append(ch)
            i += 1
            continue
        if ch == '"':
            in_q = True
            i += 1
            continue
        if ch == ",":
            out.append("".join(cur))
            cur = []
            i += 1
            continue
        cur.append(ch)
        i += 1
    out.append("".join(cur))
    return out

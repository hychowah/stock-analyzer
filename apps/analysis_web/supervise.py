"""Keep one Analysis UI serving current git HEAD.

Default ``python -m apps.analysis_web`` is a supervisor: poll
``git_head_sha`` and replace the uvicorn child when HEAD moves.
``--no-auto-restart`` is the one-shot server (debug freeze and the child).

Replacing this process is the same as Ctrl+C: Grok workers are detached
and keep running. Do not import ``packages.agent_jobs`` (those helpers
exist so Grok *survives* UI death). Stop the UI PID only — a process-tree
kill would take running Analyze/Compare with it.

``harness_version=live`` is the workspace, not a spawn-time copy.
``prompt.md`` is frozen; ``PYTHONPATH`` / ``cwd`` are not. This module
must not re-spawn or rewrite running jobs.

``None`` from git (OneDrive lock, not a repo) means keep serving — never
treat a missing SHA as a change.
"""

from __future__ import annotations

import signal
import socket
import subprocess
import sys
import time
from typing import Any

from packages.kd_research.paths import PROJECT_ROOT
from packages.kd_research.provenance import git_head_sha

SHUTDOWN_BUDGET_S = 3
POLL_S = 2
PORT_WAIT_S = SHUTDOWN_BUDGET_S + 2


def head_changed(prev: str | None, cur: str | None) -> bool:
    """True only when both SHAs are known and different."""
    if prev is None or cur is None:
        return False
    return prev != cur


def child_argv(host: str, port: int) -> list[str]:
    return [
        sys.executable,
        "-m",
        "apps.analysis_web",
        "--host",
        str(host),
        "--port",
        str(int(port)),
        "--no-auto-restart",
    ]


def run_server(host: str, port: int) -> int:
    """One-shot uvicorn (the child, or ``--no-auto-restart``)."""
    try:
        import uvicorn
    except ImportError:
        print(
            "uvicorn is required. Install: pip install -r apps/analysis_web/requirements.txt",
            file=sys.stderr,
        )
        return 1
    uvicorn.run(
        "apps.analysis_web.app:app",
        host=host,
        port=int(port),
        reload=False,
        log_level="info",
        timeout_graceful_shutdown=SHUTDOWN_BUDGET_S,
    )
    return 0


def port_bound(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=0.2):
            return True
    except OSError:
        return False


def wait_port_free(host: str, port: int, timeout_s: float = PORT_WAIT_S) -> bool:
    deadline = time.monotonic() + float(timeout_s)
    while time.monotonic() < deadline:
        if not port_bound(host, port):
            return True
        time.sleep(0.1)
    return not port_bound(host, port)


def spawn_child(host: str, port: int) -> subprocess.Popen[Any]:
    kwargs: dict[str, Any] = {"cwd": str(PROJECT_ROOT)}
    if sys.platform == "win32":
        # New group so CTRL_BREAK can target the UI child. Not DETACHED —
        # this is the UI, not Grok.
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    return subprocess.Popen(child_argv(host, port), **kwargs)  # noqa: S603


def stop_child(proc: subprocess.Popen[Any]) -> int:
    """Graceful-stop the UI process only (never a process-tree kill)."""
    if proc.poll() is not None:
        return int(proc.returncode or 0)
    try:
        if sys.platform == "win32":
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            proc.terminate()
    except (OSError, ValueError):
        pass
    try:
        return int(proc.wait(timeout=SHUTDOWN_BUDGET_S))
    except subprocess.TimeoutExpired:
        pass
    try:
        proc.kill()
    except OSError:
        pass
    try:
        return int(proc.wait(timeout=2))
    except subprocess.TimeoutExpired:
        return 1


def serve(host: str, port: int, *, auto_restart: bool) -> int:
    if not auto_restart:
        return run_server(host, port)
    return _supervise(host, port)


def _supervise(host: str, port: int) -> int:
    sha = git_head_sha()
    print("  auto-restart on (poll git HEAD; --no-auto-restart to freeze)")
    if sha:
        print(f"  git HEAD={sha[:12]}")
    else:
        print("  git HEAD=unknown (keep serving; auto-restart stays off until this supervisor is restarted)")
    proc = spawn_child(host, port)
    try:
        while True:
            code = proc.poll()
            if code is not None:
                return int(code)
            cur = git_head_sha()
            if head_changed(sha, cur):
                print(
                    f"git HEAD {sha} -> {cur}; restarting UI (Grok jobs keep running)",
                    flush=True,
                )
                stop_child(proc)
                if not wait_port_free(host, port):
                    print(
                        f"port {port} still bound after shutdown. "
                        "If a Store-Python wrapper leftover holds the port, "
                        "taskkill /F the python3.12.exe PID.",
                        file=sys.stderr,
                    )
                    return 1
                sha = cur
                proc = spawn_child(host, port)
            else:
                time.sleep(POLL_S)
    except KeyboardInterrupt:
        stop_child(proc)
        return 0

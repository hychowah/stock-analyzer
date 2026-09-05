"""Compare spawn backends.

Shared Grok/PID helpers live in ``packages.agent_jobs.spawn``. The compare
fake stays here so it can write ``99_synthesis.md`` — Analyze must not reuse it.
``COMPARE_SPAWN`` remains the env switch for Compare tests.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from packages.agent_jobs.spawn import (  # noqa: F401 — re-export
    GrokSpawnBackend,
    SpawnBackend,
    SpawnResult,
    grok_binary,
    kill_pid,
    pid_alive,
    pid_alive_for_job,
)


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


def default_spawn_backend() -> SpawnBackend:
    raw = os.environ.get("COMPARE_SPAWN") or os.environ.get("AGENT_SPAWN") or "grok"
    mode = raw.strip().lower()
    if mode in {"fake", "test"}:
        write = os.environ.get("COMPARE_SPAWN_SYNTHESIS", "1") not in (
            "0",
            "false",
            "False",
            "",
        )
        return FakeSpawnBackend(write_synthesis=write)
    return GrokSpawnBackend()

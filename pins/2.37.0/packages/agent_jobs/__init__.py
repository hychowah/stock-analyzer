"""Shared Grok job runtime (spawn, PID, capacity).

Compare and Analyze are different job kinds. This package does not invent
fair values and does not write research session artifacts.
"""

from __future__ import annotations

from packages.agent_jobs.capacity import (
    ANALYZE_MAX,
    COMPARE_MAX,
    JobsBusy,
    Limits,
    assert_capacity,
    check_slots,
    claim_start,
    exclusive_start_lock,
    limits,
    running_by_kind,
)
from packages.agent_jobs.spawn import (
    GrokSpawnBackend,
    SpawnBackend,
    SpawnResult,
    grok_binary,
    kill_pid,
    pid_alive,
    pid_alive_for_job,
)

__all__ = [
    "ANALYZE_MAX",
    "COMPARE_MAX",
    "GrokSpawnBackend",
    "JobsBusy",
    "Limits",
    "SpawnBackend",
    "SpawnResult",
    "assert_capacity",
    "check_slots",
    "claim_start",
    "exclusive_start_lock",
    "grok_binary",
    "kill_pid",
    "limits",
    "pid_alive",
    "pid_alive_for_job",
    "running_by_kind",
]

"""Shared Grok job runtime (spawn, PID, capacity, durable job write).

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
from packages.agent_jobs.reconcile import reconcile_jobs
from packages.agent_jobs.spawn import (
    GrokSpawnBackend,
    SpawnBackend,
    SpawnResult,
    grok_binary,
    kill_pid,
    pid_alive,
    pid_alive_for_job,
)
from packages.agent_jobs.store import write_job
from packages.agent_jobs.worker import (
    SLOT_STATUSES,
    apply_liveness,
    kill,
    orchestrator_alive,
    record_spawn,
    session_busy,
)

__all__ = [
    "ANALYZE_MAX",
    "COMPARE_MAX",
    "GrokSpawnBackend",
    "JobsBusy",
    "Limits",
    "SLOT_STATUSES",
    "SpawnBackend",
    "SpawnResult",
    "apply_liveness",
    "assert_capacity",
    "check_slots",
    "claim_start",
    "exclusive_start_lock",
    "grok_binary",
    "kill",
    "kill_pid",
    "limits",
    "orchestrator_alive",
    "pid_alive",
    "pid_alive_for_job",
    "reconcile_jobs",
    "record_spawn",
    "running_by_kind",
    "session_busy",
    "write_job",
]

"""Per-kind slots + global Grok process cap.

Callers must refresh job status (PID death, completion) *before* counting.
This module does not walk the archive; it only applies limits.
"""

from __future__ import annotations

import os
from typing import Mapping


class JobsBusy(Exception):
    pass


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return int(str(raw).strip())
    except ValueError:
        return default


def limits() -> tuple[int, int, int]:
    """Return (ANALYZE_MAX, COMPARE_MAX, GROK_JOBS_MAX)."""
    return (
        max(0, _env_int("ANALYZE_MAX", 1)),
        max(0, _env_int("COMPARE_MAX", 1)),
        max(0, _env_int("GROK_JOBS_MAX", 2)),
    )


ANALYZE_MAX = 1
COMPARE_MAX = 1
GROK_JOBS_MAX = 2


def assert_capacity(
    kind: str,
    *,
    running_by_kind: Mapping[str, int],
) -> None:
    """Raise JobsBusy if starting ``kind`` would exceed a slot or the global cap.

    ``running_by_kind`` is the count *after refresh*, not including the job
    being started. Same-id resume of an already-running row must not call this
    (or must exclude that row from the count).
    """
    analyze_max, compare_max, grok_max = limits()
    n_compare = int(running_by_kind.get("compare") or 0)
    n_analyze = int(running_by_kind.get("analyze") or 0)
    want = (kind or "").strip().lower()
    if want == "compare" and n_compare >= compare_max:
        raise JobsBusy(
            f"A Grok compare is already running (COMPARE_MAX={compare_max}). "
            "Wait or cancel it first."
        )
    if want == "analyze" and n_analyze >= analyze_max:
        raise JobsBusy(
            f"A Grok Analyze is already running (ANALYZE_MAX={analyze_max}). "
            "Wait or cancel it first."
        )
    total = n_compare + n_analyze
    if total >= grok_max:
        raise JobsBusy(
            f"Grok job cap reached ({total} running, GROK_JOBS_MAX={grok_max}). "
            "Wait or cancel a job first."
        )
    if want not in {"compare", "analyze"}:
        raise JobsBusy(f"unknown Grok job kind: {kind!r}")

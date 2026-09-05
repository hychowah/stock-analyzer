"""Grok job start gate: kind slots, derived global cap, census, exclusive lock.

``ANALYZE_MAX`` / ``COMPARE_MAX`` are default kind slots only. Live values are
``limits()``. Unset ``GROK_JOBS_MAX`` is the sum of the effective kind slots;
set it to tighten (``1`` serializes). Callers hold ``claim_start`` until the
job row is marked running.
"""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Mapping


class JobsBusy(Exception):
    pass


# Default kind slots. Global cap is derived unless GROK_JOBS_MAX is set.
ANALYZE_MAX = 3
COMPARE_MAX = 1


@dataclass(frozen=True)
class Limits:
    analyze: int
    compare: int
    grok: int

    @property
    def analyze_slots(self) -> int:
        """How many Analyze jobs can actually run (kind slot ∩ global cap)."""
        return min(self.analyze, self.grok)

    @property
    def compare_slots(self) -> int:
        return min(self.compare, self.grok)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return int(str(raw).strip())
    except ValueError:
        return default


def _env_int_or_none(name: str) -> int | None:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return None
    try:
        return int(str(raw).strip())
    except ValueError:
        return None


def limits() -> Limits:
    """Live kind slots and global cap (env overrides, else kind-slot sum)."""
    analyze = max(0, _env_int("ANALYZE_MAX", ANALYZE_MAX))
    compare = max(0, _env_int("COMPARE_MAX", COMPARE_MAX))
    grok_override = _env_int_or_none("GROK_JOBS_MAX")
    if grok_override is None:
        grok = analyze + compare
    else:
        grok = max(0, grok_override)
    return Limits(analyze=analyze, compare=compare, grok=grok)


def check_slots(kind: str, running_by_kind: Mapping[str, int]) -> None:
    """Raise JobsBusy if starting ``kind`` would exceed a slot or the global cap.

    ``running_by_kind`` is the count *after refresh*, not including the job
    being started. Same-id resume of an already-running row must not call this
    (or must exclude that row from the count).
    """
    caps = limits()
    n_compare = int(running_by_kind.get("compare") or 0)
    n_analyze = int(running_by_kind.get("analyze") or 0)
    want = (kind or "").strip().lower()
    if want == "compare" and n_compare >= caps.compare:
        raise JobsBusy(
            f"Compare slots full ({n_compare} running, COMPARE_MAX={caps.compare}). "
            "Wait or cancel one first."
        )
    if want == "analyze" and n_analyze >= caps.analyze:
        raise JobsBusy(
            f"Analyze slots full ({n_analyze} running, ANALYZE_MAX={caps.analyze}). "
            "Wait or cancel one first."
        )
    total = n_compare + n_analyze
    if total >= caps.grok:
        raise JobsBusy(
            f"Grok job cap reached ({total} running, GROK_JOBS_MAX={caps.grok}). "
            "Wait or cancel a job first."
        )
    if want not in {"compare", "analyze"}:
        raise JobsBusy(f"unknown Grok job kind: {kind!r}")


def running_by_kind(archive_root: Path) -> dict[str, int]:
    """Refresh both job planes and count ``running`` rows."""
    from packages.compare_jobs.jobs import count_running_compare
    from packages.research_jobs.jobs import count_running_analyze

    return {
        "compare": count_running_compare(archive_root),
        "analyze": count_running_analyze(archive_root),
    }


def assert_capacity(archive_root: Path, kind: str) -> None:
    """Census then ``check_slots``. Caller must hold ``exclusive_start_lock``."""
    check_slots(kind, running_by_kind(archive_root))


@contextmanager
def exclusive_start_lock(archive_root: Path) -> Iterator[None]:
    """Process-exclusive lock for every Grok start (Analyze and Compare)."""
    path = Path(archive_root).resolve() / ".grok_jobs.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(path, "a+b")
    try:
        fh.seek(0, os.SEEK_END)
        if fh.tell() == 0:
            fh.write(b"0")
            fh.flush()
        fh.seek(0)
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            if sys.platform == "win32":
                import msvcrt

                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        fh.close()


@contextmanager
def claim_start(archive_root: Path, kind: str) -> Iterator[None]:
    """Lock, census, slot check. Hold until the job is marked running."""
    with exclusive_start_lock(archive_root):
        assert_capacity(archive_root, kind)
        yield

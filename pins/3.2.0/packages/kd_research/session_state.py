"""Frozen vs writable research sessions.

True when the folder is frozen history: meta/prediction_snapshot.json exists
or run_manifest.immutable (or a completed status). In-progress Analyze
scaffolds and new empty trees are false. Writers may run only when false.
Export never writes the session.
"""

from __future__ import annotations

import json
from pathlib import Path

COMPLETED_STATUSES = frozenset(
    {"complete", "completed", "finalized", "done", "immutable"}
)


def session_is_completed(session: Path) -> bool:
    if (session / "meta" / "prediction_snapshot.json").is_file():
        return True
    man = session / "meta" / "run_manifest.json"
    if not man.is_file():
        return False
    try:
        data = json.loads(man.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(data, dict):
        return False
    if data.get("immutable") is True:
        return True
    status = str(data.get("status") or "").strip().lower()
    return status in COMPLETED_STATUSES

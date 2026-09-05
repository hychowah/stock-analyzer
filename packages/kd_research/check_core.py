"""Shared check I/O, result shape, and version compare.

Investment purpose: one place for (status, id, detail) rows, JSON-as-data,
and harness_version floors so domain modules do not import gates for I/O.
Writer JSON remains packages.kd_research.registry_io.load_json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, NamedTuple

from packages.kd_research.annuals import load_run_manifest_version, parse_semver

HOOK_REQUIRED_KEYS = ("from", "action", "reason")
HOOK_REASON_MIN_LEN = 10


class Check(NamedTuple):
    """One machine-check row. Unpacks as (status, id, detail)."""

    status: str
    id: str
    detail: str


def load_json(path: Path) -> tuple[Any | None, str | None]:
    """Read UTF-8 JSON. Missing or unparseable is data, not an exception."""
    if not path.exists():
        return None, "missing"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as e:  # noqa: BLE001
        return None, f"unparseable: {e}"


def session_since(session: Path, ver: tuple[int, int, int]) -> bool:
    """True when meta/run_manifest harness_version >= ver. Unparseable → False."""
    parsed = parse_semver(load_run_manifest_version(session))
    if parsed is None:
        return False
    return parsed >= ver


def validate_hooks_list(
    hooks: Any,
    *,
    check_id: str,
    empty_detail: str,
) -> list[tuple[str, str, str]]:
    """Structural validation for valuation hook arrays (MC / FDD / Street)."""
    out: list[tuple[str, str, str]] = []
    if not (isinstance(hooks, list) and len(hooks) >= 1):
        out.append(("FAIL", check_id, empty_detail))
        return out
    bad: list[str] = []
    for i, h in enumerate(hooks):
        if not isinstance(h, dict):
            bad.append(f"[{i}] not object")
            continue
        for k in HOOK_REQUIRED_KEYS:
            if k not in h or (isinstance(h.get(k), str) and not str(h.get(k)).strip()):
                bad.append(f"[{i}].{k}")
        reason = h.get("reason")
        if isinstance(reason, str) and len(reason.strip()) < HOOK_REASON_MIN_LEN:
            bad.append(f"[{i}].reason too short")
    if bad:
        out.append(("FAIL", f"{check_id} shape", "; ".join(bad[:8])))
        return out
    out.append(("PASS", check_id, f"{len(hooks)} hook(s)"))
    return out

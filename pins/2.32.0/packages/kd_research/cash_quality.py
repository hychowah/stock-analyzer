"""Wave 7 cash-quality gather (harness >= 2.15.0).

Latest-quarter cash_quality is required evidence. Agent 5 reads it; Agent 5
does not write it. Missing latest_quarter is SKIPPED.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.kd_research.annuals import load_run_manifest_version, parse_semver
from packages.kd_research.gates import load_json

WAVE7_SINCE = (2, 15, 0)
NUMERIC_KEYS = frozenset({"fcf", "cfo", "ni", "gaap_ni", "dso", "dio", "inventory"})


def session_is_wave7_runtime(session: Path) -> bool:
    parsed = parse_semver(load_run_manifest_version(session))
    if parsed is None:
        return False
    return parsed >= WAVE7_SINCE


def _as_float(val: Any) -> float | None:
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, dict):
        return _as_float(val.get("value"))
    return None


def _has_numeric(obj: Any) -> bool:
    if not isinstance(obj, dict):
        return False
    for key, val in obj.items():
        k = str(key).strip().lower()
        if k in NUMERIC_KEYS and _as_float(val) is not None:
            return True
        if isinstance(val, dict) and _has_numeric(val):
            return True
    return False


def check_cash_quality(session: Path) -> list[tuple[str, str, str]]:
    if not session_is_wave7_runtime(session):
        return [
            (
                "SKIPPED",
                "cash_quality",
                "legacy/slim (harness_version < 2.15.0)",
            )
        ]
    lq, err = load_json(session / "registry" / "latest_quarter.json")
    if err or not isinstance(lq, dict):
        return [("SKIPPED", "cash_quality", "latest_quarter.json missing")]
    cq = lq.get("cash_quality")
    if not isinstance(cq, dict) or not _has_numeric(cq):
        return [
            (
                "FAIL",
                "cash_quality",
                "harness ≥ 2.15.0 requires latest_quarter.cash_quality with ≥1 numeric "
                "among fcf, cfo, ni, gaap_ni, dso, dio, inventory (nested .value OK)",
            )
        ]
    return [("PASS", "cash_quality", "cash_quality object with a numeric field")]

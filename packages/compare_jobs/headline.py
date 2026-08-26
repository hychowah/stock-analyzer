"""Deterministic snapshot headline for two sessions (not the audit)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from scripts.kd_research.paths import resolve_session

_FIELD_GETTERS: list[tuple[str, Callable[[dict[str, Any]], Any]]] = [
    ("asof_price", lambda s: s.get("asof_price")),
    ("fv_base", lambda s: (s.get("fair_value") or {}).get("base")),
    ("fv_bear", lambda s: (s.get("fair_value") or {}).get("bear")),
    ("fv_bull", lambda s: (s.get("fair_value") or {}).get("bull")),
    ("margin_of_safety_pct", lambda s: s.get("margin_of_safety_pct")),
    ("audit_verdict", lambda s: s.get("audit_verdict")),
    ("primary_sector", lambda s: s.get("primary_sector")),
    ("region", lambda s: s.get("region")),
    ("verdict_line", lambda s: (s.get("verdict_line") or "")[:80]),
]


def load_snapshot(session_root: Path) -> dict[str, Any] | None:
    path = session_root / "meta" / "prediction_snapshot.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def headline_for_sessions(
    ticker: str,
    sessions: list[tuple[str, Path]],
) -> dict[str, Any]:
    """Build a JSON headline table from prediction snapshots.

    Missing snapshots are recorded; they do not abort the compare job.
    """
    columns: list[dict[str, Any]] = []
    for key, root in sessions:
        snap = load_snapshot(root)
        columns.append(
            {
                "session_key": key,
                "path": str(root),
                "snapshot_missing": snap is None,
                "snapshot": snap,
            }
        )

    fields: list[dict[str, Any]] = []
    for name, fn in _FIELD_GETTERS:
        values: dict[str, Any] = {}
        for col in columns:
            snap = col["snapshot"]
            values[col["session_key"]] = None if snap is None else fn(snap)
        fields.append({"field": name, "values": values})

    key_risks: dict[str, Any] = {}
    for col in columns:
        snap = col["snapshot"]
        key_risks[col["session_key"]] = None if snap is None else snap.get("key_risks")

    return {
        "ticker": ticker.upper(),
        "sessions": [c["session_key"] for c in columns],
        "degraded": any(c["snapshot_missing"] for c in columns),
        "fields": fields,
        "key_risks": key_risks,
    }


def headline_for_keys(
    ticker: str,
    session_keys: list[str],
    *,
    output_dir: Path | str | None = None,
) -> dict[str, Any]:
    sessions: list[tuple[str, Path]] = []
    for key in session_keys:
        found = resolve_session(ticker, key, output_dir)
        if found is None:
            raise FileNotFoundError(f"Session not found: {ticker} {key}")
        sessions.append((key, found))
    return headline_for_sessions(ticker, sessions)

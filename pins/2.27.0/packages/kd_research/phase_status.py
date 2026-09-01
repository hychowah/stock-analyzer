"""Default session phase_status skeleton (resume map).

Pure helpers — no I/O except optional write. Used by scaffold_session and tests.
Design: harness/design_phase_status_and_exemplars.md
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# phase_id -> agent_ids (design §A.9). Order is the resume walk order.
PHASE_AGENTS: list[tuple[str, list[str]]] = [
    ("orch", ["orchestrator"]),
    ("0", ["phase0_swarm"]),
    ("1_parallel", ["2a", "2b", "2c"]),
    ("1b", ["2d"]),
    ("1c", ["2e"]),
    ("1d", ["1d_rev", "1d_ind", "1d_ol", "1d_merge"]),
    ("2_parallel", ["4", "5", "12"]),
    ("2_5", ["phase25_swarm"]),
    ("3", ["6"]),
    ("4_parallel", ["7", "8", "11"]),
    ("5", ["13"]),
    ("done", []),
]

PHASE_IDS: list[str] = [pid for pid, _ in PHASE_AGENTS]
SCHEMA_VERSION = 2


def _agent_row(agent_id: str) -> dict[str, Any]:
    return {
        "agent_id": agent_id,
        "status": "pending",
        "artifacts": [],
        "handoff": None,
        "notes": "",
    }


def build_phase_status_skeleton(
    ticker: str,
    session_date: str,
    *,
    updated_at: str | None = None,
) -> dict[str, Any]:
    """Return a pre-filled phase_status dict: all phases/agents pending.

    Args:
        ticker: Session ticker (stored uppercase).
        session_date: YYYY-MM-DD folder date.
        updated_at: ISO-8601 UTC; default now (UTC, second resolution).
    """
    if updated_at is None:
        updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    phases: list[dict[str, Any]] = []
    for phase_id, agent_ids in PHASE_AGENTS:
        phases.append(
            {
                "phase_id": phase_id,
                "status": "pending",
                "started_at": None,
                "finished_at": None,
                "agents": [_agent_row(a) for a in agent_ids],
                "notes": "",
            }
        )

    return {
        "ticker": ticker.upper(),
        "session_date": session_date,
        "schema_version": SCHEMA_VERSION,
        "updated_at": updated_at,
        "current_phase": "orch",
        "resume_hint": (
            "New session: start at phase orch (sector_config + market_context); "
            "all agents pending."
        ),
        "phases": phases,
        "failures": [],
        "waivers": [],
    }


def write_phase_status_skeleton(
    session_root: Path,
    ticker: str,
    session_date: str,
    *,
    updated_at: str | None = None,
) -> Path:
    """Write registry/phase_status.json under session_root; return path."""
    data = build_phase_status_skeleton(ticker, session_date, updated_at=updated_at)
    path = Path(session_root) / "registry" / "phase_status.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path

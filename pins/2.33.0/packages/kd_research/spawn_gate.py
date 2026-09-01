"""Specialist subagent spawn discipline (harness >= 2.20.0).

The orchestrator lead must launch specialists via spawn_subagent. If launch
fails, the session is abandoned — the lead must not write specialist artifacts
inline. Machine gates require an on-disk spawn ledger; they cannot prove the
Task API was called, but they fail-close when the ledger is missing or the
session was abandoned.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from packages.kd_research.annuals import load_run_manifest_version, parse_semver
from packages.kd_research.phase_graph import (
    home_phase_for_subagent,
    normalize_subagent_id,
    subagent_allowed_in_phase,
    subagent_status_map,
)
from packages.kd_research.phase_status import PHASE_AGENTS

SPAWN_SINCE = (2, 20, 0)
SPAWNS_REL = "registry/spawns.json"
ABANDON_REL = "registry/abandon.json"

INLINE_EXECUTION = frozenset(
    {
        "inline",
        "orchestrator_inline",
        "self",
        "lead_inline",
    }
)

# Designed specialists (not the orchestrator row). phase complete requires these.
PHASE_REQUIRED_SPAWNS: dict[str, tuple[str, ...]] = {
    "0": ("phase0_swarm",),
    "1_parallel": ("2a", "2b", "2c"),
    "1b": ("2d",),
    "1c": ("2e",),
    "1d": ("1d_rev", "1d_ind", "1d_ol", "1d_merge"),
    "2_parallel": ("4", "5", "12"),
    "2_5": ("phase25_swarm",),
    "3": ("6",),
    "4_parallel": ("7", "8", "11"),
    "5": ("13",),
}

# If any of these paths exist, that specialist did (or claimed) work.
SPECIALIST_ARTIFACTS: dict[str, tuple[str, ...]] = {
    "phase0_swarm": ("registry/background.json", "registry/raw/phase0_*.json"),
    "2a": ("data/sp_financials.csv",),
    "2b": ("registry/sec_filings.json",),
    "2c": ("registry/news_sentiment.json",),
    "2d": ("registry/latest_quarter.json",),
    "2e": ("registry/filing_deep_dive.json",),
    "1d_rev": ("registry/raw/oppath_rev.json",),
    "1d_ind": ("registry/raw/oppath_ind.json",),
    "1d_ol": ("registry/raw/oppath_ol.json",),
    "1d_merge": ("registry/operating_path_brief.json",),
    "4": ("registry/technical.json",),
    "5": ("data/valuation_model.json",),
    "12": ("registry/tsr_validation.json",),
    "phase25_swarm": ("registry/risk_bridge.json", "registry/raw/stress_*.json"),
    "6": ("charts/*.png",),
    "7": ("reports/01_*_fundamental.md",),
    "8": ("reports/02_*_technical.md",),
    "11": ("reports/00_*_README.md",),
    "13": ("registry/audit.json",),
}

YEAR_DIVE_RE = re.compile(r"fdd_year_(?:FY)?((?:19|20)\d{2})", re.IGNORECASE)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def session_enforces_spawn(session: Path) -> bool:
    """True on harness >= 2.20.0, or when a spawn/abandon file already exists."""
    if (session / SPAWNS_REL).is_file() or (session / ABANDON_REL).is_file():
        return True
    parsed = parse_semver(load_run_manifest_version(session))
    if parsed is None:
        return False
    return parsed >= SPAWN_SINCE


def session_is_abandoned(session: Path) -> bool:
    data, err = _load_json(session / ABANDON_REL)
    if err or not isinstance(data, dict):
        return False
    return data.get("abandoned") is True


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.is_file():
        return None, "missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)
    if not isinstance(data, dict):
        return None, "not an object"
    return data, None


def load_spawns(session: Path) -> tuple[list[dict[str, Any]], str | None]:
    data, err = _load_json(session / SPAWNS_REL)
    if err == "missing":
        return [], None
    if err:
        return [], err
    assert data is not None
    rows = data.get("spawns")
    if not isinstance(rows, list):
        return [], "spawns must be an array"
    out: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            out.append(row)
    return out, None


def _artifact_exists(session: Path, rel: str) -> bool:
    if "*" in rel:
        return bool(list(session.glob(rel)))
    return (session / rel).is_file()


def specialist_has_artifacts(session: Path, subagent_id: str) -> bool:
    rels = SPECIALIST_ARTIFACTS.get(subagent_id)
    if not rels:
        return False
    return any(_artifact_exists(session, rel) for rel in rels)


def spawn_covers(spawn_id: str, required_id: str) -> bool:
    """Whether a recorded spawn satisfies a required specialist id."""
    sid = normalize_subagent_id(spawn_id)
    req = normalize_subagent_id(required_id)
    if sid == req:
        return True
    if req == "phase0_swarm" and (sid == "phase0_swarm" or sid.startswith("phase0")):
        return True
    if req == "phase25_swarm" and (
        sid == "phase25_swarm" or "phase25" in sid or sid.startswith("stress")
    ):
        return True
    return False


def _valid_returned_row(row: dict[str, Any], required_id: str) -> bool:
    """Returned spawn that was launched first, on the specialist's home phase."""
    if str(row.get("status") or "") != "returned":
        return False
    if not str(row.get("launched_at") or "").strip():
        return False
    sid = str(row.get("subagent_id") or "")
    if not sid or not spawn_covers(sid, required_id):
        return False
    home = home_phase_for_subagent(required_id)
    pid = str(row.get("phase_id") or "")
    if home and pid and pid != home:
        return False
    return True


def returned_spawn_ids(spawns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [s for s in spawns if str(s.get("status") or "") == "returned"]


def has_returned_spawn(spawns: list[dict[str, Any]], required_id: str) -> bool:
    return any(_valid_returned_row(row, required_id) for row in spawns)


def has_failed_spawn(spawns: list[dict[str, Any]], required_id: str) -> bool:
    for row in spawns:
        if str(row.get("status") or "") != "failed":
            continue
        sid = str(row.get("subagent_id") or "")
        if sid and spawn_covers(sid, required_id):
            return True
    return False


def year_reader_ids_from_disk(session: Path) -> list[tuple[str, str]]:
    """(canonical_id, filename) for each year-dive file."""
    raw = session / "registry" / "raw"
    if not raw.is_dir():
        return []
    out: list[tuple[str, str]] = []
    for path in sorted(raw.glob("fdd_year_*.json")):
        m = YEAR_DIVE_RE.search(path.name)
        if not m:
            continue
        out.append((f"2e_fy{m.group(1)}", path.name))
    return out


def swarm_raw_ids_from_disk(session: Path, pattern: str) -> list[str]:
    """File stems under registry/raw matching pattern (phase0_*.json, stress_*.json)."""
    raw = session / "registry" / "raw"
    if not raw.is_dir():
        return []
    return [p.stem for p in sorted(raw.glob(pattern))]


def _agent_skipped(status_map: dict[str, tuple[str, str]], subagent_id: str) -> bool:
    row = status_map.get(subagent_id)
    if not row:
        return False
    return row[1] in {"skipped"}


def _agent_complete(status_map: dict[str, tuple[str, str]], subagent_id: str) -> bool:
    row = status_map.get(subagent_id)
    if not row:
        return False
    return row[1] == "complete"


def _inline_execution_rows(session: Path) -> list[tuple[str, str, str]]:
    """FAIL if a specialist confesses inline / lead execution."""
    ps_path = session / "registry" / "phase_status.json"
    data, err = _load_json(ps_path)
    if err or not isinstance(data, dict):
        return []
    out: list[tuple[str, str, str]] = []
    for ph in data.get("phases") or []:
        if not isinstance(ph, dict):
            continue
        for ag in ph.get("agents") or []:
            if not isinstance(ag, dict):
                continue
            aid = str(ag.get("agent_id") or "")
            if not aid or aid == "orchestrator":
                continue
            exe = str(ag.get("execution") or "").strip().lower()
            if exe in INLINE_EXECUTION:
                out.append(
                    (
                        "FAIL",
                        f"spawn.inline:{aid}",
                        f"specialist {aid} execution={exe} — inline specialist work is forbidden; "
                        "abandon rather than writing artifacts as the lead",
                    )
                )
            elif exe == "orchestrator_lead":
                out.append(
                    (
                        "FAIL",
                        f"spawn.retag:{aid}",
                        f"specialist {aid} execution=orchestrator_lead — keep execution=subagent; "
                        "5b/merge/classification belong on the orch row, not a retagged specialist",
                    )
                )
    return out


def check_abandon(session: Path) -> list[tuple[str, str, str]]:
    """Abandon file is terminal: do not continue or finalize."""
    path = session / ABANDON_REL
    if not path.is_file():
        return []
    data, err = _load_json(path)
    if err:
        return [("FAIL", "spawn.abandon", f"{ABANDON_REL} unreadable: {err}")]
    assert data is not None
    if data.get("abandoned") is not True:
        return [
            (
                "FAIL",
                "spawn.abandon",
                f"{ABANDON_REL} present but abandoned!=true",
            )
        ]
    reason = data.get("reason") or "unspecified"
    phase = data.get("phase_id") or "?"
    sub = data.get("subagent_id") or "?"
    return [
        (
            "FAIL",
            "spawn.abandoned",
            f"session abandoned ({reason}) phase={phase} subagent={sub} — "
            "do not continue the phase graph; do not write specialist work as the lead; "
            "scaffold a new session_key if the user still wants the ticker researched",
        )
    ]


def check_spawn_discipline(
    session: Path,
    *,
    phase_id: str | None = None,
    mode: str | None = None,
) -> list[tuple[str, str, str]]:
    """Require returned spawn ledger rows for specialist work.

    ``mode=complete`` for a phase requires every designed specialist of that
    phase (unless skipped). Otherwise require a spawn when artifacts exist or
    the agent row is complete.
    """
    out: list[tuple[str, str, str]] = []
    if not session_enforces_spawn(session):
        out.append(
            (
                "SKIPPED",
                "spawn",
                "legacy/slim (no spawns.json; harness_version < 2.20.0)",
            )
        )
        return out

    abandon_rows = check_abandon(session)
    if abandon_rows:
        return abandon_rows

    spawns, err = load_spawns(session)
    if err:
        out.append(("FAIL", SPAWNS_REL, err))
        return out

    status_map: dict[str, tuple[str, str]] = {}
    ps_path = session / "registry" / "phase_status.json"
    if ps_path.is_file():
        data, ps_err = _load_json(ps_path)
        if not ps_err and isinstance(data, dict):
            status_map = subagent_status_map(data)

    out.extend(_inline_execution_rows(session))

    required: list[str] = []
    seen: set[str] = set()

    def _add(sid: str) -> None:
        if sid and sid not in seen:
            required.append(sid)
            seen.add(sid)

    if mode == "complete" and phase_id:
        for sid in PHASE_REQUIRED_SPAWNS.get(phase_id, ()):
            _add(sid)
        if phase_id == "1c":
            for cid, _name in year_reader_ids_from_disk(session):
                _add(cid)
        if phase_id == "0":
            for stem in swarm_raw_ids_from_disk(session, "phase0_*.json"):
                _add(stem)
        if phase_id == "2_5":
            for stem in swarm_raw_ids_from_disk(session, "stress_*.json"):
                _add(stem)
    else:
        for sid, _rels in SPECIALIST_ARTIFACTS.items():
            if _agent_skipped(status_map, sid):
                continue
            if specialist_has_artifacts(session, sid) or _agent_complete(status_map, sid):
                _add(sid)
        for cid, _name in year_reader_ids_from_disk(session):
            _add(cid)
        for stem in swarm_raw_ids_from_disk(session, "phase0_*.json"):
            _add(stem)
        for stem in swarm_raw_ids_from_disk(session, "stress_*.json"):
            _add(stem)

    if not required:
        out.append(("PASS", "spawn.idle", "no specialist artifacts or complete rows yet"))
        return out

    if not spawns:
        out.append(
            (
                "FAIL",
                SPAWNS_REL,
                "missing — record spawn_subagent via record_spawn.py before specialist work; "
                "if spawn fails, abandon the session (do not do the work as the lead)",
            )
        )
        return out

    for sid in required:
        if _agent_skipped(status_map, sid):
            out.append(("PASS", f"spawn.skipped:{sid}", "agent skipped"))
            continue
        if has_returned_spawn(spawns, sid):
            out.append(("PASS", f"spawn.returned:{sid}", "spawn ledger has returned"))
            continue
        if has_failed_spawn(spawns, sid):
            out.append(
                (
                    "FAIL",
                    f"spawn.failed:{sid}",
                    f"spawn failed for {sid} — abandon; do not write this specialist's artifacts as the lead",
                )
            )
            continue
        launched = any(
            spawn_covers(str(row.get("subagent_id") or ""), sid)
            and str(row.get("status") or "") == "launched"
            for row in spawns
        )
        if launched:
            out.append(
                (
                    "FAIL",
                    f"spawn.unreturned:{sid}",
                    f"{sid} spawn launched but not returned — wait for the subagent or abandon; "
                    "do not finish the work inline",
                )
            )
            continue
        out.append(
            (
                "FAIL",
                f"spawn.missing:{sid}",
                f"specialist {sid} has artifacts or is complete without a returned spawn_subagent "
                "record — inline specialist work is forbidden; abandon rather than continuing",
            )
        )
    return out


def _session_meta(session: Path) -> tuple[str, str]:
    man, _err = _load_json(session / "meta" / "run_manifest.json")
    ticker = ""
    date = ""
    if isinstance(man, dict):
        ticker = str(man.get("ticker") or "")
        date = str(man.get("session_date") or "")
    if not ticker:
        ticker = session.parent.name
    if not date:
        date = session.name.split("__", 1)[0]
    return ticker.upper(), date


def record_spawn_event(
    session: Path,
    *,
    subagent_id: str,
    phase_id: str,
    event: str,
    subagent_type: str | None = None,
    fail_reason: str | None = None,
    tool: str = "spawn_subagent",
) -> dict[str, Any]:
    """Append/update registry/spawns.json. ``event`` is launch|return|fail."""
    event = event.strip().lower()
    if event not in {"launch", "return", "fail"}:
        raise ValueError(f"event must be launch|return|fail, got {event!r}")
    sid = normalize_subagent_id(subagent_id)
    ok, detail = subagent_allowed_in_phase(sid, phase_id)
    if not ok:
        raise ValueError(detail)
    ticker, session_date = _session_meta(session)
    path = session / SPAWNS_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    data, err = _load_json(path)
    if err and err != "missing":
        raise ValueError(f"cannot read {SPAWNS_REL}: {err}")
    if not isinstance(data, dict):
        data = {
            "schema_version": 1,
            "ticker": ticker,
            "session_date": session_date,
            "spawns": [],
        }
    rows = data.get("spawns")
    if not isinstance(rows, list):
        rows = []
        data["spawns"] = rows
    now = _utc_now()
    data["ticker"] = ticker
    data["session_date"] = session_date
    data["updated_at"] = now

    def _match(row: object) -> bool:
        if not isinstance(row, dict):
            return False
        return normalize_subagent_id(str(row.get("subagent_id") or "")) == sid and str(
            row.get("phase_id") or ""
        ) == phase_id

    existing = next((r for r in reversed(rows) if _match(r)), None)
    if event == "return" and (
        existing is None or str(existing.get("status") or "") not in {"launched", "returned"}
    ):
        raise ValueError(
            f"return for {sid} requires a prior launch on phase {phase_id} "
            "(do not backfill a returned row after inline work)"
        )
    if event == "launch" or existing is None:
        row: dict[str, Any] = {
            "subagent_id": sid,
            "phase_id": phase_id,
            "tool": tool,
            "subagent_type": subagent_type,
            "status": "launched" if event == "launch" else ("failed" if event == "fail" else "returned"),
            "launched_at": now,
            "returned_at": now if event == "return" else None,
            "fail_reason": fail_reason if event == "fail" else None,
        }
        if event == "fail":
            row["status"] = "failed"
        rows.append(row)
        existing = row
    else:
        if event == "return":
            existing["status"] = "returned"
            existing["returned_at"] = now
        elif event == "fail":
            existing["status"] = "failed"
            existing["fail_reason"] = fail_reason
            existing["returned_at"] = now
        if subagent_type:
            existing["subagent_type"] = subagent_type
        existing["tool"] = tool
        row = existing

    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if event == "fail":
        write_abandon(
            session,
            reason="spawn_failed",
            phase_id=phase_id,
            subagent_id=sid,
            detail=fail_reason or "spawn_subagent failed or unavailable",
        )
    return row


def write_abandon(
    session: Path,
    *,
    reason: str,
    phase_id: str | None = None,
    subagent_id: str | None = None,
    detail: str | None = None,
) -> dict[str, Any]:
    """Write registry/abandon.json and mark phase_status failed when present."""
    ticker, session_date = _session_meta(session)
    now = _utc_now()
    payload = {
        "schema_version": 1,
        "abandoned": True,
        "ticker": ticker,
        "session_date": session_date,
        "reason": reason,
        "phase_id": phase_id,
        "subagent_id": subagent_id,
        "detail": detail or reason,
        "at": now,
    }
    path = session / ABANDON_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    _mark_phase_status_failed(
        session,
        phase_id=phase_id,
        subagent_id=subagent_id,
        error=detail or reason,
        at=now,
    )
    return payload


def _mark_phase_status_failed(
    session: Path,
    *,
    phase_id: str | None,
    subagent_id: str | None,
    error: str,
    at: str,
) -> None:
    path = session / "registry" / "phase_status.json"
    data, err = _load_json(path)
    if err or not isinstance(data, dict):
        return
    if phase_id:
        data["current_phase"] = phase_id
        for ph in data.get("phases") or []:
            if not isinstance(ph, dict):
                continue
            if ph.get("phase_id") != phase_id:
                continue
            ph["status"] = "failed"
            ph["finished_at"] = at
            sid = normalize_subagent_id(subagent_id) if subagent_id else ""
            for ag in ph.get("agents") or []:
                if not isinstance(ag, dict):
                    continue
                aid = str(ag.get("agent_id") or "")
                if not sid or aid == sid or spawn_covers(aid, sid):
                    if sid and (aid == sid or spawn_covers(aid, sid)):
                        ag["status"] = "failed"
                        ag["execution"] = "spawn_failed"
                        ag["notes"] = error
                    elif not sid and aid != "orchestrator":
                        ag["status"] = "failed"
    data["resume_hint"] = (
        "ABANDONED: specialist spawn failed. Do not continue. "
        "Do not write specialist artifacts as the lead. Scaffold a new session_key if needed."
    )
    data["updated_at"] = at
    failures = data.get("failures")
    if not isinstance(failures, list):
        failures = []
        data["failures"] = failures
    failures.append(
        {
            "phase_id": phase_id or data.get("current_phase") or "orch",
            "agent_id": subagent_id,
            "at": at,
            "error": error[:500],
            "fallback": "abandon",
        }
    )
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


# Designed spawn ids must stay a subset of PHASE_AGENTS specialists.
_DESIGNED = {sid for _pid, aids in PHASE_AGENTS for sid in aids if sid != "orchestrator"}
assert set().union(*PHASE_REQUIRED_SPAWNS.values()) <= _DESIGNED

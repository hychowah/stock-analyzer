"""Phase graph: ordered phases, allowed **subagents**, entry prerequisites.

Terminology (avoid LLM confusion):
- **Orchestrator** = main lead agent (may act in any phase; updates phase_status).
- **Subagent** = specialist worker (2a, 5, 13, phase0_swarm, …) that belongs to
  exactly one phase on the graph. On-disk ``phase_status.agents[].agent_id`` is
  the subagent id for specialists (schema field name kept for compatibility).

Enforces harness HARNESS_MAP / phase_status design mechanically:
- Enter a phase only when all prior phases are complete|skipped.
- Spawn only subagents that belong to that phase (orchestrator always allowed).
- Intra-phase parallel subagents (e.g. 2a∥2b∥2c) are unordered within the phase.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from scripts.kd_research.phase_status import PHASE_AGENTS, PHASE_IDS

# Strict walk order (must match phase_status skeleton / schema enum).
PHASE_ORDER: list[str] = list(PHASE_IDS)

# phase_id -> subagent ids allowed to produce that phase's primary work
PHASE_TO_SUBAGENTS: dict[str, list[str]] = {pid: list(aids) for pid, aids in PHASE_AGENTS}

# subagent_id -> home phase_id (specialists only; orchestrator is multi-phase)
SUBAGENT_TO_PHASE: dict[str, str] = {}
for _pid, _aids in PHASE_AGENTS:
    for _a in _aids:
        if _a != "orchestrator":
            SUBAGENT_TO_PHASE[_a] = _pid

# Back-compat aliases for older call sites
PHASE_TO_AGENTS = PHASE_TO_SUBAGENTS
AGENT_TO_PHASE = SUBAGENT_TO_PHASE

# Statuses that satisfy "prior phase done enough to start the next"
PRIOR_OK_STATUSES = frozenset({"complete", "skipped"})
# Statuses that block entry to later phases
PRIOR_BLOCKING_STATUSES = frozenset({"pending", "in_progress", "failed", "blocked"})

ORCHESTRATOR_ALIASES = frozenset(
    {
        "orchestrator",
        "main",
        "orch",
        "lead",
    }
)

# Dynamic 1c year-readers (not in PHASE_AGENTS; one per annual on disk).
YEAR_READER_RE = re.compile(
    r"^(?:2e[_-]?fy|fdd_year[_-]?fy?|year_reader[_-]?fy?|year[_-]?)(\d{4})$",
    re.IGNORECASE,
)
PHASE0_ROUND_RE = re.compile(r"^phase0[_-]?(?:r|round)[_-]?(\d+)$", re.IGNORECASE)


def load_phase_status(session: Path) -> tuple[dict[str, Any] | None, str | None]:
    path = session / "registry" / "phase_status.json"
    if not path.is_file():
        return None, "missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return None, f"unparseable: {e}"
    if not isinstance(data, dict):
        return None, "not an object"
    return data, None


def phase_status_map(data: dict[str, Any]) -> dict[str, str]:
    """phase_id -> status string."""
    out: dict[str, str] = {}
    phases = data.get("phases")
    if not isinstance(phases, list):
        return out
    for ph in phases:
        if not isinstance(ph, dict):
            continue
        pid = ph.get("phase_id")
        st = ph.get("status")
        if isinstance(pid, str) and isinstance(st, str):
            out[pid] = st
    return out


def subagent_status_map(data: dict[str, Any]) -> dict[str, tuple[str, str]]:
    """subagent_id -> (phase_id, status). Reads phase_status.agents[].agent_id."""
    out: dict[str, tuple[str, str]] = {}
    phases = data.get("phases")
    if not isinstance(phases, list):
        return out
    for ph in phases:
        if not isinstance(ph, dict):
            continue
        pid = ph.get("phase_id")
        if not isinstance(pid, str):
            continue
        agents = ph.get("agents")
        if not isinstance(agents, list):
            continue
        for ag in agents:
            if not isinstance(ag, dict):
                continue
            # schema field is agent_id; value is subagent id for specialists
            aid = ag.get("agent_id")
            st = ag.get("status")
            if isinstance(aid, str) and isinstance(st, str):
                out[aid] = (pid, st)
    return out


# back-compat
agent_status_map = subagent_status_map


def normalize_subagent_id(subagent_id: str) -> str:
    """Map common labels (valuation, Agent 5) to phase_status subagent ids."""
    raw = subagent_id.strip()
    a = raw.lower().replace("subagent_", "").replace("subagent", "")
    a = a.replace("agent_", "").replace("agent", "").strip()
    aliases = {
        "5": "5",
        "valuation": "5",
        "4": "4",
        "technical": "4",
        "2a": "2a",
        "2b": "2b",
        "2c": "2c",
        "2d": "2d",
        "2e": "2e",
        "6": "6",
        "charts": "6",
        "7": "7",
        "8": "8",
        "11": "11",
        "12": "12",
        "tsr": "12",
        "13": "13",
        "audit": "13",
        "phase0": "phase0_swarm",
        "phase0_swarm": "phase0_swarm",
        "phase25": "phase25_swarm",
        "phase25_swarm": "phase25_swarm",
        "stress": "phase25_swarm",
        "1d_rev": "1d_rev",
        "revenue_growth": "1d_rev",
        "1d_ind": "1d_ind",
        "industry_trend": "1d_ind",
        "1d_ol": "1d_ol",
        "operating_leverage": "1d_ol",
        "1d_merge": "1d_merge",
        "oppath": "1d_merge",
        "operating_path": "1d_merge",
    }
    compact = raw.replace(" ", "").replace("-", "_")
    ym = YEAR_READER_RE.match(compact)
    if ym:
        return f"2e_fy{ym.group(1)}"
    pr = PHASE0_ROUND_RE.match(compact)
    if pr:
        return f"phase0_r{pr.group(1)}"
    if raw in SUBAGENT_TO_PHASE:
        return raw
    if raw.lower() in ORCHESTRATOR_ALIASES:
        return "orchestrator"
    key = raw.lower()
    if key in aliases:
        return aliases[key]
    if a in aliases:
        return aliases[a]
    return raw


# back-compat
normalize_agent_id = normalize_subagent_id


def home_phase_for_subagent(subagent_id: str) -> str | None:
    """Graph home phase for a specialist (None = orchestrator / unknown)."""
    sid = normalize_subagent_id(subagent_id)
    if sid == "orchestrator" or sid in ORCHESTRATOR_ALIASES:
        return None
    if sid.startswith("2e_fy"):
        return "1c"
    if sid.startswith("phase0"):
        return "0"
    if sid.startswith("phase25") or sid.startswith("stress"):
        return "2_5"
    return SUBAGENT_TO_PHASE.get(sid)


def subagent_allowed_in_phase(subagent_id: str, phase_id: str) -> tuple[bool, str]:
    """Whether this subagent may be spawned while working phase_id."""
    sid = normalize_subagent_id(subagent_id)
    if sid == "orchestrator" or sid in ORCHESTRATOR_ALIASES:
        return True, "orchestrator (lead) may act in any phase — not a phase subagent"
    if phase_id not in PHASE_TO_SUBAGENTS:
        return False, f"unknown phase_id={phase_id!r}"
    allowed = PHASE_TO_SUBAGENTS[phase_id]
    if sid in allowed:
        return True, f"subagent {sid} belongs to phase {phase_id}"
    home = home_phase_for_subagent(sid)
    if home == phase_id:
        return True, f"subagent {sid} belongs to phase {phase_id}"
    if home:
        return False, f"subagent {sid} belongs to phase {home}, not {phase_id}"
    return False, f"unknown subagent_id={subagent_id!r} (not on phase graph)"


# back-compat
agent_allowed_in_phase = subagent_allowed_in_phase


def designed_phase_ids(session: Path | None = None) -> list[str]:
    """Phase ids that this session must cover. Legacy omits 1d."""
    from scripts.kd_research.operating_path import designed_phase_ids as _designed

    return _designed(session)


def prerequisites_for(phase_id: str, session: Path | None = None) -> list[str]:
    """Phases that must be complete|skipped before entering phase_id."""
    order = designed_phase_ids(session)
    if phase_id not in order:
        if phase_id == "1d":
            return [p for p in PHASE_ORDER if p != "1d" and PHASE_ORDER.index(p) < PHASE_ORDER.index("1d")]
        return []
    idx = order.index(phase_id)
    return order[:idx]


def check_phase_graph_entry(
    session: Path,
    phase_id: str,
    *,
    subagent_id: str | None = None,
    agent_id: str | None = None,  # deprecated alias for subagent_id
) -> list[tuple[str, str, str]]:
    """Mechanical gates before starting work on phase_id (and optional subagent)."""
    results: list[tuple[str, str, str]] = []
    sid = subagent_id if subagent_id is not None else agent_id

    if phase_id not in PHASE_ORDER:
        results.append(("FAIL", "phase_graph.phase_id", f"unknown phase_id={phase_id!r}"))
        return results

    results.append(("PASS", "phase_graph.phase_id", phase_id))

    if sid:
        ok, detail = subagent_allowed_in_phase(sid, phase_id)
        results.append(
            ("PASS" if ok else "FAIL", "phase_graph.subagent_phase", detail)
        )

    data, err = load_phase_status(session)
    if err == "missing":
        results.append(
            (
                "WARN",
                "phase_graph.phase_status",
                "registry/phase_status.json missing — file evidence gates only; "
                "new sessions must keep phase_status updated",
            )
        )
        return results
    if err:
        results.append(("FAIL", "phase_graph.phase_status", err))
        return results
    assert data is not None

    smap = phase_status_map(data)
    results.extend(check_phase_status_order_integrity(smap))

    for prior in prerequisites_for(phase_id, session):
        st = smap.get(prior)
        if st is None:
            results.append(
                (
                    "FAIL",
                    f"phase_graph.prereq.{prior}",
                    f"phase {prior!r} missing from phase_status — cannot enter {phase_id}",
                )
            )
        elif st in PRIOR_OK_STATUSES:
            results.append(("PASS", f"phase_graph.prereq.{prior}", f"status={st}"))
        elif st in PRIOR_BLOCKING_STATUSES:
            results.append(
                (
                    "FAIL",
                    f"phase_graph.prereq.{prior}",
                    f"status={st} — must be complete|skipped before entering {phase_id}",
                )
            )
        else:
            results.append(
                (
                    "FAIL",
                    f"phase_graph.prereq.{prior}",
                    f"unknown status={st!r}",
                )
            )

    current = data.get("current_phase")
    if isinstance(current, str) and current in PHASE_ORDER and phase_id in PHASE_ORDER:
        ci, pi = PHASE_ORDER.index(current), PHASE_ORDER.index(phase_id)
        if pi > ci + 1:
            results.append(
                (
                    "WARN",
                    "phase_graph.current_phase_lag",
                    f"phase_status.current_phase={current!r} but entering {phase_id!r} — "
                    "update current_phase as you advance",
                )
            )
        else:
            results.append(
                (
                    "PASS",
                    "phase_graph.current_phase",
                    f"current_phase={current} entering={phase_id}",
                )
            )

    return results


def check_phase_status_order_integrity(
    smap: dict[str, str],
) -> list[tuple[str, str, str]]:
    """FAIL if a later phase is complete while an earlier phase is not done."""
    results: list[tuple[str, str, str]] = []
    last_incomplete: str | None = None
    for pid in PHASE_ORDER:
        st = smap.get(pid)
        if st is None:
            continue
        if st == "complete" and last_incomplete is not None:
            li_idx = PHASE_ORDER.index(last_incomplete)
            pi = PHASE_ORDER.index(pid)
            if pi > li_idx and smap.get(last_incomplete) in ("pending", "failed", "blocked"):
                results.append(
                    (
                        "FAIL",
                        "phase_graph.order_integrity",
                        f"phase {pid} is complete but earlier {last_incomplete} is "
                        f"{smap.get(last_incomplete)} — advance in graph order only",
                    )
                )
                return results
        if st in ("pending", "failed", "blocked"):
            last_incomplete = pid
        elif st == "in_progress":
            last_incomplete = last_incomplete or pid
    if not results:
        results.append(
            ("PASS", "phase_graph.order_integrity", "no complete-after-pending inversion")
        )
    return results


def check_phase_status_graph(session: Path) -> list[tuple[str, str, str]]:
    """Session-level graph integrity for check_session."""
    data, err = load_phase_status(session)
    if err == "missing":
        return [
            (
                "SKIPPED",
                "phase_graph",
                "phase_status.json absent (legacy OK)",
            )
        ]
    if err:
        return [("FAIL", "phase_graph.phase_status", err)]
    assert data is not None
    smap = phase_status_map(data)
    results = check_phase_status_order_integrity(smap)

    designed = designed_phase_ids(session)
    missing = [p for p in designed if p not in smap]
    if missing:
        results.append(
            (
                "FAIL",
                "phase_graph.coverage",
                f"phase_status missing phase_ids: {missing}",
            )
        )
    else:
        results.append(
            ("PASS", "phase_graph.coverage", f"{len(designed)} phases present")
        )

    for sid, (pid, _st) in subagent_status_map(data).items():
        if sid == "orchestrator":
            continue
        home = home_phase_for_subagent(sid)
        if home and home != pid:
            results.append(
                (
                    "FAIL",
                    "phase_graph.subagent_home",
                    f"subagent {sid} listed under phase {pid} but graph home is {home}",
                )
            )
    if not any(r[1] == "phase_graph.subagent_home" and r[0] == "FAIL" for r in results):
        results.append(
            ("PASS", "phase_graph.subagent_home", "subagents under correct phases")
        )

    return results


def next_open_phase(session: Path) -> str | None:
    """First phase not complete|skipped, or None if all done."""
    data, err = load_phase_status(session)
    if err or not data:
        return "orch"
    smap = phase_status_map(data)
    for pid in PHASE_ORDER:
        st = smap.get(pid, "pending")
        if st not in PRIOR_OK_STATUSES:
            return pid
    return None

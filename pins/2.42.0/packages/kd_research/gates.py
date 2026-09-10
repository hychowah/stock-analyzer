"""Walk a PhaseNode and run the check catalog.

Investment purpose: block valuation/reports on incomplete evidence so later
phases do not invent decision-grade numbers. Shared by preflight_phase.py.

Domain checks are not defined here — they live in knowledge homes.
Path tables live on packages.kd_research.phase_graph.PhaseNode.
"""

from __future__ import annotations

from pathlib import Path

from packages.kd_research.check_core import check_path, check_reports, infer_ticker
from packages.kd_research.phase_graph import graph_for_session


def entry_checks(
    session: Path,
    phase_id: str,
    *,
    ticker: str | None = None,
    strict_optional: bool = False,
    subagent_id: str | None = None,
    agent_id: str | None = None,  # deprecated alias for subagent_id
) -> list[tuple[str, str, str]]:
    """Walk the node's paths, then run_catalog. Domain checks are not defined here."""
    nodes = graph_for_session(session)
    node = nodes.get(phase_id)
    if node is None:
        return [("FAIL", "phase_id", f"unknown phase_id={phase_id!r}")]

    results: list[tuple[str, str, str]] = []
    from packages.kd_research.spawn_gate import (
        check_abandon,
        check_spawn_discipline,
        session_enforces_spawn,
        session_is_abandoned,
    )

    results.extend(check_abandon(session))
    if session_is_abandoned(session):
        return results
    if session_enforces_spawn(session):
        results.extend(check_spawn_discipline(session))
    from packages.kd_research.phase_graph import check_phase_graph_entry

    results.extend(
        check_phase_graph_entry(
            session,
            phase_id,
            subagent_id=subagent_id if subagent_id is not None else agent_id,
        )
    )

    for rel in node.entry_required:
        if rel == "reports":
            t = ticker or infer_ticker(session)
            results.extend(check_reports(session, t))
            continue
        status, detail = check_path(session, rel)
        results.append((status, rel, detail))

    for rel in node.entry_optional:
        status, detail = check_path(session, rel)
        if status == "PASS":
            results.append(("PASS", f"optional:{rel}", detail))
        elif strict_optional:
            results.append(("FAIL", f"optional:{rel}", detail))
        else:
            results.append(("SKIPPED", f"optional:{rel}", f"{detail} (optional for legacy)"))

    from packages.kd_research.check_catalog import run_catalog

    results.extend(run_catalog(session, f"{phase_id}:entry"))
    return results


def complete_checks(session: Path, phase_id: str) -> list[tuple[str, str, str]]:
    """Walk the node's complete paths, then run_catalog."""
    from packages.kd_research.spawn_gate import (
        check_abandon,
        check_spawn_discipline,
        session_enforces_spawn,
        session_is_abandoned,
    )

    prefix: list[tuple[str, str, str]] = []
    prefix.extend(check_abandon(session))
    if session_is_abandoned(session):
        return prefix
    if session_enforces_spawn(session):
        prefix.extend(check_spawn_discipline(session, phase_id=phase_id, mode="complete"))

    nodes = graph_for_session(session)
    node = nodes.get(phase_id)
    complete_paths = node.complete_paths if node is not None else ()

    out: list[tuple[str, str, str]] = []
    for rel in complete_paths:
        status, detail = check_path(session, rel)
        out.append((status, rel, detail))

    from packages.kd_research.check_catalog import complete_when_ids, run_catalog

    extras = run_catalog(session, f"{phase_id}:complete")
    out.extend(extras)
    if not complete_paths and phase_id not in complete_when_ids():
        out.append(("SKIPPED", "complete_checks", f"no merge gate for phase {phase_id}"))
    return prefix + out

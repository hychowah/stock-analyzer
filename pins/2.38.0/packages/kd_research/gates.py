"""Phase evidence dispatcher: path tables + catalog extras.

Investment purpose: block valuation/reports on incomplete evidence so later
phases do not invent decision-grade numbers. Shared by preflight_phase.py.

Domain checks are not defined here — they live in knowledge homes and are
re-exported so existing tests keep importing from gates.

Phase IDs and entry path tables come from packages.kd_research.phase_graph.
"""

from __future__ import annotations

from pathlib import Path

from packages.kd_research.annuals import check_1c_year_dive_complete
from packages.kd_research.check_core import (  # re-export
    HOOK_REASON_MIN_LEN,
    HOOK_REQUIRED_KEYS,
    REPORT_MIN_BYTES,
    check_path,
    check_reports,
    infer_ticker,
    load_json,
    report_rows,
    validate_hooks_list,
)
from packages.kd_research.consumption import (
    check_filing_deep_dive_hooks,
    check_market_context_hooks_intensity,
)
from packages.kd_research.decision import (
    check_latest_quarter_risk_mapping,
    check_scenario_probability_keys,
    check_stress_coverage,
    extract_scenario_prob_mass,
)
from packages.kd_research.isolation import AGENT4_FORBIDDEN_TOKENS, check_agent4_isolation
from packages.kd_research.phase_graph import (  # re-export
    PHASE_COMPLETE_PATHS,
    PHASE_ENTRY_OPTIONAL,
    PHASE_ENTRY_REQUIRED,
)
from packages.kd_research.phase_status import (
    HANDOFF_SECTION_PATTERNS,
    PHASE_PRIMARY_ARTIFACTS,
    check_handoff_headers,
    check_phase0_coverage,
    check_phase_status_disk,
    primary_artifact_exists,
)
from packages.kd_research.provenance import check_llm_model_identity
from packages.kd_research.valuation_hygiene import (
    check_mos_units,
    check_valuation_decision_quality,
)

def entry_checks(
    session: Path,
    phase_id: str,
    *,
    ticker: str | None = None,
    strict_optional: bool = False,
    subagent_id: str | None = None,
    agent_id: str | None = None,  # deprecated alias for subagent_id
) -> list[tuple[str, str, str]]:
    """Return list of (status, check_id, detail) for entering phase_id."""
    if phase_id not in PHASE_ENTRY_REQUIRED and phase_id not in ("0",):
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

    required = PHASE_ENTRY_REQUIRED.get(phase_id, [])
    for rel in required:
        if rel == "reports":
            t = ticker or infer_ticker(session)
            results.extend(check_reports(session, t))
            continue
        status, detail = check_path(session, rel)
        results.append((status, rel, detail))

    for rel in PHASE_ENTRY_OPTIONAL.get(phase_id, []):
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
    """Checks before marking a phase complete (merge/coverage)."""
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

    out: list[tuple[str, str, str]] = []
    for rel in PHASE_COMPLETE_PATHS.get(phase_id, []):
        status, detail = check_path(session, rel)
        out.append((status, rel, detail))

    from packages.kd_research.check_catalog import complete_when_ids, run_catalog

    extras = run_catalog(session, f"{phase_id}:complete")
    out.extend(extras)
    if not PHASE_COMPLETE_PATHS.get(phase_id) and phase_id not in complete_when_ids():
        out.append(("SKIPPED", "complete_checks", f"no merge gate for phase {phase_id}"))
    return prefix + out


# Back-compat names for tests that imported the private helpers from gates.
_infer_ticker = infer_ticker
_report_rows = report_rows

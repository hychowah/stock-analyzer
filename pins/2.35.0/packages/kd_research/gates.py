"""Phase evidence dispatcher: path tables + catalog extras.

Investment purpose: block valuation/reports on incomplete evidence so later
phases do not invent decision-grade numbers. Shared by preflight_phase.py.

Domain checks are not defined here — they live in knowledge homes and are
re-exported so existing tests keep importing from gates.

Phase IDs align with harness/schemas/phase_status.schema.json and
harness/design_phase_status_and_exemplars.md §A.3.
"""

from __future__ import annotations

from pathlib import Path

from packages.kd_research.annuals import check_1c_year_dive_complete
from packages.kd_research.check_core import (  # re-export
    HOOK_REASON_MIN_LEN,
    HOOK_REQUIRED_KEYS,
    load_json,
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

# Files that must exist and (if .json) parse before entering a phase.
PHASE_ENTRY_REQUIRED: dict[str, list[str]] = {
    "orch": [],
    "0": [
        "registry/sector_config.json",
        "registry/market_context.json",
    ],
    "1_parallel": [
        "registry/sector_config.json",
    ],
    "1b": [
        "data/sp_financials.csv",
        "registry/sec_filings.json",
    ],
    "1c": [
        "registry/sec_filings.json",
    ],
    "1d": [
        "data/sp_financials.csv",
        "registry/latest_quarter.json",
        "registry/filing_deep_dive.json",
    ],
    "2_parallel": [
        "registry/sector_config.json",
        "registry/market_context.json",
        "data/sp_financials.csv",
        "registry/sec_filings.json",
        "registry/latest_quarter.json",
        "registry/filing_deep_dive.json",
    ],
    "2_5": [
        "data/valuation_model.json",
        "registry/latest_quarter.json",
        "registry/filing_deep_dive.json",
    ],
    "3": [
        "data/valuation_model.json",
    ],
    "4_parallel": [
        "data/valuation_model.json",
        "registry/risk_bridge.json",
        "registry/technical.json",
        "registry/tsr_validation.json",
    ],
    "5": [
        "reports",
    ],
    "done": [
        "registry/audit.json",
    ],
}

PHASE_ENTRY_OPTIONAL: dict[str, list[str]] = {
    "0": ["registry/research_brief.json"],
    "2_parallel": ["registry/research_brief.json", "registry/news_sentiment.json"],
    "2_5": ["registry/background.json"],
    "4_parallel": ["registry/filing_deep_dive.json", "registry/market_context.json"],
}

PHASE_COMPLETE_PATHS: dict[str, list[str]] = {
    "1_parallel": [
        "data/sp_financials.csv",
        "registry/sec_filings.json",
        "registry/news_sentiment.json",
    ],
    "2_parallel": [
        "registry/technical.json",
        "data/valuation_model.json",
        "registry/tsr_validation.json",
    ],
}

REPORT_MIN_BYTES = 2 * 1024


def check_path(session: Path, rel: str) -> tuple[str, str]:
    """Return (status, detail) with status PASS|FAIL for a relative path."""
    if "*" in rel:
        matches = list(session.glob(rel))
        if not matches:
            return "FAIL", f"no files match {rel}"
        return "PASS", f"{len(matches)} file(s) match {rel}"

    p = session / rel
    if rel == "reports":
        return "FAIL", "use check_reports()"

    if not p.exists():
        return "FAIL", "missing"

    if p.suffix == ".json":
        _, err = load_json(p)
        if err:
            return "FAIL", err
        return "PASS", "exists+parse"

    if p.is_file() and p.stat().st_size == 0:
        return "FAIL", "empty file"
    return "PASS", "exists"


def _report_rows(session: Path, ticker: str, *, exact: bool) -> list[tuple[str, str, str]]:
    """Three report files. exact=True uses exists:/size: ids; False uses report: + glob."""
    out: list[tuple[str, str, str]] = []
    t = ticker.upper()
    templates = (
        "reports/00_{t}_README.md",
        "reports/01_{t}_fundamental.md",
        "reports/02_{t}_technical.md",
    )
    for tmpl in templates:
        rel = tmpl.format(t=t)
        p = session / rel
        if exact:
            if not p.exists():
                out.append(("FAIL", f"exists: {rel}", "file missing"))
            elif p.stat().st_size < REPORT_MIN_BYTES:
                out.append(
                    ("FAIL", f"size: {rel}", f"{p.stat().st_size} bytes < {REPORT_MIN_BYTES} (stub?)")
                )
            else:
                out.append(("PASS", f"exists+size: {rel}", f"{p.stat().st_size} bytes"))
            continue
        glob_rel = (
            "reports/00_*_README.md"
            if rel.startswith("reports/00_")
            else "reports/01_*_fundamental.md"
            if rel.startswith("reports/01_")
            else "reports/02_*_technical.md"
        )
        if not p.exists():
            matches = list((session / "reports").glob(Path(glob_rel).name)) if (session / "reports").is_dir() else []
            if not matches:
                out.append(("FAIL", f"report:{rel}", "missing"))
                continue
            p = max(matches, key=lambda x: x.stat().st_size)
        if p.stat().st_size < REPORT_MIN_BYTES:
            out.append(("FAIL", f"report:{p.name}", f"{p.stat().st_size} bytes < {REPORT_MIN_BYTES}"))
        else:
            out.append(("PASS", f"report:{p.name}", f"{p.stat().st_size} bytes"))
    return out


def check_reports(session: Path, ticker: str) -> list[tuple[str, str, str]]:
    """List of (status, check_id, detail) for the three reports (glob fallback)."""
    return _report_rows(session, ticker, exact=False)


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
    results.extend(check_llm_model_identity(session, strict=True))
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
            t = ticker or _infer_ticker(session)
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


def _infer_ticker(session: Path) -> str:
    parts = session.resolve().parts
    if len(parts) >= 2:
        return parts[-2]
    return "TICKER"

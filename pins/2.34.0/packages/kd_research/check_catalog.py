"""When a preflight/merge machine check runs.

Not the archive-index linter planned as scripts/check_catalog.py (B7 in
harness/plan_research_archive_layout.md). That script does not exist yet.

Path tables in gates.py say which files a phase needs. This module says which
domain checks run at which when-tag for entry_checks / complete_checks.
scripts/check_session.py --full is still an explicit step list in that CLI;
it does not call run_catalog.

Adding a preflight gate: write check_foo in its knowledge home, add one
CheckRow. entry_checks / complete_checks do not grow an if-ladder.

PATH_EXTRAS.since is for workflow_spec display. Domain functions still
SKIPPED on legacy — the catalog does not pre-filter by version.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from packages.kd_research.library import BIND_REL, LIBRARY_SINCE
from packages.kd_research.operating_path import BRIEF_REL, OPPATH_SINCE
from packages.kd_research.street_bind import STREET_REL, STREET_SINCE

CheckFn = Callable[[Path], Sequence[tuple[str, str, str]]]

# session_core / session_full: owned by scripts/check_session.py (CLI + schema).
# Phase tags: "{phase_id}:entry" | "{phase_id}:complete".
WHEN_SESSION_CORE = "session_core"
WHEN_SESSION_FULL = "session_full"


@dataclass(frozen=True)
class CheckRow:
    id: str
    when: frozenset[str]
    run: CheckFn
    since: tuple[int, int, int] | None = None


@dataclass(frozen=True)
class PathExtra:
    phase: str
    rel: str
    required: bool
    since: tuple[int, int, int]


PATH_EXTRAS: tuple[PathExtra, ...] = (
    PathExtra("1_parallel", BIND_REL, True, LIBRARY_SINCE),
    PathExtra("2_parallel", BRIEF_REL, True, OPPATH_SINCE),
    PathExtra("2_parallel", STREET_REL, False, STREET_SINCE),
)


def _library_entry(session: Path) -> list[tuple[str, str, str]]:
    from packages.kd_research.library import check_library_gates, session_enforces_library

    if not session_enforces_library(session):
        return []
    return check_library_gates(session, phase="1_parallel_entry")


def _library_complete(session: Path) -> list[tuple[str, str, str]]:
    from packages.kd_research.library import check_library_gates

    return check_library_gates(session, phase="1_parallel_complete")


def _oppath_brief_and_hooks(session: Path) -> list[tuple[str, str, str]]:
    from packages.kd_research.gates import check_path
    from packages.kd_research.operating_path import (
        BRIEF_REL as brief_rel,
        check_operating_path_hooks,
        session_enforces_1d,
    )

    out: list[tuple[str, str, str]] = []
    vm = session / "data" / "valuation_model.json"
    if session_enforces_1d(session):
        status, detail = check_path(session, brief_rel)
        out.append((status, brief_rel, detail))
        if vm.is_file():
            out.extend(check_operating_path_hooks(session))
    return out


def _street_entry(session: Path) -> list[tuple[str, str, str]]:
    from packages.kd_research.street_bind import (
        check_street_bind,
        check_street_fetch,
        session_enforces_street,
        street_path,
    )

    out: list[tuple[str, str, str]] = []
    vm = session / "data" / "valuation_model.json"
    if session_enforces_street(session) or street_path(session).is_file():
        out.extend(check_street_fetch(session))
        if vm.is_file():
            out.extend(check_street_bind(session))
    return out


def _roic_if_vm(session: Path) -> list[tuple[str, str, str]]:
    vm = session / "data" / "valuation_model.json"
    if not vm.is_file():
        return []
    from packages.kd_research.roic_identity import check_roic_identity

    return check_roic_identity(session)


def _valuation_content_2_5(session: Path) -> list[tuple[str, str, str]]:
    from packages.kd_research.check_core import load_json

    vm, err = load_json(session / "data" / "valuation_model.json")
    if err:
        return [("FAIL", "valuation_model_content", err)]
    if isinstance(vm, dict):
        if "fair_value" not in vm and "model" not in vm:
            return [("FAIL", "valuation_model_content", "missing fair_value/model keys")]
        return [("PASS", "valuation_model_content", "core keys present")]
    return [("FAIL", "valuation_model_content", "not an object")]


def _wave2_complete_2p(session: Path) -> list[tuple[str, str, str]]:
    from packages.kd_research.decision import (
        check_decision_packet,
        check_technical_pass_allowed,
        session_is_wave2_runtime,
    )

    if not session_is_wave2_runtime(session):
        return []
    out: list[tuple[str, str, str]] = []
    out.extend(check_decision_packet(session))
    out.extend(check_technical_pass_allowed(session))
    return out


def _wave3_destock_complete(session: Path) -> list[tuple[str, str, str]]:
    from packages.kd_research.epistemology import (
        check_destock_not_silent_duration,
        session_is_wave3_runtime,
    )

    if not session_is_wave3_runtime(session):
        return []
    return check_destock_not_silent_duration(session)


def _wave4_destock_complete(session: Path) -> list[tuple[str, str, str]]:
    from packages.kd_research.epistemology import check_destock_default, session_is_wave4_runtime

    if not session_is_wave4_runtime(session):
        return []
    return check_destock_default(session)


def _wave2_complete_4p(session: Path) -> list[tuple[str, str, str]]:
    from packages.kd_research.decision import (
        check_decision_packet,
        check_readme_quotes_decision,
        session_is_wave2_runtime,
    )

    if not session_is_wave2_runtime(session):
        return []
    out: list[tuple[str, str, str]] = []
    out.extend(check_decision_packet(session))
    out.extend(check_readme_quotes_decision(session))
    return out


def _reports_complete(session: Path) -> list[tuple[str, str, str]]:
    from packages.kd_research.gates import check_reports, _infer_ticker

    return check_reports(session, _infer_ticker(session))


def _require_unique(rows: tuple[CheckRow, ...]) -> tuple[CheckRow, ...]:
    seen: set[str] = set()
    for row in rows:
        if row.id in seen:
            raise RuntimeError(f"duplicate check catalog id: {row.id}")
        seen.add(row.id)
    return rows


def _build_rows() -> tuple[CheckRow, ...]:
    from packages.kd_research.cash_quality import check_cash_quality
    from packages.kd_research.consumption import (
        check_1d_ind_background,
        check_2d_street_cite,
        check_fdd_material_hooks,
        check_stress_legal_dollar,
    )
    from packages.kd_research.decision import check_stress_bind, check_wave6_reopen
    from packages.kd_research.decision_quality import check_wave1_decision_quality
    from packages.kd_research.gates import (
        check_1c_year_dive_complete,
        check_filing_deep_dive_hooks,
        check_latest_quarter_risk_mapping,
        check_phase0_coverage,
        check_stress_coverage,
    )
    from packages.kd_research.library import check_transcript_freshness
    from packages.kd_research.operating_path import check_1d_complete, check_operating_path_hooks
    from packages.kd_research.roic_identity import check_roic_identity
    from packages.kd_research.street_bind import check_street_bind, check_street_fetch

    rows = _require_unique((
        CheckRow("library_entry", frozenset({"1_parallel:entry"}), _library_entry),
        CheckRow("cash_quality", frozenset({"1d:entry", "2_parallel:entry"}), check_cash_quality),
        CheckRow(
            "stress_coverage_entry",
            frozenset({"4_parallel:entry"}),
            check_stress_coverage,
        ),
        CheckRow(
            "lq_risk_entry",
            frozenset({"4_parallel:entry"}),
            check_latest_quarter_risk_mapping,
        ),
        CheckRow("oppath_entry", frozenset({"2_parallel:entry"}), _oppath_brief_and_hooks),
        CheckRow("street_entry", frozenset({"2_parallel:entry"}), _street_entry),
        CheckRow("roic_entry", frozenset({"2_parallel:entry"}), _roic_if_vm),
        CheckRow("vm_content_2_5", frozenset({"2_5:entry"}), _valuation_content_2_5),
        CheckRow("fdd_hooks_2_5", frozenset({"2_5:entry"}), check_filing_deep_dive_hooks),
        CheckRow("phase0_coverage", frozenset({"0:complete"}), check_phase0_coverage),
        CheckRow("street_fetch_1p", frozenset({"1_parallel:complete"}), check_street_fetch),
        CheckRow("library_complete", frozenset({"1_parallel:complete"}), _library_complete),
        CheckRow("year_dive_1c", frozenset({"1c:complete"}), check_1c_year_dive_complete),
        CheckRow("transcript_1c", frozenset({"1c:complete"}), check_transcript_freshness),
        CheckRow("oppath_1d_complete", frozenset({"1d:complete"}), check_1d_complete),
        CheckRow("oppath_1d_ind", frozenset({"1d:complete"}), check_1d_ind_background),
        CheckRow("fdd_hooks_2p", frozenset({"2_parallel:complete"}), check_filing_deep_dive_hooks),
        CheckRow("fdd_material_2p", frozenset({"2_parallel:complete"}), check_fdd_material_hooks),
        CheckRow("street_cite_2d", frozenset({"2_parallel:complete"}), check_2d_street_cite),
        CheckRow("oppath_hooks_2p", frozenset({"2_parallel:complete"}), check_operating_path_hooks),
        CheckRow("street_bind_2p", frozenset({"2_parallel:complete"}), check_street_bind),
        CheckRow("roic_2p", frozenset({"2_parallel:complete"}), check_roic_identity),
        CheckRow(
            "wave1_2p",
            frozenset({"2_parallel:complete"}),
            lambda s: check_wave1_decision_quality(s, include_reports=False),
        ),
        CheckRow("wave2_2p", frozenset({"2_parallel:complete"}), _wave2_complete_2p),
        CheckRow("wave3_2p", frozenset({"2_parallel:complete"}), _wave3_destock_complete),
        CheckRow("wave4_2p", frozenset({"2_parallel:complete"}), _wave4_destock_complete),
        CheckRow("stress_coverage_25", frozenset({"2_5:complete"}), check_stress_coverage),
        CheckRow("lq_risk_25", frozenset({"2_5:complete"}), check_latest_quarter_risk_mapping),
        CheckRow("stress_dollar_25", frozenset({"2_5:complete"}), check_stress_legal_dollar),
        CheckRow("reports_4p", frozenset({"4_parallel:complete"}), _reports_complete),
        CheckRow("wave2_4p", frozenset({"4_parallel:complete"}), _wave2_complete_4p),
        CheckRow("wave6_4p", frozenset({"4_parallel:complete"}), check_wave6_reopen),
        CheckRow("stress_bind_4p", frozenset({"4_parallel:complete"}), check_stress_bind),
    ))
    return rows


_ROWS: tuple[CheckRow, ...] | None = None


def catalog_rows() -> tuple[CheckRow, ...]:
    global _ROWS
    if _ROWS is None:
        _ROWS = _build_rows()
    return _ROWS


def run_catalog(session: Path, when: str) -> list[tuple[str, str, str]]:
    """Run every row tagged with `when`. Order is catalog order."""
    out: list[tuple[str, str, str]] = []
    for row in catalog_rows():
        if when in row.when:
            out.extend(row.run(session))
    return out


def complete_when_ids() -> set[str]:
    """Phase ids that have at least one `{phase}:complete` catalog row."""
    found: set[str] = set()
    for row in catalog_rows():
        for tag in row.when:
            if tag.endswith(":complete"):
                found.add(tag[: -len(":complete")])
    return found

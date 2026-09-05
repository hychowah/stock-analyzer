"""When a machine check runs (preflight, merge, and check_session).

Not the archive-index linter planned as scripts/check_catalog.py (B7 in
harness/plan_research_archive_layout.md). That script does not exist yet.

Path tables in gates.py say which files a phase needs. This module says which
domain checks run at which when-tag. session_core and session_full are exclusive
supersets for scripts/check_session.py (never run both in one invocation).

Adding a gate: write check_foo in its knowledge home, add one CheckRow or one
extra tag on an existing row. Dispatchers do not change.

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

# Phase tags: "{phase_id}:entry" | "{phase_id}:complete".
# session_core / session_full: exclusive check_session supersets (never both).
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
    from packages.kd_research.gates import _infer_ticker, check_reports

    return check_reports(session, _infer_ticker(session))


def _year_dive_session_full(session: Path) -> list[tuple[str, str, str]]:
    from packages.kd_research.annuals import check_1c_year_dive_complete

    return [
        row
        for row in check_1c_year_dive_complete(session)
        if row[1] != "registry/filing_deep_dive.json"
    ]


def _reports_session_full(session: Path) -> list[tuple[str, str, str]]:
    from packages.kd_research.gates import _infer_ticker, _report_rows

    return _report_rows(session, _infer_ticker(session), exact=True)


def _require_unique(rows: tuple[CheckRow, ...]) -> tuple[CheckRow, ...]:
    seen: set[str] = set()
    for row in rows:
        if row.id in seen:
            raise RuntimeError(f"duplicate check catalog id: {row.id}")
        seen.add(row.id)
    return rows


def _build_rows() -> tuple[CheckRow, ...]:
    from packages.kd_research.cash_quality import check_cash_quality
    from packages.kd_research.annuals import check_1c_year_dive_complete
    from packages.kd_research.consumption import (
        check_1d_ind_background,
        check_2d_street_cite,
        check_fdd_material_hooks,
        check_filing_deep_dive_hooks,
        check_stress_legal_dollar,
    )
    from packages.kd_research.decision import (
        check_latest_quarter_risk_mapping,
        check_stress_bind,
        check_stress_coverage,
        check_wave2_decision,
        check_wave6_reopen,
    )
    from packages.kd_research.decision_quality import check_wave1_decision_quality
    from packages.kd_research.epistemology import (
        check_wave3_epistemology,
        check_wave4_destock_default,
    )
    from packages.kd_research.isolation import check_agent4_isolation
    from packages.kd_research.phase_status import check_phase0_coverage
    from packages.kd_research.valuation_hygiene import check_valuation_decision_quality
    from packages.kd_research.library import check_transcript_freshness
    from packages.kd_research.operating_path import check_1d_complete, check_operating_path_hooks
    from packages.kd_research.roic_identity import check_roic_identity
    from packages.kd_research.street_bind import check_street_bind, check_street_fetch

    rows = _require_unique((
        CheckRow("library_entry", frozenset({"1_parallel:entry"}), _library_entry),
        CheckRow(
            "cash_quality",
            frozenset({"1d:entry", "2_parallel:entry", WHEN_SESSION_FULL}),
            check_cash_quality,
        ),
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
        CheckRow(
            "street_entry",
            frozenset({"2_parallel:entry", WHEN_SESSION_FULL}),
            _street_entry,
        ),
        CheckRow(
            "roic_entry",
            frozenset({"2_parallel:entry", WHEN_SESSION_FULL}),
            _roic_if_vm,
        ),
        CheckRow("vm_content_2_5", frozenset({"2_5:entry"}), _valuation_content_2_5),
        CheckRow("fdd_hooks_2_5", frozenset({"2_5:entry"}), check_filing_deep_dive_hooks),
        CheckRow("phase0_coverage", frozenset({"0:complete"}), check_phase0_coverage),
        CheckRow("street_fetch_1p", frozenset({"1_parallel:complete"}), check_street_fetch),
        CheckRow("library_complete", frozenset({"1_parallel:complete"}), _library_complete),
        CheckRow("year_dive_1c", frozenset({"1c:complete"}), check_1c_year_dive_complete),
        CheckRow("transcript_1c", frozenset({"1c:complete"}), check_transcript_freshness),
        CheckRow(
            "oppath_1d_complete",
            frozenset({"1d:complete", WHEN_SESSION_FULL}),
            check_1d_complete,
        ),
        CheckRow("oppath_1d_ind", frozenset({"1d:complete"}), check_1d_ind_background),
        CheckRow(
            "fdd_hooks_2p",
            frozenset({"2_parallel:complete", WHEN_SESSION_CORE, WHEN_SESSION_FULL}),
            check_filing_deep_dive_hooks,
        ),
        CheckRow("fdd_material_2p", frozenset({"2_parallel:complete"}), check_fdd_material_hooks),
        CheckRow("street_cite_2d", frozenset({"2_parallel:complete"}), check_2d_street_cite),
        CheckRow(
            "oppath_hooks_2p",
            frozenset({"2_parallel:complete", WHEN_SESSION_FULL}),
            check_operating_path_hooks,
        ),
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
        CheckRow(
            "wave6_4p",
            frozenset({"4_parallel:complete", WHEN_SESSION_FULL}),
            check_wave6_reopen,
        ),
        CheckRow("stress_bind_4p", frozenset({"4_parallel:complete"}), check_stress_bind),
        CheckRow(
            "agent4_core",
            frozenset({WHEN_SESSION_CORE}),
            lambda s: check_agent4_isolation(s, full=False),
        ),
        CheckRow(
            "agent4_full",
            frozenset({WHEN_SESSION_FULL}),
            lambda s: check_agent4_isolation(s, full=True),
        ),
        CheckRow(
            "mos_full",
            frozenset({WHEN_SESSION_FULL}),
            check_valuation_decision_quality,
        ),
        CheckRow(
            "wave1_full",
            frozenset({WHEN_SESSION_FULL}),
            lambda s: check_wave1_decision_quality(s, include_reports=True),
        ),
        CheckRow(
            "wave2_full",
            frozenset({WHEN_SESSION_FULL}),
            lambda s: check_wave2_decision(s, include_reports=True),
        ),
        CheckRow(
            "wave3_full",
            frozenset({WHEN_SESSION_FULL}),
            check_wave3_epistemology,
        ),
        CheckRow(
            "wave4_full",
            frozenset({WHEN_SESSION_FULL}),
            check_wave4_destock_default,
        ),
        CheckRow(
            "year_dive_full",
            frozenset({WHEN_SESSION_FULL}),
            _year_dive_session_full,
        ),
        CheckRow(
            "reports_full",
            frozenset({WHEN_SESSION_FULL}),
            _reports_session_full,
        ),
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

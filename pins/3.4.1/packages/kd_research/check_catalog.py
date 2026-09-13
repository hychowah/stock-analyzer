"""When a machine check runs (preflight, merge, and check_session).

Not the archive-index linter planned as scripts/check_catalog.py (B7 in
harness/plan_research_archive_layout.md). That script does not exist yet.

Path tables live on `phase_graph.PhaseNode`. This module says which domain
checks run at which when-tag. session_core and session_full are exclusive
supersets for scripts/check_session.py (never run both in one invocation).

Adding a gate: write check_foo in its knowledge home, add one CheckRow or one
extra tag on an existing row. Dispatchers do not change. Domain functions
still SKIPPED on legacy — the catalog does not pre-filter by version.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from packages.kd_research.check_core import structured_file
from packages.kd_research.phase_graph import PHASE_IDS

CheckFn = Callable[[Path], Sequence[tuple[str, str, str]]]

# Phase tags: "{phase_id}:entry" | "{phase_id}:complete".
# session_core / session_full: exclusive check_session supersets (never both).
WHEN_SESSION_CORE = "session_core"
WHEN_SESSION_FULL = "session_full"

ENTRY_WHENS = frozenset(f"{pid}:entry" for pid in PHASE_IDS)
CORE_AND_FULL = frozenset({WHEN_SESSION_CORE, WHEN_SESSION_FULL})
FULL_ONLY = frozenset({WHEN_SESSION_FULL})


@dataclass(frozen=True)
class CheckRow:
    id: str
    when: frozenset[str]
    run: CheckFn


CORE_FILE_SPECS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "registry/sector_config.json",
        "sector_config",
        ("ticker", "session_date", "primary_sector", "confidence", "rationale"),
    ),
    (
        "registry/latest_quarter.json",
        "latest_quarter",
        ("ticker", "fiscal_period", "sources"),
    ),
    (
        "data/valuation_model.json",
        "valuation_model",
        ("ticker", "model", "fair_value", "assumptions", "compute_script"),
    ),
)

FULL_FILE_SPECS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "registry/background.json",
        "background",
        ("ticker", "rounds"),
    ),
    (
        "registry/news_sentiment.json",
        "news_sentiment",
        ("ticker", "items"),
    ),
    (
        "registry/sec_filings.json",
        "sec_filings",
        ("ticker", "filings"),
    ),
    (
        "registry/filing_deep_dive.json",
        "filing_deep_dive",
        ("ticker", "session_date", "footnotes", "strategy_arc", "management_scorecard", "sources"),
    ),
    (
        "registry/technical.json",
        "technical",
        ("ticker", "indicators", "levels", "compute_script"),
    ),
    (
        "registry/tsr_validation.json",
        "tsr_validation",
        ("ticker", "tsr", "compute_script"),
    ),
    (
        "registry/risk_bridge.json",
        "risk_bridge",
        ("ticker", "scenario_probabilities", "stress_test"),
    ),
    (
        "registry/audit.json",
        "audit",
        ("verdict", "checks"),
    ),
)


def _full_deferred(_session: Path) -> list[tuple[str, str, str]]:
    return [
        (
            "SKIPPED",
            "risk_bridge/report/audit/handoff/deep-dive checks",
            "run with --full after Phase 5",
        )
    ]


def _require_unique(rows: tuple[CheckRow, ...]) -> tuple[CheckRow, ...]:
    seen: set[str] = set()
    for row in rows:
        if row.id in seen:
            raise RuntimeError(f"duplicate check catalog id: {row.id}")
        seen.add(row.id)
    return rows


def _build_rows() -> tuple[CheckRow, ...]:
    from packages.kd_research.annuals import check_1c_year_dive_complete, check_year_dives
    from packages.kd_research.damodaran_gates import check_damodaran_v3
    from packages.kd_research.cash_quality import check_cash_quality
    from packages.kd_research.check_core import check_reports, check_reports_exact
    from packages.kd_research.consumption import (
        check_1d_ind_background,
        check_2d_street_cite,
        check_fdd_material_hooks,
        check_filing_deep_dive_content,
        check_filing_deep_dive_hooks,
        check_market_context,
        check_stress_legal_dollar,
    )
    from packages.kd_research.decision import (
        check_latest_quarter_risk_mapping,
        check_risk_bridge,
        check_stress_bind,
        check_stress_coverage,
        check_stress_report_card,
        check_wave2_decision,
        check_wave2_phase2_complete,
        check_wave2_phase4_complete,
        check_wave6_reopen,
    )
    from packages.kd_research.stress_apply import (
        check_shock_surface,
        check_stress_applied,
    )
    from packages.kd_research.decision_quality import (
        check_wave1_decision_quality_core,
        check_wave1_decision_quality_full,
    )
    from packages.kd_research.epistemology import (
        check_wave3_destock_complete,
        check_wave3_epistemology,
        check_wave4_destock_complete,
        check_wave4_destock_default,
    )
    from packages.kd_research.isolation import (
        check_agent4_isolation_core,
        check_agent4_isolation_full,
        check_session_isolation_core,
        check_session_isolation_full,
    )
    from packages.kd_research.library import (
        check_library_complete,
        check_library_entry,
        check_library_path_citations_full,
        check_library_session,
        check_transcript_freshness,
    )
    from packages.kd_research.classification import check_classification_card
    from packages.kd_research.narrative_lock import check_1e_complete
    from packages.kd_research.operating_path import (
        check_1d_complete,
        check_operating_path_hooks,
        check_oppath_entry,
    )
    from packages.kd_research.phase_status import (
        check_audit_verdict,
        check_handoffs,
        check_phase0_coverage,
        check_phase_status_session,
        check_research_brief,
    )
    from packages.kd_research.provenance import (
        check_llm_identity_entry,
        check_meta_artifacts,
        check_session_identity,
    )
    from packages.kd_research.roic_identity import check_roic_identity, check_roic_if_vm
    from packages.kd_research.wacc_buildup import check_wacc_buildup, check_wacc_if_vm
    from packages.kd_research.forecast_table import (
        check_explicit_forecast,
        check_explicit_forecast_if_vm,
        check_fundamental_forecast_table,
    )
    from packages.kd_research.spawn_gate import check_spawn_session
    from packages.kd_research.street_bind import (
        check_street_bind,
        check_street_entry,
        check_street_fetch,
        check_street_schema_if_present,
    )
    from packages.kd_research.valuation_hygiene import (
        check_street_hygiene,
        check_valuation_content,
        check_valuation_decision_quality,
    )

    file_rows = [
        CheckRow(
            f"file:{rel}",
            CORE_AND_FULL,
            structured_file(rel, schema, keys),
        )
        for rel, schema, keys in CORE_FILE_SPECS
    ]
    file_rows.extend(
        CheckRow(
            f"file:{rel}",
            FULL_ONLY,
            structured_file(rel, schema, keys),
        )
        for rel, schema, keys in FULL_FILE_SPECS
    )

    rows = _require_unique((
        *file_rows,
        CheckRow("street_schema_if_present", FULL_ONLY, check_street_schema_if_present),
        CheckRow("identity", CORE_AND_FULL, check_session_identity),
        CheckRow("market_context", CORE_AND_FULL, check_market_context),
        CheckRow("research_brief", CORE_AND_FULL, check_research_brief),
        CheckRow("phase_status_session", CORE_AND_FULL, check_phase_status_session),
        CheckRow("spawn_session", CORE_AND_FULL, check_spawn_session),
        CheckRow("meta_artifacts", CORE_AND_FULL, check_meta_artifacts),
        CheckRow("session_isolation_core", frozenset({WHEN_SESSION_CORE}), check_session_isolation_core),
        CheckRow("session_isolation_full", FULL_ONLY, check_session_isolation_full),
        CheckRow("library_session", CORE_AND_FULL, check_library_session),
        CheckRow("library_citations_full", FULL_ONLY, check_library_path_citations_full),
        CheckRow("llm_identity_entry", ENTRY_WHENS, check_llm_identity_entry),
        CheckRow("library_entry", frozenset({"1_parallel:entry"}), check_library_entry),
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
        CheckRow("oppath_entry", frozenset({"2_parallel:entry"}), check_oppath_entry),
        CheckRow(
            "street_entry",
            frozenset({"2_parallel:entry", WHEN_SESSION_FULL}),
            check_street_entry,
        ),
        CheckRow(
            "street_hygiene",
            frozenset({"2_parallel:entry", "2_parallel:complete", WHEN_SESSION_FULL}),
            check_street_hygiene,
        ),
        CheckRow(
            "roic_entry",
            frozenset({"2_parallel:entry", WHEN_SESSION_FULL}),
            check_roic_if_vm,
        ),
        CheckRow(
            "wacc_entry",
            frozenset({"2_parallel:entry", WHEN_SESSION_FULL}),
            check_wacc_if_vm,
        ),
        CheckRow(
            "forecast_entry",
            frozenset({"2_parallel:entry", WHEN_SESSION_FULL}),
            check_explicit_forecast_if_vm,
        ),
        CheckRow("vm_content_2_5", frozenset({"2_5:entry"}), check_valuation_content),
        CheckRow("fdd_hooks_2_5", frozenset({"2_5:entry"}), check_filing_deep_dive_hooks),
        CheckRow("phase0_coverage", frozenset({"0:complete"}), check_phase0_coverage),
        CheckRow(
            "classification_entry",
            frozenset({"0:entry", "1e:entry", WHEN_SESSION_FULL}),
            check_classification_card,
        ),
        CheckRow(
            "narrative_1e_complete",
            frozenset({"1e:complete", WHEN_SESSION_FULL}),
            check_1e_complete,
        ),
        CheckRow("street_fetch_1p", frozenset({"1_parallel:complete"}), check_street_fetch),
        CheckRow("library_complete", frozenset({"1_parallel:complete"}), check_library_complete),
        CheckRow("year_dive_1c", frozenset({"1c:complete"}), check_1c_year_dive_complete),
        CheckRow(
            "transcript_1c",
            frozenset({"1c:complete", WHEN_SESSION_FULL}),
            check_transcript_freshness,
        ),
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
        CheckRow("wacc_2p", frozenset({"2_parallel:complete"}), check_wacc_buildup),
        CheckRow(
            "damodaran_2p",
            frozenset({"2_parallel:complete", WHEN_SESSION_FULL}),
            check_damodaran_v3,
        ),
        CheckRow("forecast_2p", frozenset({"2_parallel:complete"}), check_explicit_forecast),
        CheckRow(
            "shock_surface_2p",
            frozenset({"2_parallel:complete", WHEN_SESSION_FULL}),
            check_shock_surface,
        ),
        CheckRow(
            "wave1_2p",
            frozenset({"2_parallel:complete"}),
            check_wave1_decision_quality_core,
        ),
        CheckRow("wave2_2p", frozenset({"2_parallel:complete"}), check_wave2_phase2_complete),
        CheckRow("wave3_2p", frozenset({"2_parallel:complete"}), check_wave3_destock_complete),
        CheckRow("wave4_2p", frozenset({"2_parallel:complete"}), check_wave4_destock_complete),
        CheckRow("stress_coverage_25", frozenset({"2_5:complete"}), check_stress_coverage),
        CheckRow(
            "stress_applied_25",
            frozenset({"2_5:complete", WHEN_SESSION_FULL}),
            check_stress_applied,
        ),
        CheckRow("lq_risk_25", frozenset({"2_5:complete"}), check_latest_quarter_risk_mapping),
        CheckRow("stress_dollar_25", frozenset({"2_5:complete"}), check_stress_legal_dollar),
        CheckRow("reports_4p", frozenset({"4_parallel:complete"}), check_reports),
        CheckRow(
            "forecast_table_4p",
            frozenset({"4_parallel:complete", WHEN_SESSION_FULL}),
            check_fundamental_forecast_table,
        ),
        CheckRow("wave2_4p", frozenset({"4_parallel:complete"}), check_wave2_phase4_complete),
        CheckRow(
            "wave6_4p",
            frozenset({"4_parallel:complete", WHEN_SESSION_FULL}),
            check_wave6_reopen,
        ),
        CheckRow(
            "stress_bind_4p",
            frozenset({"4_parallel:complete", WHEN_SESSION_FULL}),
            check_stress_bind,
        ),
        CheckRow(
            "stress_card_4p",
            frozenset({"4_parallel:complete", WHEN_SESSION_FULL}),
            check_stress_report_card,
        ),
        CheckRow("agent4_core", frozenset({WHEN_SESSION_CORE}), check_agent4_isolation_core),
        CheckRow("agent4_full", FULL_ONLY, check_agent4_isolation_full),
        CheckRow("mos_full", FULL_ONLY, check_valuation_decision_quality),
        CheckRow("wave1_full", FULL_ONLY, check_wave1_decision_quality_full),
        CheckRow("wave2_full", FULL_ONLY, check_wave2_decision),
        CheckRow("wave3_full", FULL_ONLY, check_wave3_epistemology),
        CheckRow("wave4_full", FULL_ONLY, check_wave4_destock_default),
        CheckRow("year_dive_full", FULL_ONLY, check_year_dives),
        CheckRow("reports_full", FULL_ONLY, check_reports_exact),
        CheckRow("fdd_content_full", FULL_ONLY, check_filing_deep_dive_content),
        CheckRow("risk_bridge_full", FULL_ONLY, check_risk_bridge),
        CheckRow("audit_full", FULL_ONLY, check_audit_verdict),
        CheckRow("handoffs_full", FULL_ONLY, check_handoffs),
        CheckRow("full_deferred", frozenset({WHEN_SESSION_CORE}), _full_deferred),
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

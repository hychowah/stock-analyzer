"""Phase graph: one DAG of research phases. Derived tables live here too.

Terminology (avoid LLM confusion):
- **Orchestrator** = main lead agent (may act in any phase; updates phase_status).
- **Subagent** = specialist worker (2a, 5, 13, phase0_swarm, …) that belongs to
  exactly one phase on the graph. On-disk ``phase_status.agents[].agent_id`` is
  the subagent id for specialists (schema field name kept for compatibility).

Edges (after version overlays) are the gate: enter a phase only when every
prior is complete|skipped. Spawn only subagents that belong to that phase
(orchestrator always allowed). Intra-phase parallel subagents are unordered.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from packages.kd_research.check_core import session_since
from packages.kd_research.library import BIND_REL, LIBRARY_SINCE
from packages.kd_research.operating_path import BRIEF_REL, OPPATH_SINCE
from packages.kd_research.street_bind import STREET_REL, STREET_SINCE

PHASE0_PARALLEL_SINCE = (2, 30, 0)
READY_SET_SINCE = (3, 0, 0)
PRICE_SNAPSHOT_REL = "data/price_snapshot.json"
PRICE_SNAPSHOT_SINCE = (2, 42, 0)


@dataclass(frozen=True)
class VersionedPath:
    """Entry file that applies on this phase after ``since``."""

    rel: str
    required: bool
    since: tuple[int, int, int]


@dataclass(frozen=True)
class PhaseNode:
    """One research phase. Priors are direct edges.

    Evidence paths, versioned extras, display, per-subagent handoff globs,
    and phase annotations live here. Gates walk this node; workflow_spec dumps
    it. Do not keep a second copy of these facts.
    """

    phase_id: str
    priors: tuple[str, ...]
    subagents: tuple[str, ...]
    spawn_ids: tuple[str, ...]
    entry_required: tuple[str, ...]
    entry_optional: tuple[str, ...] = ()
    complete_paths: tuple[str, ...] = ()
    primary_artifacts: dict[str, tuple[str, ...]] | None = None
    specialist_artifacts: dict[str, tuple[str, ...]] | None = None
    display_writes: dict[str, tuple[str, ...]] | None = None
    annotations: tuple[str, ...] = ()
    entry_preflight: str = ""
    complete_preflight: str = ""
    label: str = ""
    stage: str = ""
    purpose: str = ""
    handoff_globs: tuple[tuple[str, tuple[str, ...]], ...] = ()
    entry_versioned: tuple[VersionedPath, ...] = ()
    # Per-subagent ready-sets (harness >= 3.0.0). Empty = inherit node.priors /
    # entry_required. Lets Agent 4 start without 1d while Agent 5 still waits.
    subagent_priors: tuple[tuple[str, tuple[str, ...]], ...] = ()
    subagent_entry: tuple[tuple[str, tuple[str, ...]], ...] = ()

    def priors_for(self, subagent_id: str | None) -> tuple[str, ...]:
        if subagent_id:
            mapping = dict(self.subagent_priors)
            if subagent_id in mapping:
                return mapping[subagent_id]
        return self.priors

    def entry_required_for(self, subagent_id: str | None) -> tuple[str, ...]:
        if subagent_id:
            mapping = dict(self.subagent_entry)
            if subagent_id in mapping:
                return mapping[subagent_id]
        return self.entry_required


def _n(
    phase_id: str,
    priors: tuple[str, ...],
    subagents: tuple[str, ...],
    *,
    spawn_ids: tuple[str, ...] | None = None,
    entry_required: tuple[str, ...] = (),
    entry_optional: tuple[str, ...] = (),
    complete_paths: tuple[str, ...] = (),
    primary_artifacts: dict[str, tuple[str, ...]] | None = None,
    specialist_artifacts: dict[str, tuple[str, ...]] | None = None,
    display_writes: dict[str, tuple[str, ...]] | None = None,
    annotations: tuple[str, ...] = (),
    label: str = "",
    stage: str = "",
    purpose: str = "",
    handoff_globs: tuple[tuple[str, tuple[str, ...]], ...] = (),
    entry_versioned: tuple[VersionedPath, ...] = (),
    subagent_priors: tuple[tuple[str, tuple[str, ...]], ...] = (),
    subagent_entry: tuple[tuple[str, tuple[str, ...]], ...] = (),
) -> PhaseNode:
    spawns = spawn_ids if spawn_ids is not None else tuple(
        s for s in subagents if s != "orchestrator"
    )
    return PhaseNode(
        phase_id=phase_id,
        priors=priors,
        subagents=subagents,
        spawn_ids=spawns,
        entry_required=entry_required,
        entry_optional=entry_optional,
        complete_paths=complete_paths,
        primary_artifacts=primary_artifacts or {},
        specialist_artifacts=specialist_artifacts or {},
        display_writes=display_writes or {},
        annotations=annotations,
        entry_preflight=f"{phase_id}:entry",
        complete_preflight=f"{phase_id}:complete",
        label=label,
        stage=stage,
        purpose=purpose,
        handoff_globs=handoff_globs,
        entry_versioned=entry_versioned,
        subagent_priors=subagent_priors,
        subagent_entry=subagent_entry,
    )


# Live DAG (harness >= 3.0.0 ready-sets). Overlays: <3.0 restore 2.44 joins;
# <2.30 add 0 as prior of 1_parallel; <2.6 omit 1d.
PHASE_GRAPH: tuple[PhaseNode, ...] = (
    _n(
        "orch",
        (),
        ("orchestrator",),
        spawn_ids=(),
        display_writes={
            "orchestrator": (
                "registry/sector_config.json",
                "registry/market_context.json",
                "registry/research_brief.json",
                BIND_REL,
                PRICE_SNAPSHOT_REL,
            ),
        },
        label="Classify & brief",
        stage="setup",
        purpose="Sector, market context, research brief, library bind",
    ),
    _n(
        "0",
        ("orch",),
        ("phase0_swarm",),
        entry_required=("registry/sector_config.json", "registry/market_context.json"),
        entry_optional=("registry/research_brief.json",),
        primary_artifacts={"phase0_swarm": ("registry/background.json",)},
        specialist_artifacts={
            "phase0_swarm": ("registry/background.json", "registry/raw/phase0_*.json"),
        },
        label="Background",
        stage="gather",
        purpose="Business model, open questions, bear case",
        handoff_globs=(
            ("phase0_swarm", ("phase0_swarm*.md", "phase0_*.md", "phase0.md")),
        ),
    ),
    _n(
        "1_parallel",
        ("orch",),
        ("2a", "2b", "2c"),
        entry_required=("registry/sector_config.json",),
        complete_paths=(
            "data/sp_financials.csv",
            "registry/sec_filings.json",
            "registry/news_sentiment.json",
        ),
        primary_artifacts={
            "2a": ("data/sp_financials.csv",),
            "2b": ("registry/sec_filings.json",),
            "2c": ("registry/news_sentiment.json",),
        },
        specialist_artifacts={
            "2a": ("data/sp_financials.csv",),
            "2b": ("registry/sec_filings.json",),
            "2c": ("registry/news_sentiment.json",),
        },
        display_writes={
            "2a": (
                "data/peer_comparison.csv",
                STREET_REL,
                "registry/data_fetch_log.json",
            ),
        },
        label="Source facts",
        stage="gather",
        purpose="Financials, filings, and news in parallel",
        handoff_globs=(
            ("2a", ("2a_*.md", "2a.md")),
            ("2b", ("2b_*.md", "2b.md")),
            ("2c", ("2c_*.md", "2c.md")),
        ),
        entry_versioned=(VersionedPath(BIND_REL, True, LIBRARY_SINCE),),
    ),
    _n(
        "1b",
        ("orch",),
        ("2d",),
        entry_required=("data/sp_financials.csv", "registry/sec_filings.json"),
        primary_artifacts={"2d": ("registry/latest_quarter.json",)},
        specialist_artifacts={"2d": ("registry/latest_quarter.json",)},
        label="Latest quarter",
        stage="gather",
        purpose="Print overrides for valuation",
        handoff_globs=(("2d", ("2d_*.md", "2d.md")),),
    ),
    _n(
        "1c",
        ("orch",),
        ("2e",),
        entry_required=("registry/sec_filings.json",),
        primary_artifacts={"2e": ("registry/filing_deep_dive.json",)},
        specialist_artifacts={"2e": ("registry/filing_deep_dive.json",)},
        label="Deep dive",
        stage="gather",
        purpose="Footnotes, strategy arc, management scorecard",
        handoff_globs=(("2e", ("2e_*.md", "2e.md")),),
    ),
    _n(
        "1d",
        ("0", "1b"),
        ("1d_rev", "1d_ind", "1d_ol", "1d_merge"),
        entry_required=(
            "data/sp_financials.csv",
            "registry/latest_quarter.json",
        ),
        primary_artifacts={
            "1d_rev": ("registry/raw/oppath_rev.json",),
            "1d_ind": ("registry/raw/oppath_ind.json",),
            "1d_ol": ("registry/raw/oppath_ol.json",),
            "1d_merge": ("registry/operating_path_brief.json",),
        },
        specialist_artifacts={
            "1d_rev": ("registry/raw/oppath_rev.json",),
            "1d_ind": ("registry/raw/oppath_ind.json",),
            "1d_ol": ("registry/raw/oppath_ol.json",),
            "1d_merge": ("registry/operating_path_brief.json",),
        },
        label="Operating path",
        stage="gather",
        purpose="Growth, industry, leverage → brief for valuation",
        handoff_globs=(
            ("1d_rev", ("1d_rev*.md",)),
            ("1d_ind", ("1d_ind*.md",)),
            ("1d_ol", ("1d_ol*.md",)),
            ("1d_merge", ("1d_merge*.md", "1d_operating_path*.md")),
        ),
    ),
    _n(
        "2_parallel",
        ("orch",),
        ("4", "5", "12"),
        entry_required=("registry/sector_config.json",),
        entry_optional=("registry/research_brief.json", "registry/news_sentiment.json"),
        complete_paths=(
            "registry/technical.json",
            "data/valuation_model.json",
            "registry/tsr_validation.json",
        ),
        primary_artifacts={
            "4": ("registry/technical.json",),
            "5": ("data/valuation_model.json",),
            "12": ("registry/tsr_validation.json",),
        },
        specialist_artifacts={
            "4": ("registry/technical.json",),
            "5": ("data/valuation_model.json",),
            "12": ("registry/tsr_validation.json",),
        },
        label="Valuation",
        stage="decide",
        purpose="Technical, DCF, and TSR in parallel",
        handoff_globs=(
            ("4", ("4_*.md", "4.md")),
            ("5", ("5_*.md", "5.md")),
            ("12", ("12_*.md", "12.md")),
        ),
        entry_versioned=(
            VersionedPath(STREET_REL, False, STREET_SINCE),
            VersionedPath(PRICE_SNAPSHOT_REL, True, PRICE_SNAPSHOT_SINCE),
        ),
        subagent_priors=(
            ("4", ("orch",)),
            ("12", ("orch",)),
            ("5", ("1d",)),
        ),
        subagent_entry=(
            (
                "4",
                (PRICE_SNAPSHOT_REL,),
            ),
            (
                "12",
                ("data/sp_financials.csv",),
            ),
            (
                "5",
                (
                    "registry/sector_config.json",
                    "registry/market_context.json",
                    "data/sp_financials.csv",
                    "registry/sec_filings.json",
                    "registry/latest_quarter.json",
                    "registry/filing_deep_dive.json",
                    BRIEF_REL,
                    PRICE_SNAPSHOT_REL,
                ),
            ),
        ),
    ),
    _n(
        "2_5",
        ("1d",),
        ("phase25_swarm",),
        entry_required=(
            "data/valuation_model.json",
            "registry/latest_quarter.json",
            "registry/filing_deep_dive.json",
        ),
        entry_optional=("registry/background.json",),
        primary_artifacts={"phase25_swarm": ("registry/risk_bridge.json",)},
        specialist_artifacts={
            "phase25_swarm": ("registry/risk_bridge.json", "registry/raw/stress_*.json"),
        },
        annotations=("5b",),
        label="Stress",
        stage="decide",
        purpose="Risk bridge and scenario shocks",
        handoff_globs=(
            (
                "phase25_swarm",
                ("phase25_swarm*.md", "phase25_*.md", "phase25.md", "2_5_*.md"),
            ),
        ),
    ),
    _n(
        "3",
        ("1d",),
        ("6",),
        entry_required=("data/valuation_model.json",),
        primary_artifacts={"6": ("charts",)},
        specialist_artifacts={"6": ("charts/*.png",)},
        label="Charts",
        stage="publish",
        purpose="Visuals for the report pack",
        handoff_globs=(("6", ("6_*.md", "6.md")),),
    ),
    _n(
        "4_parallel",
        ("2_5",),
        ("7", "8", "11"),
        entry_required=(
            "data/valuation_model.json",
            "registry/risk_bridge.json",
            "registry/technical.json",
            "registry/tsr_validation.json",
        ),
        entry_optional=("registry/filing_deep_dive.json", "registry/market_context.json"),
        primary_artifacts={
            "7": ("reports",),
            "8": ("reports",),
            "11": ("reports",),
        },
        specialist_artifacts={
            "7": ("reports/01_*_fundamental.md",),
            "8": ("reports/02_*_technical.md",),
            "11": ("reports/00_*_README.md",),
        },
        label="Reports",
        stage="publish",
        purpose="Fundamental, technical, and README",
        handoff_globs=(
            ("7", ("7_*.md", "7.md")),
            ("8", ("8_*.md", "8.md")),
            ("11", ("11_*.md", "11.md")),
        ),
    ),
    _n(
        "5",
        ("4_parallel",),
        ("13",),
        entry_required=("reports",),
        primary_artifacts={"13": ("registry/audit.json",)},
        specialist_artifacts={"13": ("registry/audit.json",)},
        label="Audit",
        stage="publish",
        purpose="Process completeness gate",
        handoff_globs=(("13", ("13_*.md", "13.md")),),
    ),
    _n(
        "done",
        ("5",),
        (),
        spawn_ids=(),
        entry_required=("registry/audit.json",),
        label="Done",
        stage="publish",
        purpose="Catalog snapshot after audit PASS",
    ),
)

PHASE_AGENTS: list[tuple[str, list[str]]] = [
    (n.phase_id, list(n.subagents)) for n in PHASE_GRAPH
]
PHASE_IDS: list[str] = [n.phase_id for n in PHASE_GRAPH]
PHASE_ORDER: list[str] = list(PHASE_IDS)
PHASE_ANNOTATIONS: frozenset[str] = frozenset(
    a for n in PHASE_GRAPH for a in n.annotations
)

PHASE_REQUIRED_SPAWNS: dict[str, tuple[str, ...]] = {
    n.phase_id: n.spawn_ids for n in PHASE_GRAPH if n.spawn_ids
}
SPECIALIST_ARTIFACTS: dict[str, tuple[str, ...]] = {}
PHASE_PRIMARY_ARTIFACTS: dict[str, list[str]] = {}
DISPLAY_WRITES: dict[str, tuple[str, ...]] = {}
for _n_node in PHASE_GRAPH:
    for _aid, _arts in (_n_node.specialist_artifacts or {}).items():
        SPECIALIST_ARTIFACTS[_aid] = _arts
    for _aid, _arts in (_n_node.primary_artifacts or {}).items():
        PHASE_PRIMARY_ARTIFACTS[_aid] = list(_arts)
    for _aid, _arts in (_n_node.display_writes or {}).items():
        DISPLAY_WRITES[_aid] = _arts

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


def session_is_phase0_parallel_runtime(session: Path | None) -> bool:
    """True when 1_parallel may start without Phase 0 complete (harness >= 2.30.0)."""
    if session is None:
        return True
    return session_since(session, PHASE0_PARALLEL_SINCE)


def session_is_ready_set_runtime(session: Path | None) -> bool:
    """True when 1b/1c/Agent 4 use file-shaped ready-sets (harness >= 3.0.0)."""
    if session is None:
        return True
    return session_since(session, READY_SET_SINCE)


def _semver_label(tup: tuple[int, int, int]) -> str:
    return f"{tup[0]}.{tup[1]}.{tup[2]}"


def dump_entry_rows(node: PhaseNode) -> list[dict[str, Any]]:
    """Entry files for the workflow dump. Versioned extras carry ``since``."""
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rel in node.entry_required:
        rows.append({"path": rel, "required": True})
        seen.add(rel)
    for _sid, paths in node.subagent_entry:
        for rel in paths:
            if rel not in seen:
                rows.append({"path": rel, "required": True, "subagent": _sid})
                seen.add(rel)
    for rel in node.entry_optional:
        if rel not in seen:
            rows.append({"path": rel, "required": False})
            seen.add(rel)
    for vp in node.entry_versioned:
        label = _semver_label(vp.since)
        if vp.rel in seen:
            for row in rows:
                if row.get("path") == vp.rel:
                    row["since"] = label
                    row["required"] = vp.required
                    break
            continue
        rows.append(
            {
                "path": vp.rel,
                "required": vp.required,
                "since": label,
            }
        )
        seen.add(vp.rel)
    return rows


def _with_versioned_entry(node: PhaseNode, session: Path | None) -> PhaseNode:
    if not node.entry_versioned:
        return node
    req = list(node.entry_required)
    opt = list(node.entry_optional)
    changed = False
    for vp in node.entry_versioned:
        if session is not None and not session_since(session, vp.since):
            continue
        if vp.required:
            if vp.rel not in req:
                req.append(vp.rel)
                changed = True
        elif vp.rel not in opt:
            opt.append(vp.rel)
            changed = True
    if not changed:
        return node
    return replace(node, entry_required=tuple(req), entry_optional=tuple(opt))


def _overlay_pre_ready_set(nodes: dict[str, PhaseNode]) -> dict[str, PhaseNode]:
    """Restore 2.44 joins: 1b/1c wait on 1_parallel; 1d waits on 1c; Agent 4/5/12
    share 2_parallel after 1d; charts and reports wait on 2.5; audit waits on charts.
    """
    fdd = "registry/filing_deep_dive.json"
    two = nodes["2_parallel"]
    nodes["1b"] = replace(nodes["1b"], priors=("1_parallel",))
    nodes["1c"] = replace(nodes["1c"], priors=("1_parallel",))
    one_d = nodes["1d"]
    d_entry = one_d.entry_required
    if fdd not in d_entry:
        d_entry = d_entry + (fdd,)
    nodes["1d"] = replace(one_d, priors=("0", "1b", "1c"), entry_required=d_entry)
    nodes["2_parallel"] = replace(
        two,
        priors=("1d",),
        subagent_priors=(),
        subagent_entry=(),
        entry_required=(
            "registry/sector_config.json",
            "registry/market_context.json",
            "data/sp_financials.csv",
            "registry/sec_filings.json",
            "registry/latest_quarter.json",
            fdd,
        ),
        entry_versioned=(
            VersionedPath(BRIEF_REL, True, OPPATH_SINCE),
            VersionedPath(STREET_REL, False, STREET_SINCE),
            VersionedPath(PRICE_SNAPSHOT_REL, True, PRICE_SNAPSHOT_SINCE),
        ),
    )
    nodes["2_5"] = replace(nodes["2_5"], priors=("2_parallel",))
    nodes["3"] = replace(nodes["3"], priors=("2_5",))
    nodes["5"] = replace(nodes["5"], priors=("3", "4_parallel"))
    return nodes


def graph_for_session(session: Path | None = None) -> dict[str, PhaseNode]:
    """Live DAG plus version overlays (not extra tables)."""
    nodes = {n.phase_id: n for n in PHASE_GRAPH}
    if not session_is_ready_set_runtime(session):
        nodes = _overlay_pre_ready_set(nodes)
    if not session_is_phase0_parallel_runtime(session):
        one_p = nodes["1_parallel"]
        if "0" not in one_p.priors:
            nodes["1_parallel"] = replace(one_p, priors=one_p.priors + ("0",))
    omit_1d = False
    if session is not None:
        from packages.kd_research.operating_path import session_enforces_1d

        omit_1d = not session_enforces_1d(session)
    if omit_1d and "1d" in nodes:
        one_d = nodes.pop("1d")
        two = nodes["2_parallel"]
        nodes["2_parallel"] = replace(two, priors=one_d.priors)
    return {pid: _with_versioned_entry(node, session) for pid, node in nodes.items()}


def designed_phase_ids(session: Path | None = None) -> list[str]:
    """Phase ids this session must cover. Overlay <2.6 omits 1d."""
    nodes = graph_for_session(session)
    return [pid for pid in PHASE_IDS if pid in nodes]


def prerequisites_for(phase_id: str, session: Path | None = None) -> list[str]:
    """Direct priors (after overlays) that must be complete|skipped."""
    node = graph_for_session(session).get(phase_id)
    if node is None:
        return []
    return list(node.priors)


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

    if phase_id not in PHASE_IDS:
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
    results.extend(check_phase_status_order_integrity(smap, session))

    node = graph_for_session(session).get(phase_id)
    prior_ids = (
        node.priors_for(sid) if node is not None else prerequisites_for(phase_id, session)
    )
    for prior in prior_ids:
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
    if isinstance(current, str) and node is not None:
        allowed_current = {phase_id, *node.priors_for(sid)}
        if current in allowed_current:
            results.append(
                (
                    "PASS",
                    "phase_graph.current_phase",
                    f"current_phase={current} entering={phase_id}",
                )
            )
        else:
            results.append(
                (
                    "WARN",
                    "phase_graph.current_phase_lag",
                    f"phase_status.current_phase={current!r} but entering {phase_id!r} — "
                    "update current_phase as you advance",
                )
            )

    return results


def check_phase_status_order_integrity(
    smap: dict[str, str],
    session: Path | None = None,
) -> list[tuple[str, str, str]]:
    """FAIL if a phase is complete while a direct prior is not done."""
    results: list[tuple[str, str, str]] = []
    nodes = graph_for_session(session)
    for pid, node in nodes.items():
        st = smap.get(pid)
        if st != "complete":
            continue
        for prior in node.priors:
            pst = smap.get(prior)
            if pst is None:
                continue
            if pst not in PRIOR_OK_STATUSES:
                results.append(
                    (
                        "FAIL",
                        "phase_graph.order_integrity",
                        f"phase {pid} is complete but prior {prior} is "
                        f"{pst} — advance along graph edges only",
                    )
                )
                return results
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
    results = check_phase_status_order_integrity(smap, session)

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
    nodes = graph_for_session(session)
    for pid in PHASE_IDS:
        if pid not in nodes:
            continue
        st = smap.get(pid, "pending")
        if st in PRIOR_OK_STATUSES:
            continue
        if all(smap.get(p) in PRIOR_OK_STATUSES for p in nodes[pid].priors):
            return pid
    return None

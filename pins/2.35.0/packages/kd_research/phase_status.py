"""Default session phase_status skeleton (resume map).

Pure helpers — no I/O except optional write. Used by scaffold_session and tests.
Design: harness/design_phase_status_and_exemplars.md
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from packages.kd_research.check_core import load_json

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


PHASE_PRIMARY_ARTIFACTS: dict[str, list[str]] = {
    "phase0_swarm": ["registry/background.json"],
    "2a": ["data/sp_financials.csv"],
    "2b": ["registry/sec_filings.json"],
    "2c": ["registry/news_sentiment.json"],
    "2d": ["registry/latest_quarter.json"],
    "2e": ["registry/filing_deep_dive.json"],
    "1d_rev": ["registry/raw/oppath_rev.json"],
    "1d_ind": ["registry/raw/oppath_ind.json"],
    "1d_ol": ["registry/raw/oppath_ol.json"],
    "1d_merge": ["registry/operating_path_brief.json"],
    "4": ["registry/technical.json"],
    "5": ["data/valuation_model.json"],
    "12": ["registry/tsr_validation.json"],
    "phase25_swarm": ["registry/risk_bridge.json"],
    "6": ["charts"],
    "7": ["reports"],
    "8": ["reports"],
    "11": ["reports"],
    "13": ["registry/audit.json"],
}

HANDOFF_SECTION_PATTERNS = (
    re.compile(r"(?im)^\s*#+\s*what i did\b"),
    re.compile(r"(?im)^\s*#+\s*data issues"),
    re.compile(r"(?im)^\s*#+\s*assumptions"),
    re.compile(r"(?im)^\s*#+\s*for downstream"),
)


def check_handoff_headers(text: str) -> list[str]:
    """Return names of missing handoff section headers (empty = all present)."""
    missing: list[str] = []
    labels = ("What I did", "Data issues", "Assumptions", "For downstream")
    for label, pat in zip(labels, HANDOFF_SECTION_PATTERNS):
        if not pat.search(text):
            missing.append(label)
    return missing


def primary_artifact_exists(session: Path, agent_id: str) -> bool | None:
    """True/False if agent has a known primary artifact; None if unmapped."""
    rels = PHASE_PRIMARY_ARTIFACTS.get(agent_id)
    if not rels:
        return None
    found = False
    for rel in rels:
        if rel == "charts":
            d = session / "charts"
            if d.is_dir() and any(d.iterdir()):
                found = True
                break
            continue
        if rel == "reports":
            d = session / "reports"
            if d.is_dir() and any(d.glob("*.md")):
                found = True
                break
            continue
        if (session / rel).exists():
            found = True
            break
    if not found:
        return False
    if agent_id == "5":
        from packages.kd_research.decision import session_is_wave2_runtime

        if session_is_wave2_runtime(session) and not (
            session / "registry" / "decision.json"
        ).exists():
            return False
    return True


def check_phase_status_disk(session: Path, data: dict[str, Any]) -> list[tuple[str, str, str]]:
    """phase_status complete ⇒ artifacts; lag WARN when files exist but agent pending."""
    out: list[tuple[str, str, str]] = []
    phases = data.get("phases")
    if not isinstance(phases, list):
        return out

    for ph in phases:
        if not isinstance(ph, dict):
            continue
        phase_id = ph.get("phase_id")
        phase_st = ph.get("status")
        agents = ph.get("agents") or []
        if not isinstance(agents, list):
            continue

        if phase_st == "complete":
            for ag in agents:
                if not isinstance(ag, dict):
                    continue
                aid = ag.get("agent_id")
                if not aid or ag.get("status") == "skipped":
                    continue
                exists = primary_artifact_exists(session, str(aid))
                if exists is False:
                    out.append(
                        (
                            "FAIL",
                            "phase_status complete artifact",
                            f"phase {phase_id} complete but agent {aid} primary artifact missing",
                        )
                    )
                handoff = ag.get("handoff")
                if isinstance(handoff, str) and handoff.strip():
                    hp = session / handoff if not Path(handoff).is_absolute() else Path(handoff)
                    if not hp.exists():
                        hp2 = session / handoff.lstrip("./")
                        hp = hp2 if hp2.exists() else hp
                    if not hp.exists():
                        out.append(
                            (
                                "FAIL",
                                "phase_status complete handoff",
                                f"phase {phase_id} agent {aid} handoff path missing: {handoff}",
                            )
                        )

        for ag in agents:
            if not isinstance(ag, dict):
                continue
            aid = ag.get("agent_id")
            st = ag.get("status")
            if not aid or st not in ("pending", "in_progress"):
                continue
            if primary_artifact_exists(session, str(aid)) is True:
                out.append(
                    (
                        "WARN",
                        "phase_status lag",
                        f"agent {aid} status={st} but primary artifact exists on disk",
                    )
                )

    if not any(c.startswith("phase_status") for _, c, _ in out):
        out.append(("PASS", "phase_status disk", "no complete/lag issues"))
    return out


def _phase0_min_raws(session: Path) -> int:
    """Coverage floor: 1 before 2.30; 3 standard / 4 deep-or-medium-high on >= 2.30."""
    from packages.kd_research.annuals import load_run_manifest_version, parse_semver

    parsed = parse_semver(load_run_manifest_version(session))
    if parsed is None or parsed < (2, 30, 0):
        return 1
    mc, _ = load_json(session / "registry" / "market_context.json")
    brief, _ = load_json(session / "registry" / "research_brief.json")
    intensity = ""
    depth = ""
    if isinstance(mc, dict):
        intensity = str(mc.get("intensity") or "").strip().lower()
    if isinstance(brief, dict):
        depth = str(brief.get("research_depth") or "").strip().lower()
    if depth == "deep" or intensity in ("medium", "high"):
        return 4
    return 3


def check_phase0_coverage(session: Path) -> list[tuple[str, str, str]]:
    """Raw + merged background presence for Phase 0 complete."""
    out: list[tuple[str, str, str]] = []
    min_n = _phase0_min_raws(session)
    bg, err = load_json(session / "registry" / "background.json")
    if err:
        out.append(("FAIL", "background.json", err))
    else:
        rounds = bg.get("rounds") if isinstance(bg, dict) else None
        n = len(rounds) if isinstance(rounds, list) else 0
        if n < min_n:
            out.append(("FAIL", "background.rounds", f"{n} round(s); need ≥{min_n}"))
        else:
            out.append(("PASS", "background.rounds", f"{n} round(s)"))

    raw = (
        list((session / "registry" / "raw").glob("phase0_*.json"))
        if (session / "registry" / "raw").is_dir()
        else []
    )
    if len(raw) < min_n:
        out.append(
            (
                "FAIL",
                "phase0_raw_count",
                f"{len(raw)} registry/raw/phase0_*.json; need ≥{min_n}",
            )
        )
    else:
        out.append(("PASS", "phase0_raw_count", f"{len(raw)} file(s)"))

    missing_rel = 0
    checked = 0
    for p in raw:
        data, e = load_json(p)
        if e or not isinstance(data, dict):
            continue
        checked += 1
        rel = data.get("downstream_relevance")
        if not (isinstance(rel, str) and rel.strip()):
            missing_rel += 1
    if checked:
        if missing_rel == checked:
            out.append(
                (
                    "FAIL",
                    "phase0_downstream_relevance",
                    f"all {checked} raw returns missing non-empty downstream_relevance",
                )
            )
        elif missing_rel:
            out.append(
                (
                    "WARN",
                    "phase0_downstream_relevance",
                    f"{missing_rel}/{checked} raw returns missing downstream_relevance",
                )
            )
        else:
            out.append(("PASS", "phase0_downstream_relevance", f"{checked} raw(s) tagged"))

    return out

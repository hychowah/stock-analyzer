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
from packages.kd_research.phase_graph import (  # re-export
    PHASE_AGENTS,
    PHASE_IDS,
    PHASE_PRIMARY_ARTIFACTS,
)

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


def check_research_brief(session: Path) -> list[tuple[str, str, str]]:
    """Optional research_brief: SKIPPED if absent; validate when present."""
    from packages.kd_research.check_core import SCHEMAS, jsonschema

    rel = "registry/research_brief.json"
    p = session / rel
    if not p.exists():
        return [
            (
                "SKIPPED",
                "research_brief",
                "file absent (legacy OK; new sessions write research_brief.json before Phase 0)",
            )
        ]
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return [("FAIL", "research_brief parse", str(e))]

    required = [
        "ticker",
        "session_date",
        "company_name",
        "investment_objective",
        "must_answer_questions",
        "peers",
        "benchmarks",
        "currency",
        "research_depth",
        "rationale",
    ]
    missing = [k for k in required if k not in data]
    if missing:
        return [("FAIL", "research_brief keys", f"missing {missing}")]

    depth = data.get("research_depth")
    if depth not in ("standard", "deep"):
        return [("FAIL", "research_brief research_depth", f"invalid research_depth={depth!r}")]

    questions = data.get("must_answer_questions")
    if not (isinstance(questions, list) and len(questions) >= 3):
        return [("FAIL", "research_brief must_answer_questions", "need >=3 questions")]

    rationale = data.get("rationale")
    if not (isinstance(rationale, str) and len(rationale.strip()) >= 20):
        return [("FAIL", "research_brief rationale", "need non-empty rationale (>=20 chars)")]

    out: list[tuple[str, str, str]] = []
    schema_path = SCHEMAS / "research_brief.schema.json"
    if jsonschema is not None and schema_path.exists():
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        errors = sorted(
            jsonschema.Draft7Validator(schema).iter_errors(data),
            key=lambda e: list(e.path),
        )
        if errors:
            msgs = [
                f"{'/'.join(str(x) for x in e.path) or '<root>'}: {e.message}" for e in errors[:5]
            ]
            return [("FAIL", "schema: research_brief", "; ".join(msgs))]
        out.append(("PASS", "schema: research_brief", ""))
    else:
        reason = (
            "jsonschema not installed (run with vendor/mcp/yfinance-market-mcp/.venv/bin/python)"
            if jsonschema is None
            else f"no schema {schema_path.name}"
        )
        out.append(("SKIPPED", "schema: research_brief", reason))
    out.append(
        ("PASS", "research_brief content", f"depth={depth} questions={len(questions)}")
    )
    return out


def check_phase_status_session(session: Path) -> list[tuple[str, str, str]]:
    """Optional phase_status: SKIPPED if absent; validate when present."""
    from packages.kd_research.check_core import SCHEMAS, jsonschema
    from packages.kd_research.phase_graph import check_phase_status_graph, designed_phase_ids

    designed = designed_phase_ids(session)
    rel = "registry/phase_status.json"
    p = session / rel
    if not p.exists():
        return [
            (
                "SKIPPED",
                "phase_status",
                "file absent (legacy/pre-cutover OK; new sessions scaffold phase_status.json)",
            )
        ]
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return [("FAIL", "phase_status parse", str(e))]

    required = [
        "ticker",
        "session_date",
        "schema_version",
        "updated_at",
        "current_phase",
        "phases",
    ]
    missing = [k for k in required if k not in data]
    if missing:
        return [("FAIL", "phase_status keys", f"missing {missing}")]

    if not isinstance(data.get("schema_version"), int) or data["schema_version"] < 1:
        return [
            (
                "FAIL",
                "phase_status schema_version",
                f"need int >= 1, got {data.get('schema_version')!r}",
            )
        ]

    current = data.get("current_phase")
    if current not in PHASE_IDS:
        return [("FAIL", "phase_status current_phase", f"invalid current_phase={current!r}")]

    phases = data.get("phases")
    if not isinstance(phases, list) or len(phases) < 1:
        return [("FAIL", "phase_status phases", "need non-empty phases[]")]

    seen_ids: list[str] = []
    allowed_status = {"pending", "in_progress", "complete", "failed", "blocked", "skipped"}
    for i, ph in enumerate(phases):
        if not isinstance(ph, dict):
            return [("FAIL", "phase_status phases shape", f"phases[{i}] not object")]
        pid = ph.get("phase_id")
        if pid not in PHASE_IDS:
            return [("FAIL", "phase_status phase_id", f"phases[{i}].phase_id={pid!r} invalid")]
        seen_ids.append(pid)
        st = ph.get("status")
        if st not in allowed_status:
            return [("FAIL", "phase_status phase status", f"phases[{i}].status={st!r}")]
        agents = ph.get("agents")
        if not isinstance(agents, list):
            return [("FAIL", "phase_status agents", f"phases[{i}].agents must be array")]
        for j, ag in enumerate(agents):
            if not isinstance(ag, dict) or not ag.get("agent_id"):
                return [
                    (
                        "FAIL",
                        "phase_status agent row",
                        f"phases[{i}].agents[{j}] need agent_id",
                    )
                ]
            if ag.get("status") not in allowed_status:
                return [
                    (
                        "FAIL",
                        "phase_status agent status",
                        f"phases[{i}].agents[{j}].status={ag.get('status')!r}",
                    )
                ]

    missing_phases = [pid for pid in designed if pid not in seen_ids]
    if missing_phases:
        return [("FAIL", "phase_status phase coverage", f"missing phase_id(s): {missing_phases}")]

    out: list[tuple[str, str, str]] = []
    schema_path = SCHEMAS / "phase_status.schema.json"
    if jsonschema is not None and schema_path.exists():
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        errors = sorted(
            jsonschema.Draft7Validator(schema).iter_errors(data),
            key=lambda e: list(e.path),
        )
        if errors:
            msgs = [
                f"{'/'.join(str(x) for x in e.path) or '<root>'}: {e.message}" for e in errors[:5]
            ]
            return [("FAIL", "schema: phase_status", "; ".join(msgs))]
        out.append(("PASS", "schema: phase_status", ""))
    else:
        reason = (
            "jsonschema not installed (run with vendor/mcp/yfinance-market-mcp/.venv/bin/python)"
            if jsonschema is None
            else f"no schema {schema_path.name}"
        )
        out.append(("SKIPPED", "schema: phase_status", reason))

    out.append(
        (
            "PASS",
            "phase_status content",
            f"current_phase={current} phases={len(phases)} schema_version={data['schema_version']}",
        )
    )
    out.extend(check_phase_status_disk(session, data))
    out.extend(check_phase_status_graph(session))
    return out


HANDOFF_MIN_BYTES = 300


def check_handoffs(session: Path) -> list[tuple[str, str, str]]:
    from packages.kd_research.phase_graph import graph_for_session

    out: list[tuple[str, str, str]] = []
    d = session / "registry/handoffs"
    if not d.is_dir():
        return [("FAIL", "handoffs", "registry/handoffs/ missing — every agent must write one")]
    specs: list[tuple[str, list[str]]] = []
    for node in graph_for_session(session).values():
        for agent, patterns in node.handoff_globs:
            specs.append((agent, list(patterns)))
    for agent, patterns in specs:
        matches: list[Path] = []
        for pat in patterns:
            matches.extend(d.glob(pat))
        matches = sorted({p.resolve() for p in matches}, key=lambda p: p.name)
        if not matches:
            out.append(("FAIL", f"handoff: agent {agent}", "file missing"))
            continue
        best = max(matches, key=lambda p: p.stat().st_size)
        if best.stat().st_size < HANDOFF_MIN_BYTES:
            out.append(
                ("FAIL", f"handoff: agent {agent}", f"< {HANDOFF_MIN_BYTES} bytes (stub?)")
            )
            continue
        out.append(("PASS", f"handoff: agent {agent}", best.name))
        try:
            text = best.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        missing = check_handoff_headers(text)
        if missing:
            out.append(
                (
                    "WARN",
                    f"handoff headers: {agent}",
                    f"missing sections: {', '.join(missing)}",
                )
            )
    return out


def check_audit_verdict(session: Path) -> list[tuple[str, str, str]]:
    p = session / "registry/audit.json"
    if not p.exists():
        return [("FAIL", "audit verdict", "audit.json missing — Phase 5 not run")]
    try:
        verdict = json.loads(p.read_text(encoding="utf-8")).get("verdict")
    except Exception as e:  # noqa: BLE001
        return [("FAIL", "audit verdict", f"unparseable: {e}")]
    if verdict == "PASS":
        return [("PASS", "audit verdict", "PASS")]
    return [
        (
            "FAIL",
            "audit verdict",
            f"{verdict!r} — session not complete until audit passes or issues are waived in the README",
        )
    ]

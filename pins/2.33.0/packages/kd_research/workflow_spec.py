"""Dump this process's phase graph + prompt slices as JSON.

Mode B consumes the dump (via Pin.workflow_spec / agent_prompt). Do not
copy entry_checks() control flow — extra rows come from the same SINCE
constants those helpers already use.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from packages.kd_research.annuals import parse_semver
from packages.kd_research.cash_quality import WAVE7_SINCE
from packages.kd_research.gates import PHASE_ENTRY_OPTIONAL, PHASE_ENTRY_REQUIRED
from packages.kd_research.library import BIND_REL, LIBRARY_SINCE
from packages.kd_research.operating_path import BRIEF_REL, OPPATH_SINCE
from packages.kd_research.paths import PROJECT_ROOT
from packages.kd_research.phase_status import PHASE_AGENTS
from packages.kd_research.provenance import load_harness_identity
from packages.kd_research.spawn_gate import SPAWN_SINCE, SPECIALIST_ARTIFACTS
from packages.kd_research.street_bind import STREET_SINCE

# Grammar for harness/agent_prompts.md (longest-id first when resolving).
AGENT_HEADING_RE = re.compile(
    r"^### Agent ([A-Za-z0-9][A-Za-z0-9._-]*)(?:\s+[—-].*)?\s*$"
)
STREET_REL = "registry/street_estimates.json"
PRICE_SNAPSHOT_REL = "data/price_snapshot.json"

# Display overlay for the /harness page model. Not spawn-gate evidence.
# SPECIALIST_ARTIFACTS stays the spawn/complete set.
PHASE_DISPLAY: dict[str, dict[str, str]] = {
    "orch": {
        "label": "Classify & brief",
        "stage": "setup",
        "purpose": "Sector, market context, research brief, library bind",
    },
    "0": {
        "label": "Background",
        "stage": "gather",
        "purpose": "Business model, open questions, bear case",
    },
    "1_parallel": {
        "label": "Source facts",
        "stage": "gather",
        "purpose": "Financials, filings, and news in parallel",
    },
    "1b": {
        "label": "Latest quarter",
        "stage": "gather",
        "purpose": "Print overrides for valuation",
    },
    "1c": {
        "label": "Deep dive",
        "stage": "gather",
        "purpose": "Footnotes, strategy arc, management scorecard",
    },
    "1d": {
        "label": "Operating path",
        "stage": "gather",
        "purpose": "Growth, industry, leverage → brief for valuation",
    },
    "2_parallel": {
        "label": "Valuation",
        "stage": "decide",
        "purpose": "Technical, DCF, and TSR in parallel",
    },
    "2_5": {
        "label": "Stress",
        "stage": "decide",
        "purpose": "Risk bridge and scenario haircuts",
    },
    "3": {
        "label": "Charts",
        "stage": "publish",
        "purpose": "Visuals for the report pack",
    },
    "4_parallel": {
        "label": "Reports",
        "stage": "publish",
        "purpose": "Fundamental, technical, and README",
    },
    "5": {
        "label": "Audit",
        "stage": "publish",
        "purpose": "Process completeness gate",
    },
    "done": {
        "label": "Done",
        "stage": "publish",
        "purpose": "Catalog snapshot after audit PASS",
    },
}

# Writes the visualizer must show that are not spawn-gated specialist artifacts.
DISPLAY_WRITES: dict[str, tuple[str, ...]] = {
    "orchestrator": (
        "registry/sector_config.json",
        "registry/market_context.json",
        "registry/research_brief.json",
        BIND_REL,
        PRICE_SNAPSHOT_REL,
    ),
    "2a": (
        "data/peer_comparison.csv",
        STREET_REL,
        "registry/data_fetch_log.json",
    ),
}

AGENT_LABELS: dict[str, str] = {
    "orchestrator": "Orchestrator",
    "phase0_swarm": "Background swarm",
    "2d": "Latest quarter",
    "phase25_swarm": "Stress swarm",
    "6": "Charts",
    "13": "Audit",
}

TITLE_RE = re.compile(
    r"^###\s+Agent\s+([A-Za-z0-9][A-Za-z0-9._-]*)"
    r"(?:\s+[—-]\s*(.+?))?"
    r"(?:\s+\(`([^`]+)`\))?\s*$"
)


def _label(tup: tuple[int, int, int]) -> str:
    return f"{tup[0]}.{tup[1]}.{tup[2]}"


def _agent_writes(aid: str) -> list[str]:
    out: list[str] = []
    for path in (*SPECIALIST_ARTIFACTS.get(aid, ()), *DISPLAY_WRITES.get(aid, ())):
        if isinstance(path, str) and path not in out:
            out.append(path)
    return out


def _agent_display(title: str, aid: str) -> tuple[str, str | None]:
    m = TITLE_RE.match((title or "").strip())
    parsed_name = (m.group(2) or "").strip() if m else ""
    spawn_role = (m.group(3) or "").strip() if m else ""
    if parsed_name:
        label = parsed_name[0].upper() + parsed_name[1:] if parsed_name[0].islower() else parsed_name
    else:
        label = AGENT_LABELS.get(aid, f"Agent {aid}" if aid else "Agent")
    return label, (spawn_role or None)


def _phase_display(pid: str) -> dict[str, str]:
    known = PHASE_DISPLAY.get(pid)
    if known:
        return dict(known)
    return {"label": pid, "stage": "other", "purpose": ""}


def parse_agent_prompts(text: str) -> dict[str, dict[str, str]]:
    """Split agent_prompts.md on ### Agent <id> headings.

    Conventions = the block before the first heading. Ids are the first
    token after 'Agent' (2e-year is one id).
    """
    lines = text.splitlines()
    headings: list[tuple[int, str, str]] = []
    for i, line in enumerate(lines):
        m = AGENT_HEADING_RE.match(line)
        if m:
            aid = m.group(1)
            title = line.strip()
            headings.append((i, aid, title))
    out: dict[str, dict[str, str]] = {}
    first = headings[0][0] if headings else len(lines)
    conventions = "\n".join(lines[:first]).strip()
    out["_conventions"] = {"id": "_conventions", "title": "Conventions", "body": conventions}
    for idx, (start, aid, title) in enumerate(headings):
        end = headings[idx + 1][0] if idx + 1 < len(headings) else len(lines)
        body = "\n".join(lines[start:end]).strip()
        # Longest-id-first: if a shorter id was already stored, keep the longer key
        # as its own entry; first-token regex already yields 2e-year vs 2e.
        out[aid] = {"id": aid, "title": title, "body": body}
    return out


def missing_prompt_ids(text: str | None = None) -> list[str]:
    """PHASE_AGENTS ids that have no ### Agent <id> heading."""
    raw = text
    if raw is None:
        raw = (PROJECT_ROOT / "harness" / "agent_prompts.md").read_text(encoding="utf-8")
    parsed = parse_agent_prompts(raw)
    missing: list[str] = []
    for _pid, aids in PHASE_AGENTS:
        for aid in aids:
            if aid not in parsed:
                missing.append(aid)
    return missing


def build_workflow_spec(*, root: Path | None = None) -> dict[str, Any]:
    base = root or PROJECT_ROOT
    ident = load_harness_identity(base)
    version = ident.get("harness_version") or ""
    parsed = parse_semver(version)
    prompts_path = base / "harness" / "agent_prompts.md"
    prompt_text = prompts_path.read_text(encoding="utf-8") if prompts_path.is_file() else ""
    prompts = parse_agent_prompts(prompt_text) if prompt_text else {}

    phases: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    def add_entry(entry: list[dict[str, Any]], pid: str, path: str, *, required: bool, since: str | None) -> None:
        row: dict[str, Any] = {"path": path, "required": required}
        if since:
            row["since"] = since
        entry.append(row)
        edge: dict[str, Any] = {"from": path, "to": pid, "kind": "entry"}
        if since:
            edge["since"] = since
        edges.append(edge)

    for pid, aids in PHASE_AGENTS:
        agents: list[dict[str, Any]] = []
        for aid in aids:
            writes = _agent_writes(aid)
            slice_ = prompts.get(aid) or {}
            title = slice_.get("title") or f"### Agent {aid}"
            label, spawn_role = _agent_display(title, aid)
            agents.append(
                {
                    "id": aid,
                    "title": title,
                    "label": label,
                    "spawn_role": spawn_role,
                    "writes": writes,
                    "prompt_present": aid in prompts,
                }
            )
            for w in writes:
                if "*" in w:
                    continue
                edges.append({"from": aid, "to": w, "kind": "write"})
        entry: list[dict[str, Any]] = []
        for rel in PHASE_ENTRY_REQUIRED.get(pid, []):
            add_entry(entry, pid, rel, required=True, since=None)
        for rel in PHASE_ENTRY_OPTIONAL.get(pid, []):
            add_entry(entry, pid, rel, required=False, since=None)
        if pid in {"1_parallel"} and parsed is not None and parsed >= LIBRARY_SINCE:
            add_entry(entry, pid, BIND_REL, required=True, since=_label(LIBRARY_SINCE))
        if pid == "2_parallel" and parsed is not None and parsed >= OPPATH_SINCE:
            add_entry(entry, pid, BRIEF_REL, required=True, since=_label(OPPATH_SINCE))
        if pid == "2_parallel" and parsed is not None and parsed >= STREET_SINCE:
            add_entry(entry, pid, STREET_REL, required=False, since=_label(STREET_SINCE))
        if pid == "2_parallel":
            add_entry(entry, pid, PRICE_SNAPSHOT_REL, required=True, since=None)
        disp = _phase_display(pid)
        phases.append(
            {
                "id": pid,
                "label": disp["label"],
                "purpose": disp["purpose"],
                "stage": disp["stage"],
                "agents": agents,
                "entry": entry,
            }
        )

    annotations = [
        {
            "id": "5b",
            "phase": "2_5",
            "agent": "orchestrator",
            "note": "After 2.5, lead reopens decision.json; do not spawn subagent 5 in 2_5.",
        },
        {
            "id": "2e-year",
            "phase": "1c",
            "agent": "2e-year",
            "note": "One year-reader spawn per annual; not a PHASE_AGENTS row.",
        },
        {
            "id": "price_snapshot",
            "before": "2_parallel",
            "path": PRICE_SNAPSHOT_REL,
            "note": "Orchestrator freeze, price-only, before Phase 2.",
        },
        {
            "id": "bind_library",
            "before": "2b",
            "path": BIND_REL,
            "since": _label(LIBRARY_SINCE),
        },
        {
            "id": "spawn_or_abandon",
            "since": _label(SPAWN_SINCE),
            "note": "Specialists must be spawn_subagent; launch failure abandons.",
        },
        {
            "id": "cash_quality",
            "phase": "1b",
            "since": _label(WAVE7_SINCE),
        },
    ]

    conventions = str((prompts.get("_conventions") or {}).get("body") or "")
    return {
        "harness_version": version,
        "harness_spec": ident.get("harness_spec"),
        "phases": phases,
        "edges": edges,
        "annotations": annotations,
        "conventions": conventions,
        "conventions_present": bool(conventions),
        "missing_prompt_ids": missing_prompt_ids(prompt_text) if prompt_text else [
            aid for _p, aids in PHASE_AGENTS for aid in aids
        ],
    }


def agent_prompt_payload(agent_id: str, *, root: Path | None = None) -> dict[str, Any]:
    base = root or PROJECT_ROOT
    text = (base / "harness" / "agent_prompts.md").read_text(encoding="utf-8")
    parsed = parse_agent_prompts(text)
    conventions = (parsed.get("_conventions") or {}).get("body") or ""
    # Longest-id-first: prefer exact, then longest prefix match only if needed.
    slice_ = parsed.get(agent_id)
    if slice_ is None:
        candidates = sorted(
            (k for k in parsed if k != "_conventions"),
            key=len,
            reverse=True,
        )
        for k in candidates:
            if agent_id == k:
                slice_ = parsed[k]
                break
    if slice_ is None:
        return {
            "id": agent_id,
            "found": False,
            "title": None,
            "body": "",
            "conventions": conventions,
        }
    return {
        "id": agent_id,
        "found": True,
        "title": slice_.get("title"),
        "body": slice_.get("body") or "",
        "conventions": conventions,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--agent", help="Dump one agent prompt slice instead of the full spec")
    args = ap.parse_args(argv)
    if args.agent:
        json.dump(agent_prompt_payload(args.agent), sys.stdout, indent=2)
    else:
        json.dump(build_workflow_spec(), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

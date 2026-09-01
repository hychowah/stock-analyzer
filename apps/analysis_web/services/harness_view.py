"""Page model for /harness.

Pin.workflow_spec / agent_prompt stay mechanical JSON. This module is the
only place that turns that dump into display keys the template and JS may
read. PHASE_META is a UI overlay for known phase ids, not Mode A law.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from apps.analysis_web.services.render_markdown import render_markdown

STAGE_ORDER: tuple[tuple[str, str], ...] = (
    ("setup", "Setup"),
    ("gather", "Gather"),
    ("decide", "Decide"),
    ("publish", "Publish"),
    ("other", "Other"),
)

# UI overlay for known phase ids. Unknown ids use stage "other" and an empty purpose.
PHASE_META: dict[str, dict[str, str]] = {
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

# Only headings with no em-dash name. Titled agents use parse_agent_title.
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
ROLE_RE = re.compile(r"^Role:\s*(.+)$", re.MULTILINE)
CONV_ITEM_RE = re.compile(r"^- \*\*([^*]+)\*\*:?\s*(.*)$")
CONV_HEADING_RE = re.compile(r"Conventions for all agents", re.IGNORECASE)

NoteTarget = Literal["page", "phase", "agent"]


def file_chip(path: str) -> dict[str, str]:
    raw = str(path or "").replace("\\", "/")
    name = raw.rsplit("/", 1)[-1] if raw else ""
    folder = raw[: -len(name)].rstrip("/") if name and "/" in raw else ""
    # Globs are the chip label (charts/*.png), not the last segment (*.png).
    label = raw if "*" in raw else (name or raw)
    return {"path": raw, "name": name or raw, "folder": folder, "label": label}


def parse_agent_title(title: str | None, agent_id: str) -> dict[str, str | None]:
    aid = str(agent_id or "").strip()
    m = TITLE_RE.match(str(title or "").strip())
    parsed_name = (m.group(2) or "").strip() if m else ""
    spawn_role = (m.group(3) or "").strip() if m else ""
    if parsed_name:
        label = parsed_name[0].upper() + parsed_name[1:] if parsed_name[0].islower() else parsed_name
    else:
        label = AGENT_LABELS.get(aid, f"Agent {aid}" if aid else "Agent")
    return {"id": aid, "label": label, "spawn_role": spawn_role or None}


def _summary(text: str, limit: int = 280) -> str:
    parts = re.split(r"\n\s*\n", (text or "").strip())
    for part in parts:
        p = part.strip()
        if not p or p.startswith("#") or p.startswith("|") or p.startswith("```"):
            continue
        p = re.sub(r"\*\*([^*]+)\*\*", r"\1", p)
        p = re.sub(r"`([^`]+)`", r"\1", p)
        p = re.sub(r"\s+", " ", p).strip()
        if len(p) <= 3:
            continue
        if len(p) > limit:
            cut = p[: limit - 1].rsplit(" ", 1)
            return (cut[0] if cut else p[: limit - 1]) + "…"
        return p
    return ""


def _split_fence(text: str) -> tuple[str, str, str]:
    lines = (text or "").splitlines()
    start = None
    end = None
    for i, line in enumerate(lines):
        if line.strip().startswith("```"):
            if start is None:
                start = i
            else:
                end = i
                break
    if start is None or end is None:
        return (text or "").strip(), "", ""
    briefing = "\n".join(lines[:start]).strip()
    template = "\n".join(lines[start + 1 : end]).strip()
    follow_on = "\n".join(lines[end + 1 :]).strip()
    return briefing, template, follow_on


def structure_prompt(body: str) -> dict[str, Any]:
    lines = (body or "").splitlines()
    if lines and lines[0].startswith("### "):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines.pop(0)
    text = "\n".join(lines).strip()
    briefing, template, follow_on = _split_fence(text)
    haystack = "\n".join(part for part in (briefing, template) if part)
    role_m = ROLE_RE.search(haystack)
    sections: list[dict[str, Any]] = []
    if briefing:
        sections.append(
            {"id": "briefing", "label": "Briefing", "kind": "prose", "html": render_markdown(briefing)}
        )
    if template:
        sections.append(
            {
                "id": "template",
                "label": "Working template",
                "kind": "template",
                "html": render_markdown("```\n" + template + "\n```"),
            }
        )
    if follow_on:
        sections.append(
            {
                "id": "follow_on",
                "label": "Follow-on",
                "kind": "prose",
                "html": render_markdown(follow_on),
            }
        )
    if not sections:
        sections.append(
            {"id": "body", "label": "Prompt", "kind": "prose", "html": render_markdown(text)}
        )
    return {
        "summary": _summary(briefing or text),
        "role_line": (role_m.group(1).strip() if role_m else ""),
        "sections": sections,
    }


def convention_items(md: str) -> list[dict[str, str]]:
    """Parse `- **Title**:` bullets after the shared conventions heading."""
    text = md or ""
    marker = CONV_HEADING_RE.search(text)
    if marker:
        text = text[marker.end() :]
        text = re.sub(r"^:?\*?\*?\s*", "", text, count=1)
    items: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in text.splitlines():
        m = CONV_ITEM_RE.match(line)
        if m:
            if current:
                items.append(current)
            current = {"title": m.group(1).strip(), "body": m.group(2).strip()}
            continue
        if current and (line.startswith("  ") or line.startswith("\t")):
            current["body"] = (current["body"] + "\n" + line).strip()
    if current:
        items.append(current)
    return [
        {"title": item["title"], "html": render_markdown(item.get("body") or "")}
        for item in items
    ]


def structure_prompt_payload(payload: dict[str, Any]) -> dict[str, Any]:
    body = str(payload.get("body") or "")
    conventions = str(payload.get("conventions") or "")
    agent_id = str(payload.get("id") or "")
    parsed = parse_agent_title(payload.get("title"), agent_id)
    structured = structure_prompt(body)
    items = convention_items(conventions)
    conv_html = render_markdown(conventions)
    out = dict(payload)
    out["label"] = parsed["label"]
    out["spawn_role"] = parsed["spawn_role"]
    out["summary"] = structured["summary"]
    out["role_line"] = structured["role_line"]
    out["sections"] = structured["sections"]
    out["body_html"] = render_markdown(body)
    out["conventions_html"] = conv_html
    out["conventions_items"] = items
    return out


def _phase_meta(phase_id: str) -> dict[str, str]:
    known = PHASE_META.get(phase_id)
    if known:
        return dict(known)
    return {"label": phase_id, "stage": "other", "purpose": ""}


def _note_text(ann: dict[str, Any]) -> str:
    note = str(ann.get("note") or "").strip()
    if note:
        return note
    parts: list[str] = []
    ident = str(ann.get("id") or "").strip()
    if ident:
        parts.append(ident)
    path = str(ann.get("path") or "").strip()
    if path:
        parts.append(file_chip(path)["label"])
    since = str(ann.get("since") or "").strip()
    if since:
        parts.append(f"≥{since}")
    return " · ".join(parts)


def _note_record(ann: dict[str, Any]) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "id": str(ann.get("id") or ""),
        "text": _note_text(ann),
    }
    since = str(ann.get("since") or "").strip()
    if since:
        rec["since"] = since
    path = str(ann.get("path") or "").strip()
    if path:
        rec["path"] = path
    return rec


def _place_annotation(
    ann: dict[str, Any],
    *,
    phase_ids: set[str],
    agent_ids: set[str],
) -> tuple[NoteTarget, str | None]:
    """Hide annotation-schema oddities from the template.

    `phase` → that phase. `before` that matches a phase id → that phase.
    `before` that matches an agent id → that agent. Otherwise page-level.
    """
    phase = str(ann.get("phase") or "").strip()
    if phase:
        return "phase", phase
    before = str(ann.get("before") or "").strip()
    if not before:
        return "page", None
    if before in phase_ids:
        return "phase", before
    if before in agent_ids:
        return "agent", before
    return "page", None


def _producers(agents: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for ag in agents:
        aid = str(ag.get("id") or "")
        label = str(ag.get("label") or aid)
        for chip in ag.get("write_chips") or []:
            path = str(chip.get("path") or "")
            if not path or "*" in path:
                continue
            out[path] = {"id": aid, "label": label}
    return out


def _need_chip(
    row: dict[str, Any],
    producers: dict[str, dict[str, str]],
) -> dict[str, Any]:
    chip = file_chip(str(row.get("path") or ""))
    producer = producers.get(chip["path"])
    out: dict[str, Any] = {
        "path": chip["path"],
        "name": chip["name"],
        "folder": chip["folder"],
        "label": chip["label"],
        "required": bool(row.get("required")),
    }
    since = row.get("since")
    if since:
        out["since"] = str(since)
    if producer:
        out["producer"] = producer["id"]
        out["producer_label"] = producer["label"]
    return out


def harness_page_model(spec: dict[str, Any], *, conventions: str = "") -> dict[str, Any]:
    """Display-only tree for /harness. Callers must not need spec.edges."""
    raw_phases = [p for p in (spec.get("phases") or []) if isinstance(p, dict)]
    phase_ids = {str(p.get("id") or "") for p in raw_phases if p.get("id")}
    agent_ids: set[str] = set()
    for phase in raw_phases:
        for ag in phase.get("agents") or []:
            if isinstance(ag, dict) and ag.get("id"):
                agent_ids.add(str(ag["id"]))

    built_phases: list[dict[str, Any]] = []
    all_agents: list[dict[str, Any]] = []
    for phase in raw_phases:
        pid = str(phase.get("id") or "")
        meta = _phase_meta(pid)
        agents: list[dict[str, Any]] = []
        write_chips: list[dict[str, str]] = []
        for ag in phase.get("agents") or []:
            if not isinstance(ag, dict):
                continue
            aid = str(ag.get("id") or "")
            parsed = parse_agent_title(ag.get("title"), aid)
            chips = [file_chip(w) for w in (ag.get("writes") or []) if isinstance(w, str)]
            write_chips.extend(chips)
            row = {
                "id": aid,
                "label": parsed["label"],
                "spawn_role": parsed["spawn_role"],
                "prompt_present": bool(ag.get("prompt_present")),
                "write_chips": chips,
                "primary_write": chips[0] if chips else None,
                "notes": [],
            }
            agents.append(row)
            all_agents.append(row)
        built_phases.append(
            {
                "id": pid,
                "label": meta["label"],
                "purpose": meta["purpose"],
                "stage": meta["stage"],
                "agents": agents,
                "writes": write_chips,
                "needs": [],
                "notes": [],
            }
        )

    producers = _producers(all_agents)
    by_id = {p["id"]: p for p in built_phases}
    agent_by_id = {a["id"]: a for a in all_agents}

    for phase, raw in zip(built_phases, raw_phases):
        needs: list[dict[str, Any]] = []
        for row in raw.get("entry") or []:
            if isinstance(row, dict):
                needs.append(_need_chip(row, producers))
        phase["needs"] = needs

    page_notes: list[dict[str, Any]] = []
    for ann in spec.get("annotations") or []:
        if not isinstance(ann, dict):
            continue
        kind, target = _place_annotation(ann, phase_ids=phase_ids, agent_ids=agent_ids)
        rec = _note_record(ann)
        if kind == "phase" and target in by_id:
            by_id[target]["notes"].append(rec)
        elif kind == "agent" and target in agent_by_id:
            agent_by_id[target]["notes"].append(rec)
        else:
            page_notes.append(rec)

    by_stage: dict[str, list[dict[str, Any]]] = {}
    for phase in built_phases:
        by_stage.setdefault(str(phase["stage"]), []).append(phase)
    stages: list[dict[str, Any]] = []
    used: set[str] = set()
    for sid, label in STAGE_ORDER:
        group = by_stage.get(sid) or []
        if not group:
            continue
        used.add(sid)
        stages.append({"id": sid, "label": label, "phases": group})
    for sid, group in by_stage.items():
        if sid in used:
            continue
        stages.append(
            {"id": sid, "label": sid.replace("_", " ").title(), "phases": group}
        )

    items = convention_items(conventions)
    conv_html = render_markdown(conventions) if conventions else ""
    return {
        "harness_version": spec.get("harness_version"),
        "harness_spec": spec.get("harness_spec"),
        "agent_count": len(all_agents),
        "phase_count": len(built_phases),
        "notes": page_notes,
        "conventions": {"cards": items, "html": conv_html if not items else ""},
        "stages": stages,
    }

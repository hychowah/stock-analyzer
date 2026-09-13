"""Phase 1e story lock (harness >= 3.4.0).

story writes registry/narrative_bind.json (story, carrier map, evidence_hooks, stage_fit).
3p writes registry/narrative_3p.json only. Lock is verdict=PASS.
Agent 5 may not start until PASS. Map keys are story carriers, not model field names
(those are bound later via story_input_bind). Identity lives on classification.json.
"""

from __future__ import annotations

from pathlib import Path

from packages.kd_research.check_core import load_json, session_since, validate_hooks_list
from packages.kd_research.classification import CLASSIFICATION_SINCE, load_classification
from packages.kd_research.consumption import _material_fdd_keys
from packages.kd_research.operating_path import brief_path

NARRATIVE_PHASE_SINCE = CLASSIFICATION_SINCE  # 3.4.0
NARRATIVE_REL = "registry/narrative_bind.json"
NARRATIVE_3P_REL = "registry/narrative_3p.json"

STORY_CARRIERS = frozenset(
    {
        "tam",
        "share_path",
        "slice",
        "target_om",
        "tax_path",
        "sales_to_capital",
        "kc_path",
        "p_fail",
        "tv_form",
        "stable_roc_vs_kc",
    }
)
HOOK_ACTIONS = frozenset({"map", "reject"})


def bind_path(session: Path) -> Path:
    return session / NARRATIVE_REL


def review_path(session: Path) -> Path:
    return session / NARRATIVE_3P_REL


def session_enforces_narrative(session: Path) -> bool:
    if bind_path(session).is_file() and review_path(session).is_file():
        return True
    if session_since(session, NARRATIVE_PHASE_SINCE):
        return True
    return False


def _norm(value: object) -> str:
    return str(value or "").strip().lower()


def required_evidence_ids(session: Path) -> list[str]:
    """Stable finding ids 1e must map or reject. Exact `from` match, no substring."""
    ids: list[str] = []
    fdd, err = load_json(session / "registry" / "filing_deep_dive.json")
    if not err and isinstance(fdd, dict):
        for key in _material_fdd_keys(fdd):
            ids.append(f"fdd.{key}")
        if isinstance(fdd.get("strategy_arc"), dict):
            ids.append("fdd.strategy_arc")
    brief, berr = load_json(brief_path(session))
    if not berr and isinstance(brief, dict):
        ids.append("oppath.brief")
        conflicts = brief.get("conflicts")
        if isinstance(conflicts, list):
            for i, row in enumerate(conflicts):
                if not isinstance(row, dict):
                    ids.append(f"oppath.conflict.{i}")
                    continue
                name = str(row.get("id") or row.get("name") or row.get("claim_a") or i).strip()
                ids.append(f"oppath.conflict.{_norm(name) or i}")
    return ids


def check_1e_complete(session: Path) -> list[tuple[str, str, str]]:
    """Coverage before marking phase 1e complete / spawning Agent 5."""
    if not session_enforces_narrative(session) and not bind_path(session).is_file():
        return [
            (
                "SKIPPED",
                "1e",
                "legacy/slim (no narrative lock; harness_version < 3.4.0)",
            )
        ]
    out: list[tuple[str, str, str]] = []
    card, cerr = load_classification(session)
    if cerr or card is None:
        out.append(("FAIL", "1e.classification", cerr or "missing classification.json"))
        return out
    out.append(("PASS", "1e.classification", "card present"))

    bind, err = load_json(bind_path(session))
    if err or not isinstance(bind, dict):
        out.append(("FAIL", NARRATIVE_REL, err or "not an object"))
        return out
    out.append(("PASS", NARRATIVE_REL, "exists+parse"))

    story = bind.get("story") if isinstance(bind.get("story"), dict) else {}
    if len(str(story.get("paragraph") or "").strip()) < 20:
        out.append(
            (
                "FAIL",
                "1e.story",
                "story.paragraph must state the business story (>=20 chars)",
            )
        )
    if len(str(bind.get("stage_fit") or "").strip()) < 40:
        out.append(
            (
                "FAIL",
                "1e.stage_fit",
                "stage_fit must say why this paragraph matches classification.life_cycle_stage (>=40 chars)",
            )
        )

    mapping = bind.get("map")
    if not isinstance(mapping, dict) or not mapping:
        out.append(("FAIL", "1e.map", "map must bind story sentences to story carriers"))
    else:
        bad = [
            key
            for key, val in mapping.items()
            if _norm(key) not in STORY_CARRIERS or val in (None, "", [], {})
        ]
        if bad:
            out.append(
                (
                    "FAIL",
                    "1e.map",
                    f"map keys must be story carriers with sentences: {bad[:6]}",
                )
            )
        elif len(mapping) < 3:
            out.append(("FAIL", "1e.map", "map must name at least 3 story carriers"))
        else:
            out.append(("PASS", "1e.map", f"{len(mapping)} carrier(s)"))

    review, rerr = load_json(review_path(session))
    if rerr or not isinstance(review, dict):
        out.append(("FAIL", NARRATIVE_3P_REL, rerr or "not an object"))
        return out
    verdict = str(review.get("verdict") or "").strip().upper()
    if verdict != "PASS":
        out.append(
            (
                "FAIL",
                "1e.3p_verdict",
                f"narrative_3p.verdict={verdict or None!r} must be PASS",
            )
        )
    else:
        out.append(("PASS", "1e.3p_verdict", "PASS"))

    three = review.get("3p") if isinstance(review.get("3p"), dict) else review
    empty = [
        key
        for key in ("possible", "plausible", "probable")
        if not isinstance(three.get(key), list) or not three.get(key)
    ]
    if empty:
        out.append(
            (
                "FAIL",
                "1e.3p_buckets",
                f"3P critic buckets must be non-empty lists: {empty}",
            )
        )

    if review.get("fairy_tale") is True:
        out.append(
            (
                "FAIL",
                "1e.fairy_tale",
                "3P critic marked fairy_tale=true — rewrite the story; do not compute",
            )
        )
    if review.get("wrong_stage") is True:
        out.append(
            (
                "FAIL",
                "1e.wrong_stage",
                "3P critic marked wrong_stage=true — reclassify or rewrite; do not compute",
            )
        )
    if _norm(review.get("iron_triangle")) == "fail":
        out.append(
            (
                "FAIL",
                "1e.iron_triangle",
                "3P critic iron_triangle=fail — growth/risk/reinvestment inconsistent",
            )
        )

    out.extend(check_story_evidence_hooks(session))
    return out


def check_story_evidence_hooks(session: Path) -> list[tuple[str, str, str]]:
    """Each required finding id must be mapped or rejected. noted_only is illegal."""
    data, err = load_json(bind_path(session))
    if err or not isinstance(data, dict):
        return []
    needed = required_evidence_ids(session)
    hooks = data.get("evidence_hooks")
    if not needed and hooks in (None, [], {}):
        return [("PASS", "1e.evidence_hooks", "no required findings")]
    out = validate_hooks_list(
        hooks,
        check_id="1e.evidence_hooks",
        empty_detail="evidence_hooks must map or reject each material finding",
    )
    if any(r[0] == "FAIL" for r in out):
        return out
    rows = [h for h in hooks if isinstance(h, dict)] if isinstance(hooks, list) else []
    if any(_norm(h.get("action")) not in HOOK_ACTIONS for h in rows):
        return [
            (
                "FAIL",
                "1e.evidence_hooks",
                "evidence_hooks.action must be map|reject (not noted_only)",
            )
        ]
    by_from = {_norm(h.get("from")): h for h in rows}
    missing = [fid for fid in needed if _norm(fid) not in by_from]
    if missing:
        return [
            (
                "FAIL",
                "1e.evidence_hooks",
                "missing map|reject for " + ", ".join(missing[:8]),
            )
        ]
    for h in rows:
        if _norm(h.get("action")) != "map":
            continue
        key = _norm(h.get("map_key"))
        if key not in STORY_CARRIERS:
            return [
                (
                    "FAIL",
                    "1e.evidence_hooks",
                    f"map hook map_key={h.get('map_key')!r} is not a story carrier",
                )
            ]
    return [("PASS", "1e.evidence_hooks", f"{len(needed)} finding(s)")]

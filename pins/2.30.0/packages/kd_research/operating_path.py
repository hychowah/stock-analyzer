"""Phase 1d operating-path evidence: version floor and completeness helpers.

Workers write registry/raw/oppath_{rev,ind,ol}.json (gather only).
1d_merge writes registry/operating_path_brief.json.
Agent 5 consumes the brief via operating_path_hooks. No network.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from packages.kd_research.annuals import load_run_manifest_version, parse_semver

# New-runtime floor: sessions stamped >= this must produce the 1d brief.
OPPATH_SINCE = (2, 6, 0)

WORKER_STEMS: tuple[str, ...] = ("rev", "ind", "ol")
WORKER_RELS: tuple[str, ...] = tuple(f"registry/raw/oppath_{s}.json" for s in WORKER_STEMS)
BRIEF_REL = "registry/operating_path_brief.json"


def worker_files(session: Path) -> list[Path]:
    raw = session / "registry" / "raw"
    if not raw.is_dir():
        return []
    return [p for stem in WORKER_STEMS if (p := raw / f"oppath_{stem}.json").is_file()]


def brief_path(session: Path) -> Path:
    return session / BRIEF_REL


def session_enforces_1d(session: Path) -> bool:
    """True when 1d completeness / Agent 5 hook gates apply.

    Enforce if the brief or any worker file already exists (must be valid)
    OR the session was stamped with harness_version >= 2.6.0.
    Legacy / slim fixtures skip.
    """
    if brief_path(session).is_file() or worker_files(session):
        return True
    parsed = parse_semver(load_run_manifest_version(session))
    if parsed is None:
        return False
    return parsed >= OPPATH_SINCE


def designed_phase_ids(session: Path | None = None) -> list[str]:
    """Phase walk for coverage/prereqs. Legacy sessions omit 1d."""
    from packages.kd_research.phase_status import PHASE_IDS

    if session is None or session_enforces_1d(session):
        return list(PHASE_IDS)
    return [p for p in PHASE_IDS if p != "1d"]


def load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.is_file():
        return None, f"missing {path.name}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)
    if not isinstance(data, dict):
        return None, "not an object"
    return data, None


def check_1d_complete(session: Path) -> list[tuple[str, str, str]]:
    """Coverage before marking phase 1d complete."""
    out: list[tuple[str, str, str]] = []
    if not session_enforces_1d(session) and not worker_files(session) and not brief_path(session).is_file():
        out.append(("SKIPPED", "1d", "legacy/slim (no oppath files; harness_version < 2.6.0)"))
        return out

    missing_workers = [rel for rel in WORKER_RELS if not (session / rel).is_file()]
    if missing_workers:
        out.append(("FAIL", "1d_workers", f"missing {missing_workers}"))
    else:
        out.append(("PASS", "1d_workers", f"{len(WORKER_RELS)} raw worker file(s)"))

    brief, err = load_json(brief_path(session))
    if err:
        out.append(("FAIL", BRIEF_REL, err))
        return out
    assert brief is not None
    out.append(("PASS", BRIEF_REL, "exists+parse"))

    rechecks = brief.get("verify_rechecks")
    if not isinstance(rechecks, list) or len(rechecks) < 3:
        out.append(("FAIL", "1d_verify_rechecks", "need >=3 verify_rechecks"))
    else:
        bad = [
            i
            for i, r in enumerate(rechecks)
            if not (isinstance(r, dict) and r.get("path") and r.get("value") is not None)
        ]
        if bad:
            out.append(("FAIL", "1d_verify_rechecks", f"entries missing path/value: {bad[:6]}"))
        else:
            out.append(("PASS", "1d_verify_rechecks", f"{len(rechecks)} re-read(s)"))

    conflicts = brief.get("conflicts")
    if conflicts is None:
        out.append(("WARN", "1d_conflicts", "conflicts[] omitted — merger should list flatten-vs-fade style fights"))
    elif not isinstance(conflicts, list):
        out.append(("FAIL", "1d_conflicts", "conflicts must be an array"))
    else:
        out.append(("PASS", "1d_conflicts", f"{len(conflicts)} conflict row(s)"))

    sources = brief.get("sources") if isinstance(brief.get("sources"), dict) else {}
    workers = sources.get("workers") if isinstance(sources, dict) else None
    if isinstance(workers, list) and len(workers) >= 3:
        out.append(("PASS", "1d_sources.workers", f"{len(workers)} path(s)"))
    else:
        out.append(("FAIL", "1d_sources.workers", "sources.workers must list the three raw worker paths"))

    return out


def check_operating_path_hooks(session: Path) -> list[tuple[str, str, str]]:
    """When 1d brief + valuation exist, require non-empty hooks that are not all noted_only."""
    from packages.kd_research.gates import validate_hooks_list

    if not brief_path(session).is_file():
        if session_enforces_1d(session):
            return [("FAIL", "operating_path_hooks", "new runtime requires registry/operating_path_brief.json")]
        return [("SKIPPED", "operating_path_hooks", "operating_path_brief.json absent")]
    vm_path = session / "data" / "valuation_model.json"
    if not vm_path.is_file():
        return [("SKIPPED", "operating_path_hooks", "valuation_model.json missing")]
    data, err = load_json(vm_path)
    if err:
        return [("FAIL", "operating_path_hooks", f"valuation_model unparseable: {err}")]
    assert data is not None
    hooks = data.get("operating_path_hooks")
    rows = validate_hooks_list(
        hooks,
        check_id="operating_path_hooks",
        empty_detail=(
            "valuation_model must have non-empty operating_path_hooks[] "
            "when registry/operating_path_brief.json exists"
        ),
    )
    if any(s == "FAIL" for s, _, _ in rows):
        return rows
    actions = []
    if isinstance(hooks, list):
        for h in hooks:
            if isinstance(h, dict):
                actions.append(str(h.get("action") or "").strip().lower())
    if actions and all(a == "noted_only" for a in actions):
        rows.append(
            (
                "FAIL",
                "operating_path_hooks noted_only",
                "all operating_path_hooks are noted_only — consume or reject material 1d recommendations",
            )
        )
    else:
        rows.append(("PASS", "operating_path_hooks noted_only", "not all noted_only"))
    return rows

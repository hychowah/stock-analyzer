"""Capture harness / model provenance for research runs (compare DB).

Always stamps intentional ``harness_version`` (from ``harness/VERSION``) plus
git SHA / dirty when available. Missing git → ``harness_git_sha="unknown"``
(never silent null for identity fields).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from packages.kd_research.paths import PROJECT_ROOT

VERSION_REL = Path("harness") / "VERSION"
DEFAULT_HARNESS_SPEC = "v2"
DEFAULT_HARNESS_VERSION = "0.0.0-unversioned"

# Free-text LLM id stamped once at scaffold (never invent late in a long run).
ENV_ORCHESTRATOR_MODEL = "RESEARCH_ORCHESTRATOR_MODEL"
ENV_SUBAGENT_MODEL = "RESEARCH_SUBAGENT_MODEL"
_MODEL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+/:-]{0,127}$")

# Paths that affect Mode A research outputs / gates (W1). Used by eng_verify.
RESEARCH_RUNTIME_PREFIXES: tuple[str, ...] = (
    "harness/",
    "packages/kd_research/",
    "scripts/scaffold_session.py",
    "scripts/build_prediction_snapshot.py",
    "scripts/finalize_session.py",
    "scripts/check_session.py",
    "scripts/preflight_phase.py",
    "scripts/ingest_library.py",
    "scripts/bind_library.py",
    "scripts/harvest_library.py",
    "scripts/export_compare_db.py",
    "scripts/rebuild_catalog.py",
    "scripts/migrate_sessions_to_archive.py",
)

# Advisory-only industry pack — does not require a harness_version bump alone.
RESEARCH_RUNTIME_EXCLUDES: tuple[str, ...] = (
    "harness/research/",
)

VERSION_PATH_POSIX = "harness/VERSION"


def file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def git_head_sha(repo: Path | None = None) -> str | None:
    root = repo or PROJECT_ROOT
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0:
            sha = out.stdout.strip()
            return sha or None
    except (OSError, subprocess.TimeoutExpired):
        return None
    return None


def git_is_dirty(repo: Path | None = None) -> bool | None:
    root = repo or PROJECT_ROOT
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode != 0:
            return None
        return bool(out.stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        return None


def load_harness_identity(repo: Path | None = None) -> dict[str, str]:
    """Read intentional product version from harness/VERSION.

    File is JSON: ``{"harness_version": "2.1.0", "harness_spec": "v2"}``.
    Also accepts a single-line plain version string.
    """
    root = repo or PROJECT_ROOT
    path = root / VERSION_REL
    if not path.is_file():
        return {
            "harness_version": DEFAULT_HARNESS_VERSION,
            "harness_spec": DEFAULT_HARNESS_SPEC,
        }
    raw = path.read_text(encoding="utf-8", errors="replace").strip()
    if not raw:
        return {
            "harness_version": DEFAULT_HARNESS_VERSION,
            "harness_spec": DEFAULT_HARNESS_SPEC,
        }
    if raw.startswith("{"):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {
                "harness_version": DEFAULT_HARNESS_VERSION,
                "harness_spec": DEFAULT_HARNESS_SPEC,
            }
        if not isinstance(data, dict):
            return {
                "harness_version": DEFAULT_HARNESS_VERSION,
                "harness_spec": DEFAULT_HARNESS_SPEC,
            }
        ver = str(data.get("harness_version") or data.get("version") or "").strip()
        spec = str(data.get("harness_spec") or data.get("spec") or "").strip()
        return {
            "harness_version": ver or DEFAULT_HARNESS_VERSION,
            "harness_spec": spec or DEFAULT_HARNESS_SPEC,
        }
    # plain text: first token is version
    ver = raw.splitlines()[0].strip().split()[0]
    return {
        "harness_version": ver or DEFAULT_HARNESS_VERSION,
        "harness_spec": DEFAULT_HARNESS_SPEC,
    }


def normalize_model_id(raw: str | None) -> str | None:
    """Return a cleaned model id or None if empty/invalid shape."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    # Collapse internal whitespace (agents sometimes paste "grok 4.5")
    s = re.sub(r"\s+", "-", s)
    if not _MODEL_ID_RE.match(s):
        return None
    return s


def require_model_id(raw: str | None, *, field: str = "orchestrator_model") -> str:
    """Strict parse for scaffold CLI — raises ValueError with operator guidance."""
    mid = normalize_model_id(raw)
    if mid is None:
        raise ValueError(
            f"{field} is required (non-empty model id, e.g. grok-4.5). "
            f"Pass --orchestrator-model at scaffold, or set {ENV_ORCHESTRATOR_MODEL}. "
            "Stamp once at session start; do not invent the model id after a long context."
        )
    return mid


def resolve_scaffold_models(
    orchestrator_model: str | None,
    default_subagent_model: str | None,
) -> tuple[str, str]:
    """Resolve LLM ids for a new session (CLI > env; subagent defaults to orchestrator)."""
    orch = orchestrator_model or os.environ.get(ENV_ORCHESTRATOR_MODEL)
    orch_id = require_model_id(orch, field="orchestrator_model")
    sub = default_subagent_model or os.environ.get(ENV_SUBAGENT_MODEL) or orch_id
    sub_id = require_model_id(sub, field="default_subagent_model")
    return orch_id, sub_id


def load_manifest_models(session: Path) -> dict[str, Any]:
    """Read orchestrator/subagent model fields from meta/run_manifest.json if present."""
    path = session / "meta" / "run_manifest.json"
    if not path.is_file():
        return {"present": False, "orchestrator_model": None, "default_subagent_model": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "present": True,
            "parse_error": True,
            "orchestrator_model": None,
            "default_subagent_model": None,
        }
    if not isinstance(data, dict):
        return {
            "present": True,
            "parse_error": True,
            "orchestrator_model": None,
            "default_subagent_model": None,
        }
    return {
        "present": True,
        "parse_error": False,
        "status": data.get("status"),
        "immutable": data.get("immutable"),
        "orchestrator_model": normalize_model_id(data.get("orchestrator_model")),
        "default_subagent_model": normalize_model_id(data.get("default_subagent_model")),
        "raw": data,
    }


def check_llm_model_identity(
    session: Path,
    *,
    strict: bool = True,
) -> list[tuple[str, str, str]]:
    """Require orchestrator_model stamped at scaffold (manifest), not invented late.

    ``strict=True`` (preflight / active sessions): missing → FAIL.
    ``strict=False`` (legacy completed runs in check_session): missing → WARN.
    """
    info = load_manifest_models(session)
    if not info.get("present"):
        msg = (
            "meta/run_manifest.json missing — re-scaffold with "
            "--orchestrator-model (stamp LLM id at session start)"
        )
        return [("FAIL" if strict else "WARN", "orchestrator_model", msg)]
    if info.get("parse_error"):
        return [("FAIL", "orchestrator_model", "run_manifest.json unreadable")]
    orch = info.get("orchestrator_model")
    if not orch:
        legacy = bool(info.get("immutable")) or str(info.get("status") or "") in {
            "completed",
            "finalized",
            "exported",
        }
        if legacy and not strict:
            return [
                (
                    "WARN",
                    "orchestrator_model",
                    "missing (legacy completed OK); new runs must stamp at scaffold",
                )
            ]
        return [
            (
                "FAIL",
                "orchestrator_model",
                "missing/empty — re-scaffold with --orchestrator-model; "
                "do not invent the model id after a long context",
            )
        ]
    sub = info.get("default_subagent_model")
    detail = f"orchestrator={orch}"
    if sub:
        detail += f" subagent={sub}"
    else:
        detail += " subagent=(unset)"
    return [("PASS", "orchestrator_model", detail)]


def _pin_meta(root: Path) -> dict[str, Any] | None:
    """Published pin folder (pins/<ver>/PIN.json). Never git-probe those trees."""
    path = root / "PIN.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def capture_harness_provenance(repo: Path | None = None) -> dict[str, Any]:
    """Snapshot harness identity + git + key instruction files for scaffold.

    Published pin folders stamp ``copied_from_sha`` and ``harness_dirty=false``.
    Do not git-probe an extract / pin copy (there is no meaningful HEAD).
    """
    root = repo or PROJECT_ROOT
    identity = load_harness_identity(root)
    agents = root / "AGENTS.md"
    if not agents.is_file():
        agents = root / "Agents.md"
    research_law = root / "harness" / "RESEARCH_AGENTS.md"
    prompts = root / "harness" / "agent_prompts.md"
    pin_meta = _pin_meta(root)
    if pin_meta is not None:
        sha = str(pin_meta.get("copied_from_sha") or "").strip() or "unknown"
        dirty = False
    else:
        sha = git_head_sha(root) or "unknown"
        dirty_flag = git_is_dirty(root)
        dirty = dirty_flag if dirty_flag is not None else True
    return {
        "harness_version": identity["harness_version"],
        "harness_spec": identity["harness_spec"],
        "harness_git_sha": sha if sha else "unknown",
        "harness_dirty": dirty,
        "agents_md_sha256": file_sha256(agents),
        "research_agents_sha256": file_sha256(research_law),
        "prompts_sha256": file_sha256(prompts),
        "version_file_sha256": file_sha256(root / VERSION_REL),
    }


def is_research_runtime_path(rel_posix: str) -> bool:
    """True if path is Mode A research runtime (requires version bump when changed)."""
    p = rel_posix.replace("\\", "/").lstrip("./")
    for ex in RESEARCH_RUNTIME_EXCLUDES:
        if p == ex.rstrip("/") or p.startswith(ex):
            return False
    for pref in RESEARCH_RUNTIME_PREFIXES:
        if p == pref.rstrip("/") or p.startswith(pref):
            return True
    return False


def paths_require_version_bump(changed_paths: list[str] | set[str]) -> tuple[bool, list[str]]:
    """Return (needs_bump, runtime_paths_changed excluding VERSION itself)."""
    runtime: list[str] = []
    for raw in changed_paths:
        p = raw.replace("\\", "/").lstrip("./")
        if p == VERSION_PATH_POSIX:
            continue
        if is_research_runtime_path(p):
            runtime.append(p)
    return (len(runtime) > 0, sorted(set(runtime)))


def check_llm_identity_entry(session: Path) -> list[tuple[str, str, str]]:
    return check_llm_model_identity(session, strict=True)


def check_session_identity(session: Path) -> list[tuple[str, str, str]]:
    """Ticker / session_date / confidence gate vs the folder name.

    ≥2.17.0 does not force primary_sector=standard when confidence < 0.70;
    it still requires requires_manual_review=true.
    """
    from packages.kd_research.annuals import load_run_manifest_version, parse_semver
    from packages.kd_research.paths import parse_session_key

    out: list[tuple[str, str, str]] = []
    ticker = session.parent.name
    session_date = session.name
    p = session / "registry/sector_config.json"
    if not p.exists():
        return [("SKIPPED", "identity/consistency", "sector_config.json missing")]
    try:
        sc = json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return [("SKIPPED", "identity/consistency", "sector_config.json unparseable")]
    ok = True
    if sc.get("ticker") and sc["ticker"].upper() != ticker.upper():
        out.append(
            ("FAIL", "identity: ticker", f"json says {sc['ticker']}, folder says {ticker}")
        )
        ok = False
    asof, _ = parse_session_key(session_date)
    if sc.get("session_date") and sc["session_date"] != asof and sc["session_date"] != session_date:
        out.append(
            (
                "FAIL",
                "identity: session_date",
                f"json says {sc['session_date']}, folder as-of/key says {asof}/{session_date}",
            )
        )
        ok = False
    conf = sc.get("confidence")
    if isinstance(conf, (int, float)) and conf < 0.70:
        parsed = parse_semver(load_run_manifest_version(session))
        wave9 = parsed is not None and parsed >= (2, 17, 0)
        if sc.get("requires_manual_review") is not True:
            out.append(
                (
                    "FAIL",
                    "confidence gate",
                    f"confidence {conf} < 0.70 requires requires_manual_review=true",
                )
            )
            ok = False
        elif not wave9 and sc.get("primary_sector") != "standard":
            out.append(
                (
                    "FAIL",
                    "confidence gate",
                    f"confidence {conf} < 0.70 requires primary_sector=standard and "
                    "requires_manual_review=true (harness < 2.17.0)",
                )
            )
            ok = False
    if ok:
        out.append(("PASS", "identity + confidence gate", ""))
    return out


def check_meta_artifacts(session: Path) -> list[tuple[str, str, str]]:
    """Optional meta/ prediction snapshot + run_manifest (archive layout)."""
    out: list[tuple[str, str, str]] = []
    meta = session / "meta"
    if not meta.is_dir():
        return [
            (
                "SKIPPED",
                "meta/",
                "absent (legacy OK; new sessions scaffold meta/ + post-Phase-5 snapshot)",
            )
        ]
    snap = meta / "prediction_snapshot.json"
    man = meta / "run_manifest.json"
    if not snap.exists() and not man.exists():
        return [
            (
                "SKIPPED",
                "meta content",
                "meta/ empty — run build_prediction_snapshot.py after Phase 5",
            )
        ]
    if man.exists():
        try:
            data = json.loads(man.read_text())
            missing = False
            for k in ("run_id", "ticker", "session_date"):
                if k not in data:
                    out.append(("FAIL", "run_manifest keys", f"missing {k}"))
                    missing = True
                    break
            if not missing:
                out.append(("PASS", "run_manifest", data.get("run_id", "")))
            hv = data.get("harness_version")
            hsha = data.get("harness_git_sha")
            if not hv or not str(hv).strip():
                out.append(
                    (
                        "WARN",
                        "run_manifest harness_version",
                        "missing — re-run finalize_session / scaffold; source harness/VERSION",
                    )
                )
            else:
                out.append(("PASS", "run_manifest harness_version", str(hv)))
            if not hsha or not str(hsha).strip():
                out.append(
                    (
                        "WARN",
                        "run_manifest harness_git_sha",
                        "missing — finalize should stamp git HEAD or 'unknown'",
                    )
                )
            else:
                dirty = data.get("harness_dirty")
                out.append(("PASS", "run_manifest harness_git_sha", f"{hsha} dirty={dirty}"))
            legacy_done = bool(data.get("immutable")) or str(data.get("status") or "") in {
                "completed",
                "finalized",
                "exported",
            }
            for st, cid, detail in check_llm_model_identity(session, strict=not legacy_done):
                out.append((st, f"run_manifest {cid}", detail))
        except Exception as e:  # noqa: BLE001
            out.append(("FAIL", "run_manifest parse", str(e)))
    else:
        out.append(("SKIPPED", "run_manifest", "file missing"))
    if snap.exists():
        try:
            data = json.loads(snap.read_text())
            missing = False
            for k in ("run_id", "ticker", "session_date", "fair_value"):
                if k not in data:
                    out.append(("FAIL", "prediction_snapshot keys", f"missing {k}"))
                    missing = True
                    break
            if not missing:
                out.append(("PASS", "prediction_snapshot", data.get("run_id", "")))
            prov = data.get("provenance") if isinstance(data.get("provenance"), dict) else {}
            if not prov.get("harness_version") or not prov.get("harness_git_sha"):
                out.append(
                    (
                        "WARN",
                        "prediction_snapshot provenance",
                        "harness_version/git missing — re-run finalize_session to stamp identity",
                    )
                )
            else:
                out.append(
                    (
                        "PASS",
                        "prediction_snapshot provenance",
                        f"v={prov.get('harness_version')} git={prov.get('harness_git_sha')}",
                    )
                )
            om = prov.get("orchestrator_model")
            if not om or not str(om).strip():
                out.append(
                    (
                        "WARN",
                        "prediction_snapshot orchestrator_model",
                        "missing in provenance — re-scaffold new runs with --orchestrator-model",
                    )
                )
            else:
                out.append(("PASS", "prediction_snapshot orchestrator_model", str(om)))
        except Exception as e:  # noqa: BLE001
            out.append(("FAIL", "prediction_snapshot parse", str(e)))
    else:
        out.append(("SKIPPED", "prediction_snapshot", "file missing"))
    return out

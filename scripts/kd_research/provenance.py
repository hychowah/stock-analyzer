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

from scripts.kd_research.paths import PROJECT_ROOT

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
    "scripts/kd_research/",
    "scripts/scaffold_session.py",
    "scripts/build_prediction_snapshot.py",
    "scripts/finalize_session.py",
    "scripts/check_session.py",
    "scripts/preflight_phase.py",
    "scripts/export_compare_db.py",
    "scripts/rebuild_catalog.py",
    "scripts/migrate_sessions_to_archive.py",
    "templates/",
    "sector_",
    "region_",
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


def capture_harness_provenance(repo: Path | None = None) -> dict[str, Any]:
    """Snapshot harness identity + git + key instruction files for every run."""
    root = repo or PROJECT_ROOT
    identity = load_harness_identity(root)
    agents = root / "AGENTS.md"
    if not agents.is_file():
        agents = root / "Agents.md"
    research_law = root / "harness" / "RESEARCH_AGENTS.md"
    prompts = root / "harness" / "agent_prompts.md"
    sha = git_head_sha(root)
    dirty = git_is_dirty(root)
    return {
        "harness_version": identity["harness_version"],
        "harness_spec": identity["harness_spec"],
        "harness_git_sha": sha if sha else "unknown",
        "harness_dirty": dirty if dirty is not None else True,
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
        if pref.endswith("_"):
            # sector_*.md / region_*.md at repo root
            name = Path(p).name
            if p == name and name.startswith(pref) and name.endswith(".md"):
                return True
            if "/" not in p and p.startswith(pref) and p.endswith(".md"):
                return True
            continue
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

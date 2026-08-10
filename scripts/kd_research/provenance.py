"""Capture harness / model provenance for research runs (compare DB).

Best-effort only: missing git or files → null fields, never fail the scaffold.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

from scripts.kd_research.paths import PROJECT_ROOT


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


def capture_harness_provenance(repo: Path | None = None) -> dict[str, Any]:
    """Snapshot git + key instruction files for variation analysis."""
    root = repo or PROJECT_ROOT
    agents = root / "AGENTS.md"
    if not agents.is_file():
        agents = root / "Agents.md"
    prompts = root / "harness" / "agent_prompts.md"
    return {
        "harness_git_sha": git_head_sha(root),
        "harness_dirty": git_is_dirty(root),
        "agents_md_sha256": file_sha256(agents),
        "prompts_sha256": file_sha256(prompts),
        "harness_spec": "v2",
    }

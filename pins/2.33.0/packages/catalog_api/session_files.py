"""Open research session files without sqlite (in-progress Analyze)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.catalog_api.client import (
    DEFAULT_ALLOW_PREFIXES,
    DEFAULT_DENY_PREFIXES,
    DEFAULT_MAX_BYTES,
    ArtifactDenied,
)

IN_PROGRESS_BODY_ALLOW = (
    "registry/phase_status.json",
    "registry/session_isolation.json",
    "registry/handoffs/",
    "meta/run_manifest.json",
)

IN_PROGRESS_NAME_ONLY = (
    "reports/",
    "charts/",
)

IN_PROGRESS_BODY_DENY = (
    "data/valuation_model.json",
    "registry/decision.json",
    "registry/audit.json",
    "meta/prediction_snapshot.json",
    "data/raw_sec/",
    "data/transcripts/",
    "grok.log",
    "reports/",
    "charts/",
)


def normalize_relpath(relpath: str) -> str:
    if not relpath or relpath.startswith("/") or relpath.startswith("~"):
        raise ArtifactDenied(f"absolute or empty relpath denied: {relpath!r}")
    if "\\" in relpath:
        raise ArtifactDenied("backslashes not allowed in relpath")
    norm = Path(relpath).as_posix()
    if norm.startswith("../") or "/../" in f"/{norm}/" or norm == "..":
        raise ArtifactDenied(f"path traversal denied: {relpath!r}")
    return norm


def _match(norm: str, prefixes: tuple[str, ...]) -> bool:
    for p in prefixes:
        if p.endswith("/"):
            if norm.startswith(p):
                return True
        elif norm == p:
            return True
    return False


def _contain(session_root: Path, relpath: str) -> Path:
    norm = normalize_relpath(relpath)
    root = session_root.resolve()
    target = (root / norm).resolve()
    try:
        target.relative_to(root)
    except ValueError as e:
        raise ArtifactDenied(f"escapes session root: {relpath!r}") from e
    return target


def open_session_artifact(
    session_root: Path,
    relpath: str,
    *,
    snapshot_ready: bool,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> bytes:
    norm = normalize_relpath(relpath)
    if snapshot_ready:
        if not any(norm == a.rstrip("/") or norm.startswith(a) for a in DEFAULT_ALLOW_PREFIXES):
            raise ArtifactDenied(f"prefix not allowlisted: {norm}")
        if _match(norm, DEFAULT_DENY_PREFIXES):
            raise ArtifactDenied(f"prefix denied: {norm}")
    else:
        if _match(norm, IN_PROGRESS_BODY_DENY) or not _match(norm, IN_PROGRESS_BODY_ALLOW):
            raise ArtifactDenied(f"in-progress body denied: {norm}")
    target = _contain(session_root, norm)
    if not target.is_file():
        raise FileNotFoundError(str(target))
    data = target.read_bytes()
    if len(data) > max_bytes:
        raise ArtifactDenied(f"artifact exceeds max_bytes={max_bytes} (size={len(data)})")
    return data


def list_session_artifacts(
    session_root: Path,
    *,
    snapshot_ready: bool,
    max_files: int = 200,
) -> list[dict[str, Any]]:
    root = session_root.resolve()
    if not root.is_dir():
        return []
    out: list[dict[str, Any]] = []
    prefixes = DEFAULT_ALLOW_PREFIXES if snapshot_ready else (
        IN_PROGRESS_BODY_ALLOW + IN_PROGRESS_NAME_ONLY
    )
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            rel = path.resolve().relative_to(root).as_posix()
        except ValueError:
            continue
        if snapshot_ready:
            if not any(rel == a.rstrip("/") or rel.startswith(a) for a in prefixes):
                continue
            if _match(rel, DEFAULT_DENY_PREFIXES):
                continue
        else:
            if not _match(rel, prefixes):
                continue
        try:
            size = path.stat().st_size
        except OSError:
            size = None
        body_ok = snapshot_ready or _match(rel, IN_PROGRESS_BODY_ALLOW)
        out.append(
            {
                "relpath": rel,
                "name": path.name,
                "size_bytes": size,
                "body_ok": body_ok,
            }
        )
        if len(out) >= max_files:
            break
    return out

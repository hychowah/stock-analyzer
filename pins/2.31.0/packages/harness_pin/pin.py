"""Pin: a Mode A execution root that can run scripts and describe itself."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from packages.kd_research.annuals import parse_semver
from packages.kd_research.paths import PROJECT_ROOT
from packages.kd_research.provenance import (
    capture_harness_provenance,
    git_head_sha,
    load_harness_identity,
)

LIVE = "live"
PINS_DIRNAME = "pins"
PIN_META = "PIN.json"
SEMVER_DIR_RE = re.compile(r"^\d+\.\d+\.\d+$")

COPY_REL = ("AGENTS.md", "harness", "packages", "scripts")
COPY_IGNORE = shutil.ignore_patterns(
    "__pycache__",
    "*.py[cod]",
    "*.egg-info",
    ".pytest_cache",
    ".mypy_cache",
    ".git",
    ".DS_Store",
)


class PinError(Exception):
    """Pin resolve / publish / run failure."""


class UnknownVersion(PinError):
    """Version is not live and has no pins/<semver>/ folder."""


def _workspace(ws: Path | None) -> Path:
    return (ws or PROJECT_ROOT).resolve()


def list_versions(workspace: Path | None = None) -> list[str]:
    """Return ['live', ...] plus published semver folders, newest first after live."""
    ws = _workspace(workspace)
    found: list[tuple[tuple[int, int, int], str]] = []
    pins = ws / PINS_DIRNAME
    if pins.is_dir():
        for child in pins.iterdir():
            if not child.is_dir() or not SEMVER_DIR_RE.match(child.name):
                continue
            if not (child / "harness" / "VERSION").is_file():
                continue
            parsed = parse_semver(child.name)
            if parsed is None:
                continue
            found.append((parsed, child.name))
    found.sort(reverse=True)
    return [LIVE, *[name for _p, name in found]]


def resolve(version: str | None, *, workspace: Path | None = None) -> Pin:
    """Resolve 'live' or a published semver to a Pin. Unknown → UnknownVersion."""
    ws = _workspace(workspace)
    raw = (version or LIVE).strip() or LIVE
    if raw.lower() == LIVE:
        ident = load_harness_identity(ws)
        return Pin(
            version=LIVE,
            label=str(ident.get("harness_version") or LIVE),
            root=ws,
            copied_from_sha=git_head_sha(ws),
        )
    if not SEMVER_DIR_RE.match(raw):
        raise UnknownVersion(f"not a published pin version: {raw!r}")
    root = ws / PINS_DIRNAME / raw
    if not root.is_dir() or not (root / "harness" / "VERSION").is_file():
        raise UnknownVersion(
            f"not a folder under pins/ (going-forward pins only): {raw}"
        )
    meta = _read_pin_meta(root)
    return Pin(
        version=raw,
        label=raw,
        root=root.resolve(),
        copied_from_sha=meta.get("copied_from_sha"),
    )


def _read_pin_meta(root: Path) -> dict[str, Any]:
    path = root / PIN_META
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def publish(workspace: Path | None = None, *, force: bool = False) -> Path:
    """Copy the live Mode A runtime into pins/<harness/VERSION>/."""
    ws = _workspace(workspace)
    ident = load_harness_identity(ws)
    ver = str(ident.get("harness_version") or "").strip()
    if not ver or parse_semver(ver) is None:
        raise PinError(f"cannot publish: bad harness_version {ver!r}")
    dest = ws / PINS_DIRNAME / ver
    if dest.exists() and not force:
        raise PinError(f"pin already exists (immutable): {dest}")
    if dest.exists() and force:
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for rel in COPY_REL:
        src = ws / rel
        if not src.exists():
            raise PinError(f"missing source for pin: {rel}")
        target = dest / rel
        if src.is_file():
            shutil.copy2(src, target)
        else:
            shutil.copytree(src, target, ignore=COPY_IGNORE, dirs_exist_ok=True)
    nested = dest / PINS_DIRNAME
    if nested.exists():
        shutil.rmtree(nested)
    meta = {
        "harness_version": ver,
        "copied_from_sha": git_head_sha(ws) or "unknown",
        "copied_at": _utc_now(),
        "contents": list(COPY_REL),
    }
    (dest / PIN_META).write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )
    dest_ver = load_harness_identity(dest).get("harness_version")
    if dest_ver != ver:
        raise PinError(f"pin VERSION mismatch: folder {ver} file {dest_ver}")
    return dest


@dataclass(frozen=True)
class Pin:
    """A Mode A execution root. Live root is the workspace; published is pins/<ver>/."""

    version: str
    label: str
    root: Path
    copied_from_sha: str | None

    def identity(self) -> dict[str, Any]:
        """Write-once stamp fields. Never git-probes a published pin folder."""
        prov = capture_harness_provenance(self.root)
        out = {
            "version": self.version,
            "label": self.label,
            "root": str(self.root),
            "harness_version": prov.get("harness_version"),
            "harness_spec": prov.get("harness_spec"),
            "harness_git_sha": prov.get("harness_git_sha"),
            "harness_dirty": prov.get("harness_dirty"),
            "copied_from_sha": self.copied_from_sha,
            "agents_md_sha256": prov.get("agents_md_sha256"),
            "research_agents_sha256": prov.get("research_agents_sha256"),
            "prompts_sha256": prov.get("prompts_sha256"),
            "version_file_sha256": prov.get("version_file_sha256"),
        }
        return out

    def spawn_env(
        self,
        parent: dict[str, str] | os._Environ[str],
        archive_root: Path | str,
    ) -> dict[str, str]:
        """Child env: PYTHONPATH replaced with this root; ARCHIVE_ROOT = live archive."""
        env = {str(k): str(v) for k, v in parent.items()}
        env["PYTHONPATH"] = str(self.root)
        env["ARCHIVE_ROOT"] = str(Path(archive_root).resolve())
        return env

    def run(
        self,
        argv: list[str],
        *,
        archive_root: Path | str,
        cwd: Path | str | None = None,
        check: bool = True,
        capture: bool = False,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run argv[0] as a script under this pin's Python path."""
        env = self.spawn_env(os.environ, archive_root)
        cmd = [sys.executable, *[str(a) for a in argv]]
        return subprocess.run(  # noqa: S603
            cmd,
            cwd=str(cwd or self.root),
            env=env,
            check=check,
            capture_output=capture,
            text=True,
            timeout=timeout,
        )

    def scaffold_research(
        self,
        ticker: str,
        session_date: str,
        archive_root: Path | str,
        *,
        slug: str | None = None,
        orchestrator_model: str = "grok-4.5",
        default_subagent_model: str | None = None,
        notes: str | None = None,
        auto_replicate: bool = True,
    ) -> Path:
        """Create a session under live archive using this pin's scaffold."""
        if not (self.root / PIN_META).is_file():
            from packages.kd_research.scaffold import scaffold

            return scaffold(
                ticker,
                session_date,
                output_dir=archive_root,
                force=False,
                slug=slug,
                orchestrator_model=orchestrator_model,
                default_subagent_model=default_subagent_model,
                notes=notes,
                auto_replicate=auto_replicate,
            )
        script = self.root / "scripts" / "scaffold_session.py"
        argv = [
            str(script),
            "--ticker",
            ticker,
            "--date",
            session_date,
            "--output-dir",
            str(Path(archive_root).resolve()),
            "--orchestrator-model",
            orchestrator_model,
            "--skip-ticker-check",
        ]
        if slug:
            argv.extend(["--slug", slug])
        if default_subagent_model:
            argv.extend(["--subagent-model", default_subagent_model])
        if notes:
            argv.extend(["--notes", notes])
        if not auto_replicate:
            argv.append("--no-auto-replicate")
        proc = self.run(
            argv,
            archive_root=archive_root,
            capture=True,
            check=False,
            timeout=120,
        )
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
            raise PinError(f"pin scaffold failed: {err}")
        session: Path | None = None
        for line in (proc.stdout or "").splitlines():
            if line.startswith("Session scaffolded:"):
                session = Path(line.split(":", 1)[1].strip())
                break
        if session is None or not session.is_dir():
            raise PinError("pin scaffold did not print a session path")
        return session

    def _spec_proc(self, extra: list[str] | None = None) -> dict[str, Any]:
        env = self.spawn_env(os.environ, os.environ.get("ARCHIVE_ROOT") or self.root)
        cmd = [sys.executable, "-m", "packages.kd_research.workflow_spec", *(extra or [])]
        proc = subprocess.run(  # noqa: S603
            cmd,
            cwd=str(self.root),
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        if proc.returncode != 0:
            raise PinError(
                f"workflow_spec failed: {(proc.stderr or proc.stdout or '')[-2000:]}"
            )
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            raise PinError(f"workflow_spec produced invalid JSON: {e}") from e
        if not isinstance(data, dict):
            raise PinError("workflow_spec JSON must be an object")
        return data

    def workflow_spec(self) -> dict[str, Any]:
        return self._spec_proc()

    def agent_prompt(self, agent_id: str) -> dict[str, Any]:
        return self._spec_proc(["--agent", agent_id])

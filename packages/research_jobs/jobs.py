"""Analyze job lifecycle: verify ticker, scaffold, spawn, refresh, cancel."""

from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from packages.agent_jobs.capacity import JobsBusy, assert_capacity
from packages.agent_jobs.spawn import (
    GrokSpawnBackend,
    SpawnBackend,
    SpawnResult,
    grok_binary,
    kill_pid,
    pid_alive_for_job,
)
from packages.research_jobs.paths import (
    UI_SCHEDULED_HEADING,
    analyze_id,
    analyze_job_dir,
    parse_analyze_id,
    research_jobs_root,
)
from packages.research_jobs.prompt import build_prompt
from scripts.kd_research.paths import PROJECT_ROOT
from scripts.kd_research.spawn_gate import write_abandon
from scripts.kd_research.ticker_lookup import LookupBackend, check_ticker
from scripts.scaffold_session import scaffold

TERMINAL = frozenset({"complete", "failed", "cancelled"})
JOB_NAME = "job.json"
QUEUED_STALE_S = 60
NOTES_UI = (
    "UI-scheduled Analyze; session already scaffolded; "
    "do not re-scaffold or list archive/research/{ticker}/ except this session_key."
)


class AnalyzeError(Exception):
    pass


class AnalyzeValidationError(AnalyzeError):
    pass


class AnalyzeTickerError(AnalyzeValidationError):
    def __init__(
        self,
        status: str,
        reason: str,
        *,
        matches: list[str] | None = None,
    ) -> None:
        super().__init__(reason)
        self.status = status
        self.matches = list(matches or [])
        self.reason = reason


class AnalyzeBusy(AnalyzeError):
    pass


class AnalyzeNotFound(AnalyzeError, KeyError):
    pass


class AnalyzeGrokMissing(AnalyzeError):
    pass


class AnalyzeRunbookMissing(AnalyzeError):
    pass


class AnalyzeArchiveRootError(AnalyzeValidationError):
    pass


class AnalyzeDiscardRefused(AnalyzeError):
    pass


class AnalyzeResumeConflict(AnalyzeError):
    pass


class FakeAnalyzeSpawnBackend:
    """Writes job_dir only. Never writes S/ and never completes Mode A."""

    def spawn(self, job: dict[str, Any]) -> SpawnResult:
        out = Path(str(job["job_dir"]))
        out.mkdir(parents=True, exist_ok=True)
        (out / "fake_spawn.txt").write_text("fake\n", encoding="utf-8")
        return SpawnResult(pid=None, grok_session_id="fake", command=["fake-analyze"])


def default_analyze_spawn() -> SpawnBackend:
    mode = (os.environ.get("AGENT_SPAWN") or "grok").strip().lower()
    if mode in {"fake", "test"}:
        return FakeAnalyzeSpawnBackend()
    return GrokSpawnBackend()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_stamp(dt: datetime | None = None) -> str:
    return (dt or _utc_now()).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = str(value).strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def env_archive_is_non_default(*, project_root: Path | None = None) -> bool:
    raw = os.environ.get("ARCHIVE_ROOT")
    if not raw or not str(raw).strip():
        return False
    root = project_root or PROJECT_ROOT
    return Path(raw).expanduser().resolve() != (root / "archive").resolve()


def refuse_http_analyze(*, project_root: Path | None = None) -> bool:
    """True when a real Grok Analyze would split-brain vs ARCHIVE_ROOT.

    Fake spawn (tests) may use a tmp ARCHIVE_ROOT; Mode A CLIs ignore it.
    """
    if not env_archive_is_non_default(project_root=project_root):
        return False
    mode = (os.environ.get("AGENT_SPAWN") or "grok").strip().lower()
    return mode not in {"fake", "test"}


def runbook_has_ui_scheduled_heading(project_root: Path | None = None) -> bool:
    path = (project_root or PROJECT_ROOT) / "harness" / "orchestrator_runbook.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return UI_SCHEDULED_HEADING in text


@contextmanager
def exclusive_job_lock(archive_root: Path) -> Iterator[None]:
    path = research_jobs_root(archive_root) / ".lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(path, "a+b")
    try:
        fh.seek(0, os.SEEK_END)
        if fh.tell() == 0:
            fh.write(b"0")
            fh.flush()
        fh.seek(0)
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            if sys.platform == "win32":
                import msvcrt

                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        fh.close()


def iter_job_files(archive_root: Path) -> list[Path]:
    root = research_jobs_root(archive_root)
    if not root.is_dir():
        return []
    out: list[Path] = []
    for ticker_dir in sorted(root.iterdir()):
        if not ticker_dir.is_dir() or ticker_dir.name.startswith("."):
            continue
        for packet in sorted(ticker_dir.iterdir()):
            job = packet / JOB_NAME
            if job.is_file():
                out.append(job)
    return out


def _load_job_file(path: Path) -> dict[str, Any] | None:
    return _read_json(path)


def _job_path(archive_root: Path, ticker: str, session_key: str) -> Path:
    return analyze_job_dir(ticker, session_key, archive_root) / JOB_NAME


def _session_snapshot(session: Path) -> Path:
    return session / "meta" / "prediction_snapshot.json"


def _session_abandon(session: Path) -> Path:
    return session / "registry" / "abandon.json"


def _count_running_compare(archive_root: Path) -> int:
    from packages.compare_jobs.jobs import list_compares

    n = 0
    for job in list_compares(archive_root, refresh=True):
        if job.get("status") == "running":
            n += 1
    return n


def count_running_analyze(archive_root: Path) -> int:
    n = 0
    for path in iter_job_files(archive_root):
        job = _load_job_file(path)
        if job is None:
            continue
        job = refresh_analyze(archive_root, str(job.get("analyze_id") or ""), job=job)
        if job.get("status") == "running":
            n += 1
    return n


def _running_by_kind(archive_root: Path) -> dict[str, int]:
    return {
        "compare": _count_running_compare(archive_root),
        "analyze": count_running_analyze(archive_root),
    }


def _maybe_abandon(session: Path, *, reason: str, detail: str) -> None:
    if _session_snapshot(session).is_file():
        return
    write_abandon(session, reason=reason, detail=detail)


def refresh_analyze(
    archive_root: Path,
    analyze_id_value: str,
    *,
    job: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if job is None:
        job = _require_job(archive_root, analyze_id_value)
    session = Path(str(job.get("session_root") or ""))
    job_dir = Path(str(job.get("job_dir") or ""))
    changed = False

    snap = _session_snapshot(session) if session.as_posix() not in {".", ""} else None
    abandon = _session_abandon(session) if session.as_posix() not in {".", ""} else None

    if not session.exists():
        if job.get("status") not in TERMINAL:
            job["status"] = "failed"
            job["error"] = "session_root missing"
            job["abandoned"] = False
            changed = True
        job["snapshot_ready"] = False
        if changed:
            job["updated_at"] = _utc_stamp()
            if job_dir:
                _atomic_write_json(job_dir / JOB_NAME, job)
        return job

    if snap is not None and snap.is_file():
        if job.get("status") != "complete" or not job.get("snapshot_ready"):
            job["status"] = "complete"
            job["snapshot_ready"] = True
            changed = True
        job["snapshot_ready"] = True
        if abandon is not None and abandon.is_file():
            if job.get("abandoned") or not job.get("error"):
                job["abandoned"] = False
                job["error"] = (
                    "abandon.json present on finalized session; not treating as abandoned"
                )
                changed = True
        payload = _read_json(snap) or {}
        audit_path = session / "registry" / "audit.json"
        audit = _read_json(audit_path) or {}
        verdict = audit.get("verdict") or payload.get("audit_verdict")
        if verdict and job.get("audit_verdict") != verdict:
            job["audit_verdict"] = verdict
            changed = True
        man = _read_json(session / "meta" / "run_manifest.json") or {}
        st = man.get("status")
        if st and job.get("run_manifest_status") != st:
            job["run_manifest_status"] = st
            changed = True
        job["catalog_run_ready"] = _catalog_run_ready(
            archive_root, str(job.get("run_id") or "")
        )
    elif abandon is not None and abandon.is_file():
        if job.get("status") != "failed" or not job.get("abandoned"):
            job["status"] = "failed"
            job["abandoned"] = True
            payload = _read_json(abandon) or {}
            job["error"] = str(payload.get("reason") or payload.get("detail") or "abandoned")
            changed = True
        job["snapshot_ready"] = False
    elif str(job.get("status") or "") == "running":
        pid = job.get("pid")
        spawned = job.get("spawned_at")
        if pid and not pid_alive_for_job(int(pid), spawned if isinstance(spawned, str) else None):
            job["status"] = "failed"
            job["error"] = "Grok process exited before finalize"
            job["abandoned"] = False
            changed = True
        elif not pid:
            # Fake spawn: stay running until a snapshot appears (tests).
            pass
    elif str(job.get("status") or "") == "queued":
        spawned = _parse_ts(str(job.get("updated_at") or job.get("spawned_at") or ""))
        pid = job.get("pid")
        live = pid_alive_for_job(
            int(pid) if pid else None,
            str(job.get("spawned_at") or "") or None,
        )
        if not live and spawned and _utc_now() - spawned > timedelta(seconds=QUEUED_STALE_S):
            job["status"] = "failed"
            job["error"] = "spawn did not start"
            job["abandoned"] = False
            changed = True

    phase = _read_json(session / "registry" / "phase_status.json")
    if phase is None and (session / "registry" / "phase_status.json").is_file():
        if job.get("phase_current") != "unknown":
            job["phase_current"] = "unknown"
            job["error"] = job.get("error") or "unreadable phase_status"
            changed = True
    elif isinstance(phase, dict):
        cur = phase.get("current_phase") or phase.get("status")
        hint = phase.get("resume_hint")
        if cur is not None and job.get("phase_current") != cur:
            job["phase_current"] = cur
            changed = True
        if hint is not None and job.get("resume_hint") != hint:
            job["resume_hint"] = hint
            changed = True

    if changed and job_dir:
        job["updated_at"] = _utc_stamp()
        _atomic_write_json(job_dir / JOB_NAME, job)
    return job


def _catalog_run_ready(archive_root: Path, run_id: str) -> bool:
    if not run_id:
        return False
    try:
        from packages.catalog_api.client import CatalogApi, DbMissing, RunNotFound

        api = CatalogApi(archive_root, readonly=True)
        api.get_run(run_id)
        return True
    except (DbMissing, RunNotFound, OSError, KeyError, ValueError):
        return False
    except Exception:
        return False


def _require_job(archive_root: Path, analyze_id_value: str) -> dict[str, Any]:
    try:
        ticker, session_key = parse_analyze_id(analyze_id_value)
    except ValueError as e:
        raise AnalyzeNotFound(str(e)) from e
    path = _job_path(archive_root, ticker, session_key)
    if not path.is_file():
        raise AnalyzeNotFound(analyze_id_value)
    job = _load_job_file(path)
    if job is None:
        raise AnalyzeNotFound(analyze_id_value)
    return job


def get_analyze(archive_root: Path, analyze_id_value: str) -> dict[str, Any]:
    job = _require_job(archive_root, analyze_id_value)
    return refresh_analyze(archive_root, analyze_id_value, job=job)


def list_analyzes(
    archive_root: Path,
    *,
    ticker: str | None = None,
    refresh: bool = True,
) -> list[dict[str, Any]]:
    want = ticker.strip().upper() if ticker else None
    rows: list[dict[str, Any]] = []
    for path in iter_job_files(archive_root):
        job = _load_job_file(path)
        if job is None:
            continue
        if want and str(job.get("ticker") or "").upper() != want:
            continue
        if refresh:
            try:
                job = refresh_analyze(
                    archive_root, str(job.get("analyze_id") or ""), job=job
                )
            except AnalyzeNotFound:
                continue
        rows.append(job)
    rows.sort(
        key=lambda j: (str(j.get("updated_at") or ""), str(j.get("analyze_id") or "")),
        reverse=True,
    )
    return rows


def reconcile_analyze_jobs(archive_root: Path) -> list[dict[str, Any]]:
    """Walk every job.json and refresh (UI startup / CLI after crash)."""
    return list_analyzes(archive_root, refresh=True)


def start_analyze(
    archive_root: Path,
    ticker: str,
    *,
    session_date: str | None = None,
    slug: str | None = None,
    orchestrator_model: str = "grok-4.5",
    subagent_model: str | None = None,
    notes: str | None = None,
    ingest_library: bool = False,
    spawn: SpawnBackend | None = None,
    ticker_backend: LookupBackend | None = None,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Library entry: accepts any archive_root (tmp tests). No env ARCHIVE_ROOT refuse."""
    checked = check_ticker(ticker, backend=ticker_backend)
    if not checked.ok:
        raise AnalyzeTickerError(
            checked.status,
            checked.reason or f"ticker {ticker!r} rejected",
            matches=checked.matches,
        )
    canonical = str(checked.canonical or ticker).strip().upper()
    asof = session_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    orch = orchestrator_model or "grok-4.5"
    sub = subagent_model or orch
    proj = str((project_root or PROJECT_ROOT).resolve())
    note = notes or NOTES_UI.format(ticker=canonical)
    backend = spawn or default_analyze_spawn()

    if isinstance(backend, GrokSpawnBackend):
        if not grok_binary():
            raise AnalyzeGrokMissing(
                "Grok CLI not found. Install grok, set GROK_BIN, or set AGENT_SPAWN=fake."
            )
        if not runbook_has_ui_scheduled_heading(Path(proj)):
            raise AnalyzeRunbookMissing(
                "UI-scheduled runbook heading missing; merge W1 PR 3 before real Grok Analyze"
            )

    with exclusive_job_lock(archive_root):
        try:
            assert_capacity("analyze", running_by_kind=_running_by_kind(archive_root))
        except JobsBusy as e:
            raise AnalyzeBusy(str(e)) from e

        try:
            session = scaffold(
                canonical,
                asof,
                output_dir=archive_root,
                force=False,
                legacy=False,
                slug=slug,
                orchestrator_model=orch,
                default_subagent_model=sub,
                notes=note,
                auto_replicate=True,
                verify_ticker=False,
            )
        except SystemExit as e:
            raise AnalyzeValidationError(str(e)) from e

        session_key = session.name
        job_dir = analyze_job_dir(canonical, session_key, archive_root)
        job_dir.mkdir(parents=True, exist_ok=True)
        cid = analyze_id(canonical, session_key)
        job: dict[str, Any] = {
            "schema_version": 1,
            "kind": "analyze",
            "analyze_id": cid,
            "ticker": canonical,
            "session_date": asof,
            "session_key": session_key,
            "run_id": f"research:{canonical}:{session_key}",
            "session_root": str(session.resolve()),
            "job_dir": str(job_dir.resolve()),
            "out_dir": str(job_dir.resolve()),
            "status": "queued",
            "mode": "new",
            "orchestrator_model": orch,
            "subagent_model": sub,
            "notes": note,
            "pid": None,
            "grok_session_id": None,
            "command": None,
            "project_root": proj,
            "spawned_at": None,
            "updated_at": _utc_stamp(),
            "error": None,
            "mcp_status": "unknown",
            "phase_current": "orch",
            "resume_hint": None,
            "snapshot_ready": False,
            "catalog_run_ready": False,
            "abandoned": False,
            "audit_verdict": None,
            "run_manifest_status": "scaffolded",
            "library_ingest": bool(ingest_library),
        }
        (job_dir / "prompt.md").write_text(build_prompt(job), encoding="utf-8")
        _atomic_write_json(job_dir / JOB_NAME, job)

        try:
            result = backend.spawn(job)
        except FileNotFoundError as e:
            _maybe_abandon(session, reason="spawn_fail", detail=str(e))
            job["status"] = "failed"
            job["abandoned"] = _session_abandon(session).is_file()
            job["error"] = str(e)
            job["updated_at"] = _utc_stamp()
            _atomic_write_json(job_dir / JOB_NAME, job)
            raise AnalyzeGrokMissing(str(e)) from e
        except Exception as e:  # noqa: BLE001
            _maybe_abandon(session, reason="spawn_fail", detail=str(e))
            job["status"] = "failed"
            job["abandoned"] = _session_abandon(session).is_file()
            job["error"] = str(e)
            job["updated_at"] = _utc_stamp()
            _atomic_write_json(job_dir / JOB_NAME, job)
            raise AnalyzeError(str(e)) from e

        job["pid"] = result.pid
        job["grok_session_id"] = result.grok_session_id
        job["command"] = result.command
        job["status"] = "running"
        job["spawned_at"] = _utc_stamp()
        job["updated_at"] = job["spawned_at"]
        _atomic_write_json(job_dir / JOB_NAME, job)
        return refresh_analyze(archive_root, cid, job=job)


def cancel_analyze(archive_root: Path, analyze_id_value: str) -> dict[str, Any]:
    job = get_analyze(archive_root, analyze_id_value)
    if job.get("status") in TERMINAL:
        return job
    kill_pid(job.get("pid"))
    job["status"] = "cancelled"
    job["updated_at"] = _utc_stamp()
    job["error"] = "cancelled"
    _atomic_write_json(Path(str(job["job_dir"])) / JOB_NAME, job)
    return job


def discard_analyze(archive_root: Path, analyze_id_value: str) -> dict[str, Any]:
    job = get_analyze(archive_root, analyze_id_value)
    session = Path(str(job["session_root"]))
    if _session_snapshot(session).is_file():
        raise AnalyzeDiscardRefused("session already finalized")
    kill_pid(job.get("pid"))
    _maybe_abandon(session, reason="ui_discard", detail="UI discard")
    if not _session_abandon(session).is_file():
        raise AnalyzeError("write_abandon did not create abandon.json")
    job["status"] = "failed"
    job["abandoned"] = True
    job["error"] = "ui_discard"
    job["updated_at"] = _utc_stamp()
    _atomic_write_json(Path(str(job["job_dir"])) / JOB_NAME, job)
    return job


def resume_analyze(
    archive_root: Path,
    analyze_id_value: str,
    *,
    spawn: SpawnBackend | None = None,
    project_root: Path | None = None,
) -> dict[str, Any]:
    job = get_analyze(archive_root, analyze_id_value)
    session = Path(str(job["session_root"]))
    if job.get("abandoned"):
        raise AnalyzeValidationError("session is abandoned; start a new analysis")
    if _session_snapshot(session).is_file():
        raise AnalyzeValidationError("session already finalized")
    if not session.is_dir():
        raise AnalyzeValidationError("session_root missing")
    pid = job.get("pid")
    spawned = job.get("spawned_at")
    if pid_alive_for_job(int(pid) if pid else None, spawned if isinstance(spawned, str) else None):
        raise AnalyzeResumeConflict("orchestrator still running; cancel first or wait")
    status = str(job.get("status") or "")
    if status not in {"failed", "cancelled"} and not (
        status == "running" and not pid_alive_for_job(int(pid) if pid else None, spawned if isinstance(spawned, str) else None)
    ):
        if status == "complete":
            raise AnalyzeValidationError("job already complete")
        if status == "running":
            raise AnalyzeResumeConflict("orchestrator still running; cancel first or wait")

    backend = spawn or default_analyze_spawn()
    if isinstance(backend, GrokSpawnBackend):
        if not grok_binary():
            raise AnalyzeGrokMissing(
                "Grok CLI not found. Install grok, set GROK_BIN, or set AGENT_SPAWN=fake."
            )
        if not runbook_has_ui_scheduled_heading(project_root or PROJECT_ROOT):
            raise AnalyzeRunbookMissing(
                "UI-scheduled runbook heading missing; merge W1 PR 3 before real Grok Analyze"
            )

    with exclusive_job_lock(archive_root):
        try:
            assert_capacity("analyze", running_by_kind=_running_by_kind(archive_root))
        except JobsBusy as e:
            raise AnalyzeBusy(str(e)) from e

        job["mode"] = "resume"
        job_dir = Path(str(job["job_dir"]))
        (job_dir / "prompt.md").write_text(build_prompt(job, resume=True), encoding="utf-8")
        result = backend.spawn(job)
        job["pid"] = result.pid
        job["grok_session_id"] = result.grok_session_id
        job["command"] = result.command
        job["status"] = "running"
        job["error"] = None
        job["spawned_at"] = _utc_stamp()
        job["updated_at"] = job["spawned_at"]
        _atomic_write_json(job_dir / JOB_NAME, job)
        return refresh_analyze(archive_root, analyze_id_value, job=job)

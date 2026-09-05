"""Compare job lifecycle: validate, allocate, spawn, refresh, cancel."""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from packages.catalog_api.client import parse_run_id
from packages.compare_jobs.headline import headline_for_sessions
from packages.agent_jobs.capacity import JobsBusy, claim_start
from packages.compare_jobs.spawn import (
    SpawnBackend,
    default_spawn_backend,
    grok_binary,
    kill_pid,
    pid_alive,
)
from packages.compare_jobs.paths import (
    allocate_compare_key,
    compare_id,
    compare_packet_dir,
    comparisons_root,
    parse_compare_id,
)
from packages.kd_research.paths import PROJECT_ROOT, resolve_session

TERMINAL = frozenset({"complete", "failed", "cancelled"})
SYNTHESIS_NAME = "99_synthesis.md"
JOB_NAME = "job.json"


class CompareError(Exception):
    pass


class CompareValidationError(CompareError):
    pass


class CompareBusy(CompareError):
    pass


class CompareNotFound(CompareError, KeyError):
    pass


class GrokMissing(CompareError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    return date.today().isoformat()


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _archive_parent(archive_root: Path) -> Path:
    """paths.* helpers take project root or archive dir."""
    return Path(archive_root).resolve()


def _output_dir(archive_root: Path) -> Path:
    return _archive_parent(archive_root)


def _session_root(archive_root: Path, ticker: str, session_key: str) -> Path | None:
    return resolve_session(ticker, session_key, _output_dir(archive_root))


def _order_sessions(key_a: str, key_b: str) -> tuple[str, str]:
    """Older (or first-named on tie) is A."""
    if key_a <= key_b:
        return key_a, key_b
    return key_b, key_a


def _job_path(archive_root: Path, ticker: str, packet_key: str) -> Path:
    return compare_packet_dir(ticker, packet_key, _output_dir(archive_root)) / JOB_NAME


def iter_job_files(archive_root: Path) -> list[Path]:
    root = comparisons_root(_output_dir(archive_root))
    if not root.is_dir():
        return []
    out: list[Path] = []
    for ticker_dir in sorted(root.iterdir()):
        if not ticker_dir.is_dir():
            continue
        for packet in sorted(ticker_dir.iterdir()):
            job = packet / JOB_NAME
            if job.is_file():
                out.append(job)
    return out


def _load_job_file(path: Path) -> dict[str, Any] | None:
    try:
        data = _read_json(path)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def list_compares(
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
            job = refresh_compare(archive_root, str(job.get("compare_id") or ""), job=job)
        rows.append(job)
    rows.sort(key=lambda j: (str(j.get("updated_at") or ""), str(j.get("compare_id") or "")), reverse=True)
    return rows


def _running_jobs(archive_root: Path) -> list[dict[str, Any]]:
    running: list[dict[str, Any]] = []
    for path in iter_job_files(archive_root):
        job = _load_job_file(path)
        if job is None:
            continue
        job = refresh_compare(archive_root, str(job.get("compare_id") or ""), job=job)
        if job.get("status") == "running":
            running.append(job)
    return running


def count_running_compare(archive_root: Path) -> int:
    return len(_running_jobs(archive_root))


def _find_pair(
    archive_root: Path,
    ticker: str,
    session_a: str,
    session_b: str,
) -> dict[str, Any] | None:
    for path in iter_job_files(archive_root):
        job = _load_job_file(path)
        if job is None:
            continue
        if str(job.get("ticker") or "").upper() != ticker:
            continue
        if job.get("session_a") == session_a and job.get("session_b") == session_b:
            return refresh_compare(archive_root, str(job.get("compare_id") or ""), job=job)
    return None


def _build_prompt(job: dict[str, Any]) -> str:
    return (
        "Run /session-valuation-audit.\n\n"
        "HARD RULES:\n"
        "- Read only the two named research sessions below.\n"
        "- Write ONLY under the OUT directory. Never write archive/research session\n"
        "  folders or archive/outcomes.\n"
        "- Do not invent fair values, WACC, MoS, or scenario masses.\n"
        "- Do not average the two base FVs into a compromise target.\n"
        "- Do not git commit.\n"
        "- Follow .grok/skills/session-valuation-audit/SKILL.md. If this prompt\n"
        "  names OUT, use it instead of the skill default path.\n"
        "- Keep subagent fan-out (six auditors, then synthesizer).\n\n"
        f"Ticker: {job['ticker']}\n"
        f"Session A key: {job['session_a']}\n"
        f"Session A path: {job['path_a']}\n"
        f"Session B key: {job['session_b']}\n"
        f"Session B path: {job['path_b']}\n"
        f"OUT (absolute, write only here): {job['out_dir']}\n\n"
        "Stop when 99_synthesis.md is written under OUT.\n"
    )


def refresh_compare(
    archive_root: Path,
    compare_id_value: str,
    *,
    job: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if job is None:
        job = _require_job(archive_root, compare_id_value)
    status = str(job.get("status") or "")
    out_dir = Path(str(job.get("out_dir") or ""))
    synthesis = out_dir / SYNTHESIS_NAME
    changed = False
    if synthesis.is_file() and status not in {"cancelled"}:
        if status != "complete":
            job["status"] = "complete"
            job["error"] = None
            job["synthesis_ready"] = True
            changed = True
    elif status == "running":
        pid = job.get("pid")
        if pid and not pid_alive(int(pid)):
            job["status"] = "failed"
            job["error"] = "Grok process exited before 99_synthesis.md"
            changed = True
        elif not pid:
            # Fake/incomplete spawn without a process: stay running only if we
            # expect a later write. Treat as failed if synthesis never coming.
            pass
    job["synthesis_ready"] = synthesis.is_file()
    job["readme_ready"] = (out_dir / "README.md").is_file()
    job["headline_ready"] = (out_dir / "headline.json").is_file()
    if changed:
        job["updated_at"] = _utc_now()
        _atomic_write_json(out_dir / JOB_NAME, job)
    return job


def _require_job(archive_root: Path, compare_id_value: str) -> dict[str, Any]:
    try:
        ticker, packet_key = parse_compare_id(compare_id_value)
    except ValueError as e:
        raise CompareNotFound(str(e)) from e
    path = _job_path(archive_root, ticker, packet_key)
    if not path.is_file():
        raise CompareNotFound(compare_id_value)
    job = _load_job_file(path)
    if job is None:
        raise CompareNotFound(compare_id_value)
    return job


def get_compare(archive_root: Path, compare_id_value: str) -> dict[str, Any]:
    job = _require_job(archive_root, compare_id_value)
    return refresh_compare(archive_root, compare_id_value, job=job)


def start_compare(
    archive_root: Path,
    run_id_a: str,
    run_id_b: str,
    *,
    force: bool = False,
    spawn: SpawnBackend | None = None,
    project_root: Path | None = None,
) -> dict[str, Any]:
    try:
        ticker_a, key_a = parse_run_id(run_id_a)
        ticker_b, key_b = parse_run_id(run_id_b)
    except ValueError as e:
        raise CompareValidationError(str(e)) from e
    if ticker_a != ticker_b:
        raise CompareValidationError(
            f"Sessions must be the same ticker (got {ticker_a} and {ticker_b})"
        )
    if key_a == key_b:
        raise CompareValidationError("Select two different sessions")

    ticker = ticker_a
    session_a, session_b = _order_sessions(key_a, key_b)
    path_a = _session_root(archive_root, ticker, session_a)
    path_b = _session_root(archive_root, ticker, session_b)
    if path_a is None:
        raise CompareValidationError(f"Session not found: {ticker} {session_a}")
    if path_b is None:
        raise CompareValidationError(f"Session not found: {ticker} {session_b}")

    model_a = path_a / "data" / "valuation_model.json"
    model_b = path_b / "data" / "valuation_model.json"
    missing = []
    if not model_a.is_file():
        missing.append(f"{session_a} (data/valuation_model.json)")
    if not model_b.is_file():
        missing.append(f"{session_b} (data/valuation_model.json)")
    if missing:
        raise CompareValidationError(
            "Both sessions need data/valuation_model.json. Missing: " + ", ".join(missing)
        )

    degraded = not (path_a / "meta" / "prediction_snapshot.json").is_file() or not (
        path_b / "meta" / "prediction_snapshot.json"
    ).is_file()

    existing = _find_pair(archive_root, ticker, session_a, session_b)
    if existing and existing.get("status") == "running" and not force:
        return existing
    if existing and existing.get("status") == "complete" and not force:
        return existing

    backend = spawn or default_spawn_backend()
    from packages.compare_jobs.spawn import GrokSpawnBackend

    if isinstance(backend, GrokSpawnBackend) and not grok_binary():
        raise GrokMissing(
            "Grok CLI not found. Install grok, set GROK_BIN, or set COMPARE_SPAWN=fake."
        )

    try:
        with claim_start(archive_root, "compare"):
            existing = _find_pair(archive_root, ticker, session_a, session_b)
            if existing and existing.get("status") == "running" and not force:
                return existing
            if existing and existing.get("status") == "complete" and not force:
                return existing
            return _spawn_compare(
                archive_root,
                ticker=ticker,
                session_a=session_a,
                session_b=session_b,
                path_a=path_a,
                path_b=path_b,
                degraded=degraded,
                backend=backend,
                project_root=project_root,
            )
    except JobsBusy as e:
        raise CompareBusy(str(e)) from e


def _spawn_compare(
    archive_root: Path,
    *,
    ticker: str,
    session_a: str,
    session_b: str,
    path_a: Path,
    path_b: Path,
    degraded: bool,
    backend: SpawnBackend,
    project_root: Path | None,
) -> dict[str, Any]:
    packet_key = allocate_compare_key(
        ticker,
        session_a,
        session_b,
        asof=_today(),
        output_dir=_output_dir(archive_root),
    )
    out_dir = compare_packet_dir(ticker, packet_key, _output_dir(archive_root))
    out_dir.mkdir(parents=True, exist_ok=True)
    cid = compare_id(ticker, packet_key)
    proj = str((project_root or PROJECT_ROOT).resolve())
    job: dict[str, Any] = {
        "compare_id": cid,
        "ticker": ticker,
        "packet_key": packet_key,
        "asof": _today(),
        "session_a": session_a,
        "session_b": session_b,
        "run_id_a": f"research:{ticker}:{session_a}",
        "run_id_b": f"research:{ticker}:{session_b}",
        "path_a": str(path_a.resolve()),
        "path_b": str(path_b.resolve()),
        "out_dir": str(out_dir.resolve()),
        "status": "queued",
        "degraded": degraded,
        "pid": None,
        "grok_session_id": None,
        "command": None,
        "project_root": proj,
        "spawned_at": None,
        "updated_at": _utc_now(),
        "error": None,
        "headline_ready": False,
        "synthesis_ready": False,
    }
    (out_dir / "prompt.md").write_text(_build_prompt(job), encoding="utf-8")
    try:
        headline = headline_for_sessions(
            ticker, [(session_a, path_a), (session_b, path_b)]
        )
        _atomic_write_json(out_dir / "headline.json", headline)
        job["headline_ready"] = True
        job["degraded"] = bool(degraded or headline.get("degraded"))
    except Exception as e:  # noqa: BLE001
        job["headline_ready"] = False
        job["error"] = f"headline failed: {e}"

    _atomic_write_json(out_dir / JOB_NAME, job)

    try:
        result = backend.spawn(job)
    except FileNotFoundError as e:
        job["status"] = "failed"
        job["error"] = str(e)
        job["updated_at"] = _utc_now()
        _atomic_write_json(out_dir / JOB_NAME, job)
        raise GrokMissing(str(e)) from e
    except Exception as e:  # noqa: BLE001
        job["status"] = "failed"
        job["error"] = str(e)
        job["updated_at"] = _utc_now()
        _atomic_write_json(out_dir / JOB_NAME, job)
        raise CompareError(str(e)) from e

    job["pid"] = result.pid
    job["grok_session_id"] = result.grok_session_id
    job["command"] = result.command
    job["status"] = "running"
    job["spawned_at"] = _utc_now()
    job["updated_at"] = job["spawned_at"]
    _atomic_write_json(out_dir / JOB_NAME, job)
    return refresh_compare(archive_root, cid, job=job)


def cancel_compare(archive_root: Path, compare_id_value: str) -> dict[str, Any]:
    job = get_compare(archive_root, compare_id_value)
    if job.get("status") in TERMINAL:
        return job
    kill_pid(job.get("pid"))
    job["status"] = "cancelled"
    job["updated_at"] = _utc_now()
    job["error"] = "cancelled"
    out_dir = Path(str(job["out_dir"]))
    _atomic_write_json(out_dir / JOB_NAME, job)
    return job

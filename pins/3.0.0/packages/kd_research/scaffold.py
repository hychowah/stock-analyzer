"""Create a research session folder under archive/research/.

Library entry used by Mode A CLI and Mode B Analyze. The CLI wrapper is
``scripts/scaffold_session.py``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from packages.kd_research.paths import (
    allocate_session_key,
    ensure_archive_tree,
    make_session_key,
    parse_session_key,
    rel_to_project,
    run_id as make_run_id,
    session_dir_nonempty,
    session_root,
)
from packages.kd_research.phase_status import write_phase_status_skeleton
from packages.kd_research.provenance import capture_harness_provenance, resolve_scaffold_models

SUBDIRS = [
    "reports",
    "data/compute",
    "data/raw_sec",
    "data/transcripts",
    "charts",
    "registry/handoffs",
    "registry/raw",
    "meta",
]


def _write_manifest_stub(
    root: Path,
    *,
    ticker: str,
    session_date: str,
    session_key: str,
    experiment_id: str | None,
    experiment_label: str | None,
    replicate: int | None,
    orchestrator_model: str,
    default_subagent_model: str,
    notes: str | None,
    layout: str = "archive",
) -> Path:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    prov = capture_harness_provenance()
    rid = make_run_id(ticker, session_key)
    manifest: dict[str, Any] = {
        "schema_version": 2,
        "run_id": rid,
        "product": "research",
        "ticker": ticker.upper(),
        "quote_symbol": None,
        "session_date": session_date,
        "session_key": session_key,
        "created_at": now,
        "completed_at": None,
        "harness_version": prov.get("harness_version"),
        "harness_spec": prov.get("harness_spec") or "v2",
        "paths": {
            "session_root": rel_to_project(root),
            "reports": "reports/",
            "valuation": "data/valuation_model.json",
            "audit": "registry/audit.json",
            "prediction_snapshot": "meta/prediction_snapshot.json",
        },
        "status": "scaffolded",
        "audit_verdict": None,
        "immutable": False,
        "layout": layout,
        "experiment_id": experiment_id,
        "experiment_label": experiment_label or experiment_id,
        "replicate": replicate,
        "harness_git_sha": prov.get("harness_git_sha") or "unknown",
        "harness_dirty": prov.get("harness_dirty"),
        "agents_md_sha256": prov.get("agents_md_sha256"),
        "research_agents_sha256": prov.get("research_agents_sha256"),
        "prompts_sha256": prov.get("prompts_sha256"),
        "version_file_sha256": prov.get("version_file_sha256"),
        "orchestrator_model": orchestrator_model,
        "default_subagent_model": default_subagent_model,
        "model_map": None,
        "temperature": None,
        "seed": None,
        "notes": notes,
    }
    path = root / "meta" / "run_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _write_session_isolation(
    root: Path,
    *,
    ticker: str,
    session_date: str,
    session_key: str,
) -> Path:
    """Default: share freely inside S/; prior sessions must not feed valuation."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "schema_version": 1,
        "mode": "isolated",
        "ticker": ticker.upper(),
        "session_date": session_date,
        "session_key": session_key,
        "created_at": now,
        "allow_prior_session_keys": [],
        "rules": {
            "intra_session_share": True,
            "prior_valuation_as_input": False,
            "prior_for_post_audit_compare": True,
            "library_bind_into_session": True,
            "library_direct_read": False,
            "prior_session_documents_as_input": False,
        },
        "notes": (
            "Agents within this session share registry/handoffs/data. "
            "Do not open or list other session_keys under archive/research/ "
            "(including yesterday) unless the user explicitly resumes that folder "
            "or asks for post-finalize compare. "
            "Prior FV/MoS/probs/WACC/thesis are not inputs to any phase. "
            "Filings and transcripts for this run live under S/data/raw_sec and "
            "S/data/transcripts (bound by orchestrator code). Do not mine other "
            "archive trees for documents or judgments."
        ),
    }
    path = root / "registry" / "session_isolation.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def scaffold(
    ticker: str,
    session_date: str,
    output_dir: str | Path | None = None,
    force: bool = False,
    *,
    slug: str | None = None,
    experiment_id: str | None = None,
    experiment_label: str | None = None,
    replicate: int | None = None,
    orchestrator_model: str | None = None,
    default_subagent_model: str | None = None,
    notes: str | None = None,
    auto_replicate: bool = True,
) -> Path:
    """Create archive/research/<TICKER>/<SESSION_KEY>/ and stamp the manifest.

    Callers existence-check the ticker first. This function only writes.
    quote_symbol stays null until the orchestrator confirms a live listing.

    Raises ValueError / RuntimeError / FileExistsError on validation failures
    (never SystemExit — callers map to CLI codes).
    """
    orch_id, sub_id = resolve_scaffold_models(orchestrator_model, default_subagent_model)

    if "__" in session_date and slug is None:
        session_date, slug = parse_session_key(session_date)

    ensure_archive_tree(output_dir)

    if slug:
        session_key = make_session_key(session_date, slug)
    else:
        session_key = allocate_session_key(
            ticker,
            session_date,
            None,
            output_dir=output_dir,
            auto_replicate=auto_replicate and not force,
        )

    date_only, _ = parse_session_key(session_key)
    root = session_root(ticker, session_key, output_dir)

    if session_dir_nonempty(root) and not force:
        raise FileExistsError(
            f"Refusing to overwrite existing session folder: {root}\n"
            "Pass a free --slug, omit --slug for auto __rN on same day, "
            "or --force only for broken empty scaffolds."
        )

    for sub in SUBDIRS:
        (root / sub).mkdir(parents=True, exist_ok=True)
    write_phase_status_skeleton(root, ticker, date_only)
    _write_session_isolation(
        root,
        ticker=ticker,
        session_date=date_only,
        session_key=session_key,
    )
    _write_manifest_stub(
        root,
        ticker=ticker,
        session_date=date_only,
        session_key=session_key,
        experiment_id=experiment_id,
        experiment_label=experiment_label,
        replicate=replicate,
        orchestrator_model=orch_id,
        default_subagent_model=sub_id,
        notes=notes,
        layout="archive",
    )
    return root

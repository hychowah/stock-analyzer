#!/usr/bin/env python3
"""Create the session folder structure for a research session.

Usage:
    python scripts/scaffold_session.py --ticker JPM --date 2026-07-25

    # Controlled experiment / replicate (same calendar date, distinct folder)
    python scripts/scaffold_session.py --ticker META --date 2026-08-10 \\
      --experiment exp-model-bakeoff --slug model-grok45 --replicate 1 \\
      --orchestrator-model grok-4.5

Creates archive/research/<TICKER>/<SESSION_KEY>/{reports,data/...,charts,registry,meta},
writes registry/phase_status.json (resume skeleton), meta/run_manifest.json (provenance
stub), and refuses to overwrite an existing non-empty session folder.

Legacy path (root/<TICKER>/<KEY>) is only used with --legacy.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.kd_research.paths import (  # noqa: E402
    ensure_archive_tree,
    make_session_key,
    parse_session_key,
    rel_to_project,
    run_id as make_run_id,
    session_root,
)
from scripts.kd_research.phase_status import write_phase_status_skeleton  # noqa: E402
from scripts.kd_research.provenance import capture_harness_provenance  # noqa: E402

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
    orchestrator_model: str | None,
    default_subagent_model: str | None,
    notes: str | None,
    layout: str,
) -> Path:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    prov = capture_harness_provenance()
    rid = make_run_id(ticker, session_key)
    manifest: dict[str, Any] = {
        "schema_version": 2,
        "run_id": rid,
        "product": "research",
        "ticker": ticker.upper(),
        "session_date": session_date,
        "session_key": session_key,
        "created_at": now,
        "completed_at": None,
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
        "harness_git_sha": prov.get("harness_git_sha"),
        "harness_dirty": prov.get("harness_dirty"),
        "agents_md_sha256": prov.get("agents_md_sha256"),
        "prompts_sha256": prov.get("prompts_sha256"),
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


def scaffold(
    ticker: str,
    session_date: str,
    output_dir: str | None = None,
    force: bool = False,
    *,
    legacy: bool = False,
    slug: str | None = None,
    experiment_id: str | None = None,
    experiment_label: str | None = None,
    replicate: int | None = None,
    orchestrator_model: str | None = None,
    default_subagent_model: str | None = None,
    notes: str | None = None,
) -> Path:
    # Allow passing full session_key as --date for convenience
    if "__" in session_date and slug is None:
        session_date, slug = parse_session_key(session_date)

    session_key = make_session_key(session_date, slug)
    date_only, _ = parse_session_key(session_key)

    if not legacy:
        ensure_archive_tree(output_dir)
    prefer = "legacy" if legacy else "archive"
    root = session_root(ticker, session_key, output_dir, prefer=prefer)
    if root.exists() and any(root.iterdir()) and not force:
        raise SystemExit(
            f"Refusing to overwrite existing session folder: {root}\n"
            "Use a new date, a new --slug for experiments, or pass --force if you really mean it."
        )
    for sub in SUBDIRS:
        (root / sub).mkdir(parents=True, exist_ok=True)
    write_phase_status_skeleton(root, ticker, date_only)
    _write_manifest_stub(
        root,
        ticker=ticker,
        session_date=date_only,
        session_key=session_key,
        experiment_id=experiment_id,
        experiment_label=experiment_label,
        replicate=replicate,
        orchestrator_model=orchestrator_model,
        default_subagent_model=default_subagent_model,
        notes=notes,
        layout="legacy" if legacy else "archive",
    )
    return root


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker", required=True)
    ap.add_argument(
        "--date",
        required=True,
        help="As-of session date YYYY-MM-DD (or full session_key date__slug)",
    )
    ap.add_argument(
        "--slug",
        default=None,
        help="Optional run slug → folder date__slug (experiments / same-day replicates)",
    )
    ap.add_argument(
        "--experiment",
        dest="experiment_id",
        default=None,
        help="Experiment id grouping A/B runs in the compare DB",
    )
    ap.add_argument(
        "--experiment-label",
        default=None,
        help="Human label for the experiment (default: --experiment value)",
    )
    ap.add_argument(
        "--replicate",
        type=int,
        default=None,
        help="Replicate number within an experiment (1..N)",
    )
    ap.add_argument(
        "--orchestrator-model",
        default=None,
        help="Model id for the main/orchestrator agent (free text for now)",
    )
    ap.add_argument(
        "--subagent-model",
        dest="default_subagent_model",
        default=None,
        help="Default model id for subagents when uniform",
    )
    ap.add_argument(
        "--notes",
        default=None,
        help="Why this run exists (bakeoff axis, hypothesis, etc.)",
    )
    ap.add_argument(
        "--output-dir",
        default=None,
        help="Project root override (default: workspace root). "
        "Sessions are written under <root>/archive/research/ unless --legacy.",
    )
    ap.add_argument(
        "--legacy",
        action="store_true",
        help="Write to root/<TICKER>/<KEY> instead of archive/research/ (tests/compat).",
    )
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    root = scaffold(
        args.ticker,
        args.date,
        args.output_dir,
        args.force,
        legacy=args.legacy,
        slug=args.slug,
        experiment_id=args.experiment_id,
        experiment_label=args.experiment_label,
        replicate=args.replicate,
        orchestrator_model=args.orchestrator_model,
        default_subagent_model=args.default_subagent_model,
        notes=args.notes,
    )
    print(f"Session scaffolded: {root}")
    for sub in SUBDIRS:
        print(f"  {root / sub}/")
    print(f"  {root / 'registry' / 'phase_status.json'}")
    print(f"  {root / 'meta' / 'run_manifest.json'}")


if __name__ == "__main__":
    main()

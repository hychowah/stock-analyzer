#!/usr/bin/env python3
"""Build meta/prediction_snapshot.json + meta/run_manifest.json from a session.

Hermetic: reads only session files on disk. Does not fetch live market data.

Usage:
    python3 scripts/build_prediction_snapshot.py --ticker META --date 2026-08-03
    python3 scripts/build_prediction_snapshot.py --session-dir archive/research/META/2026-08-03
    python3 scripts/build_prediction_snapshot.py --all
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
    iter_research_sessions,
    rel_to_project,
    resolve_session,
    run_id as make_run_id,
)
from scripts.kd_research.provenance import capture_harness_provenance  # noqa: E402
from scripts.kd_research.session_extract import extract_session_bundle, load_json  # noqa: E402


_PROVENANCE_IDENTITY_KEYS = (
    "harness_version",
    "harness_spec",
    "harness_git_sha",
    "harness_dirty",
    "agents_md_sha256",
    "research_agents_sha256",
    "prompts_sha256",
    "version_file_sha256",
)

_PROVENANCE_EXPERIMENT_KEYS = (
    "experiment_id",
    "experiment_label",
    "replicate",
    "orchestrator_model",
    "default_subagent_model",
    "model_map",
    "temperature",
    "seed",
    "notes",
)


def _merge_provenance(
    existing: dict[str, Any],
    from_bundle: dict[str, Any],
) -> dict[str, Any]:
    """Prefer scaffold/manifest experiment knobs; always refresh version/git at finalize."""
    live = capture_harness_provenance()
    out = dict(existing)
    # Experiment knobs: keep existing unless empty
    for k in _PROVENANCE_EXPERIMENT_KEYS:
        if out.get(k) in (None, "") and from_bundle.get(k) not in (None, ""):
            out[k] = from_bundle.get(k)
    # Always refresh harness identity + fingerprints at snapshot time
    for k in _PROVENANCE_IDENTITY_KEYS:
        if live.get(k) is not None:
            out[k] = live[k]
    if not out.get("harness_version"):
        out["harness_version"] = live.get("harness_version") or from_bundle.get("harness_version")
    if not out.get("harness_spec"):
        out["harness_spec"] = live.get("harness_spec") or from_bundle.get("harness_spec") or "v2"
    if not out.get("harness_git_sha"):
        out["harness_git_sha"] = live.get("harness_git_sha") or "unknown"
    if out.get("harness_dirty") is None:
        out["harness_dirty"] = live.get("harness_dirty")
        if out["harness_dirty"] is None:
            out["harness_dirty"] = True
    return out


def build_for_session(session: Path, *, force: bool = False) -> dict[str, Any]:
    session = session.resolve()
    bundle = extract_session_bundle(session)
    ticker = bundle["ticker"]
    session_key = bundle["session_key"]
    session_date = bundle["session_date"]
    rid = make_run_id(ticker, session_key)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    gaps = list(bundle.get("gaps") or [])

    layout = "archive" if "archive/research" in session.as_posix() else "legacy"
    existing_manifest = load_json(session / "meta" / "run_manifest.json") or {}
    prov = _merge_provenance(existing_manifest, bundle.get("provenance") or {})

    snapshot = {
        "schema_version": 2,
        "run_id": rid,
        "ticker": ticker,
        "session_date": session_date,
        "session_key": session_key,
        "built_at": now,
        "asof_price": bundle.get("asof_price"),
        "asof_price_source": bundle.get("asof_price_source"),
        "currency": bundle.get("currency") or "",
        "fair_value": bundle.get("fair_value") or {},
        "scenario_probabilities": bundle.get("scenario_probabilities") or {},
        "margin_of_safety_pct": bundle.get("margin_of_safety_pct"),
        "verdict_line": bundle.get("verdict_line") or "",
        "primary_sector": bundle.get("primary_sector") or "",
        "region": bundle.get("region") or "",
        "intensity": bundle.get("intensity") or "",
        "key_risks": bundle.get("key_risks") or [],
        "peers": bundle.get("peers") or [],
        "benchmark": bundle.get("benchmark") or "",
        "data_quality": bundle.get("data_quality") or "ok",
        "audit_verdict": bundle.get("audit_verdict"),
        "priced_for_perfection": bundle.get("priced_for_perfection"),
        "decision_usefulness": bundle.get("decision_usefulness"),
        "decision_action": bundle.get("decision_action"),
        "kill_triggers": bundle.get("kill_triggers") or [],
        "model_name": bundle.get("model_name"),
        **(
            {"roic_identity": bundle["roic_identity"]}
            if bundle.get("roic_identity") is not None
            else {}
        ),
        "tech_signal": bundle.get("tech_signal"),
        "tech_regime": bundle.get("tech_regime"),
        "tech_summary": bundle.get("tech_summary") or {},
        "research_depth": bundle.get("research_depth"),
        "provenance": prov,
        "gaps": gaps,
        "source_paths": {
            "valuation": "data/valuation_model.json",
            "technical": "registry/technical.json",
            "sector_config": "registry/sector_config.json",
            "market_context": "registry/market_context.json",
            "audit": "registry/audit.json",
            "risk_bridge": "registry/risk_bridge.json",
            "price_snapshot": "data/price_snapshot.json",
        },
    }

    status = bundle.get("status") or existing_manifest.get("status") or "unknown"
    if bundle.get("audit_verdict") == "PASS":
        status = "complete"
    elif bundle.get("audit_verdict"):
        status = "audited"

    manifest = {
        "schema_version": max(2, int(existing_manifest.get("schema_version") or 1)),
        "run_id": rid,
        "product": "research",
        "ticker": ticker,
        "session_date": session_date,
        "session_key": session_key,
        "created_at": existing_manifest.get("created_at") or now,
        "completed_at": now,
        "harness_version": prov.get("harness_version"),
        "harness_spec": prov.get("harness_spec") or "v2",
        "paths": {
            "session_root": rel_to_project(session),
            "reports": "reports/",
            "valuation": "data/valuation_model.json",
            "audit": "registry/audit.json",
            "prediction_snapshot": "meta/prediction_snapshot.json",
        },
        "status": status,
        "audit_verdict": bundle.get("audit_verdict"),
        "immutable": bundle.get("audit_verdict") == "PASS",
        "layout": layout,
        "experiment_id": prov.get("experiment_id"),
        "experiment_label": prov.get("experiment_label"),
        "replicate": prov.get("replicate"),
        "harness_git_sha": prov.get("harness_git_sha") or "unknown",
        "harness_dirty": prov.get("harness_dirty"),
        "agents_md_sha256": prov.get("agents_md_sha256"),
        "research_agents_sha256": prov.get("research_agents_sha256"),
        "prompts_sha256": prov.get("prompts_sha256"),
        "version_file_sha256": prov.get("version_file_sha256"),
        "orchestrator_model": prov.get("orchestrator_model"),
        "default_subagent_model": prov.get("default_subagent_model"),
        "model_map": prov.get("model_map"),
        "temperature": prov.get("temperature"),
        "seed": prov.get("seed"),
        "notes": prov.get("notes"),
    }
    # Keep snapshot provenance in sync with finalized manifest
    snapshot["provenance"] = {
        k: prov.get(k)
        for k in (
            "experiment_id",
            "experiment_label",
            "replicate",
            "harness_version",
            "harness_spec",
            "harness_git_sha",
            "harness_dirty",
            "agents_md_sha256",
            "research_agents_sha256",
            "prompts_sha256",
            "version_file_sha256",
            "orchestrator_model",
            "default_subagent_model",
            "model_map",
            "temperature",
            "seed",
            "notes",
        )
    }

    meta = session / "meta"
    meta.mkdir(parents=True, exist_ok=True)
    snap_path = meta / "prediction_snapshot.json"
    man_path = meta / "run_manifest.json"
    if snap_path.exists() and not force:
        # Snapshots are projections; always rewrite from disk for hermetic consistency
        pass
    snap_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    man_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"session": str(session), "run_id": rid, "gaps": gaps, "snapshot": snapshot}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker")
    ap.add_argument("--date", help="Session date or session_key (YYYY-MM-DD or YYYY-MM-DD__slug)")
    ap.add_argument("--session-dir")
    ap.add_argument("--all", action="store_true", help="All discovered sessions (archive + legacy)")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    results = []
    if args.all:
        sessions = iter_research_sessions(include_legacy=True)
        for _t, _d, path in sessions:
            results.append(build_for_session(path, force=args.force))
    elif args.session_dir:
        results.append(build_for_session(Path(args.session_dir), force=args.force))
    elif args.ticker and args.date:
        path = resolve_session(args.ticker, args.date)
        if path is None:
            print(f"Session not found: {args.ticker} {args.date}", file=sys.stderr)
            return 2
        results.append(build_for_session(path, force=args.force))
    else:
        ap.error("pass --all, --session-dir, or --ticker and --date")

    for r in results:
        gap_note = f" gaps={r['gaps']}" if r["gaps"] else ""
        print(f"OK {r['run_id']} -> {r['session']}/meta/{gap_note}")
    print(f"Built {len(results)} snapshot(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

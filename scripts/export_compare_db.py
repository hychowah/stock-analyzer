#!/usr/bin/env python3
"""Export finished research sessions into archive/catalog/research_compare.sqlite.

Disk remains system of record. This DB is a rebuildable projection for comparison + UI.

Usage:
    python3 scripts/export_compare_db.py --ticker SOFI --date 2026-08-09
    python3 scripts/export_compare_db.py --session-dir archive/research/SOFI/2026-08-09
    python3 scripts/export_compare_db.py --all --rebuild
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.build_prediction_snapshot import build_for_session  # noqa: E402
from scripts.kd_research.compare_db import (  # noqa: E402
    compute_run_metrics,
    count_runs,
    db_path,
    ensure_experiment,
    open_db,
    replace_run_metrics,
    row_from_export_payload,
    upsert_run,
    utc_now,
)
from scripts.kd_research.roic_identity import thin_roic_metrics  # noqa: E402
from scripts.kd_research.paths import (  # noqa: E402
    iter_research_sessions,
    rel_to_project,
    resolve_session,
    run_id as make_run_id,
)
from scripts.kd_research.session_extract import extract_session_bundle  # noqa: E402


def _payload_for_session(session: Path, *, refresh_snapshot: bool = True) -> dict[str, Any]:
    session = session.resolve()
    if refresh_snapshot:
        build_for_session(session, force=True)

    bundle = extract_session_bundle(session)
    ticker = bundle["ticker"]
    session_key = bundle["session_key"]
    rid = make_run_id(ticker, session_key)
    fv = bundle.get("fair_value") or {}
    probs = bundle.get("scenario_probabilities") or {}
    prov = bundle.get("provenance") or {}

    extras = {
        "key_risks": bundle.get("key_risks") or [],
        "asof_price_source": bundle.get("asof_price_source"),
        "gaps": bundle.get("gaps") or [],
        "experiment_label": prov.get("experiment_label"),
    }
    ident = bundle.get("roic_identity")
    if isinstance(ident, dict):
        extras["roic_identity"] = ident
        if ident.get("cheap_claim"):
            extras["roic_cheap_claim"] = ident.get("cheap_claim")
        if ident.get("quality_bucket"):
            extras["roic_quality_bucket"] = ident.get("quality_bucket")
    if bundle.get("decision_usefulness"):
        extras["decision_usefulness"] = bundle.get("decision_usefulness")
    if bundle.get("priced_for_perfection") is not None:
        extras["priced_for_perfection"] = bundle.get("priced_for_perfection")
    if bundle.get("decision_action"):
        extras["decision_action"] = bundle.get("decision_action")
    if bundle.get("kill_triggers"):
        extras["kill_triggers"] = bundle.get("kill_triggers")

    payload: dict[str, Any] = {
        "run_id": rid,
        "ticker": ticker,
        "session_date": bundle["session_date"],
        "session_key": session_key,
        "path": rel_to_project(session),
        "experiment_id": prov.get("experiment_id"),
        "replicate": prov.get("replicate"),
        "exported_at": utc_now(),
        "audit_verdict": bundle.get("audit_verdict"),
        "data_quality": bundle.get("data_quality"),
        "status": bundle.get("status"),
        "harness_version": prov.get("harness_version"),
        "harness_spec": prov.get("harness_spec"),
        "harness_git_sha": prov.get("harness_git_sha"),
        "harness_dirty": prov.get("harness_dirty"),
        "agents_md_sha256": prov.get("agents_md_sha256"),
        "prompts_sha256": prov.get("prompts_sha256"),
        "orchestrator_model": prov.get("orchestrator_model"),
        "default_subagent_model": prov.get("default_subagent_model"),
        "model_map": prov.get("model_map"),
        "temperature": prov.get("temperature"),
        "seed": prov.get("seed"),
        "research_depth": bundle.get("research_depth"),
        "notes": prov.get("notes"),
        "asof_price": bundle.get("asof_price"),
        "currency": bundle.get("currency"),
        "primary_sector": bundle.get("primary_sector") or None,
        "region": bundle.get("region") or None,
        "intensity": bundle.get("intensity") or None,
        "benchmark": bundle.get("benchmark") or None,
        "peers": bundle.get("peers") or [],
        "fv_bear": fv.get("bear"),
        "fv_base": fv.get("base"),
        "fv_bull": fv.get("bull"),
        "fv_weighted": fv.get("probability_weighted"),
        "p_bear": probs.get("bear"),
        "p_base": probs.get("base"),
        "p_bull": probs.get("bull"),
        "margin_of_safety_pct": bundle.get("margin_of_safety_pct"),
        "model_name": bundle.get("model_name"),
        "priced_for_perfection": bundle.get("priced_for_perfection"),
        "decision_usefulness": bundle.get("decision_usefulness"),
        "verdict_line": bundle.get("verdict_line"),
        "tech_signal": bundle.get("tech_signal"),
        "tech_regime": bundle.get("tech_regime"),
        "tech_summary": bundle.get("tech_summary"),
        "extras": extras,
        "snapshot_path": f"{rel_to_project(session)}/meta/prediction_snapshot.json",
        "manifest_path": f"{rel_to_project(session)}/meta/run_manifest.json",
    }
    return payload


def export_session(
    session: Path,
    conn,
    *,
    refresh_snapshot: bool = True,
) -> dict[str, Any]:
    payload = _payload_for_session(session, refresh_snapshot=refresh_snapshot)
    if payload.get("experiment_id"):
        ensure_experiment(
            conn,
            payload["experiment_id"],
            label=(payload.get("extras") or {}).get("experiment_label")
            or payload["experiment_id"],
        )
    row = row_from_export_payload(payload)
    upsert_run(conn, row)
    metrics = compute_run_metrics(row)
    extras = payload.get("extras") or {}
    metrics.update(thin_roic_metrics({"roic_identity": extras.get("roic_identity")}))
    replace_run_metrics(conn, row["run_id"], metrics)
    return {
        "run_id": row["run_id"],
        "path": row["path"],
        "asof_price": row.get("asof_price"),
        "fv_base": row.get("fv_base"),
        "fv_weighted": row.get("fv_weighted"),
        "audit_verdict": row.get("audit_verdict"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker")
    ap.add_argument("--date", help="Session date or session_key")
    ap.add_argument("--session-dir")
    ap.add_argument("--all", action="store_true", help="Export all discovered sessions")
    ap.add_argument(
        "--rebuild",
        action="store_true",
        help="Delete existing SQLite DB and recreate schema before export",
    )
    ap.add_argument(
        "--no-refresh-snapshot",
        action="store_true",
        help="Do not rewrite meta/prediction_snapshot.json (use existing extract only)",
    )
    ap.add_argument(
        "--archive-only",
        action="store_true",
        help="With --all, only archive/research (skip legacy root sessions)",
    )
    ap.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Project root whose archive/ receives the sqlite "
        "(default: repo root). Use eng/fixtures for CI fixtures.",
    )
    args = ap.parse_args()

    refresh = not args.no_refresh_snapshot
    out = args.output_dir
    conn = open_db(out, rebuild=args.rebuild)

    sessions: list[Path] = []
    if args.all:
        for _t, _d, path in iter_research_sessions(
            out, include_legacy=not args.archive_only
        ):
            sessions.append(path)
    elif args.session_dir:
        sessions.append(Path(args.session_dir))
    elif args.ticker and args.date:
        path = resolve_session(args.ticker, args.date, out)
        if path is None:
            print(f"Session not found: {args.ticker} {args.date}", file=sys.stderr)
            return 2
        sessions.append(path)
    else:
        ap.error("pass --all, --session-dir, or --ticker and --date")

    results = []
    for s in sessions:
        try:
            results.append(export_session(s, conn, refresh_snapshot=refresh))
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {s}: {e}", file=sys.stderr)
            raise
    conn.commit()

    for r in results:
        print(
            f"OK {r['run_id']} price={r.get('asof_price')} "
            f"fv_base={r.get('fv_base')} weighted={r.get('fv_weighted')} "
            f"audit={r.get('audit_verdict')}"
        )

    n = count_runs(conn)
    conn.close()
    print(f"Exported {len(results)} session(s); DB has {n} run(s) -> {db_path(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Rebuild archive/catalog/runs_index.json and tickers_index.json from disk.

Usage:
    python3 scripts/rebuild_catalog.py
    python3 scripts/rebuild_catalog.py --include-legacy
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
    is_production_session_key,
    iter_research_sessions,
    outcomes_root,
    parse_session_key,
    rel_to_project,
    run_id as make_run_id,
)


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001
        return None


def _row_for_session(ticker: str, session_key: str, path: Path) -> dict[str, Any]:
    rid = make_run_id(ticker, session_key)
    session_date, slug = parse_session_key(session_key)
    snap = _load_json(path / "meta" / "prediction_snapshot.json")
    audit = _load_json(path / "registry" / "audit.json")
    sector = _load_json(path / "registry" / "sector_config.json")
    market = _load_json(path / "registry" / "market_context.json")
    valuation = _load_json(path / "data" / "valuation_model.json")
    manifest = _load_json(path / "meta" / "run_manifest.json")

    outcomes_dir = outcomes_root() / ticker / session_key
    if not outcomes_dir.is_dir():
        # also try plain date for outcomes keyed historically by date
        outcomes_dir = outcomes_root() / ticker / session_date
    has_outcomes = outcomes_dir.is_dir() and (
        (outcomes_dir / "price_path.json").is_file()
        or (outcomes_dir / "scorecard.json").is_file()
        or any(outcomes_dir.iterdir())
    )

    fv_base = None
    fv_weighted = None
    fv_bear = None
    fv_bull = None
    p_bear = p_base = p_bull = None
    mos = None
    asof = None
    tech_signal = None
    experiment_id = None
    orchestrator_model = None

    if snap:
        fv = snap.get("fair_value") or {}
        if isinstance(fv, dict):
            fv_base = fv.get("base")
            fv_weighted = fv.get("probability_weighted")
            fv_bear = fv.get("bear")
            fv_bull = fv.get("bull")
        probs = snap.get("scenario_probabilities") or {}
        if isinstance(probs, dict):
            p_bear, p_base, p_bull = probs.get("bear"), probs.get("base"), probs.get("bull")
        mos = snap.get("margin_of_safety_pct")
        asof = snap.get("asof_price")
        audit_verdict = snap.get("audit_verdict")
        primary_sector = snap.get("primary_sector") or None
        region = snap.get("region") or None
        tech_signal = snap.get("tech_signal")
        prov = snap.get("provenance") or {}
        if isinstance(prov, dict):
            experiment_id = prov.get("experiment_id")
            orchestrator_model = prov.get("orchestrator_model")
    else:
        audit_verdict = (audit or {}).get("verdict") if audit else None
        primary_sector = (sector or {}).get("primary_sector") if sector else None
        region = (market or {}).get("primary_region") if market else None
        if valuation:
            fv = valuation.get("fair_value") or {}
            if isinstance(fv, dict):
                fv_base = fv.get("base")
                fv_weighted = fv.get("probability_weighted")
                fv_bear = fv.get("bear")
                fv_bull = fv.get("bull")
                mos = fv.get("margin_of_safety_pct")

    if manifest:
        experiment_id = experiment_id or manifest.get("experiment_id")
        orchestrator_model = orchestrator_model or manifest.get("orchestrator_model")

    return {
        "run_id": rid,
        "ticker": ticker,
        "session_date": session_date,
        "session_key": session_key,
        "is_production": is_production_session_key(session_key),
        "slug": slug,
        "path": rel_to_project(path),
        "audit_verdict": audit_verdict,
        "asof_price": asof,
        "fv_bear": fv_bear,
        "fv_base": fv_base,
        "fv_bull": fv_bull,
        "fv_weighted": fv_weighted,
        "p_bear": p_bear,
        "p_base": p_base,
        "p_bull": p_bull,
        "margin_of_safety_pct": mos,
        "primary_sector": primary_sector,
        "region": region,
        "tech_signal": tech_signal,
        "experiment_id": experiment_id,
        "orchestrator_model": orchestrator_model,
        "has_prediction_snapshot": snap is not None,
        "has_outcomes": has_outcomes,
    }


def rebuild(*, include_legacy: bool = True) -> dict[str, Any]:
    dirs = ensure_archive_tree()
    sessions = iter_research_sessions(include_legacy=include_legacy)
    runs = [_row_for_session(t, k, p) for t, k, p in sessions]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    runs_index = {
        "schema_version": 2,
        "updated_at": now,
        "runs": runs,
    }

    by_ticker: dict[str, list[dict[str, Any]]] = {}
    for r in runs:
        by_ticker.setdefault(r["ticker"], []).append(r)

    tickers: dict[str, Any] = {}
    for ticker, rows in sorted(by_ticker.items()):
        rows_sorted = sorted(rows, key=lambda x: (x["session_date"], x["session_key"]))
        # Latest production PASS preferred; else any PASS; else latest key
        prod = [r for r in rows_sorted if r.get("is_production")]
        prod_pass = [r for r in prod if r.get("audit_verdict") == "PASS"]
        any_pass = [r for r in rows_sorted if r.get("audit_verdict") == "PASS"]
        if prod_pass:
            latest = prod_pass[-1]
        elif prod:
            latest = prod[-1]
        elif any_pass:
            latest = any_pass[-1]
        else:
            latest = rows_sorted[-1]
        tickers[ticker] = {
            "ticker": ticker,
            "latest_run_id": latest["run_id"],
            "latest_path": latest["path"],
            "latest_audit": latest.get("audit_verdict"),
            "latest_session_date": latest["session_date"],
            "latest_session_key": latest["session_key"],
            "run_count": len(rows_sorted),
            "runs": [
                {
                    "run_id": r["run_id"],
                    "path": r["path"],
                    "session_date": r["session_date"],
                    "session_key": r["session_key"],
                    "is_production": r.get("is_production"),
                    "audit_verdict": r.get("audit_verdict"),
                    "experiment_id": r.get("experiment_id"),
                }
                for r in rows_sorted
            ],
        }

    tickers_index = {
        "schema_version": 2,
        "updated_at": now,
        "tickers": tickers,
    }

    catalog = dirs["catalog"]
    (catalog / "runs_index.json").write_text(
        json.dumps(runs_index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (catalog / "tickers_index.json").write_text(
        json.dumps(tickers_index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (catalog / "schema_version").write_text("2\n", encoding="utf-8")
    return {"n_runs": len(runs), "n_tickers": len(tickers), "catalog": str(catalog)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--include-legacy",
        action="store_true",
        default=True,
        help="Include root/<TICKER>/<DATE> sessions not yet migrated (default: true)",
    )
    ap.add_argument(
        "--archive-only",
        action="store_true",
        help="Only index archive/research sessions",
    )
    args = ap.parse_args()
    include_legacy = not args.archive_only
    result = rebuild(include_legacy=include_legacy)
    print(
        f"Catalog rebuilt: {result['n_runs']} runs, {result['n_tickers']} tickers -> {result['catalog']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

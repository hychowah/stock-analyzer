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
from scripts.kd_research.registry_io import atomic_write_text, load_json  # noqa: E402


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
    harness_version = None
    harness_git_sha = None

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
            harness_version = prov.get("harness_version")
            harness_git_sha = prov.get("harness_git_sha")
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
        harness_version = harness_version or manifest.get("harness_version")
        harness_git_sha = harness_git_sha or manifest.get("harness_git_sha")

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
        "harness_version": harness_version,
        "harness_git_sha": harness_git_sha,
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
    atomic_write_text(
        catalog / "runs_index.json",
        json.dumps(runs_index, indent=2, ensure_ascii=False) + "\n",
    )
    atomic_write_text(
        catalog / "tickers_index.json",
        json.dumps(tickers_index, indent=2, ensure_ascii=False) + "\n",
    )
    atomic_write_text(catalog / "schema_version", "2\n")
    return {
        "n_runs": len(runs),
        "n_tickers": len(tickers),
        "catalog": str(catalog),
        "mode": "full_scan",
        "include_legacy": include_legacy,
    }


def patch_run_into_catalog(
    ticker: str,
    session_key: str,
    path: Path,
    *,
    include_legacy_on_missing: bool = False,
) -> dict[str, Any]:
    """O(1)-ish upsert of one session into thin JSON indexes (atomic publish).

    If indexes are missing, falls back to full rebuild (archive-only by default).
    """
    dirs = ensure_archive_tree()
    catalog = dirs["catalog"]
    runs_path = catalog / "runs_index.json"
    tickers_path = catalog / "tickers_index.json"

    if not runs_path.is_file() or not tickers_path.is_file():
        return rebuild(include_legacy=include_legacy_on_missing)

    runs_index = load_json(runs_path) or {}
    tickers_index = load_json(tickers_path) or {}
    if not isinstance(runs_index, dict) or not isinstance(tickers_index, dict):
        return rebuild(include_legacy=include_legacy_on_missing)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    row = _row_for_session(ticker.upper(), session_key, path)
    rid = row["run_id"]

    runs: list[dict[str, Any]] = list(runs_index.get("runs") or [])
    runs = [r for r in runs if r.get("run_id") != rid]
    runs.append(row)
    runs.sort(key=lambda r: (r.get("ticker") or "", r.get("session_date") or "", r.get("session_key") or ""))
    runs_index = {"schema_version": 2, "updated_at": now, "runs": runs}

    # Rebuild tickers slice for this ticker only from runs list
    by_ticker: dict[str, list[dict[str, Any]]] = {}
    for r in runs:
        by_ticker.setdefault(str(r.get("ticker")), []).append(r)

    tickers = dict(tickers_index.get("tickers") or {})
    # Recompute all tickers present in runs (cheap for ~dozens–hundreds)
    new_tickers: dict[str, Any] = {}
    for t, rows in sorted(by_ticker.items()):
        rows_sorted = sorted(rows, key=lambda x: (x.get("session_date") or "", x.get("session_key") or ""))
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
        new_tickers[t] = {
            "ticker": t,
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
    tickers_index = {"schema_version": 2, "updated_at": now, "tickers": new_tickers}

    atomic_write_text(
        runs_path, json.dumps(runs_index, indent=2, ensure_ascii=False) + "\n"
    )
    atomic_write_text(
        tickers_path, json.dumps(tickers_index, indent=2, ensure_ascii=False) + "\n"
    )
    atomic_write_text(catalog / "schema_version", "2\n")
    return {
        "n_runs": len(runs),
        "n_tickers": len(new_tickers),
        "catalog": str(catalog),
        "mode": "patch",
        "patched_run_id": rid,
    }


def rebuild_from_sqlite(*, output_dir: Path | str | None = None) -> dict[str, Any]:
    """Rebuild thin JSON indexes from research_compare.sqlite (no full session scan).

    Faster recovery path when disk SoR is large but the warehouse is current.
    Paths in the index come from the sqlite ``path`` column.
    """
    import sqlite3

    from scripts.kd_research.compare_db import db_path
    from scripts.kd_research.paths import catalog_root, is_production_session_key

    path = db_path(output_dir)
    if not path.is_file():
        raise FileNotFoundError(f"Compare DB not found: {path}")

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    rows_db = conn.execute(
        """
        SELECT run_id, ticker, session_date, session_key, path,
               audit_verdict, asof_price, fv_bear, fv_base, fv_bull, fv_weighted,
               p_bear, p_base, p_bull, margin_of_safety_pct,
               primary_sector, region, tech_signal, experiment_id, orchestrator_model
        FROM runs
        ORDER BY ticker, session_date, session_key
        """
    ).fetchall()
    conn.close()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    runs: list[dict[str, Any]] = []
    for r in rows_db:
        sk = r["session_key"] or r["session_date"]
        runs.append(
            {
                "run_id": r["run_id"],
                "ticker": r["ticker"],
                "session_date": r["session_date"],
                "session_key": sk,
                "is_production": is_production_session_key(str(sk)),
                "slug": None
                if is_production_session_key(str(sk))
                else (str(sk).split("__", 1)[1] if "__" in str(sk) else None),
                "path": r["path"],
                "audit_verdict": r["audit_verdict"],
                "asof_price": r["asof_price"],
                "fv_bear": r["fv_bear"],
                "fv_base": r["fv_base"],
                "fv_bull": r["fv_bull"],
                "fv_weighted": r["fv_weighted"],
                "p_bear": r["p_bear"],
                "p_base": r["p_base"],
                "p_bull": r["p_bull"],
                "margin_of_safety_pct": r["margin_of_safety_pct"],
                "primary_sector": r["primary_sector"],
                "region": r["region"],
                "tech_signal": r["tech_signal"],
                "experiment_id": r["experiment_id"],
                "orchestrator_model": r["orchestrator_model"],
                "has_prediction_snapshot": None,
                "has_outcomes": None,
            }
        )

    by_ticker: dict[str, list[dict[str, Any]]] = {}
    for row in runs:
        by_ticker.setdefault(str(row["ticker"]), []).append(row)

    tickers: dict[str, Any] = {}
    for ticker, trows in sorted(by_ticker.items()):
        rows_sorted = sorted(
            trows, key=lambda x: (x.get("session_date") or "", x.get("session_key") or "")
        )
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

    catalog = catalog_root(output_dir)
    catalog.mkdir(parents=True, exist_ok=True)
    runs_index = {"schema_version": 2, "updated_at": now, "runs": runs}
    tickers_index = {"schema_version": 2, "updated_at": now, "tickers": tickers}
    atomic_write_text(
        catalog / "runs_index.json",
        json.dumps(runs_index, indent=2, ensure_ascii=False) + "\n",
    )
    atomic_write_text(
        catalog / "tickers_index.json",
        json.dumps(tickers_index, indent=2, ensure_ascii=False) + "\n",
    )
    atomic_write_text(catalog / "schema_version", "2\n")
    return {
        "n_runs": len(runs),
        "n_tickers": len(tickers),
        "catalog": str(catalog),
        "mode": "from_sqlite",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--include-legacy",
        action="store_true",
        help="Include root/<TICKER>/<DATE> sessions not yet migrated",
    )
    ap.add_argument(
        "--archive-only",
        action="store_true",
        default=True,
        help="Only index archive/research (default for full disk scan)",
    )
    ap.add_argument(
        "--from-sqlite",
        action="store_true",
        help="Rebuild thin JSON indexes from research_compare.sqlite (no disk walk)",
    )
    args = ap.parse_args()
    if args.from_sqlite:
        result = rebuild_from_sqlite()
    else:
        include_legacy = bool(args.include_legacy)
        result = rebuild(include_legacy=include_legacy)
    print(
        f"Catalog rebuilt ({result.get('mode')}): {result['n_runs']} runs, "
        f"{result['n_tickers']} tickers -> {result['catalog']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

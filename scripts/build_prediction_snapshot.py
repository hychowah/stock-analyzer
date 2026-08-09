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
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.kd_research.paths import (  # noqa: E402
    PROJECT_ROOT,
    iter_research_sessions,
    rel_to_project,
    require_session,
    resolve_session,
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


def _asof_price(session: Path, valuation: dict | None, technical: dict | None) -> tuple[float | None, list[str]]:
    gaps: list[str] = []
    # Prefer technical registry
    if technical:
        for key in ("asof_price", "last_price", "price", "close"):
            v = technical.get(key)
            if isinstance(v, (int, float)):
                return float(v), gaps
        levels = technical.get("levels") or {}
        if isinstance(levels, dict):
            for key in ("last", "close", "price", "asof_price"):
                v = levels.get(key)
                if isinstance(v, (int, float)):
                    return float(v), gaps
        indicators = technical.get("indicators") or {}
        if isinstance(indicators, dict):
            for key in ("last_close", "close", "price"):
                v = indicators.get(key)
                if isinstance(v, (int, float)):
                    return float(v), gaps
                if isinstance(v, dict) and isinstance(v.get("value"), (int, float)):
                    return float(v["value"]), gaps
    if valuation:
        for key in ("asof_price", "price", "current_price"):
            v = valuation.get(key)
            if isinstance(v, (int, float)):
                return float(v), gaps
            if isinstance(v, dict) and isinstance(v.get("value"), (int, float)):
                return float(v["value"]), gaps
        fv = valuation.get("fair_value") or {}
        if isinstance(fv, dict) and isinstance(fv.get("asof_price"), (int, float)):
            return float(fv["asof_price"]), gaps
    # Try prices_stock.csv last row Close
    for name in ("prices_stock.csv", "prices_tsr_stock.csv"):
        p = session / "data" / name
        if not p.is_file():
            # ticker-specific tsr files
            continue
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").strip().splitlines()
            if len(lines) < 2:
                continue
            header = [h.strip().lower() for h in lines[0].split(",")]
            close_idx = None
            for cand in ("close", "adj close", "adj_close", "price"):
                if cand in header:
                    close_idx = header.index(cand)
                    break
            if close_idx is None and len(header) >= 2:
                close_idx = len(header) - 1
            if close_idx is not None:
                last = lines[-1].split(",")
                if close_idx < len(last):
                    return float(last[close_idx]), gaps
        except Exception:  # noqa: BLE001
            continue
    # glob prices_tsr_*.csv excluding benchmarks
    for p in sorted((session / "data").glob("prices_*.csv")) if (session / "data").is_dir() else []:
        if "benchmark" in p.name or "sector" in p.name:
            continue
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").strip().splitlines()
            if len(lines) < 2:
                continue
            header = [h.strip().lower() for h in lines[0].split(",")]
            close_idx = next((i for i, h in enumerate(header) if h in ("close", "adj close", "adj_close")), None)
            if close_idx is None:
                continue
            last = lines[-1].split(",")
            return float(last[close_idx]), gaps
        except Exception:  # noqa: BLE001
            continue
    gaps.append("asof_price not found in technical/valuation/prices csv")
    return None, gaps


def _key_risks(session: Path) -> list[str]:
    risks: list[str] = []
    rb = _load_json(session / "registry" / "risk_bridge.json")
    if rb:
        scenarios = (rb.get("stress_test") or {}).get("scenarios") or rb.get("scenarios") or []
        if isinstance(scenarios, list):
            for s in scenarios[:5]:
                if isinstance(s, dict):
                    name = s.get("name") or s.get("id") or s.get("scenario")
                    if name:
                        risks.append(str(name))
        top = rb.get("top_risks") or rb.get("key_risks")
        if isinstance(top, list):
            for r in top[:5]:
                if isinstance(r, str):
                    risks.append(r)
                elif isinstance(r, dict) and r.get("name"):
                    risks.append(str(r["name"]))
    lq = _load_json(session / "registry" / "latest_quarter.json")
    if lq and isinstance(lq.get("risks"), list):
        for r in lq["risks"][:5]:
            if isinstance(r, str):
                risks.append(r)
            elif isinstance(r, dict):
                risks.append(str(r.get("risk") or r.get("description") or r.get("name") or r))
    # dedupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for r in risks:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out[:8]


def _verdict_line(session: Path, ticker: str) -> str:
    readme = session / "reports" / f"00_{ticker.upper()}_README.md"
    if not readme.is_file():
        # try any 00_*README
        matches = list((session / "reports").glob("00_*README.md")) if (session / "reports").is_dir() else []
        readme = matches[0] if matches else readme
    if not readme.is_file():
        return ""
    text = readme.read_text(encoding="utf-8", errors="replace")
    # Prefer a Verdict section line
    for pattern in (
        r"(?im)^#+\s*verdict[^\n]*\n+([^\n]+)",
        r"(?im)^\*\*verdict\*\*[:\s]+([^\n]+)",
        r"(?im)^verdict[:\s]+([^\n]+)",
    ):
        m = re.search(pattern, text)
        if m:
            return m.group(1).strip()[:500]
    # fallback: first non-empty line after "bull/base/bear"
    for line in text.splitlines():
        low = line.lower()
        if "bull" in low and "bear" in low:
            return line.strip()[:500]
    return ""


def _peers(session: Path, sector: dict | None) -> list[str]:
    if sector:
        for key in ("peers", "peer_tickers", "closest_peers"):
            v = sector.get(key)
            if isinstance(v, list):
                return [str(x) for x in v]
            if isinstance(v, str) and v.strip():
                return [p.strip() for p in v.split(",") if p.strip()]
        signals = sector.get("signals") or []
        # sometimes peers only in rationale — skip
    peer_csv = session / "data" / "peer_comparison.csv"
    if peer_csv.is_file():
        try:
            lines = peer_csv.read_text(encoding="utf-8", errors="replace").splitlines()
            if len(lines) >= 2:
                header = [h.strip().lower() for h in lines[0].split(",")]
                t_idx = 0
                if "ticker" in header:
                    t_idx = header.index("ticker")
                tickers = []
                for line in lines[1:6]:
                    parts = line.split(",")
                    if t_idx < len(parts):
                        tickers.append(parts[t_idx].strip())
                return tickers
        except Exception:  # noqa: BLE001
            pass
    return []


def build_for_session(session: Path, *, force: bool = False) -> dict[str, Any]:
    session = session.resolve()
    ticker = session.parent.name.upper()
    session_date = session.name
    rid = make_run_id(ticker, session_date)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    gaps: list[str] = []

    valuation = _load_json(session / "data" / "valuation_model.json")
    technical = _load_json(session / "registry" / "technical.json")
    sector = _load_json(session / "registry" / "sector_config.json")
    market = _load_json(session / "registry" / "market_context.json")
    audit = _load_json(session / "registry" / "audit.json")

    if valuation is None:
        gaps.append("data/valuation_model.json missing or unparseable")

    fv_raw = (valuation or {}).get("fair_value") or {}
    if not isinstance(fv_raw, dict):
        fv_raw = {}
    fair_value = {
        "base": fv_raw.get("base"),
        "bear": fv_raw.get("bear"),
        "bull": fv_raw.get("bull"),
        "probability_weighted": fv_raw.get("probability_weighted"),
        "currency": fv_raw.get("currency") or (valuation or {}).get("currency") or "",
    }
    mos = fv_raw.get("margin_of_safety_pct")
    if mos is None and valuation:
        mos = valuation.get("margin_of_safety_pct")

    price, price_gaps = _asof_price(session, valuation, technical)
    gaps.extend(price_gaps)

    audit_verdict = (audit or {}).get("verdict") if audit else None
    if audit is None:
        gaps.append("registry/audit.json missing")

    layout = "archive" if "archive/research" in session.as_posix() else "legacy"

    snapshot = {
        "schema_version": 1,
        "run_id": rid,
        "ticker": ticker,
        "session_date": session_date,
        "built_at": now,
        "asof_price": price,
        "currency": fair_value.get("currency") or "",
        "fair_value": fair_value,
        "margin_of_safety_pct": mos,
        "verdict_line": _verdict_line(session, ticker),
        "primary_sector": (sector or {}).get("primary_sector") or "",
        "region": (market or {}).get("primary_region") or "",
        "intensity": (market or {}).get("intensity") or "",
        "key_risks": _key_risks(session),
        "peers": _peers(session, sector),
        "benchmark": (technical or {}).get("benchmark")
        or (technical or {}).get("benchmark_symbol")
        or "",
        "data_quality": (sector or {}).get("data_quality")
        or ("degraded" if gaps else "ok"),
        "audit_verdict": audit_verdict,
        "priced_for_perfection": (valuation or {}).get("priced_for_perfection"),
        "gaps": gaps,
        "source_paths": {
            "valuation": "data/valuation_model.json",
            "technical": "registry/technical.json",
            "sector_config": "registry/sector_config.json",
            "market_context": "registry/market_context.json",
            "audit": "registry/audit.json",
            "risk_bridge": "registry/risk_bridge.json",
        },
    }

    manifest = {
        "schema_version": 1,
        "run_id": rid,
        "product": "research",
        "ticker": ticker,
        "session_date": session_date,
        "created_at": now,
        "completed_at": now,
        "harness_spec": "v2",
        "paths": {
            "session_root": rel_to_project(session),
            "reports": "reports/",
            "valuation": "data/valuation_model.json",
            "audit": "registry/audit.json",
            "prediction_snapshot": "meta/prediction_snapshot.json",
        },
        "status": "complete" if audit_verdict == "PASS" else ("audited" if audit_verdict else "unknown"),
        "audit_verdict": audit_verdict,
        "immutable": audit_verdict == "PASS",
        "layout": layout,
    }

    meta = session / "meta"
    meta.mkdir(parents=True, exist_ok=True)
    snap_path = meta / "prediction_snapshot.json"
    man_path = meta / "run_manifest.json"
    if snap_path.exists() and not force:
        # Still rewrite — snapshots are projections; force only needed if policy freezes
        pass
    snap_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    man_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"session": str(session), "run_id": rid, "gaps": gaps, "snapshot": snapshot}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker")
    ap.add_argument("--date")
    ap.add_argument("--session-dir")
    ap.add_argument("--all", action="store_true", help="All discovered sessions (archive + legacy)")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    results = []
    if args.all:
        sessions = iter_research_sessions(include_legacy=True)
        for t, d, path in sessions:
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

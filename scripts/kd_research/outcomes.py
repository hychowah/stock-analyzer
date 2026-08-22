"""Outcomes helpers: horizons, mechanical grades, SQLite upsert.

Outcomes live under archive/outcomes/ and never mutate research sessions.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from scripts.kd_research.paths import (
    PROJECT_ROOT,
    outcomes_root,
    parse_session_key,
    rel_to_project,
    run_id as make_run_id,
)

HORIZON_DAYS: dict[str, int] = {
    "1d": 1,
    "1w": 7,
    "1m": 30,
    "3m": 91,
    "6m": 182,
    "1y": 365,
}

DEFAULT_HORIZONS = ("1d", "1w", "1m", "3m", "6m", "1y")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso_date(s: str) -> date:
    return date.fromisoformat(s[:10])


def target_date_for(session_date: str, horizon: str) -> date:
    if horizon not in HORIZON_DAYS:
        raise ValueError(f"unknown horizon {horizon!r}; expected one of {list(HORIZON_DAYS)}")
    return parse_iso_date(session_date) + timedelta(days=HORIZON_DAYS[horizon])


def outcomes_dir_for(
    ticker: str,
    session_key: str,
    output_dir: Path | str | None = None,
) -> Path:
    return outcomes_root(output_dir) / ticker.upper() / session_key


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001
        return None


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def research_snapshot_fields(session: Path) -> dict[str, Any]:
    """Pull asof price, MoS, FV band, benchmark from session projection/files."""
    snap = load_json(session / "meta" / "prediction_snapshot.json") or {}
    valuation = load_json(session / "data" / "valuation_model.json") or {}
    technical = load_json(session / "registry" / "technical.json") or {}
    price_snap = load_json(session / "data" / "price_snapshot.json") or {}

    fv = snap.get("fair_value") if isinstance(snap.get("fair_value"), dict) else {}
    if not fv and isinstance(valuation.get("fair_value"), dict):
        fv = valuation["fair_value"]

    asof = snap.get("asof_price")
    if asof is None:
        for src in (price_snap, technical, valuation):
            for k in ("close", "current_price", "asof_price", "last_price", "price"):
                v = src.get(k) if isinstance(src, dict) else None
                if isinstance(v, (int, float)):
                    asof = float(v)
                    break
            if asof is not None:
                break
        if asof is None and isinstance(technical.get("price_anchor"), dict):
            v = technical["price_anchor"].get("last_close")
            if isinstance(v, (int, float)):
                asof = float(v)

    mos = snap.get("margin_of_safety_pct")
    if mos is None and isinstance(fv, dict):
        mos = fv.get("margin_of_safety_pct")

    benchmark = snap.get("benchmark") or technical.get("benchmark") or technical.get("benchmark_symbol")
    if not benchmark and isinstance(technical.get("benchmarks"), dict):
        b = technical["benchmarks"]
        benchmark = b.get("primary") or b.get("symbol") or next(iter(b), None)

    return {
        "asof_price": float(asof) if isinstance(asof, (int, float)) else None,
        "currency": snap.get("currency") or fv.get("currency") or valuation.get("currency") or "",
        "margin_of_safety_pct": float(mos) if isinstance(mos, (int, float)) else None,
        "fv_bear": float(fv["bear"]) if isinstance(fv.get("bear"), (int, float)) else None,
        "fv_base": float(fv["base"]) if isinstance(fv.get("base"), (int, float)) else None,
        "fv_bull": float(fv["bull"]) if isinstance(fv.get("bull"), (int, float)) else None,
        "fv_weighted": float(fv["probability_weighted"])
        if isinstance(fv.get("probability_weighted"), (int, float))
        else None,
        "benchmark": str(benchmark) if benchmark else None,
        "audit_verdict": snap.get("audit_verdict"),
        "primary_sector": snap.get("primary_sector"),
        "region": snap.get("region"),
    }


def pct_return(start: float | None, end: float | None) -> float | None:
    if start is None or end is None or start == 0:
        return None
    return round((end / start - 1.0) * 100.0, 4)


def direction_hit(mos_pct: float | None, total_return_pct: float | None, *, deadband: float = 2.0) -> int | None:
    """1 if MoS sign agrees with realized return sign; 0 if disagree; None if too flat / missing.

    Policy (mechanical_v1): |MoS| < deadband or |return| < deadband → too early / noise → null.
    """
    if mos_pct is None or total_return_pct is None:
        return None
    if abs(mos_pct) < deadband or abs(total_return_pct) < deadband:
        return None
    mos_pos = mos_pct > 0
    ret_pos = total_return_pct > 0
    return 1 if mos_pos == ret_pos else 0


def fv_band_status(
    price: float | None,
    bear: float | None,
    bull: float | None,
) -> str | None:
    """Whether realized price sits inside [bear, bull] at the mark."""
    if price is None or bear is None or bull is None:
        return None
    lo, hi = (bear, bull) if bear <= bull else (bull, bear)
    if lo <= price <= hi:
        return "inside"
    if price < lo:
        return "below_bear"
    return "above_bull"


def mechanical_scorecard(
    *,
    run_id: str,
    ticker: str,
    session_date: str,
    session_key: str,
    fields: dict[str, Any],
    price_path: dict[str, Any],
    horizon_primary: str = "3m",
) -> dict[str, Any]:
    """Build a mechanical scorecard from price_path marks + research snapshot fields."""
    mos = fields.get("margin_of_safety_pct")
    marks = price_path.get("marks") or []
    by_h = {m.get("horizon"): m for m in marks if isinstance(m, dict)}

    metrics: dict[str, Any] = {
        "direction_vs_price": {},
        "fv_band_at_mark": {},
        "total_return_pct": {},
        "excess_return_pct": {},
    }
    for h, m in by_h.items():
        if m.get("status") != "ok":
            metrics["direction_vs_price"][h] = {
                "value": "too_early" if m.get("status") == "pending" else "unavailable",
                "rule": "mechanical_v1: require ok mark",
                "rationale": f"Mark status={m.get('status')}",
                "basis": "outcomes/price_path.json",
            }
            continue
        tr = m.get("total_return_pct")
        dh = direction_hit(mos, tr)
        if dh is None:
            dval = "too_early"
        else:
            dval = "correct" if dh == 1 else "incorrect"
        metrics["direction_vs_price"][h] = {
            "value": dval,
            "direction_hit": dh,
            "rule": "mechanical_v1: sign(MoS) agrees with sign(return); |MoS| and |ret| >= 2pp",
            "rationale": f"MoS={mos}% vs total_return={tr}% at {h}",
            "basis": "prediction_snapshot.margin_of_safety_pct + price_path mark",
        }
        bear = fields.get("fv_bear")
        base = fields.get("fv_base")
        bull = fields.get("fv_bull")
        span_ineligible = (
            isinstance(base, (int, float))
            and not isinstance(base, bool)
            and float(base) > 0
            and isinstance(bear, (int, float))
            and isinstance(bull, (int, float))
            and (float(bull) - float(bear)) / float(base) > 1.0
        )
        if span_ineligible:
            band = "ineligible"
            band_rule = (
                "mechanical_v1: inside [fv_bear, fv_bull] ineligible when "
                "(bull-bear)/base > 100%"
            )
        else:
            band = fv_band_status(m.get("price"), bear, bull)
            band_rule = "mechanical_v1: mark price inside [fv_bear, fv_bull]"
        metrics["fv_band_at_mark"][h] = {
            "value": band,
            "rule": band_rule,
            "rationale": f"price={m.get('price')} band=[{bear}, {bull}] base={base}",
            "basis": "valuation fair_value + price_path",
        }
        metrics["total_return_pct"][h] = {
            "value": tr,
            "rule": "(mark_price / asof_price - 1) * 100",
            "basis": "price_path",
        }
        metrics["excess_return_pct"][h] = {
            "value": m.get("excess_return_pct"),
            "rule": "total_return_pct - benchmark_return_pct",
            "basis": "price_path",
        }

    primary = by_h.get(horizon_primary) or {}
    overall = None
    if primary.get("status") == "ok":
        d = (metrics["direction_vs_price"].get(horizon_primary) or {}).get("value")
        if d == "correct":
            overall = "mostly_right"
        elif d == "incorrect":
            overall = "mostly_wrong"
        elif d == "too_early":
            overall = "too_early"
        else:
            overall = "mixed"
    else:
        # 1d/1w sign(MoS)×return is tape hygiene, never the overall skill label.
        overall = "too_early"

    return {
        "schema_version": 1,
        "run_id": run_id,
        "ticker": ticker,
        "session_date": session_date,
        "session_key": session_key,
        "graded_at": utc_now(),
        "horizon_primary": horizon_primary,
        "metrics": metrics,
        "overall_label": overall,
        "grader": "mechanical_v1",
        "notes_path": "notes.md",
        "source_paths": {
            "price_path": "price_path.json",
            "research_snapshot": "meta/prediction_snapshot.json",
        },
        "inputs": {
            "asof_price": fields.get("asof_price"),
            "margin_of_safety_pct": mos,
            "fv_bear": fields.get("fv_bear"),
            "fv_base": fields.get("fv_base"),
            "fv_bull": fields.get("fv_bull"),
        },
    }


def upsert_outcomes_rows(conn: sqlite3.Connection, run_id: str, price_path: dict[str, Any], scorecard: dict[str, Any] | None) -> int:
    """Replace SQLite outcomes rows for a run from price_path (+ scorecard direction)."""
    conn.execute("DELETE FROM outcomes WHERE run_id = ?", (run_id,))
    marks = price_path.get("marks") or []
    dir_by_h: dict[str, Any] = {}
    if scorecard and isinstance(scorecard.get("metrics"), dict):
        dvp = scorecard["metrics"].get("direction_vs_price") or {}
        if isinstance(dvp, dict):
            dir_by_h = dvp

    n = 0
    for m in marks:
        if not isinstance(m, dict):
            continue
        h = m.get("horizon")
        if not h:
            continue
        dh = None
        meta = dir_by_h.get(h) if isinstance(dir_by_h.get(h), dict) else None
        if meta and meta.get("direction_hit") is not None:
            dh = int(meta["direction_hit"])
        extras = {
            "status": m.get("status"),
            "source": m.get("source"),
            "target_date": m.get("target_date"),
            "fetched_at": m.get("fetched_at"),
            "notes": m.get("notes"),
        }
        conn.execute(
            """
            INSERT INTO outcomes(
              run_id, horizon, mark_date, realized_price, total_return_pct,
              benchmark_return_pct, excess_return_pct, direction_hit, extras_json
            ) VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                run_id,
                h,
                m.get("mark_date"),
                m.get("price"),
                m.get("total_return_pct"),
                m.get("benchmark_return_pct"),
                m.get("excess_return_pct"),
                dh,
                json.dumps(extras, ensure_ascii=False),
            ),
        )
        n += 1
    return n


def session_identity(session: Path) -> tuple[str, str, str, str]:
    """Return ticker, session_key, session_date, run_id."""
    session = session.resolve()
    session_key = session.name
    ticker = session.parent.name.upper()
    session_date, _ = parse_session_key(session_key)
    return ticker, session_key, session_date, make_run_id(ticker, session_key)

"""Compose one AnalysisReport document from stored session files.

Display math only. Does not author fair values or invent cash-flow rows.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote

from packages.kd_research.check_core import load_json
from packages.kd_research.decision import cheap_claim_label, duration_label
from packages.kd_research.forecast_table import ForecastTable, from_session

from apps.analysis_web.services.render_markdown import render_session_report
from apps.analysis_web.templating import fmt_num


def _money(value: float | None, *, share: bool = False) -> str:
    if value is None:
        return "—"
    sign = "-" if value < 0 else ""
    av = abs(value)
    if share or av < 1_000_000:
        return f"{sign}${av:,.2f}"
    if av >= 1_000_000_000_000:
        return f"{sign}${av / 1_000_000_000_000:.1f}T"
    if av >= 1_000_000_000:
        return f"{sign}${av / 1_000_000_000:.1f}B"
    return f"{sign}${av / 1_000_000:.1f}M"


def _pct(value: float | None) -> str:
    if value is None:
        return "—"
    if abs(value) <= 2:
        return f"{value * 100:.1f}%".replace(".0%", "%")
    return f"{value:.1f}%"


def _cell(value: float | None, unit: str) -> str:
    if value is None:
        return "—"
    if unit == "percent":
        return _pct(value)
    return _money(value)


def _float(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    if n != n or n in (float("inf"), float("-inf")):
        return None
    return n


def _glob_one(folder: Path, pattern: str) -> Path | None:
    if not folder.is_dir():
        return None
    hits = sorted(folder.glob(pattern))
    return hits[0] if hits else None


def _wacc_rows(vm: dict[str, Any] | None) -> tuple[list[dict[str, str]], str | None]:
    if not isinstance(vm, dict):
        return [], None
    ident = vm.get("wacc_buildup")
    if not isinstance(ident, dict):
        return [], None
    if ident.get("applies") is False:
        reason = str(ident.get("not_applicable_reason") or "").strip()
        analog = ident.get("native_analog")
        bits = [reason] if reason else []
        if analog:
            bits.append(f"Native analog: {analog}.")
        return [], " ".join(bits) or "This model does not use an industrial WACC."
    rows: list[dict[str, str]] = []
    mapping = (
        ("wacc", "WACC", True),
        ("rf", "Risk-free rate", True),
        ("ke", "Cost of equity", True),
        ("kd_pretax", "Cost of debt (pretax)", True),
        ("we", "Equity weight", True),
        ("wd", "Debt weight", True),
        ("tax", "Tax rate", True),
    )
    for key, label, pct in mapping:
        n = _float(ident.get(key))
        if n is None:
            continue
        rows.append({"label": label, "value": _pct(n) if pct else fmt_num(n)})
    return rows, None


def _forecast_view(table: ForecastTable | None) -> dict[str, Any] | None:
    if table is None:
        return None
    scenarios: dict[str, Any] = {}
    for scen in table.scenarios:
        rows_out = []
        for row, series in table.scenario_rows(scen):
            rows_out.append(
                {
                    "id": row.id,
                    "label": row.label,
                    "unit": row.unit,
                    "cells": [_cell(v, row.unit) for v in series],
                }
            )
        if rows_out:
            scenarios[scen] = {"rows": rows_out}
    if not scenarios:
        return None
    return {
        "years": table.years,
        "scenarios": scenarios,
        "present": list(table.scenarios),
        "source": table.source,
        "currency": table.currency,
        "n_years": table.n_years,
    }


def _chapter(
    session: Path,
    *,
    run_id: str,
    rel: Path | None,
    chapter_id: str,
    title: str,
    kicker: str,
    strip_forecast: bool = False,
) -> dict[str, Any] | None:
    if rel is None or not rel.is_file():
        return None
    session_rel = rel.relative_to(session).as_posix()
    text = rel.read_text(encoding="utf-8", errors="replace")
    doc = render_session_report(
        text,
        run_id=run_id,
        relpath=session_rel,
        id_prefix=chapter_id,
        strip_forecast=strip_forecast,
    )
    h2 = [item for item in doc["toc"] if int(item.get("level") or 0) == 2]
    return {
        "id": chapter_id,
        "title": title,
        "kicker": kicker,
        "html": doc["html"],
        "h2": h2,
        "relpath": session_rel,
    }


def load_analysis_report(
    *,
    run: dict[str, Any],
    session: Path,
    run_id: str,
    football_href: str | None = None,
) -> dict[str, Any]:
    """One document: verdict, model, forecast, worth, then markdown chapters."""
    vm, _err = load_json(session / "data" / "valuation_model.json")
    if not isinstance(vm, dict):
        vm = None
    model = vm.get("model") if isinstance(vm, dict) else None
    model_name = ""
    model_why = ""
    if isinstance(model, dict):
        model_name = str(model.get("name") or "")
        model_why = str(model.get("rationale") or "")
    elif run.get("model_name"):
        model_name = str(run.get("model_name") or "")

    action = str(run.get("decision_action") or "").strip()
    label = duration_label(action)
    price = _float(run.get("asof_price"))
    fv_base = _float(run.get("fv_base"))
    fv_bear = _float(run.get("fv_bear"))
    fv_bull = _float(run.get("fv_bull"))
    mos = _float(run.get("margin_of_safety_pct"))
    currency = str(run.get("currency") or "")
    claim_raw = str(run.get("cheap_claim") or "").strip()
    if isinstance(vm, dict):
        roic = vm.get("roic_identity")
        if isinstance(roic, dict):
            cc = roic.get("cheap_claim")
            if isinstance(cc, dict) and cc.get("class"):
                claim_raw = str(cc.get("class"))

    sentences: list[str] = []
    if label:
        sentences.append(f"{label}.")
    if price is not None and fv_base is not None:
        sentences.append(
            f"The freeze price is {_money(price, share=True)}. "
            f"The model's central estimate of value is {_money(fv_base, share=True)}."
        )
    if claim_raw:
        sentences.append(f"Cheap claim: {cheap_claim_label(claim_raw)}.")
    if not sentences:
        sentences.append("This session has no stored duration verdict.")

    table = from_session(session)
    forecast = _forecast_view(table)
    wacc_rows, wacc_na = _wacc_rows(vm)

    reports = session / "reports"
    cio = _chapter(
        session,
        run_id=run_id,
        rel=_glob_one(reports, "00_*_README.md"),
        chapter_id="cio",
        title="CIO cover",
        kicker="CIO cover",
    )
    fundamental = _chapter(
        session,
        run_id=run_id,
        rel=_glob_one(reports, "01_*_fundamental.md"),
        chapter_id="fundamental",
        title="Fundamental",
        kicker="Fundamental",
        strip_forecast=True,
    )
    technical = _chapter(
        session,
        run_id=run_id,
        rel=_glob_one(reports, "02_*_technical.md"),
        chapter_id="technical",
        title="Technical",
        kicker="Technical overlay — not the duration book",
    )

    chapters = [c for c in (cio, fundamental, technical) if c]
    toc: list[dict[str, Any]] = [
        {"id": "verdict", "title": "Verdict", "h2": []},
        {"id": "model", "title": "Model", "h2": []},
        {"id": "forecast", "title": "Forecast", "h2": []},
        {"id": "worth", "title": "Worth", "h2": []},
    ]
    for ch in chapters:
        toc.append({"id": ch["id"], "title": ch["title"], "h2": ch["h2"]})

    raw_cio = None
    if cio:
        raw_cio = f"/artifact?run_id={quote(run_id, safe='')}&path={quote(cio['relpath'], safe='')}&raw=1"

    return {
        "ticker": run.get("ticker") or "",
        "session_key": run.get("session_key") or "",
        "currency": currency,
        "asof": run.get("session_date") or run.get("session_key") or "",
        "sentences": sentences,
        "model_name": model_name,
        "model_why": model_why,
        "wacc_rows": wacc_rows,
        "wacc_na": wacc_na,
        "forecast": forecast,
        "forecast_gap": (
            None
            if forecast
            else "This model has no year-by-year cash-flow table."
        ),
        "worth": {
            "price": _money(price, share=True),
            "bear": _money(fv_bear, share=True),
            "base": _money(fv_base, share=True),
            "bull": _money(fv_bull, share=True),
            "mos": None if mos is None else f"{mos:.1f}%",
        },
        "football_href": football_href,
        "chapters": chapters,
        "toc": toc,
        "raw_cio_href": raw_cio,
        "run_href": f"/runs/{run_id}",
        "run_id": run_id,
    }

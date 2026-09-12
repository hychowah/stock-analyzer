"""Closed year-by-year forecast table (harness >= 2.43.0).

Agent 5 writes valuation_model.explicit_forecast. The loader paints a table
from that object, or from a short list of known compute-result layouts.
Unknown dumps return None — never invent a metric from another.

The website renders ForecastTable only. It does not parse compute JSON.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from packages.kd_research.check_core import load_json, session_since

FORECAST_SINCE = (2, 43, 0)
VM_REL = "data/valuation_model.json"
RESULT_REL = "data/compute/valuation_result.json"
REASON_MIN = 40
# Relative 1% or $1M — display rounding, not a second valuation.
IDENT_REL = 0.01
IDENT_ABS = 1_000_000.0

SCENARIOS = ("bear", "base", "bull")

# Display rows. Aliases are stored keys; never derive one metric from another.
_ROW_SPEC: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("revenue", "Revenue", "money", ("revenue", "revenues", "nr")),
    ("operating_profit", "Operating profit", "money", ("operating_profit", "oi", "ebit")),
    ("operating_margin", "Margin", "percent", ("operating_margin", "om")),
    ("ebitda_margin", "EBITDA margin", "percent", ("ebitda_m", "ebitda_margin")),
    ("capex", "Capex", "money", ("capex",)),
    ("capex_pct", "Capex %", "percent", ("capex_pct",)),
    ("fcff", "Free cash flow", "money", ("fcff", "fcf")),
)


def session_is_forecast_runtime(session: Path) -> bool:
    return session_since(session, FORECAST_SINCE)


def _as_float(val: Any) -> float | None:
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        n = float(val)
        if n != n or n in (float("inf"), float("-inf")):
            return None
        return n
    if isinstance(val, dict):
        return _as_float(val.get("value"))
    return None


def _float_list(val: Any) -> list[float | None] | None:
    if not isinstance(val, list) or not val:
        return None
    out: list[float | None] = []
    any_num = False
    for item in val:
        n = _as_float(item)
        out.append(n)
        if n is not None:
            any_num = True
    return out if any_num else None


def _pick_alias(obj: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    for key in aliases:
        if key in obj:
            return obj[key]
    return None


@dataclass(frozen=True)
class ForecastRow:
    id: str
    label: str
    unit: str
    values: dict[str, list[float | None]]


@dataclass(frozen=True)
class ForecastTable:
    currency: str | None
    years: list[str]
    rows: tuple[ForecastRow, ...]
    scenarios: tuple[str, ...]
    source: str
    n_years: int = 0

    def scenario_rows(self, scenario: str) -> list[tuple[ForecastRow, list[float | None]]]:
        out: list[tuple[ForecastRow, list[float | None]]] = []
        for row in self.rows:
            series = row.values.get(scenario)
            if series:
                out.append((row, series))
        return out

    @classmethod
    def from_session(cls, session: Path) -> ForecastTable | None:
        return _load_from_session(session)


def _years_from_n(n: int, labels: list[str] | None = None) -> list[str]:
    if labels and len(labels) == n:
        return [str(x) for x in labels]
    return [f"Y{i}" for i in range(1, n + 1)]


def _rows_from_scenario_maps(
    maps: dict[str, dict[str, list[float | None]]],
) -> tuple[ForecastRow, ...]:
    n = 0
    for scen_map in maps.values():
        for series in scen_map.values():
            n = max(n, len(series))
    rows: list[ForecastRow] = []
    used_om = False
    for rid, label, unit, aliases in _ROW_SPEC:
        values: dict[str, list[float | None]] = {}
        for scen, scen_map in maps.items():
            series = None
            for alias in aliases:
                got = scen_map.get(alias)
                if got:
                    series = got
                    break
            if series:
                values[scen] = series
        if not values:
            continue
        if rid == "operating_margin":
            used_om = True
        if rid == "ebitda_margin" and used_om:
            continue
        rows.append(ForecastRow(id=rid, label=label, unit=unit, values=values))
    return tuple(rows)


def _from_explicit(obj: dict[str, Any]) -> ForecastTable | None:
    if obj.get("applies") is False:
        return None
    maps: dict[str, dict[str, list[float | None]]] = {}
    n = 0
    year_labels: list[str] | None = None
    raw_years = obj.get("years") or obj.get("fiscal_years")
    if isinstance(raw_years, list) and raw_years:
        year_labels = [str(y) for y in raw_years]
    for scen in SCENARIOS:
        block = obj.get(scen)
        if not isinstance(block, dict):
            continue
        scen_map: dict[str, list[float | None]] = {}
        for _rid, _label, _unit, aliases in _ROW_SPEC:
            for alias in aliases:
                series = _float_list(block.get(alias))
                if series:
                    scen_map[alias] = series
                    n = max(n, len(series))
        if scen_map:
            maps[scen] = scen_map
    rows = _rows_from_scenario_maps(maps)
    if not rows or n < 1:
        return None
    currency = obj.get("currency")
    return ForecastTable(
        currency=str(currency) if currency else None,
        years=_years_from_n(n, year_labels),
        rows=rows,
        scenarios=tuple(s for s in SCENARIOS if s in maps),
        source="explicit_forecast",
        n_years=n,
    )


def _from_parallel_scenarios(result: dict[str, Any]) -> ForecastTable | None:
    scenarios = result.get("scenarios")
    if not isinstance(scenarios, dict):
        return None
    maps: dict[str, dict[str, list[float | None]]] = {}
    n = 0
    for scen in SCENARIOS:
        block = scenarios.get(scen)
        if not isinstance(block, dict):
            continue
        scen_map: dict[str, list[float | None]] = {}
        for _rid, _label, _unit, aliases in _ROW_SPEC:
            series = _float_list(_pick_alias(block, aliases))
            if series:
                scen_map[aliases[0]] = series
                n = max(n, len(series))
        if scen_map:
            maps[scen] = scen_map
    rows = _rows_from_scenario_maps(maps)
    if not rows or n < 2:
        return None
    currency = result.get("currency")
    return ForecastTable(
        currency=str(currency) if currency else None,
        years=_years_from_n(n),
        rows=rows,
        scenarios=tuple(s for s in SCENARIOS if s in maps),
        source="scenarios",
        n_years=n,
    )


def _year_objects_to_map(years: list[Any]) -> dict[str, list[float | None]] | None:
    if not years or not all(isinstance(y, dict) for y in years):
        return None
    n = len(years)
    scen_map: dict[str, list[float | None]] = {}
    for _rid, _label, _unit, aliases in _ROW_SPEC:
        series: list[float | None] = []
        hit = False
        for year in years:
            val = None
            for alias in aliases:
                if alias in year:
                    val = _as_float(year.get(alias))
                    break
            series.append(val)
            if val is not None:
                hit = True
        if hit:
            scen_map[aliases[0]] = series
    return scen_map if scen_map else None


def _years_labels_from_objects(years: list[Any], n: int) -> list[str]:
    labels: list[str] = []
    for i, year in enumerate(years):
        if isinstance(year, dict) and year.get("fy") is not None:
            labels.append(str(year.get("fy")))
        else:
            labels.append(f"Y{i + 1}")
    if len(labels) == n:
        return labels
    return _years_from_n(n)


def _from_dcf_years(result: dict[str, Any]) -> ForecastTable | None:
    dcf = result.get("dcf")
    if not isinstance(dcf, dict):
        return None
    maps: dict[str, dict[str, list[float | None]]] = {}
    n = 0
    labels: list[str] | None = None
    for scen in SCENARIOS:
        block = dcf.get(scen)
        if not isinstance(block, dict):
            continue
        years = block.get("years")
        if not isinstance(years, list):
            continue
        scen_map = _year_objects_to_map(years)
        if not scen_map:
            continue
        maps[scen] = scen_map
        n = max(n, max(len(v) for v in scen_map.values()))
        if labels is None:
            labels = _years_labels_from_objects(years, n)
    rows = _rows_from_scenario_maps(maps)
    if not rows or n < 2:
        return None
    currency = result.get("currency")
    return ForecastTable(
        currency=str(currency) if currency else None,
        years=labels if labels and len(labels) == n else _years_from_n(n),
        rows=rows,
        scenarios=tuple(s for s in SCENARIOS if s in maps),
        source="dcf_years",
        n_years=n,
    )


def _from_paths(result: dict[str, Any]) -> ForecastTable | None:
    paths = result.get("paths")
    if not isinstance(paths, dict):
        return None
    maps: dict[str, dict[str, list[float | None]]] = {}
    n = 0
    labels: list[str] | None = None
    for scen in SCENARIOS:
        years = paths.get(scen)
        if not isinstance(years, list):
            continue
        scen_map = _year_objects_to_map(years)
        if not scen_map:
            continue
        maps[scen] = scen_map
        n = max(n, max(len(v) for v in scen_map.values()))
        if labels is None:
            labels = _years_labels_from_objects(years, n)
    rows = _rows_from_scenario_maps(maps)
    if not rows or n < 2:
        return None
    currency = result.get("currency")
    return ForecastTable(
        currency=str(currency) if currency else None,
        years=labels if labels and len(labels) == n else _years_from_n(n),
        rows=rows,
        scenarios=tuple(s for s in SCENARIOS if s in maps),
        source="paths",
        n_years=n,
    )


def ForecastTable_from_result(result: dict[str, Any]) -> ForecastTable | None:
    """Named compute-result layouts only. Order is part of the contract."""
    for loader in (_from_parallel_scenarios, _from_dcf_years, _from_paths):
        table = loader(result)
        if table is not None:
            return table
    return None


def _load_from_session(session: Path) -> ForecastTable | None:
    """Prefer valuation_model.explicit_forecast, else known compute layouts."""
    vm, _err = load_json(session / VM_REL)
    if isinstance(vm, dict):
        expl = vm.get("explicit_forecast")
        if isinstance(expl, dict):
            table = _from_explicit(expl)
            if table is not None:
                return table
            if expl.get("applies") is False:
                return None
    result, _err = load_json(session / RESULT_REL)
    if isinstance(result, dict):
        return ForecastTable_from_result(result)
    return None


def from_session(session: Path) -> ForecastTable | None:
    return _load_from_session(session)


def _close(a: float, b: float) -> bool:
    scale = max(abs(a), abs(b), 1.0)
    return abs(a - b) <= max(IDENT_ABS, IDENT_REL * scale)


def _first_series(table: ForecastTable, row_id: str, scenario: str = "base") -> list[float | None] | None:
    for row in table.rows:
        if row.id == row_id:
            return row.values.get(scenario)
    return None


def check_explicit_forecast(session: Path) -> list[tuple[str, str, str]]:
    """Identity vs compute. Legacy without the object is SKIPPED."""
    enforce = session_is_forecast_runtime(session)
    vm_path = session / VM_REL
    if not vm_path.is_file():
        return [("SKIPPED", "explicit_forecast", "valuation_model.json missing")]
    vm, err = load_json(vm_path)
    if err or not isinstance(vm, dict):
        return [("FAIL", "explicit_forecast", f"valuation_model unparseable: {err}")]
    expl = vm.get("explicit_forecast")
    if not isinstance(expl, dict):
        if enforce:
            return [
                (
                    "FAIL",
                    "explicit_forecast",
                    "new runtime requires valuation_model.explicit_forecast "
                    "(year-by-year path copied from the compute script; "
                    "applies:false with reason when the model is not a path)",
                )
            ]
        return [
            (
                "SKIPPED",
                "explicit_forecast",
                "legacy/slim (no explicit_forecast; harness_version < 2.43.0)",
            )
        ]

    applies = expl.get("applies")
    if applies is False:
        reason = str(expl.get("not_applicable_reason") or "").strip()
        analog = expl.get("native_analog")
        if len(reason) < REASON_MIN:
            return [
                (
                    "FAIL",
                    "explicit_forecast.na",
                    f"applies:false requires not_applicable_reason ≥{REASON_MIN} chars",
                )
            ]
        if analog is None or (isinstance(analog, str) and not analog.strip()):
            return [
                (
                    "FAIL",
                    "explicit_forecast.analog",
                    "applies:false requires native_analog (name the non-FCFF path)",
                )
            ]
        return [("PASS", "explicit_forecast", "applies=false")]

    table = _from_explicit(expl)
    if table is None:
        return [
            (
                "FAIL",
                "explicit_forecast.empty",
                "explicit_forecast applies but has no year-by-year numeric path",
            )
        ]

    result, rerr = load_json(session / RESULT_REL)
    if rerr or not isinstance(result, dict):
        return [
            (
                "FAIL",
                "explicit_forecast.compute",
                "explicit_forecast present but data/compute/valuation_result.json missing",
            )
        ]
    computed = ForecastTable_from_result(result)
    if computed is None:
        return [
            (
                "PASS",
                "explicit_forecast",
                "compute result has no named layout to identity-check; path stored",
            )
        ]
    base_rev = _first_series(table, "revenue")
    comp_rev = _first_series(computed, "revenue")
    if base_rev and comp_rev:
        a = next((x for x in base_rev if x is not None), None)
        b = next((x for x in comp_rev if x is not None), None)
        if a is not None and b is not None and not _close(a, b):
            return [
                (
                    "FAIL",
                    "explicit_forecast.identity",
                    f"Y1 revenue {a} does not match compute {b}",
                )
            ]
    base_fcff = _first_series(table, "fcff")
    comp_fcff = _first_series(computed, "fcff")
    if base_fcff and comp_fcff:
        a = next((x for x in base_fcff if x is not None), None)
        b = next((x for x in comp_fcff if x is not None), None)
        if a is not None and b is not None and not _close(a, b):
            return [
                (
                    "FAIL",
                    "explicit_forecast.identity",
                    f"Y1 FCFF {a} does not match compute {b}",
                )
            ]
    return [("PASS", "explicit_forecast", f"source=explicit_forecast n={table.n_years}")]


def check_explicit_forecast_if_vm(session: Path) -> list[tuple[str, str, str]]:
    if not (session / VM_REL).is_file():
        return []
    return check_explicit_forecast(session)


_PIPE_ROW = re.compile(r"^\s*\|(.+)\|\s*$")


def _parse_md_tables(text: str) -> list[list[list[str]]]:
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in text.splitlines():
        m = _PIPE_ROW.match(line)
        if not m:
            if current:
                tables.append(current)
                current = []
            continue
        cells = [c.strip() for c in m.group(1).split("|")]
        if cells and set("".join(cells)) <= set("-: "):
            continue
        current.append(cells)
    if current:
        tables.append(current)
    return tables


def _cell_number(text: str) -> float | None:
    raw = text.replace(",", "").replace("$", "").strip()
    if not raw:
        return None
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*([BbMmTt])?\b", raw)
    if not m:
        return None
    n = float(m.group(1))
    suf = (m.group(2) or "").upper()
    if suf == "B":
        n *= 1_000_000_000.0
    elif suf == "M":
        n *= 1_000_000.0
    elif suf == "T":
        n *= 1_000_000_000_000.0
    return n


def check_fundamental_forecast_table(session: Path) -> list[tuple[str, str, str]]:
    """Fundamental markdown must restate Y1 of the stored path (harness >= 2.43)."""
    if not session_is_forecast_runtime(session):
        return [("SKIPPED", "report_forecast_table", "harness_version < 2.43.0")]
    reports = session / "reports"
    if not reports.is_dir():
        return [("SKIPPED", "report_forecast_table", "reports/ missing")]
    matches = list(reports.glob("01_*_fundamental.md"))
    if not matches:
        return [("FAIL", "report_forecast_table", "fundamental report missing")]
    text = matches[0].read_text(encoding="utf-8", errors="replace")
    table = from_session(session)
    vm, _err = load_json(session / VM_REL)
    expl = vm.get("explicit_forecast") if isinstance(vm, dict) else None
    if isinstance(expl, dict) and expl.get("applies") is False:
        return [("PASS", "report_forecast_table", "explicit_forecast applies=false")]
    if table is None:
        return [
            (
                "FAIL",
                "report_forecast_table",
                "no stored year-by-year path to restate in the fundamental report",
            )
        ]
    series = _first_series(table, "revenue") or _first_series(table, "fcff")
    if not series or len(series) < 2:
        return [("FAIL", "report_forecast_table", "stored path has no Y1 + later year")]
    y1 = next((x for x in series if x is not None), None)
    later = next((x for x in series[1:] if x is not None), None)
    if y1 is None or later is None:
        return [("FAIL", "report_forecast_table", "stored path missing numeric years")]
    found_y1 = False
    found_later = False
    for grid in _parse_md_tables(text):
        for row in grid:
            for cell in row:
                n = _cell_number(cell)
                if n is None:
                    continue
                if _close(n, y1):
                    found_y1 = True
                if _close(n, later):
                    found_later = True
    if not found_y1 or not found_later:
        return [
            (
                "FAIL",
                "report_forecast_table",
                "fundamental report must include a markdown table whose Y1 "
                "native KPI and a later year match explicit_forecast / compute",
            )
        ]
    return [("PASS", "report_forecast_table", "Y1 and later year restated")]

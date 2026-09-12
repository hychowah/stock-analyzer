"""Street-estimate gates (harness >= 2.7.0; Y1 baseline >= 2.18.0; gated Y1 >= 2.28.0).

2.7–2.17: Street FY+1 is a *calibration* after an independent company-evidence
stack. Copying Street into base is FAIL-quality. |delta| > 20% is a WARN.

2.18.0–2.27.x: Street FY+1 revenue is the required base Y1 start. |delta| > 5%
FAILs unless response=street_unusable. keep_independent_vs_street is illegal.

>= 2.28.0: Street FY+1 is the *default* Y1 start (street_baseline; |delta|>5%
FAIL). independent_y1 is legal when a named evidence gate resolves.
Destock-in-base is legal only when destock_this_print. ttc_midcycle is not a
Y1 license. keep_independent_vs_street remains illegal.

Legacy sessions without street_estimates.json and harness < 2.7.0 SKIPPED.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from packages.kd_research.check_core import load_json, session_since, validate_hooks_list
from packages.kd_research.street_y1 import (
    STREET_GATED_Y1_SINCE,
    STREET_SINCE,
    STREET_Y1_SINCE,
    StreetY1Policy,
)


STREET_REL = "registry/street_estimates.json"
VM_REL = "data/valuation_model.json"
BRIEF_REL = "registry/operating_path_brief.json"
SECTOR_REL = "registry/sector_config.json"
RESULT_REL = "data/compute/valuation_result.json"

DELTA_EPS = 0.005
CONSTRUCTION_MIN_LEN = 40
DIVERGENCE_MIN_LEN = 40
N_REVENUE_MIN = 5

LEGAL_INDEPENDENCE_GATES = frozenset(
    {
        "destock_this_print",
        "definition_mismatch",
        "native_kpi",
        "street_unusable",
        "story_fail",
        "ttc_midcycle",
    }
)
GATES_SINCE_300 = frozenset({"story_fail", "ttc_midcycle"})
NATIVE_KPI_SECTORS = frozenset({"banking", "insurance", "reit"})
PATH_COPY_NEEDLES = (
    "used_as:revenue_path",
    "used_as:street_mean",
    "used_as:consensus",
    "used_as:copy_street",
)
FY1_BASELINE_NEEDLES = (
    "used_as:fy1_baseline",
    "used_as:street_baseline",
    "used_as:revenue_path",
    "used_as:street_mean",
)


def street_path(session: Path) -> Path:
    return session / STREET_REL


def check_street_entry(session: Path) -> list[tuple[str, str, str]]:
    """2_parallel entry / --full: fetch + bind when Street is in force or on disk."""
    out: list[tuple[str, str, str]] = []
    vm = session / VM_REL
    if session_enforces_street(session) or street_path(session).is_file():
        out.extend(check_street_fetch(session))
        if vm.is_file():
            out.extend(check_street_bind(session))
    return out


def check_street_schema_if_present(session: Path) -> list[tuple[str, str, str]]:
    if not street_path(session).is_file():
        return []
    from packages.kd_research.check_core import check_structured_file

    return check_structured_file(
        session,
        STREET_REL,
        "street_estimates",
        ["ticker", "session_date", "source", "fiscal_convention", "years"],
    )


def session_is_street_runtime(session: Path) -> bool:
    """True when harness_version >= 2.7.0 (omit-dials / both-methods law)."""
    return session_since(session, STREET_SINCE)


def session_enforces_street(session: Path) -> bool:
    """True when Street fetch/bind gates apply."""
    if street_path(session).is_file():
        return True
    return session_is_street_runtime(session)


def session_is_street_y1_runtime(session: Path) -> bool:
    """True when StreetY1Policy.y1 (harness >= 2.18.0)."""
    return StreetY1Policy.for_session(session).y1


def session_is_gated_y1_runtime(session: Path) -> bool:
    """True when StreetY1Policy.gated (harness >= 2.28.0)."""
    return StreetY1Policy.for_session(session).gated


def destock_this_print(brief: dict[str, Any] | None) -> bool:
    """Facade: destock analog lives in epistemology."""
    from packages.kd_research.epistemology import destock_this_print as _destock

    return _destock(brief)


def street_y1_usable(session: Path, street_data: dict[str, Any] | None = None) -> bool:
    """Numeric FY+1 Street is usable as the Y1 baseline (not unavailable / unusable)."""
    data = street_data
    if data is None:
        if not street_path(session).is_file():
            return False
        data, err = load_json(street_path(session))
        if err or not isinstance(data, dict):
            return False
    if data.get("unavailable") is True:
        return False
    rev = fy1_street_revenue(data)
    if rev is None:
        return False
    n_rev = _fy1_n_revenue(data)
    if n_rev is not None and n_rev < N_REVENUE_MIN:
        return False
    vm, _ = load_json(session / VM_REL)
    if isinstance(vm, dict):
        bind = vm.get("street_bind")
        if isinstance(bind, dict) and str(bind.get("response") or "").strip() == "street_unusable":
            return False
    return True


_FY1_PREFER = ("+1y", "fy+1", "fy+ 1", "next year")


def _fy1_year_row(data: dict[str, Any]) -> dict[str, Any] | None:
    """Shared labeled / i==1 FY+1 year row. Numeric fallback stays in fy1_street_revenue."""
    years = data.get("years")
    if not isinstance(years, list):
        return None
    extra: dict[str, Any] | None = None
    for i, row in enumerate(years):
        if not isinstance(row, dict):
            continue
        label = str(row.get("label") or "").strip().lower()
        if i == 1 or any(p in label for p in _FY1_PREFER) or label.endswith("+1y"):
            return row
        if extra is None and label in ("+1y", "1y", "next"):
            extra = row
    if extra is not None:
        return extra
    if len(years) >= 2 and isinstance(years[1], dict):
        return years[1]
    return None


def _fy1_n_revenue(data: dict[str, Any]) -> int | None:
    row = _fy1_year_row(data)
    if row is None:
        return None
    n = row.get("n_revenue")
    return n if isinstance(n, int) else None


def _fetch_log_street_failed(session: Path) -> bool:
    log, err = load_json(session / "registry" / "data_fetch_log.json")
    if err or not isinstance(log, dict):
        return False
    blob = json.dumps(log).lower()
    needles = ("street", "consensus", "revenue_estimate", "earnings_estimate")
    failed = log.get("failed") or log.get("substitutions") or []
    if any(n in blob and ("fail" in blob or "unavail" in blob) for n in needles):
        if isinstance(failed, list) and failed:
            return True
        if "street fy estimates unavailable" in blob:
            return True
    if isinstance(failed, list):
        for item in failed:
            t = json.dumps(item).lower() if not isinstance(item, str) else item.lower()
            if any(n in t for n in needles):
                return True
    return False


def fy1_street_revenue(data: dict[str, Any]) -> float | None:
    """Best-effort FY+1 revenue from street_estimates.years."""
    row = _fy1_year_row(data)
    if row is not None:
        rev = row.get("revenue")
        if isinstance(rev, (int, float)) and not isinstance(rev, bool):
            return float(rev)
    years = data.get("years")
    if not isinstance(years, list):
        return None
    numeric = [
        float(r["revenue"])
        for r in years
        if isinstance(r, dict) and isinstance(r.get("revenue"), (int, float)) and not isinstance(r.get("revenue"), bool)
    ]
    if len(numeric) >= 2:
        return numeric[1]
    return numeric[0] if len(numeric) == 1 else None


def check_street_fetch(session: Path) -> list[tuple[str, str, str]]:
    """1_parallel complete / 2_parallel entry: file or explicit fetch failure on new runtime."""
    if not session_enforces_street(session) and not street_path(session).is_file():
        return [
            (
                "SKIPPED",
                "street_estimates",
                "legacy/slim (no street_estimates.json; harness_version < 2.7.0)",
            )
        ]
    p = street_path(session)
    if p.is_file():
        data, err = load_json(p)
        if err:
            return [("FAIL", STREET_REL, err)]
        assert isinstance(data, dict)
        if data.get("unavailable") is True:
            return [("PASS", STREET_REL, "present; unavailable=true (Agent 5 must widen range)")]
        years = data.get("years")
        if not isinstance(years, list) or not years:
            return [("FAIL", STREET_REL, "years[] empty unless unavailable=true")]
        return [("PASS", STREET_REL, f"{len(years)} year row(s)")]
    if _fetch_log_street_failed(session):
        return [
            (
                "PASS",
                STREET_REL,
                "missing but data_fetch_log records Street/consensus failure — widen range",
            )
        ]
    if session_enforces_street(session):
        return [
            (
                "FAIL",
                STREET_REL,
                "new runtime requires registry/street_estimates.json or an explicit Street fetch failure in data_fetch_log",
            )
        ]
    return [("SKIPPED", STREET_REL, "absent")]


def _as_float(val: Any) -> float | None:
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    return None


def _y1_construction_rationale(bind: dict[str, Any]) -> str:
    for key in ("y1_construction", "independent_construction"):
        construction = bind.get(key)
        if isinstance(construction, dict):
            return str(construction.get("rationale") or "")
        if isinstance(construction, str) and construction.strip():
            return construction
    return ""


def _independence_gate_resolved(
    session: Path, bind: dict[str, Any], *, gate_optional: bool = False
) -> tuple[bool, str]:
    gate = str(bind.get("independence_gate") or "").strip()
    if not gate:
        if gate_optional:
            return True, "independent_y1 default (no gate)"
        return False, "independent_y1 requires independence_gate"
    if gate in GATES_SINCE_300 and not session_since(session, (3, 0, 0)):
        return False, f"independence_gate {gate!r} requires harness ≥ 3.0.0"
    if gate not in LEGAL_INDEPENDENCE_GATES:
        return (
            False,
            f"independence_gate {gate!r} is not a legal gate "
            f"(legal: {sorted(LEGAL_INDEPENDENCE_GATES)})",
        )
    if gate == "destock_this_print":
        from packages.kd_research.epistemology import destock_this_print as _destock

        brief, err = load_json(session / BRIEF_REL)
        if err or not isinstance(brief, dict):
            return False, "destock_this_print requires registry/operating_path_brief.json"
        if not _destock(brief):
            return (
                False,
                "destock_this_print requires analog_class inventory_channel|advertiser_budget "
                "and current_print_is_destock=true",
            )
        return True, "destock_this_print"
    if gate == "definition_mismatch":
        vendor = str(bind.get("vendor_revenue_class") or "").strip()
        filing = str(bind.get("filing_revenue_class") or "").strip()
        if not vendor or not filing:
            return (
                False,
                "definition_mismatch requires vendor_revenue_class and filing_revenue_class",
            )
        if vendor.lower() == filing.lower():
            return False, "definition_mismatch classes must differ"
        return True, "definition_mismatch"
    if gate == "native_kpi":
        sc, err = load_json(session / SECTOR_REL)
        sector = ""
        if isinstance(sc, dict):
            sector = str(sc.get("primary_sector") or "").strip().lower()
        if sector not in NATIVE_KPI_SECTORS:
            return (
                False,
                f"native_kpi requires primary_sector in banking|insurance|reit (got {sector!r})",
            )
        return True, "native_kpi"
    if gate == "street_unusable":
        return True, "street_unusable"
    if gate == "story_fail":
        nb, err = load_json(session / "registry" / "narrative_bind.json")
        if err or not isinstance(nb, dict):
            rat = str(bind.get("divergence_rationale") or "")
            if len(rat.strip()) >= DIVERGENCE_MIN_LEN:
                return True, "story_fail (rationale)"
            return False, "story_fail requires narrative_bind or divergence_rationale ≥40 chars"
        restory = nb.get("street_restory") if isinstance(nb.get("street_restory"), dict) else {}
        if restory.get("will_own") is False:
            return True, "story_fail"
        rat = str(restory.get("implied_story") or bind.get("divergence_rationale") or "")
        if len(rat.strip()) >= DIVERGENCE_MIN_LEN:
            return True, "story_fail"
        return False, "story_fail requires street_restory.will_own=false or ≥40 char rationale"
    if gate == "ttc_midcycle":
        sc, err = load_json(session / SECTOR_REL)
        sector = ""
        if isinstance(sc, dict):
            sector = str(sc.get("primary_sector") or "").strip().lower()
        if sector != "cyclical":
            return False, "ttc_midcycle requires primary_sector=cyclical"
        return True, "ttc_midcycle"
    return False, f"independence_gate {gate!r} unresolved"


def _check_y1_rehydrate(session: Path, base: float) -> list[tuple[str, str, str]]:
    path = session / RESULT_REL
    if not path.is_file():
        return []
    data, err = load_json(path)
    if err or not isinstance(data, dict):
        return []
    y1 = None
    for key in ("y1_revenue", "base_y1_revenue", "fy1_revenue"):
        y1 = _as_float(data.get(key))
        if y1 is not None:
            break
    dcf = data.get("dcf") if isinstance(data.get("dcf"), dict) else {}
    if y1 is None:
        y1 = _as_float(dcf.get("y1_revenue") or dcf.get("base_y1"))
    if y1 is None:
        return []
    if abs(y1 - base) > max(0.01, DELTA_EPS * abs(base)):
        return [
            (
                "FAIL",
                "street_bind.rehydrate",
                f"valuation_result Y1 {y1} != street_bind.base {base}",
            )
        ]
    return [("PASS", "street_bind.rehydrate", "matches compute Y1")]


def _band_pct(band: float) -> str:
    return f"{band * 100:.0f}%"


def _apply_y1_policy(
    policy: StreetY1Policy,
    session: Path,
    bind: dict[str, Any],
    resp: str,
    expected: float,
) -> list[tuple[str, str, str]]:
    """Apply one StreetY1Policy: legal responses, |delta| bands, calibration."""
    out: list[tuple[str, str, str]] = []
    abs_d = abs(expected)
    fail = policy.fail_band
    warn = policy.warn_band
    cal = policy.calibration_band

    if policy.keep_independent_illegal and resp == "keep_independent_vs_street":
        out.append(
            (
                "FAIL",
                "street_bind.response",
                "harness ≥ 2.18.0: keep_independent_vs_street is not a legal Y1 "
                "response when Street FY+1 is numeric; use street_baseline, "
                "independent_y1 (≥2.28 with a resolved gate), or street_unusable",
            )
        )

    if policy.independent_y1_ok and resp == "street_unusable":
        band = _band_pct(fail) if fail is not None else "fail-band"
        out.append(("PASS", "street_bind.y1_band", f"street_unusable; no {band} identity"))
        return out

    if policy.independent_y1_ok and resp == "independent_y1":
        ok, detail = _independence_gate_resolved(
            session, bind, gate_optional=policy.gate_optional
        )
        if not ok:
            out.append(("FAIL", "street_bind.independence_gate", detail))
        else:
            out.append(("PASS", "street_bind.independence_gate", detail))
        if abs_d > cal:
            div = str(bind.get("divergence_rationale") or "")
            if len(div.strip()) < DIVERGENCE_MIN_LEN:
                out.append(
                    (
                        "FAIL",
                        "street_bind.delta_calibration",
                        f"|delta_pct| > {_band_pct(cal)} on independent_y1 requires "
                        "divergence_rationale ≥40 chars",
                    )
                )
            else:
                out.append(
                    ("PASS", "street_bind.delta_calibration", "divergence_rationale present")
                )
        elif fail is not None and abs_d > fail:
            out.append(
                (
                    "WARN",
                    "street_bind.y1_band",
                    f"|delta_pct| {expected:.4f} > {_band_pct(fail)} on independent_y1 "
                    "— document the gate overlay",
                )
            )
        elif warn is not None and abs_d > warn:
            out.append(
                (
                    "WARN",
                    "street_bind.y1_band",
                    f"|delta_pct| {expected:.4f} > {_band_pct(warn)} vs Street FY+1 "
                    "— document the overlay",
                )
            )
        blob = (
            _y1_construction_rationale(bind)
            + " "
            + str(bind.get("divergence_rationale") or "")
        ).lower()
        if "average" in blob and "destock" in blob and "street" in blob:
            out.append(
                (
                    "FAIL",
                    "street_bind.average",
                    "do not average destock and Street into one CAGR called base",
                )
            )
        return out

    if fail is not None and abs_d > fail and resp != "street_unusable":
        if policy.independent_y1_ok:
            msg = (
                f"|delta_pct| {expected:.4f} > {_band_pct(fail)} vs Street FY+1 — "
                "street_baseline must start from Street, or set response=independent_y1 "
                "with a resolved gate, or street_unusable"
            )
        else:
            msg = (
                f"|delta_pct| {expected:.4f} > {_band_pct(fail)} vs Street FY+1 — "
                "base Y1 must start from Street (or response=street_unusable)"
            )
        out.append(("FAIL", "street_bind.y1_band", msg))
    elif warn is not None and abs_d > warn and resp != "street_unusable":
        out.append(
            (
                "WARN",
                "street_bind.y1_band",
                f"|delta_pct| {expected:.4f} > {_band_pct(warn)} vs Street FY+1 "
                "— document the overlay",
            )
        )
    elif policy.independent_y1_ok and fail is not None:
        out.append(
            (
                "PASS",
                "street_bind.y1_band",
                f"|delta_pct| {expected:.4f} inside {_band_pct(fail)}",
            )
        )

    if policy.independent_y1_ok:
        return out

    if fail is not None:
        if abs_d > cal:
            div = str(bind.get("divergence_rationale") or "")
            if len(div.strip()) < DIVERGENCE_MIN_LEN or resp not in policy.responses:
                out.append(
                    (
                        "WARN",
                        "street_bind.delta_calibration",
                        f"|delta_pct| > {_band_pct(cal)} vs Street FY+1 still needs "
                        "divergence_rationale and a legal ≥2.18 response "
                        "(street_unusable / reopen_path to Street)",
                    )
                )
        return out

    if abs_d > cal:
        div = str(bind.get("divergence_rationale") or "")
        if len(div.strip()) < DIVERGENCE_MIN_LEN or resp not in policy.responses:
            out.append(
                (
                    "WARN",
                    "street_bind.delta_calibration",
                    f"|delta_pct| > {_band_pct(cal)} vs Street FY+1 is a calibration note, "
                    "not a valuation skill miss. Record divergence_rationale / response if you "
                    "have them. Copying Street into the path remains FAIL on harness < 2.18.0.",
                )
            )
        else:
            out.append(("PASS", "street_bind.divergence", f"response={resp}"))
    return out


def _apply_hook_policy(
    policy: StreetY1Policy,
    actions: list[str],
    resp: str,
    copy_hits: list[str],
) -> list[tuple[str, str, str]]:
    """Apply StreetY1Policy to street_hooks actions (copy needles, fy1 baseline)."""
    out: list[tuple[str, str, str]] = []
    independent = policy.independent_y1_ok and resp == "independent_y1"
    if policy.path_copy_legal:
        if copy_hits and not independent:
            out.append(
                (
                    "PASS",
                    "street_hooks copy",
                    "≥2.18.0: used_as:revenue_path / street_mean is legal (Street is Y1 baseline)",
                )
            )
        has_baseline = any(any(n in a for n in FY1_BASELINE_NEEDLES) for a in actions)
        if actions and all(a == "noted_only" for a in actions):
            out.append(
                (
                    "FAIL",
                    "street_hooks noted_only",
                    "all street_hooks are noted_only — consume Street as used_as:fy1_baseline "
                    "or, on ≥2.28 independent_y1, as calibration/reject",
                )
            )
        elif independent:
            out.append(
                (
                    "PASS",
                    "street_hooks fy1_baseline",
                    "independent_y1: Street consumed without requiring used_as:fy1_baseline",
                )
            )
        elif policy.fy1_baseline_required and not has_baseline:
            out.append(
                (
                    "FAIL",
                    "street_hooks fy1_baseline",
                    "harness ≥ 2.18.0 requires a street_hooks action used_as:fy1_baseline "
                    "(or used_as:revenue_path / street_mean) when Street FY+1 is numeric "
                    "and response is not independent_y1",
                )
            )
        else:
            out.append(("PASS", "street_hooks fy1_baseline", "Street consumed as Y1 baseline"))
        return out
    if copy_hits:
        out.append(
            (
                "FAIL",
                "street_hooks copy",
                "street_hooks must not set the revenue path from consensus (forbidden action needles). Use used_as:calibration_check after an independent build.",
            )
        )
    elif actions and all(a == "noted_only" for a in actions):
        out.append(
            (
                "FAIL",
                "street_hooks noted_only",
                "all street_hooks are noted_only — consume Street as a calibration check or reject with reason",
            )
        )
    else:
        out.append(("PASS", "street_hooks noted_only", "not all noted_only; no path-copy action"))
    return out


def check_street_bind(session: Path) -> list[tuple[str, str, str]]:
    """When Street file or new runtime + valuation: bind table, identity, legal responses, and street_hooks (hygiene is check_street_hygiene)."""
    out: list[tuple[str, str, str]] = []
    vm_path = session / VM_REL
    has_street = street_path(session).is_file()
    enforce = session_enforces_street(session)

    if not vm_path.is_file():
        if enforce and has_street:
            return [("SKIPPED", "street_bind", "valuation_model.json missing")]
        if not has_street and not enforce:
            return [("SKIPPED", "street_bind", "legacy/slim")]
        return [("SKIPPED", "street_bind", "valuation_model.json missing")]

    vm, err = load_json(vm_path)
    if err:
        return [("FAIL", "street_bind", f"valuation_model unparseable: {err}")]
    assert isinstance(vm, dict)

    street_data: dict[str, Any] | None = None
    if has_street:
        street_data, serr = load_json(street_path(session))
        if serr:
            return [("FAIL", STREET_REL, serr)]
        assert isinstance(street_data, dict)

    need_bind = has_street or (enforce and vm_path.is_file())
    if not need_bind:
        return [("SKIPPED", "street_bind", "not required")]

    unavailable = bool(street_data and street_data.get("unavailable") is True)
    street_rev = fy1_street_revenue(street_data) if street_data else None

    bind = vm.get("street_bind")
    if unavailable or (enforce and not has_street and _fetch_log_street_failed(session)):
        # Still want hooks noting the gap / widen
        hooks = vm.get("street_hooks")
        rows = validate_hooks_list(
            hooks if isinstance(hooks, list) else [],
            check_id="street_hooks",
            empty_detail="valuation_model must have street_hooks[] when Street is missing/unavailable (widen range; do not invent consensus)",
        )
        out.extend(rows)
        return out

    if not isinstance(bind, dict):
        out.append(
            (
                "FAIL",
                "street_bind",
                "valuation_model.street_bind object required when street_estimates.json exists (Street FY+1 vs modeled Y1)",
            )
        )
        return out

    base = _as_float(bind.get("base"))
    street_col = _as_float(bind.get("street"))
    resp_early = str(bind.get("response") or "").strip()
    if street_rev is not None and resp_early != "street_unusable":
        if street_col is None:
            out.append(
                (
                    "FAIL",
                    "street_bind.street",
                    "street_bind.street must match registry/street_estimates.json FY+1 revenue "
                    f"({street_rev}); omit is not allowed unless response=street_unusable",
                )
            )
        elif abs(street_col - street_rev) > max(0.01, DELTA_EPS * abs(street_rev)):
            out.append(
                (
                    "FAIL",
                    "street_bind.street",
                    f"street_bind.street {street_col} != street_estimates FY+1 {street_rev} "
                    "(do not set street=base to skip the |delta|>20% must-respond)",
                )
            )
        else:
            out.append(("PASS", "street_bind.street", f"matches file FY+1 {street_rev}"))
        street_col = street_rev
    elif street_col is None:
        street_col = street_rev
    if base is None:
        out.append(("FAIL", "street_bind.base", "base (model FY+1 revenue) required"))
        return out

    policy = StreetY1Policy.for_session(session)
    rationale = _y1_construction_rationale(bind)
    construction_id = (
        "street_bind.y1_construction" if policy.gated else "street_bind.independent_construction"
    )
    if len(rationale.strip()) < CONSTRUCTION_MIN_LEN:
        out.append(
            (
                "FAIL",
                construction_id,
                "y1_construction.rationale (or independent_construction) must show the Y1 "
                "construction (≥2.28: Street as the start, or the named independence gate; "
                "2.18–2.27: Street FY+1 as the start plus any overlay; 2.7–2.17: company-evidence stack)",
            )
        )
    else:
        out.append(("PASS", construction_id, "present"))
    if policy.rehydrate:
        out.extend(_check_y1_rehydrate(session, base))

    if street_col is not None and abs(street_col) > 1e-12:
        delta = bind.get("delta_pct")
        expected = (base - street_col) / street_col
        d = _as_float(delta)
        if d is None:
            out.append(("FAIL", "street_bind.delta_pct", "delta_pct required when street revenue is numeric"))
        elif abs(d - expected) > DELTA_EPS:
            out.append(
                (
                    "FAIL",
                    "street_bind.delta_pct",
                    f"delta_pct {d} != (base-street)/street {expected:.6f}",
                )
            )
        else:
            out.append(("PASS", "street_bind.delta_pct", f"{d:.4f}"))
        resp = str(bind.get("response") or "").strip()
        out.extend(_apply_y1_policy(policy, session, bind, resp, expected))
    else:
        out.append(("PASS", "street_bind.street", "street column null — skip delta identity"))

    hooks = vm.get("street_hooks")
    out.extend(
        validate_hooks_list(
            hooks,
            check_id="street_hooks",
            empty_detail="valuation_model must have non-empty street_hooks[] when street_estimates.json exists",
        )
    )
    if isinstance(hooks, list) and hooks:
        actions = []
        copy_hits = []
        for h in hooks:
            if not isinstance(h, dict):
                continue
            a = str(h.get("action") or "").strip().lower()
            actions.append(a)
            if any(n in a for n in PATH_COPY_NEEDLES):
                copy_hits.append(a)
        out.extend(_apply_hook_policy(policy, actions, resp_early, copy_hits))

    return out

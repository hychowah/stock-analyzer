"""Damodaran identities for harness >= 3.0.0. Older stamps SKIPPED."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.kd_research.check_core import load_json, session_since

DAMODARAN_SINCE = (3, 0, 0)
VM_REL = "data/valuation_model.json"
NARRATIVE_REL = "registry/narrative_bind.json"
SECTOR_REL = "registry/sector_config.json"
FINANCIALS = frozenset({"banking", "insurance"})


def _v3(session: Path) -> bool:
    return session_since(session, DAMODARAN_SINCE)


def _vm(session: Path) -> dict[str, Any] | None:
    data, err = load_json(session / VM_REL)
    if err or not isinstance(data, dict):
        return None
    return data


def check_damodaran_v3(session: Path) -> list[tuple[str, str, str]]:
    """Bundle of v3 identities when a valuation_model exists."""
    if not _v3(session):
        return [
            (
                "SKIPPED",
                "damodaran.v3",
                "harness < 3.0.0",
            )
        ]
    vm = _vm(session)
    if vm is None:
        return []
    out: list[tuple[str, str, str]] = []
    out.extend(_check_narrative_locked(session, vm))
    out.extend(_check_bank_engine(session, vm))
    out.extend(_check_growth_triad(vm))
    out.extend(_check_tv_method(vm))
    out.extend(_check_p_fail_double_count(vm))
    out.extend(_check_ledgers_not_averaged(vm))
    out.extend(_check_truncation_writes_base(vm))
    out.extend(_check_possible_in_base(session, vm))
    return out


def _check_narrative_locked(
    session: Path, vm: dict[str, Any]
) -> list[tuple[str, str, str]]:
    data, err = load_json(session / NARRATIVE_REL)
    if err or not isinstance(data, dict):
        return [
            (
                "FAIL",
                "damodaran.narrative_locked",
                "harness ≥ 3.0.0 requires registry/narrative_bind.json before valuation",
            )
        ]
    status = str(data.get("status") or "").strip().lower()
    if status != "locked":
        return [
            (
                "FAIL",
                "damodaran.narrative_locked",
                f"narrative_bind.status={status!r} must be locked",
            )
        ]
    return [("PASS", "damodaran.narrative_locked", "locked")]


def _check_bank_engine(
    session: Path, vm: dict[str, Any]
) -> list[tuple[str, str, str]]:
    sc, err = load_json(session / SECTOR_REL)
    sector = ""
    if isinstance(sc, dict):
        sector = str(sc.get("primary_sector") or "").strip().lower()
    if sector not in FINANCIALS:
        return []
    wacc = vm.get("wacc_buildup") if isinstance(vm.get("wacc_buildup"), dict) else {}
    if wacc.get("applies") is True:
        return [
            (
                "FAIL",
                "damodaran.bank_engine",
                "banking/insurance must set wacc_buildup.applies=false (equity at ke)",
            )
        ]
    name = ""
    model = vm.get("model")
    if isinstance(model, dict):
        name = str(model.get("name") or "").strip().lower()
    banned = ("fcff", "ev_ebitda", "wacc_dcf", "firm_dcf")
    if any(b in name.replace(" ", "_") for b in banned):
        return [
            (
                "FAIL",
                "damodaran.bank_engine",
                f"financials model.name={name!r} must not be industrial FCFF/EV",
            )
        ]
    return [("PASS", "damodaran.bank_engine", f"sector={sector} equity engine")]


def _check_growth_triad(vm: dict[str, Any]) -> list[tuple[str, str, str]]:
    tc = vm.get("terminal_consistency")
    if not isinstance(tc, dict):
        return []
    method = str(tc.get("method") or "").strip().lower()
    if method not in {"gordon", "gordon_growth", "stable_growth"}:
        return []
    g = tc.get("g_n")
    if g is None:
        g = vm.get("g") or (vm.get("assumptions") or {}).get("g") if isinstance(vm.get("assumptions"), dict) else None
    rr = tc.get("reinvestment_rate")
    roc = tc.get("roc_n") or tc.get("return_on_capital")
    try:
        gv = float(g) if g is not None else None
        rrv = float(rr) if rr is not None else None
        rocv = float(roc) if roc is not None else None
    except (TypeError, ValueError):
        return [
            (
                "FAIL",
                "damodaran.growth_triad",
                "Gordon TV requires numeric g_n, reinvestment_rate, roc_n",
            )
        ]
    if gv is None or rrv is None or rocv is None:
        return [
            (
                "FAIL",
                "damodaran.growth_triad",
                "Gordon TV requires g_n, reinvestment_rate, roc_n on terminal_consistency",
            )
        ]
    if abs(rocv) < 1e-8:
        return [("FAIL", "damodaran.growth_triad", "roc_n is zero")]
    implied = rrv * rocv
    if abs(implied - gv) > 0.005:
        return [
            (
                "FAIL",
                "damodaran.growth_triad",
                f"g_n {gv} != RR×ROC {implied}",
            )
        ]
    rf = None
    wacc_b = vm.get("wacc_buildup") if isinstance(vm.get("wacc_buildup"), dict) else {}
    rf = wacc_b.get("rf") or wacc_b.get("risk_free")
    if rf is not None:
        try:
            if gv > float(rf) + 1e-9:
                return [
                    (
                        "FAIL",
                        "damodaran.g_vs_rf",
                        f"g_n {gv} > session rf {rf}",
                    )
                ]
        except (TypeError, ValueError):
            pass
    spread = tc.get("wacc_minus_g") or tc.get("ke_minus_g")
    if spread is not None:
        try:
            if float(spread) <= 0:
                return [
                    (
                        "FAIL",
                        "damodaran.gordon_spread",
                        "wacc_minus_g / ke_minus_g must be > 0",
                    )
                ]
        except (TypeError, ValueError):
            pass
    return [("PASS", "damodaran.growth_triad", "RR×ROC matches g_n")]


def _check_tv_method(vm: dict[str, Any]) -> list[tuple[str, str, str]]:
    tc = vm.get("terminal_consistency")
    if not isinstance(tc, dict):
        return []
    method = str(tc.get("method") or "").strip().lower()
    if method in {"exit", "exit_multiple", "comps_exit"}:
        return [
            (
                "FAIL",
                "damodaran.tv_method",
                "exit multiple is price, not intrinsic TV",
            )
        ]
    return []


def _check_p_fail_double_count(vm: dict[str, Any]) -> list[tuple[str, str, str]]:
    trunc = vm.get("truncation") if isinstance(vm.get("truncation"), dict) else {}
    try:
        p = float(trunc.get("p") or 0)
    except (TypeError, ValueError):
        p = 0.0
    if p <= 0:
        return []
    dials = vm.get("conservatism_dials")
    if isinstance(dials, list):
        for d in dials:
            if not isinstance(d, dict):
                continue
            if str(d.get("key") or "") == "wacc_vs_buildup" and str(d.get("applies_in") or "") == "base":
                return [
                    (
                        "FAIL",
                        "damodaran.p_fail_double_count",
                        "p_fail>0 cannot also pad WACC in base",
                    )
                ]
    return [("PASS", "damodaran.p_fail_double_count", "truncation not in WACC")]


def _check_ledgers_not_averaged(vm: dict[str, Any]) -> list[tuple[str, str, str]]:
    rec = vm.get("multi_method_reconciliation")
    if not isinstance(rec, dict):
        return []
    why = str(rec.get("why_primary_wins") or rec.get("rationale") or "").lower()
    if "average" in why and ("dcf" in why or "multiple" in why or "sotp" in why):
        return [
            (
                "FAIL",
                "damodaran.ledgers_not_averaged",
                "do not average DCF and a multiple into fair_value.base",
            )
        ]
    return []


def _check_truncation_writes_base(vm: dict[str, Any]) -> list[tuple[str, str, str]]:
    trunc = vm.get("truncation") if isinstance(vm.get("truncation"), dict) else {}
    if trunc.get("material") is not True:
        return []
    try:
        p = float(trunc.get("p") or 0)
        gc = float(trunc.get("going_concern_upper_bound") or trunc.get("gc") or 0)
        fail = float(trunc.get("failure_payoff") or 0)
        expected = (1 - p) * gc + p * fail
    except (TypeError, ValueError):
        return [
            (
                "FAIL",
                "damodaran.truncation_base",
                "material truncation requires p, going_concern_upper_bound, failure_payoff",
            )
        ]
    fv = vm.get("fair_value") if isinstance(vm.get("fair_value"), dict) else {}
    try:
        base = float(fv.get("base"))
    except (TypeError, ValueError):
        return [("FAIL", "damodaran.truncation_base", "fair_value.base missing")]
    if abs(base - expected) > max(0.01, 0.005 * abs(expected)):
        return [
            (
                "FAIL",
                "damodaran.truncation_base",
                f"fair_value.base {base} != (1-p)×GC + p×fail {expected}",
            )
        ]
    return [("PASS", "damodaran.truncation_base", "base is truncated value")]


def _check_possible_in_base(
    session: Path, vm: dict[str, Any]
) -> list[tuple[str, str, str]]:
    data, err = load_json(session / NARRATIVE_REL)
    if err or not isinstance(data, dict):
        return []
    three = data.get("3p") if isinstance(data.get("3p"), dict) else {}
    possible = three.get("possible")
    if not isinstance(possible, list):
        return []
    fcst = vm.get("explicit_forecast") if isinstance(vm.get("explicit_forecast"), dict) else {}
    revs = fcst.get("base") if isinstance(fcst.get("base"), dict) else fcst
    rev_path = revs.get("revenue") if isinstance(revs, dict) else None
    if not isinstance(rev_path, list):
        return []
    for strand in possible:
        if not isinstance(strand, dict):
            continue
        if strand.get("revenue_in_dcf") not in (0, 0.0, None, False):
            return [
                (
                    "FAIL",
                    "damodaran.possible_in_base",
                    "3P possible strands must have revenue_in_dcf=0",
                )
            ]
    return []

"""Owner-earnings ROIC identity gates (harness >= 2.8.0).

DCF defines value. ROIC decides whether that DCF is a business or a spreadsheet.
Agent 5's compute script must print NOPAT/IC on the same stack as the DCF, a
dual column (residual-claim FCFF vs residual-income EV), and a g=0
counterfactual. The machine rehydrates identities and forbids illegal paperwork.
It never writes g or fair value.

Legacy / missing harness_version / harness < 2.8.0 SKIPPED when the object is
absent. Presence on an old session is validated, never omit-FAIL.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from scripts.kd_research.annuals import load_run_manifest_version, parse_semver
from scripts.kd_research.gates import load_json

ROIC_SINCE = (2, 8, 0)
MIDCYCLE_SINCE = (2, 13, 0)
VM_REL = "data/valuation_model.json"
RESULT_REL = "data/compute/valuation_result.json"

WACC_EPS = 0.0005  # 5 bp
ROIC_EPS = 0.0025  # 25 bp
SPREAD_EPS = 0.0005
BUCKET_BP = 0.005  # 50 bp
IC_NOISE = 0.08
G_ZERO_EPS = 0.0005
REASON_MIN = 40
EV_EPS_ABS = 1.0
EV_EPS_REL = 0.005

LEASES_OK = frozenset({"opex_and_out_of_ic", "capitalized_both"})
BUCKETS = frozenset({"above_wacc", "approx_wacc", "below_wacc"})
LEGAL_EXITS = frozenset(
    {
        "g_zero",
        "cut_earnings_power",
        "reinvestment_in_engine",
        "reconciled_to_ic",
    }
)
CHEAP_OK = frozenset(
    {
        "franchise_mos",
        "equity_near_book",
        "residual_option",
        "not_cheap",
    }
)
CHEAP_WHEN_NOT_ABOVE = frozenset(
    {"equity_near_book", "residual_option", "not_cheap"}
)
WINDOW_KINDS = frozenset(
    {"ttc_cycle", "multi_year_avg", "last_year", "peak_year", "insufficient_window"}
)
LICENSE_WINDOW_KINDS = frozenset({"ttc_cycle", "multi_year_avg"})


def session_is_roic_runtime(session: Path) -> bool:
    """True when harness_version >= 2.8.0. Missing version is legacy (Street clone)."""
    parsed = parse_semver(load_run_manifest_version(session))
    if parsed is None:
        return False
    return parsed >= ROIC_SINCE


def session_is_midcycle_runtime(session: Path) -> bool:
    parsed = parse_semver(load_run_manifest_version(session))
    if parsed is None:
        return False
    return parsed >= MIDCYCLE_SINCE


def _year_int(val: Any) -> int | None:
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, float) and val == int(val):
        return int(val)
    if isinstance(val, str):
        match = re.search(r"(?:19|20)\d{2}", val)
        if match:
            return int(match.group(0))
    return None


def _window_year_count(years_used: Any) -> int:
    """Count distinct years. A dash-string is one year (first match), not a span."""
    if isinstance(years_used, dict):
        start = _year_int(years_used.get("start"))
        end = _year_int(years_used.get("end"))
        if start is None or end is None:
            return 0
        return abs(end - start) + 1
    if isinstance(years_used, list):
        years = {_year_int(item) for item in years_used}
        years.discard(None)
        return len(years)
    if _year_int(years_used) is not None:
        return 1
    return 0


def check_mid_cycle_construction(ident: dict[str, Any], session: Path) -> list[tuple[str, str, str]]:
    """Wave 5: franchise/above_wacc needs a ≥2-year window, not last-year SOI."""
    if not session_is_midcycle_runtime(session):
        return []
    if ident.get("applies") is not True:
        return [("PASS", "mid_cycle_construction", "applies=false")]
    cons = ident.get("mid_cycle_construction")
    if not isinstance(cons, dict):
        return [
            (
                "FAIL",
                "mid_cycle_construction",
                "applies:true on harness ≥ 2.13.0 requires mid_cycle_construction "
                "(window_kind, years_used, print_vs_midcycle ≥20 chars)",
            )
        ]
    kind = str(cons.get("window_kind") or "").strip()
    if kind not in WINDOW_KINDS:
        return [
            (
                "FAIL",
                "mid_cycle_construction.window_kind",
                f"window_kind must be one of {sorted(WINDOW_KINDS)}; got {kind!r}",
            )
        ]
    n_years = _window_year_count(cons.get("years_used"))
    if n_years < 1:
        return [
            (
                "FAIL",
                "mid_cycle_construction.years_used",
                "years_used must be a year list or {start,end} with at least one year",
            )
        ]
    print_vs = cons.get("print_vs_midcycle")
    if print_vs is None:
        print_vs = cons.get("print_vs_mid_cycle")
    if not isinstance(print_vs, str) or len(print_vs.strip()) < 20:
        return [
            (
                "FAIL",
                "mid_cycle_construction.print_vs_midcycle",
                "print_vs_midcycle must be a rationale ≥20 chars (this print vs the window)",
            )
        ]
    bucket = str(ident.get("quality_bucket") or "").strip()
    cheap = _cheap_class(ident)
    licensed = bucket == "above_wacc" or cheap == "franchise_mos"
    if licensed and (kind not in LICENSE_WINDOW_KINDS or n_years < 2):
        return [
            (
                "FAIL",
                "mid_cycle_construction.license",
                "above_wacc / franchise_mos require window_kind ttc_cycle|multi_year_avg "
                "and a ≥2-year window (last_year/peak_year/insufficient_window never license)",
            )
        ]
    return [
        (
            "PASS",
            "mid_cycle_construction",
            f"kind={kind} years={n_years} licensed={licensed}",
        )
    ]


def _as_float(val: Any) -> float | None:
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, dict):
        return _as_float(val.get("value"))
    return None


def _nested_float(obj: Any, *keys: str) -> float | None:
    cur: Any = obj
    for k in keys:
        if not isinstance(cur, dict):
            return _as_float(cur)
        if k in cur:
            cur = cur[k]
        else:
            return None
    return _as_float(cur)


def _assumption_float(vm: dict[str, Any], key: str) -> float | None:
    assumptions = vm.get("assumptions")
    if not isinstance(assumptions, dict):
        return None
    return _as_float(assumptions.get(key))


def _cheap_class(ident: dict[str, Any]) -> str | None:
    cc = ident.get("cheap_claim")
    if isinstance(cc, str) and cc.strip():
        return cc.strip()
    if isinstance(cc, dict):
        raw = cc.get("class") or cc.get("value")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return None


def _gate_response(ident: dict[str, Any]) -> str:
    gate = ident.get("gate")
    if isinstance(gate, str):
        return gate.strip()
    if isinstance(gate, dict):
        return str(gate.get("response") or "").strip()
    return ""


def _gate_rationale(ident: dict[str, Any]) -> str:
    gate = ident.get("gate")
    if isinstance(gate, dict):
        return str(gate.get("rationale") or "")
    return ""


def _bucket_from_spread(spread: float) -> str:
    if spread > BUCKET_BP:
        return "above_wacc"
    if spread < -BUCKET_BP:
        return "below_wacc"
    return "approx_wacc"


def _terminal_g(vm: dict[str, Any], ident: dict[str, Any]) -> float | None:
    g = _assumption_float(vm, "terminal_growth")
    if g is not None:
        return g
    ri = ident.get("reinvestment_identity")
    if isinstance(ri, dict):
        g2 = _as_float(ri.get("g"))
        if g2 is not None:
            return g2
    tc = vm.get("terminal_consistency")
    if isinstance(tc, dict):
        return _as_float(tc.get("g"))
    return None


def _result_base_ev(session: Path) -> float | None:
    data, err = load_json(session / RESULT_REL)
    if err or not isinstance(data, dict):
        return None
    dcf = data.get("dcf")
    if isinstance(dcf, dict):
        base = dcf.get("base")
        if isinstance(base, dict):
            return _as_float(base.get("ev"))
    return _as_float(data.get("ev"))


def _result_nopat(session: Path) -> float | None:
    data, err = load_json(session / RESULT_REL)
    if err or not isinstance(data, dict):
        return None
    n = _as_float(data.get("nopat")) or _nested_float(data, "mid_cycle", "nopat")
    if n is not None:
        return n
    dcf = data.get("dcf")
    if isinstance(dcf, dict):
        base = dcf.get("base")
        if isinstance(base, dict):
            years = base.get("years")
            if isinstance(years, list) and years:
                last = years[-1]
                if isinstance(last, dict):
                    return _as_float(last.get("nopat"))
    return None


def thin_roic_from_valuation(vm: dict[str, Any] | None) -> dict[str, Any] | None:
    """Thin projection for prediction_snapshot. None if the object is absent."""
    if not isinstance(vm, dict):
        return None
    ident = vm.get("roic_identity")
    if not isinstance(ident, dict):
        return None
    applies = ident.get("applies")
    if applies is False:
        out: dict[str, Any] = {"applies": False}
        analog = ident.get("native_analog")
        if analog not in (None, ""):
            out["native_analog"] = analog
        reason = ident.get("not_applicable_reason")
        if isinstance(reason, str) and reason.strip():
            out["not_applicable_reason"] = reason.strip()
        return out
    out = {"applies": True}
    nopat = _as_float(ident.get("nopat"))
    ic = _as_float(ident.get("invested_capital"))
    wacc = _as_float(ident.get("wacc"))
    mid = _as_float(ident.get("mid_cycle_roic"))
    ttc = _as_float(ident.get("ttc_roic"))
    spread = _as_float(ident.get("spread_mid_cycle"))
    bucket = ident.get("quality_bucket")
    cheap = _cheap_class(ident)
    resp = _gate_response(ident)
    g0 = _nested_float(ident, "g0_counterfactual", "equity_fv")
    a_ev = _nested_float(ident, "column_a", "ev")
    b_ev = _nested_float(ident, "column_b", "ev")
    if nopat is not None:
        out["nopat"] = nopat
    if mid is not None:
        out["mid_cycle_roic"] = mid
    if ttc is not None:
        out["ttc_roic"] = ttc
    if wacc is not None:
        out["wacc"] = wacc
    if spread is not None:
        out["spread_mid_cycle"] = spread
    if isinstance(bucket, str) and bucket:
        out["quality_bucket"] = bucket
    if cheap:
        out["cheap_claim"] = cheap
    if resp:
        out["gate_response"] = resp
    if g0 is not None:
        out["g0_equity_fv"] = g0
    if a_ev is not None:
        out["column_a_ev"] = a_ev
    if b_ev is not None:
        out["column_b_ev"] = b_ev
    if ic is not None:
        out["invested_capital"] = ic
    return out


def thin_roic_metrics(bundle: dict[str, Any] | None) -> dict[str, Any]:
    """run_metrics keys from extract bundle. Empty if identity absent."""
    if not isinstance(bundle, dict):
        return {}
    ident = bundle.get("roic_identity")
    if not isinstance(ident, dict):
        return {}
    metrics: dict[str, Any] = {}
    if ident.get("applies") is False:
        metrics["roic_applies"] = 0.0
        analog = ident.get("native_analog")
        if analog:
            metrics["roic_native_analog"] = str(analog)
        return metrics
    metrics["roic_applies"] = 1.0
    numeric = (
        ("mid_cycle_roic", "mid_cycle_roic"),
        ("ttc_roic", "ttc_roic"),
        ("wacc", "roic_wacc"),
        ("spread_mid_cycle", "roic_spread"),
        ("g0_equity_fv", "g0_equity_fv"),
        ("column_a_ev", "column_a_ev"),
        ("column_b_ev", "column_b_ev"),
        ("invested_capital", "invested_capital"),
        ("nopat", "roic_nopat"),
    )
    for src, dst in numeric:
        v = ident.get(src)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            metrics[dst] = float(v)
    for src, dst in (
        ("quality_bucket", "quality_bucket"),
        ("cheap_claim", "cheap_claim"),
        ("gate_response", "roic_gate_response"),
    ):
        v = ident.get(src)
        if isinstance(v, str) and v.strip():
            metrics[dst] = v.strip()
    return metrics


def check_roic_identity(session: Path) -> list[tuple[str, str, str]]:
    """When new runtime + valuation, or object present: identity paperwork."""
    vm_path = session / VM_REL
    enforce = session_is_roic_runtime(session)
    present = False
    if vm_path.is_file():
        peek, _ = load_json(vm_path)
        present = isinstance(peek, dict) and isinstance(peek.get("roic_identity"), dict)

    if not vm_path.is_file():
        if enforce:
            return [("SKIPPED", "roic_identity", "valuation_model.json missing")]
        return [("SKIPPED", "roic_identity", "legacy/slim")]

    vm, err = load_json(vm_path)
    if err:
        return [("FAIL", "roic_identity", f"valuation_model unparseable: {err}")]
    assert isinstance(vm, dict)

    ident = vm.get("roic_identity")
    if not isinstance(ident, dict):
        if enforce:
            return [
                (
                    "FAIL",
                    "roic_identity",
                    "new runtime requires valuation_model.roic_identity "
                    "(same-script owner-earnings ROIC; applies:false with reason when "
                    "industrial IC does not apply)",
                )
            ]
        return [("SKIPPED", "roic_identity", "legacy/slim (no roic_identity; harness_version < 2.8.0)")]

    out: list[tuple[str, str, str]] = []
    applies = ident.get("applies")
    if applies is not True and applies is not False:
        out.append(
            (
                "FAIL",
                "roic_identity.applies",
                "applies must be a boolean (true for DCF/FCFF family; false with reason otherwise)",
            )
        )
        return out

    if applies is False:
        reason = str(ident.get("not_applicable_reason") or "")
        if len(reason.strip()) < REASON_MIN:
            out.append(
                (
                    "FAIL",
                    "roic_identity.not_applicable_reason",
                    "applies:false requires not_applicable_reason (≥40 chars; native analog for banks/REITs/growth)",
                )
            )
            return out
        analog = ident.get("native_analog")
        detail = f"applies=false analog={analog}" if analog else "applies=false"
        out.append(("PASS", "roic_identity", detail))
        return out

    nopat = _as_float(ident.get("nopat"))
    ic = _as_float(ident.get("invested_capital"))
    wacc = _as_float(ident.get("wacc"))
    mid = _as_float(ident.get("mid_cycle_roic"))
    ttc = _as_float(ident.get("ttc_roic"))
    spread = _as_float(ident.get("spread_mid_cycle"))
    bucket = ident.get("quality_bucket")
    a_ev = _nested_float(ident, "column_a", "ev")
    b_ev = _nested_float(ident, "column_b", "ev")
    b_ic = _nested_float(ident, "column_b", "ic")
    g0_fv = _nested_float(ident, "g0_counterfactual", "equity_fv")
    cheap = _cheap_class(ident)
    resp = _gate_response(ident)
    leases = str(ident.get("leases") or "").strip()

    missing: list[str] = []
    if nopat is None:
        missing.append("nopat.value")
    if ic is None:
        missing.append("invested_capital.value")
    if wacc is None:
        missing.append("wacc")
    if mid is None:
        missing.append("mid_cycle_roic.value")
    if ttc is None:
        missing.append("ttc_roic.value")
    if a_ev is None:
        missing.append("column_a.ev")
    if b_ev is None and b_ic is None and ic is None:
        missing.append("column_b.ev or column_b.ic")
    if g0_fv is None:
        missing.append("g0_counterfactual.equity_fv")
    if not cheap:
        missing.append("cheap_claim.class")
    if missing:
        out.append(
            (
                "FAIL",
                "roic_identity",
                "applies:true requires " + ", ".join(missing),
            )
        )
        return out

    if cheap not in CHEAP_OK:
        out.append(
            (
                "FAIL",
                "roic_identity.cheap_claim",
                f"cheap_claim.class must be one of {sorted(CHEAP_OK)}; got {cheap!r}",
            )
        )
    else:
        out.append(("PASS", "roic_identity.cheap_claim", cheap or ""))

    if leases not in LEASES_OK:
        out.append(
            (
                "FAIL",
                "roic_identity.leases",
                "leases must be opex_and_out_of_ic or capitalized_both (mixed is FAIL)",
            )
        )
    else:
        out.append(("PASS", "roic_identity.leases", leases))

    awacc = _assumption_float(vm, "wacc")
    if awacc is not None and wacc is not None and abs(wacc - awacc) > WACC_EPS:
        out.append(
            (
                "FAIL",
                "roic_identity.wacc",
                f"roic_identity.wacc {wacc} != assumptions.wacc {awacc} (5 bp); "
                "hurdle is in-model WACC, not a 15% Buffett paste",
            )
        )
    else:
        out.append(("PASS", "roic_identity.wacc", f"{wacc}"))

    assert nopat is not None and ic is not None and mid is not None
    if abs(ic) > 1e-12:
        expected_mid = nopat / ic
        if abs(mid - expected_mid) > ROIC_EPS:
            out.append(
                (
                    "FAIL",
                    "roic_identity.mid_cycle_roic",
                    f"mid_cycle_roic {mid} != nopat/IC {expected_mid:.6f}",
                )
            )
        else:
            out.append(("PASS", "roic_identity.mid_cycle_roic", f"{mid:.4f}"))
    expected_spread = mid - (wacc or 0.0)
    if spread is None:
        out.append(("FAIL", "roic_identity.spread_mid_cycle", "spread_mid_cycle required"))
        spread = expected_spread
    elif abs(spread - expected_spread) > SPREAD_EPS + ROIC_EPS:
        out.append(
            (
                "FAIL",
                "roic_identity.spread_mid_cycle",
                f"spread_mid_cycle {spread} != mid_cycle_roic − wacc {expected_spread:.6f}",
            )
        )
    else:
        out.append(("PASS", "roic_identity.spread_mid_cycle", f"{spread:.4f}"))

    derived = _bucket_from_spread(spread if spread is not None else expected_spread)
    if not isinstance(bucket, str) or bucket not in BUCKETS:
        out.append(
            (
                "FAIL",
                "roic_identity.quality_bucket",
                f"quality_bucket must be one of {sorted(BUCKETS)}",
            )
        )
        bucket = derived
    elif bucket != derived:
        out.append(
            (
                "FAIL",
                "roic_identity.quality_bucket",
                f"quality_bucket {bucket} != {derived} from spread vs 50 bp band",
            )
        )
    else:
        out.append(("PASS", "roic_identity.quality_bucket", bucket))

    res_nopat = _result_nopat(session)
    if res_nopat is not None and abs(nopat - res_nopat) > max(EV_EPS_ABS, EV_EPS_REL * abs(res_nopat)):
        out.append(
            (
                "FAIL",
                "roic_identity.nopat",
                f"nopat {nopat} != compute-script NOPAT {res_nopat} (same stack as the DCF)",
            )
        )
    elif res_nopat is not None:
        out.append(("PASS", "roic_identity.nopat", "matches valuation_result"))

    res_ev = _result_base_ev(session)
    if res_ev is not None and a_ev is not None:
        if abs(a_ev - res_ev) > max(EV_EPS_ABS, EV_EPS_REL * abs(res_ev)):
            out.append(
                (
                    "FAIL",
                    "roic_identity.column_a",
                    f"column_a.ev {a_ev} != dcf.base.ev {res_ev}",
                )
            )
        else:
            out.append(("PASS", "roic_identity.column_a", f"ev={a_ev}"))
    elif a_ev is not None:
        out.append(("PASS", "roic_identity.column_a", f"ev={a_ev}"))

    ri = ident.get("reinvestment_identity")
    mismatch = None
    ri_g = None
    if isinstance(ri, dict):
        mismatch = ri.get("mismatch")
        ri_g = _as_float(ri.get("g"))
    g = _terminal_g(vm, ident)
    if ri_g is not None and g is not None and abs(ri_g - g) > G_ZERO_EPS:
        out.append(
            (
                "FAIL",
                "roic_identity.reinvestment_identity",
                f"reinvestment_identity.g {ri_g} != terminal g {g}",
            )
        )
    elif isinstance(ri, dict):
        out.append(("PASS", "roic_identity.reinvestment_identity", f"mismatch={mismatch}"))

    below_or_approx = bucket in ("below_wacc", "approx_wacc")
    if below_or_approx and cheap == "franchise_mos":
        out.append(
            (
                "FAIL",
                "roic_identity.cheap_claim",
                "franchise_mos forbidden when quality_bucket is below_wacc or approx_wacc "
                "(use equity_near_book / residual_option / not_cheap)",
            )
        )

    g_pos = g is not None and g > G_ZERO_EPS
    mismatch_true = mismatch is True
    if below_or_approx:
        if resp not in LEGAL_EXITS:
            out.append(
                (
                    "FAIL",
                    "roic_identity.gate",
                    "mid-cycle ROIC ≤ WACC requires gate.response in "
                    f"{sorted(LEGAL_EXITS)} (harness never writes g)",
                )
            )
        else:
            ic_ref = ic if ic is not None else b_ic
            if resp == "g_zero":
                if g is None or abs(g) > G_ZERO_EPS:
                    out.append(
                        (
                            "FAIL",
                            "roic_identity.gate",
                            "gate.response=g_zero requires terminal g = 0",
                        )
                    )
                else:
                    out.append(("PASS", "roic_identity.gate", "g_zero"))
            elif resp == "reinvestment_in_engine":
                if mismatch_true:
                    out.append(
                        (
                            "FAIL",
                            "roic_identity.gate",
                            "gate.response=reinvestment_in_engine requires "
                            "reinvestment_identity.mismatch=false",
                        )
                    )
                else:
                    out.append(("PASS", "roic_identity.gate", "reinvestment_in_engine"))
            elif resp == "reconciled_to_ic":
                if ic_ref is None or a_ev is None or abs(ic_ref) < 1e-12:
                    out.append(
                        (
                            "FAIL",
                            "roic_identity.gate",
                            "reconciled_to_ic requires column_a.ev and invested_capital",
                        )
                    )
                elif abs(a_ev - ic_ref) / abs(ic_ref) > IC_NOISE:
                    out.append(
                        (
                            "FAIL",
                            "roic_identity.gate",
                            f"|column_a.ev − IC| / IC = {abs(a_ev - ic_ref) / abs(ic_ref):.3f} "
                            f"> {IC_NOISE:.0%} (Gordon plug while ROIC ≤ WACC is not equity≈book)",
                        )
                    )
                elif cheap not in CHEAP_WHEN_NOT_ABOVE:
                    out.append(
                        (
                            "FAIL",
                            "roic_identity.gate",
                            "reconciled_to_ic requires cheap_claim equity_near_book / "
                            "residual_option / not_cheap",
                        )
                    )
                else:
                    out.append(("PASS", "roic_identity.gate", "reconciled_to_ic"))
            elif resp == "cut_earnings_power":
                if len(_gate_rationale(ident).strip()) < REASON_MIN:
                    out.append(
                        (
                            "FAIL",
                            "roic_identity.gate",
                            "cut_earnings_power requires gate.rationale (≥40 chars) naming the cut NOPAT",
                        )
                    )
                else:
                    out.append(("PASS", "roic_identity.gate", "cut_earnings_power"))
            if g_pos and mismatch_true and resp not in LEGAL_EXITS:
                out.append(
                    (
                        "FAIL",
                        "roic_identity.gate",
                        "g>0 with reinvestment mismatch while ROIC ≤ WACC is illegal paperwork",
                    )
                )
    else:
        out.append(("PASS", "roic_identity.gate", "above_wacc — Gordon allowed"))

    out.extend(check_mid_cycle_construction(ident, session))

    if not any(r[0] == "FAIL" for r in out):
        out.append(("PASS", "roic_identity", f"bucket={bucket} cheap={cheap}"))
    return out

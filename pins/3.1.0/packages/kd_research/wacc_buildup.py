"""WACC-buildup identity gates (harness >= 2.40.0).

Agent 5 still judges Rf, beta, ERP, spread, and target weights. The machine
fails impossible ingredients (coupon-as-Kd, Kd below Rf, trough market weights
as the sole going-concern structure). It never writes a WACC or fair value.

Legacy / missing harness_version / harness < 2.40.0 SKIPPED when the object is
absent. Presence on an old session is validated, never omit-FAIL.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.kd_research.check_core import load_json, session_since

WACC_SINCE = (2, 40, 0)
VM_REL = "data/valuation_model.json"

WACC_EPS = 0.0005  # 5 bp
WEIGHT_SUM_EPS = 0.01
COPY_WD_EPS = 0.02
WD_DISTRESSED = 0.35
WD_SKIP_KD = 0.05
GAP_BP = 200.0
KE_GAP_BP = 50.0
SPREAD_FLOOR_BP = 25.0
REASON_MIN = 40
GAP_BP_EPS = 25.0

KD_SOURCES = frozenset({"current_yield", "rf_plus_spread"})
WEIGHT_POLICIES = frozenset({"current_market", "target", "blended"})
BELOW_RF_GATES = frozenset({"negative_rate_market"})
SPREAD_HATCHES = frozenset({"gov_or_aaa", "quoted_ytm_equals_rf", "negative_rate_market"})

IMPLIED_WACC_KEYS = (
    "wacc_on_base_path",
    "wacc_on_base_volume_om_path",
    "wacc",
)

KD_WEIGHT_NEEDLES = (
    "kd",
    "cost of debt",
    "coupon",
    "yield",
    "weight",
    "leverage",
    "capital structure",
    "wd",
    "debt mix",
)


def session_is_wacc_runtime(session: Path) -> bool:
    return session_since(session, WACC_SINCE)


def _as_float(val: Any) -> float | None:
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, dict):
        return _as_float(val.get("value"))
    return None


def _assumption_float(vm: dict[str, Any], key: str) -> float | None:
    assumptions = vm.get("assumptions")
    if not isinstance(assumptions, dict):
        return None
    return _as_float(assumptions.get(key))


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


def _implied_wacc(vm: dict[str, Any]) -> float | None:
    re = vm.get("reverse_engineering")
    if not isinstance(re, dict):
        return None
    implied = re.get("implied")
    if isinstance(implied, dict):
        for key in IMPLIED_WACC_KEYS:
            v = _as_float(implied.get(key))
            if v is not None:
                return v
    for key in IMPLIED_WACC_KEYS:
        v = _as_float(re.get(key))
        if v is not None:
            return v
    return None


def _rationale_has_needle(text: str, needles: tuple[str, ...]) -> bool:
    blob = text.lower()
    return any(n in blob for n in needles)


def check_wacc_if_vm(session: Path) -> list[tuple[str, str, str]]:
    if not (session / VM_REL).is_file():
        return []
    return check_wacc_buildup(session)


def check_wacc_buildup(session: Path) -> list[tuple[str, str, str]]:
    vm_path = session / VM_REL
    enforce = session_is_wacc_runtime(session)
    if not vm_path.is_file():
        if enforce:
            return [("SKIPPED", "wacc_buildup", "valuation_model.json missing")]
        return [("SKIPPED", "wacc_buildup", "legacy/slim")]

    vm, err = load_json(vm_path)
    if err:
        return [("FAIL", "wacc_buildup", f"valuation_model unparseable: {err}")]
    assert isinstance(vm, dict)

    ident = vm.get("wacc_buildup")
    if not isinstance(ident, dict):
        if enforce:
            return [
                (
                    "FAIL",
                    "wacc_buildup",
                    "new runtime requires valuation_model.wacc_buildup "
                    "(Kd is current yield or Rf+spread; coupon illegal as Kd; "
                    "applies:false with reason when WACC is not the native hurdle)",
                )
            ]
        return [
            (
                "SKIPPED",
                "wacc_buildup",
                "legacy/slim (no wacc_buildup; harness_version < 2.40.0)",
            )
        ]

    out: list[tuple[str, str, str]] = []
    applies = ident.get("applies")
    if applies is not True and applies is not False:
        out.append(
            (
                "FAIL",
                "wacc_buildup.applies",
                "applies must be a boolean (true for FCFF/WACC DCF; false with "
                "reason for banks/insurance/other non-WACC natives; REIT keeps WACC on ≥ 3.1.0)",
            )
        )
        return out

    if applies is False:
        reason = str(ident.get("not_applicable_reason") or "")
        if len(reason.strip()) < REASON_MIN:
            out.append(
                (
                    "FAIL",
                    "wacc_buildup.not_applicable_reason",
                    "applies:false requires not_applicable_reason (≥40 chars; "
                    "native analog for banks/insurance; REIT keeps WACC on ≥ 3.1.0)",
                )
            )
            return out
        analog = ident.get("native_analog")
        detail = f"applies=false analog={analog}" if analog else "applies=false"
        out.append(("PASS", "wacc_buildup", detail))
        return out

    rf = _as_float(ident.get("rf"))
    ke = _as_float(ident.get("ke"))
    kd_pre = _as_float(ident.get("kd_pretax"))
    kd_at = _as_float(ident.get("kd_aftertax"))
    tax = _as_float(ident.get("tax"))
    we = _as_float(ident.get("we"))
    wd = _as_float(ident.get("wd"))
    wacc = _as_float(ident.get("wacc"))
    kd_source = str(ident.get("kd_source") or "").strip()
    weight_policy = str(ident.get("weight_policy") or "").strip()
    current_wd = _as_float(ident.get("current_market_wd"))
    spread_bp = _as_float(ident.get("spread_bp"))
    below_rf_gate = str(ident.get("kd_below_rf_gate") or "").strip()
    spread_hatch = str(ident.get("kd_spread_hatch") or "").strip()
    lev_hatch = str(ident.get("structural_leverage_hatch") or "").strip()
    gap_rationale = str(ident.get("wacc_gap_rationale") or "")
    stored_gap = _as_float(ident.get("implied_wacc_gap_bp"))

    missing: list[str] = []
    for name, val in (
        ("rf", rf),
        ("ke", ke),
        ("we", we),
        ("wd", wd),
        ("wacc", wacc),
        ("tax", tax),
    ):
        if val is None:
            missing.append(name)
    skip_kd = wd is not None and wd < WD_SKIP_KD
    if not skip_kd:
        if kd_pre is None:
            missing.append("kd_pretax")
        if kd_at is None:
            missing.append("kd_aftertax")
        if not kd_source:
            missing.append("kd_source")
    if missing:
        out.append(
            (
                "FAIL",
                "wacc_buildup.fields",
                "applies:true missing " + ", ".join(missing),
            )
        )
        return out

    assert rf is not None and ke is not None and we is not None
    assert wd is not None and wacc is not None and tax is not None

    if weight_policy not in WEIGHT_POLICIES:
        out.append(
            (
                "FAIL",
                "wacc_buildup.weight_policy",
                "weight_policy must be current_market | target | blended; "
                f"got {weight_policy!r}",
            )
        )
        return out

    if abs(we + wd - 1.0) > WEIGHT_SUM_EPS:
        out.append(
            (
                "FAIL",
                "wacc_buildup.weights_sum",
                f"we+wd={we + wd:.4f} must equal 1 within {WEIGHT_SUM_EPS}",
            )
        )
        return out

    if not skip_kd:
        if kd_source not in KD_SOURCES:
            out.append(
                (
                    "FAIL",
                    "wacc_buildup.kd_source",
                    "kd_source must be current_yield or rf_plus_spread; "
                    "coupon is illegal as the WACC input "
                    f"(got {kd_source!r})",
                )
            )
            return out
        assert kd_pre is not None and kd_at is not None
        expected_at = kd_pre * (1.0 - tax)
        if abs(kd_at - expected_at) > WACC_EPS:
            out.append(
                (
                    "FAIL",
                    "wacc_buildup.kd_aftertax",
                    f"kd_aftertax {kd_at} != kd_pretax×(1−t) {expected_at:.6f} "
                    f"(5 bp)",
                )
            )
            return out
        if kd_pre + 1e-12 < rf:
            if below_rf_gate not in BELOW_RF_GATES:
                out.append(
                    (
                        "FAIL",
                        "wacc_buildup.kd_vs_rf",
                        f"kd_pretax {kd_pre} < rf {rf}; coupon-as-Kd is illegal. "
                        "Only kd_below_rf_gate=negative_rate_market with local Rf "
                        "evidence may pass.",
                    )
                )
                return out
            gate_r = str(ident.get("kd_below_rf_rationale") or "")
            if len(gate_r.strip()) < REASON_MIN:
                out.append(
                    (
                        "FAIL",
                        "wacc_buildup.kd_below_rf_gate",
                        "negative_rate_market requires kd_below_rf_rationale ≥40 chars "
                        "with local Rf evidence (not US 10Y pasted onto local Kd)",
                    )
                )
                return out
            out.append(
                (
                    "PASS",
                    "wacc_buildup.kd_vs_rf",
                    "kd_pretax < rf with negative_rate_market hatch",
                )
            )
        else:
            out.append(
                ("PASS", "wacc_buildup.kd_vs_rf", f"kd_pretax {kd_pre} >= rf {rf}")
            )

        if kd_source == "rf_plus_spread":
            if spread_bp is None:
                out.append(
                    (
                        "FAIL",
                        "wacc_buildup.spread_bp",
                        "kd_source=rf_plus_spread requires spread_bp (basis points)",
                    )
                )
                return out
            if spread_bp < SPREAD_FLOOR_BP and spread_hatch not in SPREAD_HATCHES:
                out.append(
                    (
                        "FAIL",
                        "wacc_buildup.spread_bp",
                        f"rf_plus_spread spread_bp {spread_bp} < {SPREAD_FLOOR_BP} "
                        "requires kd_spread_hatch gov_or_aaa | quoted_ytm_equals_rf | "
                        "negative_rate_market (0 bp is not a silent default)",
                    )
                )
                return out
            out.append(
                (
                    "PASS",
                    "wacc_buildup.spread_bp",
                    f"spread_bp={spread_bp} hatch={spread_hatch or 'none'}",
                )
            )
    else:
        out.append(
            (
                "PASS",
                "wacc_buildup.kd_skip",
                f"wd {wd} < {WD_SKIP_KD} — skip Kd-vs-Rf / spread floor (net-cash)",
            )
        )

    kd_at_use = 0.0 if skip_kd or kd_at is None else kd_at
    expected_wacc = we * ke + wd * kd_at_use
    if abs(wacc - expected_wacc) > WACC_EPS:
        out.append(
            (
                "FAIL",
                "wacc_buildup.wacc",
                f"wacc {wacc} != we×Ke + wd×Kd(1−t) {expected_wacc:.6f} (5 bp)",
            )
        )
        return out
    out.append(("PASS", "wacc_buildup.wacc", f"{wacc}"))

    awacc = _assumption_float(vm, "wacc")
    if awacc is not None and abs(wacc - awacc) > WACC_EPS:
        out.append(
            (
                "FAIL",
                "wacc_buildup.assumptions",
                f"wacc_buildup.wacc {wacc} != assumptions.wacc {awacc} (5 bp)",
            )
        )
        return out

    roic = vm.get("roic_identity")
    if isinstance(roic, dict) and roic.get("applies") is True:
        rw = _as_float(roic.get("wacc"))
        if rw is not None and abs(wacc - rw) > WACC_EPS:
            out.append(
                (
                    "FAIL",
                    "wacc_buildup.roic_wacc",
                    f"wacc_buildup.wacc {wacc} != roic_identity.wacc {rw} (5 bp)",
                )
            )
            return out

    implied = _implied_wacc(vm)
    re_obj = vm.get("reverse_engineering")
    has_re = isinstance(re_obj, dict)
    gap_bp = None
    if implied is not None:
        gap_bp = (implied - wacc) * 10000.0
        if stored_gap is not None and abs(stored_gap - gap_bp) > GAP_BP_EPS:
            out.append(
                (
                    "FAIL",
                    "wacc_buildup.implied_wacc_gap_bp",
                    f"implied_wacc_gap_bp {stored_gap} != computed {gap_bp:.1f} "
                    f"(implied {implied} − wacc {wacc})",
                )
            )
            return out

    distressed = wd > WD_DISTRESSED and gap_bp is not None and gap_bp > GAP_BP
    if wd > WD_DISTRESSED and has_re and implied is None:
        out.append(
            (
                "FAIL",
                "wacc_buildup.implied_wacc",
                f"wd {wd} > {WD_DISTRESSED} requires an implied WACC on "
                "reverse_engineering so the distressed-weight tripwire can fire "
                "(do not omit the inversion to keep current_market weights)",
            )
        )
        return out

    if distressed:
        if current_wd is None:
            out.append(
                (
                    "FAIL",
                    "wacc_buildup.current_market_wd",
                    "distressed-equity tripwire (wd>0.35 and implied gap>200bp) "
                    "requires current_market_wd so target weights cannot silently "
                    "copy the trough mix",
                )
            )
            return out
        if weight_policy == "current_market":
            out.append(
                (
                    "FAIL",
                    "wacc_buildup.weight_policy",
                    "going-concern DCF may not use only current_market weights "
                    f"when wd {wd:.3f} > 0.35 and implied-WACC gap {gap_bp:.0f} bp "
                    "> 200; use target or blended (and do not copy trough wd)",
                )
            )
            return out
        if abs(wd - current_wd) < COPY_WD_EPS and len(lev_hatch) < REASON_MIN:
            out.append(
                (
                    "FAIL",
                    "wacc_buildup.target_wd_copy",
                    f"|wd {wd:.4f} − current_market_wd {current_wd:.4f}| < "
                    f"{COPY_WD_EPS} while distressed tripwire is on — relabeling "
                    "trough leverage as target is illegal without "
                    "structural_leverage_hatch ≥40 chars (non-price basis: mgmt "
                    "target, rating agency, indenture, peer book)",
                )
            )
            return out
        out.append(
            (
                "PASS",
                "wacc_buildup.distressed_weights",
                f"policy={weight_policy} wd={wd:.3f} current_wd={current_wd:.3f}",
            )
        )
    else:
        out.append(
            (
                "PASS",
                "wacc_buildup.distressed_weights",
                "tripwire off",
            )
        )

    if gap_bp is not None and gap_bp > GAP_BP:
        if len(gap_rationale.strip()) < REASON_MIN:
            out.append(
                (
                    "FAIL",
                    "wacc_buildup.wacc_gap_rationale",
                    "implied WACC > model by >200 bp requires wacc_gap_rationale "
                    "≥40 chars that addresses Kd or capital-structure weights — "
                    "not only 'tape is cheap' / franchise_mos",
                )
            )
            return out
        if not _rationale_has_needle(gap_rationale, KD_WEIGHT_NEEDLES):
            out.append(
                (
                    "FAIL",
                    "wacc_buildup.wacc_gap_rationale",
                    "wacc_gap_rationale must name Kd, yield, coupon, weights, or "
                    "leverage; 'tape is cheap' / franchise MoS alone is circular",
                )
            )
            return out
        if abs((implied - ke) * 10000.0) < KE_GAP_BP:
            out.append(
                (
                    "WARN",
                    "wacc_buildup.implied_vs_ke",
                    f"implied WACC {implied:.4f} ≈ Ke {ke:.4f} while WACC {wacc:.4f} "
                    "is >200 bp below — gap is the debt mix, not CAPM vs tape",
                )
            )
        out.append(
            (
                "PASS",
                "wacc_buildup.wacc_gap_rationale",
                f"gap {gap_bp:.0f} bp explained",
            )
        )

    cheap = vm.get("roic_identity")
    cheap_class = None
    if isinstance(cheap, dict):
        cc = cheap.get("cheap_claim")
        if isinstance(cc, dict):
            cheap_class = str(cc.get("class") or "").strip()
        elif isinstance(cc, str):
            cheap_class = cc.strip()
    if (
        cheap_class == "franchise_mos"
        and gap_bp is not None
        and gap_bp > GAP_BP
    ):
        note = str(ident.get("franchise_hurdle_note") or "")
        if len(note.strip()) < REASON_MIN:
            out.append(
                (
                    "WARN",
                    "wacc_buildup.franchise_hurdle_note",
                    "franchise_mos with implied-WACC gap >200 bp should discuss "
                    "mid-cycle ROIC vs Ke or vs a WACC rebuilt with legal Kd and "
                    "non-trough weights (disclosure; not a second hurdle number)",
                )
            )

    out.append(("PASS", "wacc_buildup.gate", "ingredients legal"))
    return out

"""Valuation hygiene gates that are not Street identity.

Conservatism dials, Y1 stacking pair, SOTP/DCF gap, same-period box floor.
Catalog row check_street_hygiene runs these; check_street_bind does not.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.kd_research.check_core import load_json
from packages.kd_research.street_y1 import StreetY1Policy

DIAL_KEYS = (
    "volume_vs_guide",
    "gaap_om_vs_guide",
    "sbc_in_fcff",
    "wacc_vs_buildup",
)
DIAL_APPLIES = frozenset({"base", "bear_only", "none"})
STACK_JUSTIFY_MIN_LEN = 40
SOTP_GAP_THRESHOLD = 0.40
GAP_RATIONALE_MIN_LEN = 40
MOS_CONSISTENCY_EPS = 0.1  # |pct - 100*frac| tolerance


def _as_float(val: Any) -> float | None:
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    return None


def _sotp_and_dcf_both_present(vm: dict[str, Any]) -> bool:
    """True when model name/methods/assumption keys indicate both SOTP and DCF ran."""
    model = vm.get("model") if isinstance(vm.get("model"), dict) else {}
    name = str(model.get("name") or "").lower()
    methods = model.get("methods") or model.get("cross_checks") or []
    if isinstance(methods, list):
        method_text = " ".join(str(m).lower() for m in methods)
    else:
        method_text = str(methods).lower()
    assumption_keys: list[str] = []
    assumptions = vm.get("assumptions")
    if isinstance(assumptions, dict):
        assumption_keys = [str(k).lower() for k in assumptions]
    blob = " ".join([name, method_text, *assumption_keys])
    has_sotp = any(t in blob for t in ("sotp", "sum-of-the-parts", "sum_of_the_parts"))
    has_dcf = any(t in blob for t in ("dcf", "discounted-cash", "discounted_cash"))
    return has_sotp and has_dcf


def check_conservatism_dials(vm: dict[str, Any], *, require: bool) -> list[tuple[str, str, str]]:
    dials = vm.get("conservatism_dials")
    if dials is None:
        if require:
            return [
                (
                    "FAIL",
                    "conservatism_dials",
                    "new runtime requires conservatism_dials[] with keys "
                    "volume_vs_guide, gaap_om_vs_guide, sbc_in_fcff, wacc_vs_buildup "
                    "(applies_in base|bear_only|none). Omitting the array is silent stacking.",
                )
            ]
        return [("SKIPPED", "conservatism_dials", "omitted")]
    if not isinstance(dials, list):
        return [("FAIL", "conservatism_dials", "must be an array")]
    by_key: dict[str, str] = {}
    for d in dials:
        if not isinstance(d, dict):
            continue
        k = str(d.get("key") or d.get("dial") or "").strip()
        applies = str(d.get("applies_in") or "").strip()
        if k:
            by_key[k] = applies
    missing = [k for k in DIAL_KEYS if k not in by_key]
    if require and missing:
        return [
            (
                "FAIL",
                "conservatism_dials",
                f"new runtime requires all four conservatism_dials keys; missing {missing}",
            )
        ]
    n_base = sum(1 for k in DIAL_KEYS if by_key.get(k) == "base")
    just = str(vm.get("stacking_justification") or "")
    if n_base >= 3 and len(just.strip()) < STACK_JUSTIFY_MIN_LEN:
        return [
            (
                "FAIL",
                "conservatism_dials stacking",
                "≥3 conservatism_dials applies_in=base requires stacking_justification "
                "(do not stack volume + GAAP OM + SBC-as-cash + high WACC silently into base)",
            )
        ]
    return [("PASS", "conservatism_dials", f"{len(dials)} dial(s); n_base={n_base}")]


def check_y1_stacking_pair(
    vm: dict[str, Any],
    abs_delta: float,
    *,
    fail_band: float | None,
) -> list[tuple[str, str, str]]:
    """FAIL volume_vs_guide ∧ sbc_in_fcff in base while Y1 is outside the Street fail band."""
    dials = vm.get("conservatism_dials")
    if not isinstance(dials, list):
        return []
    if fail_band is None:
        return []
    by_key: dict[str, str] = {}
    for d in dials:
        if not isinstance(d, dict):
            continue
        k = str(d.get("key") or d.get("dial") or "").strip()
        applies = str(d.get("applies_in") or "").strip()
        if k:
            by_key[k] = applies
    if (
        by_key.get("volume_vs_guide") == "base"
        and by_key.get("sbc_in_fcff") == "base"
        and abs_delta > fail_band
    ):
        return [
            (
                "FAIL",
                "conservatism_dials stacking_pair",
                "volume_vs_guide and sbc_in_fcff both applies_in=base while Y1 is "
                f"outside the Street {fail_band * 100:.0f}% band",
            )
        ]
    return [
        (
            "PASS",
            "conservatism_dials stacking_pair",
            "no destock-below-Street + SBC-in-base pair",
        )
    ]


def check_same_period_box_floor(
    session: Path, vm: dict[str, Any]
) -> list[tuple[str, str, str]]:
    """FAIL a same-period remaining-box low undercut while Street is usable."""
    lq, err = load_json(session / "registry" / "latest_quarter.json")
    if err or not isinstance(lq, dict):
        return [("SKIPPED", "guide_floor", "latest_quarter.json missing")]
    guidance = lq.get("guidance") if isinstance(lq.get("guidance"), dict) else {}
    box_low = _as_float(guidance.get("revenue_box_low"))
    period = str(guidance.get("revenue_box_period") or "").strip()
    if box_low is None or not period:
        return [("PASS", "guide_floor", "no typed same-period revenue box")]
    bind = vm.get("street_bind") if isinstance(vm.get("street_bind"), dict) else {}
    intra = bind.get("intra_year")
    if not isinstance(intra, list):
        return [("PASS", "guide_floor", "no intra_year path to compare")]
    hits = []
    for row in intra:
        if not isinstance(row, dict):
            continue
        if str(row.get("period") or "").strip().lower() != period.lower():
            continue
        rev = _as_float(row.get("revenue"))
        if rev is not None:
            hits.append(rev)
    if not hits:
        return [("PASS", "guide_floor", f"no {period} path encoded")]
    path_rev = hits[0]
    if path_rev + 1e-9 < box_low:
        return [
            (
                "FAIL",
                "guide_floor",
                f"{period} path {path_rev} is below printed box low {box_low}",
            )
        ]
    return [("PASS", "guide_floor", f"{period} path {path_rev} >= box low {box_low}")]


def check_sotp_gap(vm: dict[str, Any], *, require_if_both: bool = False) -> list[tuple[str, str, str]]:
    rec = vm.get("multi_method_reconciliation")
    both = _sotp_and_dcf_both_present(vm)
    if both and not isinstance(rec, dict):
        if require_if_both:
            return [
                (
                    "FAIL",
                    "sotp_dcf_gap",
                    "SOTP and DCF both present in model.name/methods/assumption keys — "
                    "write multi_method_reconciliation (do not leave a 40%+ gap as theater)",
                )
            ]
        return []
    if not isinstance(rec, dict):
        return []
    primary = _as_float(rec.get("primary_fv_for_decision") or rec.get("primary_fv"))
    cross = _as_float(rec.get("cross_check_fv"))
    if primary is None or cross is None or abs(primary) < 1e-12:
        return [("PASS", "sotp_dcf_gap", "reconciliation present without both FVs")]
    gap = abs(cross - primary) / abs(primary)
    stored = _as_float(rec.get("delta_pct"))
    if stored is not None:
        as_frac = stored / 100.0 if abs(stored) > 1.5 else stored
        if abs(as_frac - (cross - primary) / primary) > 0.02 and abs(stored - gap) > 0.02:
            if abs(abs(as_frac) - gap) > 0.02:
                return [
                    (
                        "FAIL",
                        "sotp_dcf_gap delta_pct",
                        f"delta_pct {stored} inconsistent with |cross-primary|/primary {gap:.4f}",
                    )
                ]
    if gap > SOTP_GAP_THRESHOLD:
        reopened = rec.get("path_reopened")
        why = str(rec.get("what_changed") or rec.get("gap_rationale") or rec.get("why_primary_wins") or "")
        if reopened is True:
            if len(str(rec.get("what_changed") or "").strip()) < 10:
                return [
                    (
                        "FAIL",
                        "sotp_dcf_gap",
                        "|SOTP−DCF|/DCF > 40% with path_reopened=true requires what_changed",
                    )
                ]
            return [("PASS", "sotp_dcf_gap", "path_reopened")]
        if len(why.strip()) < GAP_RATIONALE_MIN_LEN:
            return [
                (
                    "FAIL",
                    "sotp_dcf_gap",
                    "|SOTP−DCF|/primary > 40% requires path_reopened + what_changed, or a gap_rationale/why_primary_wins that explains why the gap is real (segments, cash vs earnings) — then reopen the independent volume path if it is a skill miss",
                )
            ]
        return [("PASS", "sotp_dcf_gap", f"gap={gap:.2f} explained")]
    return [("PASS", "sotp_dcf_gap", f"gap={gap:.2f} <= 0.40")]


def check_mos_units(fair_value: object) -> list[tuple[str, str, str]]:
    """MoS unit hygiene for valuation_model.fair_value."""
    out: list[tuple[str, str, str]] = []
    if not isinstance(fair_value, dict):
        out.append(("SKIPPED", "mos_units", "fair_value missing or not object"))
        return out

    frac = fair_value.get("margin_of_safety")
    pct = fair_value.get("margin_of_safety_pct")

    if isinstance(frac, (int, float)) and isinstance(pct, (int, float)):
        expected = 100.0 * float(frac)
        if abs(float(pct) - expected) <= MOS_CONSISTENCY_EPS:
            out.append(
                (
                    "PASS",
                    "mos_units_dual",
                    f"fraction={frac} pct={pct} (consistent within {MOS_CONSISTENCY_EPS})",
                )
            )
        else:
            out.append(
                (
                    "FAIL",
                    "mos_units_dual",
                    f"pct={pct} vs 100*fraction={expected:.4f} — "
                    "write margin_of_safety as signed fraction and "
                    "margin_of_safety_pct as 100*fraction (never put 0-1 in *_pct)",
                )
            )
        return out

    if isinstance(pct, (int, float)) and not isinstance(frac, (int, float)):
        ap = abs(float(pct))
        if 0 < ap <= 1.5:
            out.append(
                (
                    "WARN",
                    "mos_units_pct_field",
                    f"margin_of_safety_pct={pct} looks like a fraction in a *_pct field; "
                    "store percent points (e.g. 29.2) and optionally margin_of_safety fraction",
                )
            )
        else:
            out.append(("PASS", "mos_units_pct_field", f"margin_of_safety_pct={pct}"))
        return out

    if isinstance(frac, (int, float)) and not isinstance(pct, (int, float)):
        out.append(
            (
                "WARN",
                "mos_units_fraction_only",
                f"margin_of_safety={frac} present without margin_of_safety_pct — "
                "prefer both fields for cross-session comparability",
            )
        )
        return out

    out.append(("SKIPPED", "mos_units", "no margin_of_safety fields"))
    return out


def check_valuation_decision_quality(session: Path) -> list[tuple[str, str, str]]:
    """Session-level MoS unit checks from data/valuation_model.json."""
    data, err = load_json(session / "data" / "valuation_model.json")
    if err:
        return [("SKIPPED", "mos_units", f"valuation_model.json {err}")]
    if not isinstance(data, dict):
        return [("SKIPPED", "mos_units", "valuation_model not an object")]
    return check_mos_units(data.get("fair_value"))


def check_valuation_content(session: Path) -> list[tuple[str, str, str]]:
    """2.5 entry: valuation_model has fair_value or model keys."""
    vm, err = load_json(session / "data" / "valuation_model.json")
    if err:
        return [("FAIL", "valuation_model_content", err)]
    if isinstance(vm, dict):
        if "fair_value" not in vm and "model" not in vm:
            return [("FAIL", "valuation_model_content", "missing fair_value/model keys")]
        return [("PASS", "valuation_model_content", "core keys present")]
    return [("FAIL", "valuation_model_content", "not an object")]


def check_street_hygiene(session: Path) -> list[tuple[str, str, str]]:
    """Dials / stacking / SOTP / box floor. Independent of Street identity."""
    vm_path = session / "data" / "valuation_model.json"
    if not vm_path.is_file():
        return []
    vm, err = load_json(vm_path)
    if err or not isinstance(vm, dict):
        return []
    from packages.kd_research.street_bind import session_is_street_runtime

    policy = StreetY1Policy.for_session(session)
    require = session_is_street_runtime(session)
    out: list[tuple[str, str, str]] = []
    out.extend(check_conservatism_dials(vm, require=require))
    bind = vm.get("street_bind") if isinstance(vm.get("street_bind"), dict) else {}
    base = _as_float(bind.get("base"))
    street_col = _as_float(bind.get("street"))
    if policy.y1 and street_col is not None and base is not None and abs(street_col) > 1e-12:
        out.extend(
            check_y1_stacking_pair(
                vm,
                abs((base - street_col) / street_col),
                fail_band=policy.fail_band,
            )
        )
    out.extend(check_sotp_gap(vm, require_if_both=require))
    if policy.y1:
        out.extend(check_same_period_box_floor(session, vm))
    return out

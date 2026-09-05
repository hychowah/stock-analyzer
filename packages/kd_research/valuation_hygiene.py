"""Valuation hygiene gates that are not Street identity.

Conservatism dials, Y1 stacking pair, SOTP/DCF gap, same-period box floor.
check_street_bind still invokes these so --full / 2_parallel complete keep one
row-set; the law lives here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.kd_research.check_core import load_json
from packages.kd_research.street_y1 import Y1_BAND

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


def check_y1_stacking_pair(vm: dict[str, Any], abs_delta: float) -> list[tuple[str, str, str]]:
    """FAIL volume_vs_guide ∧ sbc_in_fcff in base while Y1 is outside the Street 5% band."""
    dials = vm.get("conservatism_dials")
    if not isinstance(dials, list):
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
        and abs_delta > Y1_BAND
    ):
        return [
            (
                "FAIL",
                "conservatism_dials stacking_pair",
                "volume_vs_guide and sbc_in_fcff both applies_in=base while Y1 is "
                "outside the Street 5% band",
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

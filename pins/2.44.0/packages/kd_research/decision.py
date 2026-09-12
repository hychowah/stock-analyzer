"""Wave 2 decision-object gates (harness >= 2.10.0).

Duration action including pass. initiate illegal on a decision-useless cone.
Technical may emit pass. Legacy / missing version SKIPPED.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from packages.kd_research.check_core import load_json, session_since
from packages.kd_research.stress_apply import (
    haircut_from_values,
    restates_bear_numeric,
    session_is_stress_book_runtime,
)

WAVE2_SINCE = (2, 10, 0)
WAVE6_SINCE = (2, 14, 0)
WAVE8_SINCE = (2, 16, 0)
STRESS_BIND_SINCE = (2, 29, 0)
REPORT_ENGLISH_SINCE = (2, 43, 0)
MATERIAL_HAIRCUT = 0.25
MATERIAL_PROB = 0.15
# Expected-loss → size_cap (one schedule, one hard floor). EL = p × haircut.
EL_FULL = 0.04
EL_HALF = 0.08
EL_STUB = 0.12
SIZE_CAP_FULL = 1.0
SIZE_CAP_HALF = 0.50
SIZE_CAP_STUB = 0.25
SIZE_CAP_ZERO = 0.0
STRESS_CARD_HEADING = "## Unstressed vs stressed"
DURATION_ACTIONS = frozenset(
    {"initiate", "add", "hold", "trim", "sell", "short", "pass", "too_hard"}
)
DURATION_LABELS: dict[str, str] = {
    "pass": "Do not initiate",
    "too_hard": "Too hard",
    "initiate": "Initiate",
    "add": "Add",
    "hold": "Hold",
    "trim": "Trim",
    "sell": "Sell",
    "short": "Short",
}
CHEAP_CLAIM_LABELS: dict[str, str] = {
    "franchise_mos": "Franchise MoS",
    "equity_near_book": "Equity near book",
    "residual_option": "Residual option",
    "not_cheap": "Not cheap",
}
INITIATE_BLOCKED_ON_WIDE = frozenset({"initiate", "add"})
PASS_DURATION = frozenset({"pass", "too_hard", "sell", "short"})
ZERO_CAP_DURATION = frozenset({"pass", "too_hard", "sell", "short"})
TECH_SIDES = frozenset({"long", "short", "pass"})
SCENARIO_PROB_KEYS = ("bear", "base", "bull")
MIN_STRESS_RAW = 5
MIN_STRESS_SCENARIOS = 5


def session_is_wave2_runtime(session: Path) -> bool:
    return session_since(session, WAVE2_SINCE)


def session_is_wave8_runtime(session: Path) -> bool:
    return session_since(session, WAVE8_SINCE)


def session_is_wave6_runtime(session: Path) -> bool:
    return session_since(session, WAVE6_SINCE)


def session_is_stress_bind_runtime(session: Path) -> bool:
    return session_since(session, STRESS_BIND_SINCE)


def session_is_report_english_runtime(session: Path) -> bool:
    return session_since(session, REPORT_ENGLISH_SINCE)


def duration_label(token: str) -> str:
    """Product English for duration.action. Empty token → empty string."""
    s = (token or "").strip()
    if not s:
        return ""
    key = s.lower()
    if key in DURATION_LABELS:
        return DURATION_LABELS[key]
    return s.replace("_", " ").replace("-", " ").title()


def cheap_claim_label(token: str) -> str:
    """Product English for cheap_claim.class. Empty token → empty string."""
    s = (token or "").strip()
    if not s:
        return ""
    key = s.lower()
    if key in CHEAP_CLAIM_LABELS:
        return CHEAP_CLAIM_LABELS[key]
    return s.replace("_", " ").replace("-", " ").title()


def _truthy_flag(data: dict[str, Any], key: str) -> bool:
    val = data.get(key)
    if isinstance(val, dict):
        val = val.get("value")
    if val is True:
        return True
    if isinstance(val, str) and val.strip().lower() in {"true", "yes", "1"}:
        return True
    return False


def check_wave6_reopen(session: Path) -> list[tuple[str, str, str]]:
    """Duration verb is final only after risk_bridge exists (Phase 2.5 done)."""
    if not session_is_wave6_runtime(session):
        return [
            (
                "SKIPPED",
                "decision_reopen",
                "legacy/slim (harness_version < 2.14.0)",
            )
        ]
    rb, rerr = load_json(session / "registry" / "risk_bridge.json")
    if rerr or not isinstance(rb, dict):
        return [
            (
                "SKIPPED",
                "decision_reopen",
                "risk_bridge.json missing (Phase 2 provisional decision is legal)",
            )
        ]
    data, err = load_json(session / "registry" / "decision.json")
    if err or not isinstance(data, dict):
        return [
            (
                "FAIL",
                "decision_reopen",
                "risk_bridge exists so decision.json must be reopened after 2.5 "
                "(reopened_after_stress=true; Agent 5 single writer, no second valuer)",
            )
        ]
    if not _truthy_flag(data, "reopened_after_stress"):
        return [
            (
                "FAIL",
                "decision_reopen",
                "reopened_after_stress must be true after Phase 2.5 "
                "(orchestrator 5b; do not spawn subagent 5 in 2_5)",
            )
        ]
    tsr, terr = load_json(session / "registry" / "tsr_validation.json")
    tsr_present = not terr and isinstance(tsr, dict)
    if tsr_present and not _truthy_flag(data, "tsr_seen"):
        return [
            (
                "FAIL",
                "decision_reopen.tsr",
                "tsr_validation.json exists so tsr_seen must be true "
                "(tsr_missing is not a substitute)",
            )
        ]
    return [
        (
            "PASS",
            "decision_reopen",
            f"reopened_after_stress tsr_seen={_truthy_flag(data, 'tsr_seen')} "
            f"tsr_present={tsr_present}",
        )
    ]


def _haircut_frac(val: Any) -> float | None:
    n = _as_float(val)
    if n is None:
        return None
    n = abs(n)
    if n > 1.0:
        return n / 100.0
    return n


def _material_scenarios(rb: dict[str, Any]) -> list[dict[str, Any]]:
    st = rb.get("stress_test") if isinstance(rb.get("stress_test"), dict) else {}
    scenarios = st.get("scenarios")
    if not isinstance(scenarios, list):
        return []
    out: list[dict[str, Any]] = []
    for sc in scenarios:
        if not isinstance(sc, dict):
            continue
        hair = _haircut_frac(sc.get("fair_value_haircut_pct"))
        prob = _as_float(sc.get("probability"))
        if hair is None or prob is None:
            continue
        if hair >= MATERIAL_HAIRCUT and prob >= MATERIAL_PROB:
            out.append(sc)
    return out


def _signed_haircut_frac(val: Any) -> float | None:
    n = _as_float(val)
    if n is None:
        return None
    if abs(n) > 1.0:
        return n / 100.0
    return n


def size_cap_for_el(el: float) -> float:
    """One EL schedule. Hard floor: EL >= 12% → size_cap 0."""
    if el >= EL_STUB:
        return SIZE_CAP_ZERO
    if el >= EL_HALF:
        return SIZE_CAP_STUB
    if el >= EL_FULL:
        return SIZE_CAP_HALF
    return SIZE_CAP_FULL


class UnappliedStressError(ValueError):
    """Merged shocks exist but Apply has not stamped applied.stressed_fv."""


def _scenario_stressed_fv(sc: dict[str, Any]) -> float | None:
    """applied.stressed_fv only. Do not reconstruct from a guessed haircut."""
    applied = sc.get("applied") if isinstance(sc.get("applied"), dict) else {}
    return _as_float(applied.get("stressed_fv"))


def _scenario_restates_bear(
    sc: dict[str, Any],
    base: float | None,
    bear: float | None,
) -> bool:
    fv = _scenario_stressed_fv(sc)
    if fv is None or base is None or base <= 0 or bear is None:
        return False
    return restates_bear_numeric(fv, base, bear)


def _liquidity_fails(sc: dict[str, Any]) -> bool:
    lp = sc.get("liquidity_path")
    if not isinstance(lp, dict):
        return False
    if lp.get("applies") is False:
        return False
    return lp.get("survival_12m") is False


def _narrative_only(sc: dict[str, Any]) -> bool:
    direction = str(sc.get("direction") or "").strip().lower()
    va = sc.get("valuation_adjustment")
    if isinstance(va, dict):
        direction = str(va.get("direction") or direction).strip().lower()
    return direction == "narrative_only"


def compute_stress_bind(rb: dict[str, Any], vm: dict[str, Any]) -> dict[str, Any]:
    """Book vs map. Map stays Agent 5 base FV. Book is this object.

    expected_loss_pct = p × (1 − applied.stressed_fv/base) of the binding
    independent scenario (max EL among restates_bear=false; do not sum).
    size_cap is the max duration-book fraction. material is derived
    (size_cap < 1). Refuses an unapplied bridge (no full-book default).
    """
    fv = vm.get("fair_value") if isinstance(vm.get("fair_value"), dict) else {}
    base = _as_float(fv.get("base"))
    bear = _as_float(fv.get("bear"))
    st = rb.get("stress_test") if isinstance(rb.get("stress_test"), dict) else {}
    scenarios = st.get("scenarios") if isinstance(st, dict) else None
    if not isinstance(scenarios, list) or not scenarios or base is None or base <= 0:
        raise UnappliedStressError(
            "merged scenarios with applied.stressed_fv required "
            "(run stress_apply after merge)"
        )
    rows = [sc for sc in scenarios if isinstance(sc, dict)]
    missing = [
        str(sc.get("name") or sc.get("scenario_id") or "unnamed")
        for sc in rows
        if _scenario_stressed_fv(sc) is None
    ]
    if missing:
        raise UnappliedStressError(
            "unapplied scenarios "
            f"{missing[:4]}: run python -m packages.kd_research.stress_apply "
            "after merge (no size_cap=1 default)"
        )
    empty = {
        "material": False,
        "binding_scenario": None,
        "haircut_pct": 0.0,
        "probability": 0.0,
        "stressed_fv": base,
        "expected_loss_pct": 0.0,
        "size_cap": SIZE_CAP_FULL,
    }
    best: tuple[float, dict[str, Any], float, float, float] | None = None
    liq_fail = False
    for sc in rows:
        if _liquidity_fails(sc):
            liq_fail = True
        if _scenario_restates_bear(sc, base, bear):
            continue
        sfv = _scenario_stressed_fv(sc)
        prob = _as_float(sc.get("probability"))
        if sfv is None or prob is None:
            continue
        hair = haircut_from_values(base, sfv)
        el = max(0.0, hair) * prob
        if best is None or el > best[0]:
            best = (el, sc, hair, prob, sfv)
    if best is None:
        out = dict(empty)
        if liq_fail:
            out["size_cap"] = SIZE_CAP_ZERO
            out["material"] = True
        return out
    el, sc, hair, prob, sfv = best
    cap = size_cap_for_el(el)
    if liq_fail:
        cap = SIZE_CAP_ZERO
    return {
        "material": cap < 1.0,
        "binding_scenario": sc.get("name") or sc.get("scenario_id"),
        "haircut_pct": hair,
        "probability": prob,
        "stressed_fv": sfv,
        "expected_loss_pct": el,
        "size_cap": cap,
    }


def _bind_close(got: float | None, want: float, *, abs_tol: float, rel: float) -> bool:
    if got is None:
        return False
    return abs(got - want) <= max(abs_tol, abs(want) * rel)


def check_stress_bind(session: Path) -> list[tuple[str, str, str]]:
    """Material 2.5 haircuts bind the book. No DCF rewrite. No self-grade override."""
    if not session_is_stress_bind_runtime(session):
        return [
            (
                "SKIPPED",
                "stress_bind",
                "legacy/slim (harness_version < 2.29.0)",
            )
        ]
    if session_is_stress_book_runtime(session):
        return _check_stress_book_bind(session)
    return _check_stress_cliff_bind(session)


def _check_stress_book_bind(session: Path) -> list[tuple[str, str, str]]:
    rb, rerr = load_json(session / "registry" / "risk_bridge.json")
    if rerr or not isinstance(rb, dict):
        return [("SKIPPED", "stress_bind", "risk_bridge.json missing")]
    vm, verr = load_json(session / "data" / "valuation_model.json")
    if verr or not isinstance(vm, dict):
        return [("FAIL", "stress_bind", "valuation_model.json required for book bind")]
    data, err = load_json(session / "registry" / "decision.json")
    if err or not isinstance(data, dict):
        return [
            (
                "FAIL",
                "stress_bind",
                "decision.json required after Phase 2.5 on harness ≥ 2.29.0",
            )
        ]
    bind = data.get("stress_bind")
    if not isinstance(bind, dict):
        return [
            (
                "FAIL",
                "stress_bind",
                "decision.stress_bind required when risk_bridge exists "
                "(run compute_stress_bind; do not rewrite valuation_model.json)",
            )
        ]
    try:
        want = compute_stress_bind(rb, vm)
    except UnappliedStressError as exc:
        return [("FAIL", "stress_bind.unapplied", str(exc))]
    flag = bind.get("material")
    if not isinstance(flag, bool):
        return [
            (
                "FAIL",
                "stress_bind.material",
                "stress_bind.material must be a boolean (derived: size_cap < 1)",
            )
        ]
    if flag is not want["material"]:
        return [
            (
                "FAIL",
                "stress_bind.material",
                f"material must be {want['material']} (size_cap={want['size_cap']})",
            )
        ]
    for key, abs_tol, rel in (
        ("size_cap", 0.001, 0.0),
        ("expected_loss_pct", 0.005, 0.02),
        ("haircut_pct", 0.02, 0.02),
        ("probability", 0.01, 0.0),
        ("stressed_fv", 0.05, 0.01),
    ):
        if key == "haircut_pct":
            got = _signed_haircut_frac(bind.get(key))
        elif key == "expected_loss_pct":
            got = _signed_haircut_frac(bind.get(key))
            if got is not None:
                got = abs(got)
        else:
            got = _as_float(bind.get(key))
        want_v = want[key]
        if want_v is None:
            continue
        if not _bind_close(got, float(want_v), abs_tol=abs_tol, rel=rel):
            return [
                (
                    "FAIL",
                    f"stress_bind.{key}",
                    f"{key} {got} does not match compute_stress_bind {want_v}",
                )
            ]
    want_name = want.get("binding_scenario")
    got_name = bind.get("binding_scenario")
    if want_name and str(got_name or "").strip() != str(want_name).strip():
        return [
            (
                "FAIL",
                "stress_bind.binding",
                f"binding_scenario must be {want_name!r} (max independent EL; "
                "restates_bear cannot bind)",
            )
        ]
    st = rb.get("stress_test") if isinstance(rb.get("stress_test"), dict) else {}
    scenarios = st.get("scenarios") if isinstance(st, dict) else []
    fv = vm.get("fair_value") if isinstance(vm.get("fair_value"), dict) else {}
    base = _as_float(fv.get("base"))
    bear = _as_float(fv.get("bear"))
    if isinstance(scenarios, list):
        for sc in scenarios:
            if not isinstance(sc, dict):
                continue
            if _scenario_restates_bear(sc, base, bear):
                continue
            if not _narrative_only(sc):
                continue
            sfv = _scenario_stressed_fv(sc)
            prob = _as_float(sc.get("probability"))
            if sfv is None or prob is None or base is None or base <= 0:
                continue
            hair = haircut_from_values(base, sfv)
            if size_cap_for_el(max(0.0, hair) * prob) < 1.0:
                return [
                    (
                        "FAIL",
                        "stress_bind.narrative_only",
                        f"binding-class scenario {sc.get('name')!r} cannot be narrative_only",
                    )
                ]
    action = _duration_action(data)
    cap = float(want["size_cap"])
    if cap <= 0 and action not in ZERO_CAP_DURATION:
        return [
            (
                "FAIL",
                "stress_bind.size_cap",
                "size_cap=0 forbids initiate/add/hold; use pass/too_hard/sell/short "
                "— no override hatch",
            )
        ]
    return [
        (
            "PASS",
            "stress_bind",
            f"size_cap={cap} el={want['expected_loss_pct']:.4f} action={action}",
        )
    ]


def _check_stress_cliff_bind(session: Path) -> list[tuple[str, str, str]]:
    rb, rerr = load_json(session / "registry" / "risk_bridge.json")
    if rerr or not isinstance(rb, dict):
        return [("SKIPPED", "stress_bind", "risk_bridge.json missing")]
    data, err = load_json(session / "registry" / "decision.json")
    if err or not isinstance(data, dict):
        return [
            (
                "FAIL",
                "stress_bind",
                "decision.json required after Phase 2.5 on harness ≥ 2.29.0",
            )
        ]
    bind = data.get("stress_bind")
    if not isinstance(bind, dict):
        return [
            (
                "FAIL",
                "stress_bind",
                "decision.stress_bind required when risk_bridge exists "
                "(material boolean + binding scenario)",
            )
        ]
    flag = bind.get("material")
    if not isinstance(flag, bool):
        return [
            (
                "FAIL",
                "stress_bind.material",
                "stress_bind.material must be a boolean",
            )
        ]
    material = _material_scenarios(rb)
    for sc in material:
        if _narrative_only(sc):
            return [
                (
                    "FAIL",
                    "stress_bind.narrative_only",
                    f"material scenario {sc.get('name')!r} cannot be narrative_only",
                )
            ]
    risks = rb.get("risks")
    if isinstance(risks, list):
        for risk in risks:
            if not isinstance(risk, dict):
                continue
            va = risk.get("valuation_adjustment")
            if not isinstance(va, dict):
                continue
            if str(va.get("direction") or "").strip().lower() != "narrative_only":
                continue
            prob = _as_float(risk.get("probability"))
            mag = _haircut_frac(va.get("magnitude") or va.get("fair_value_haircut_pct"))
            if (
                prob is not None
                and prob >= MATERIAL_PROB
                and mag is not None
                and mag >= MATERIAL_HAIRCUT
            ):
                return [
                    (
                        "FAIL",
                        "stress_bind.narrative_only",
                        "material risk cannot use valuation_adjustment.direction=narrative_only",
                    )
                ]
    if material:
        if not flag:
            return [
                (
                    "FAIL",
                    "stress_bind.material",
                    "material stress scenarios exist so stress_bind.material must be true",
                )
            ]
        action = _duration_action(data)
        if action in INITIATE_BLOCKED_ON_WIDE:
            return [
                (
                    "FAIL",
                    "stress_bind.initiate",
                    "material stress (haircut≥25% and p≥0.15) forbids initiate/add; "
                    "use pass/too_hard/hold/trim/sell/short — no override hatch",
                )
            ]
        return [
            (
                "PASS",
                "stress_bind",
                f"material n={len(material)} action={action}",
            )
        ]
    if flag:
        return [
            (
                "FAIL",
                "stress_bind.material",
                "stress_bind.material is true but no scenario meets haircut≥25% and p≥0.15",
            )
        ]
    return [("PASS", "stress_bind", "no material stress")]


def _as_float(val: Any) -> float | None:
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, dict):
        return _as_float(val.get("value"))
    return None


def _cone_blocks_initiate(fv: dict[str, Any]) -> bool:
    du = fv.get("decision_usefulness")
    if isinstance(du, dict):
        du = du.get("value") or du.get("class")
    if isinstance(du, str) and du.strip().lower() == "low":
        return True
    base = _as_float(fv.get("base"))
    bear = _as_float(fv.get("bear"))
    bull = _as_float(fv.get("bull"))
    if base is None or base <= 0 or bear is None or bull is None:
        return False
    return (bull - bear) / base > 1.0 or bear < 0.4 * base


def _duration_action(decision: dict[str, Any]) -> str:
    dur = decision.get("duration")
    if isinstance(dur, dict):
        return str(dur.get("action") or "").strip().lower()
    return str(decision.get("action") or "").strip().lower()


def _tech_side(technical: dict[str, Any]) -> str:
    side = technical.get("side")
    if isinstance(side, dict):
        side = side.get("value")
    if isinstance(side, str) and side.strip().lower() in TECH_SIDES:
        return side.strip().lower()
    levels = technical.get("levels") if isinstance(technical.get("levels"), dict) else {}
    setup = levels.get("setup") or levels.get("side")
    if isinstance(setup, str) and setup.strip().lower() in TECH_SIDES:
        return setup.strip().lower()
    return ""


def check_decision_packet(session: Path) -> list[tuple[str, str, str]]:
    vm, vm_err = load_json(session / "data" / "valuation_model.json")
    if vm_err or not isinstance(vm, dict):
        return [("SKIPPED", "decision_packet", "valuation_model.json missing")]
    data, err = load_json(session / "registry" / "decision.json")
    if err == "missing" or not isinstance(data, dict):
        return [
            (
                "FAIL",
                "decision_packet",
                "new runtime requires registry/decision.json with duration.action "
                "including pass/too_hard (Agent 5 single writer)",
            )
        ]
    if err:
        return [("FAIL", "decision_packet", f"decision.json {err}")]
    action = _duration_action(data)
    if action not in DURATION_ACTIONS:
        return [
            (
                "FAIL",
                "decision_packet.action",
                f"duration.action must be one of {sorted(DURATION_ACTIONS)}; got {action!r}",
            )
        ]
    dur = data.get("duration") if isinstance(data.get("duration"), dict) else {}
    rationale = str(dur.get("rationale") or data.get("rationale") or "")
    if len(rationale.strip()) < 20:
        return [
            (
                "FAIL",
                "decision_packet.rationale",
                "duration.rationale must be ≥20 chars",
            )
        ]
    fv = vm.get("fair_value") if isinstance(vm.get("fair_value"), dict) else {}
    if action in INITIATE_BLOCKED_ON_WIDE and _cone_blocks_initiate(fv):
        return [
            (
                "FAIL",
                "decision_packet.initiate",
                "initiate/add illegal when decision_usefulness=low or "
                "(bull−bear)/base > 100% or bear < 0.4×base; use pass/too_hard/hold/trim/sell/short",
            )
        ]
    return [("PASS", "decision_packet", f"duration.action={action}")]


def check_technical_pass_allowed(session: Path) -> list[tuple[str, str, str]]:
    tech, err = load_json(session / "registry" / "technical.json")
    if err or not isinstance(tech, dict):
        return [("SKIPPED", "technical_pass", "technical.json missing")]
    side = _tech_side(tech)
    levels = tech.get("levels") if isinstance(tech.get("levels"), dict) else {}
    entry = levels.get("entry")
    stop = levels.get("stop_loss") or levels.get("stop")
    entry_val = _as_float(entry if not isinstance(entry, dict) else entry.get("value"))
    stop_val = _as_float(stop if not isinstance(stop, dict) else stop.get("value"))
    if side == "pass":
        return [("PASS", "technical_pass", "side=pass; entry/stop not required")]
    effective = side if side in ("long", "short") else "long"
    if entry_val is None or stop_val is None:
        return [
            (
                "FAIL",
                "technical_pass",
                f"side={effective} requires entry and stop_loss values "
                "(omit both only when side=pass)",
            )
        ]
    if effective == "long" and stop_val >= entry_val:
        return [
            (
                "FAIL",
                "technical_pass",
                "long stop_loss must be below entry",
            )
        ]
    if effective == "short" and stop_val <= entry_val:
        return [
            (
                "FAIL",
                "technical_pass",
                "short stop_loss must be above entry",
            )
        ]
    return [("PASS", "technical_pass", f"side={effective} entry/stop coherent")]


def check_duration_vs_ta_long(session: Path) -> list[tuple[str, str, str]]:
    dec, err = load_json(session / "registry" / "decision.json")
    if err or not isinstance(dec, dict):
        return [("SKIPPED", "duration_vs_ta", "decision.json missing")]
    tech, terr = load_json(session / "registry" / "technical.json")
    if terr or not isinstance(tech, dict):
        return [("SKIPPED", "duration_vs_ta", "technical.json missing")]
    action = _duration_action(dec)
    side = _tech_side(tech)
    # Isolated specialists may disagree. Duration pass + TA long is legal (C2 demoted).
    return [
        (
            "PASS",
            "duration_vs_ta",
            f"duration={action}; TA side={side or 'unset'} "
            "(conflict is README quoting duration.action, not a JSON veto)",
        )
    ]


def _readme_action_index(
    text: str,
    action: str,
    *,
    accept_english: bool = False,
) -> int | None:
    """First match of duration.action; skip 'audit pass'. Optional product English."""
    if not action:
        return None
    needles = [action.strip().lower()]
    if accept_english:
        label = duration_label(action).lower()
        if label and label not in needles:
            needles.append(label)
    for needle in needles:
        for match in re.finditer(r"\b" + re.escape(needle) + r"\b", text):
            prefix = text[max(0, match.start() - 12) : match.start()]
            if needle == "pass" and prefix.rstrip().endswith("audit"):
                continue
            return match.start()
    return None


def _first_bid_index(text: str) -> int | None:
    hits = []
    for marker in ("fair value vs price", "margin of safety"):
        i = text.find(marker)
        if i >= 0:
            hits.append(i)
    return min(hits) if hits else None


def check_readme_quotes_decision(session: Path) -> list[tuple[str, str, str]]:
    dec, err = load_json(session / "registry" / "decision.json")
    if err or not isinstance(dec, dict):
        return [("SKIPPED", "readme_quotes_decision", "decision.json missing")]
    action = _duration_action(dec)
    reports = session / "reports"
    if not reports.is_dir():
        return [("SKIPPED", "readme_quotes_decision", "reports/ missing")]
    matches = list(reports.glob("00_*_README.md"))
    if not matches:
        return [("SKIPPED", "readme_quotes_decision", "README missing")]
    text = matches[0].read_text(encoding="utf-8", errors="replace").lower()
    wave8 = session_is_wave8_runtime(session)
    accept_english = session_is_report_english_runtime(session)
    idx = _readme_action_index(text, action, accept_english=accept_english)
    if idx is None:
        quoted = duration_label(action) if accept_english else action
        msg = (
            f"README does not quote duration.action={action}"
            + (f" (or {quoted!r})" if accept_english and quoted != action else "")
            + " (Agent 11 must not invent a second verdict)"
        )
        if wave8:
            return [("FAIL", "readme_quotes_decision", msg)]
        return [("WARN", "readme_quotes_decision", msg)]
    if wave8:
        bid = _first_bid_index(text)
        if bid is not None and idx > bid:
            return [
                (
                    "FAIL",
                    "readme_cio_lead",
                    "duration.action must appear before fair value vs price / "
                    "margin of safety (CIO cover, not a bid poster)",
                )
            ]
    atr_shares = "atr" in text and "shares" in text
    if atr_shares and "position size" in text:
        if session_is_stress_book_runtime(session):
            return [
                (
                    "FAIL",
                    "readme_quotes_decision",
                    "README must not present ATR share-count as book size "
                    "(quote decision.stress_bind.size_cap)",
                )
            ]
        return [
            (
                "WARN",
                "readme_quotes_decision",
                "README quotes the decision action but still leads ATR share-count as a size",
            )
        ]
    return [("PASS", "readme_quotes_decision", f"README quotes duration.action={action}")]


def _stress_card_section(text: str) -> str | None:
    lower = text.lower()
    needle = STRESS_CARD_HEADING.lower()
    i = lower.find(needle)
    if i < 0:
        return None
    rest = text[i:]
    nxt = re.search(r"\n## ", rest[3:])
    return rest if nxt is None else rest[: nxt.start() + 3]


def _fold_card(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def format_stress_card(bind: dict[str, Any], base: float) -> str:
    """Canonical Unstressed vs stressed body (no heading).

    Expected loss is the one book number — do not print a second formula.
    """
    stressed = bind.get("stressed_fv")
    el = bind.get("expected_loss_pct") or 0.0
    cap = bind.get("size_cap")
    name = bind.get("binding_scenario") or "none"
    stressed_s = f"{float(stressed):.2f}" if stressed is not None else "unknown"
    cap_s = f"{float(cap):.2f}" if cap is not None else "unknown"
    return (
        f"Unstressed {float(base):.2f}. "
        f"Stressed {stressed_s} ({name}). "
        f"Expected loss {float(el) * 100:.1f} percent. "
        f"Size cap {cap_s}."
    )


def check_stress_report_card(session: Path) -> list[tuple[str, str, str]]:
    """README and fundamental must copy format_stress_card under the heading."""
    if not session_is_stress_book_runtime(session):
        return [
            (
                "SKIPPED",
                "stress_report_card",
                "legacy/slim (harness_version < 2.44.0)",
            )
        ]
    reports = session / "reports"
    if not reports.is_dir():
        return [("SKIPPED", "stress_report_card", "reports/ missing")]
    rb, rerr = load_json(session / "registry" / "risk_bridge.json")
    if rerr or not isinstance(rb, dict):
        return [("SKIPPED", "stress_report_card", "risk_bridge.json missing")]
    vm, verr = load_json(session / "data" / "valuation_model.json")
    if verr or not isinstance(vm, dict):
        return [("FAIL", "stress_report_card", "valuation_model.json required")]
    dec, derr = load_json(session / "registry" / "decision.json")
    if derr or not isinstance(dec, dict):
        return [("FAIL", "stress_report_card", "decision.json required")]
    bind = dec.get("stress_bind")
    if not isinstance(bind, dict):
        return [("FAIL", "stress_report_card", "decision.stress_bind required")]
    want = compute_stress_bind(rb, vm)
    fv = vm.get("fair_value") if isinstance(vm.get("fair_value"), dict) else {}
    base = _as_float(fv.get("base"))
    if base is None:
        return [("FAIL", "stress_report_card", "fair_value.base missing")]
    body = format_stress_card(want, base)
    folded_body = _fold_card(body)
    files = [
        ("readme", list(reports.glob("00_*_README.md"))),
        ("fundamental", list(reports.glob("01_*_fundamental.md"))),
    ]
    out: list[tuple[str, str, str]] = []
    for label, matches in files:
        if not matches:
            out.append(("FAIL", f"stress_report_card.{label}", f"{label} report missing"))
            continue
        text = matches[0].read_text(encoding="utf-8", errors="replace")
        section = _stress_card_section(text)
        if section is None:
            out.append(
                (
                    "FAIL",
                    f"stress_report_card.{label}",
                    f"{label} must have heading exactly {STRESS_CARD_HEADING!r}",
                )
            )
            continue
        if folded_body not in _fold_card(section):
            out.append(
                (
                    "FAIL",
                    f"stress_report_card.{label}",
                    f"{label} must copy format_stress_card (do not recompute): {body}",
                )
            )
            continue
        out.append(("PASS", f"stress_report_card.{label}", f"{label} card matches bind"))
    if not out:
        return [("SKIPPED", "stress_report_card", "no report files")]
    return out


def extract_kill_triggers(session: Path) -> list[str]:
    rb, err = load_json(session / "registry" / "risk_bridge.json")
    if err or not isinstance(rb, dict):
        return []
    out: list[str] = []
    seen: set[str] = set()
    risks = rb.get("risks")
    if isinstance(risks, list):
        for item in risks:
            if not isinstance(item, dict):
                continue
            trig = item.get("monitoring_trigger")
            if isinstance(trig, str) and trig.strip() and trig.strip() not in seen:
                seen.add(trig.strip())
                out.append(trig.strip())
            if len(out) >= 8:
                break
    return out


def extract_decision_action(session: Path) -> str | None:
    dec, err = load_json(session / "registry" / "decision.json")
    if err or not isinstance(dec, dict):
        return None
    action = _duration_action(dec)
    return action or None


def check_wave2_decision(
    session: Path,
    *,
    include_reports: bool = True,
) -> list[tuple[str, str, str]]:
    if not session_is_wave2_runtime(session):
        return [
            (
                "SKIPPED",
                "wave2_decision",
                "legacy/slim (harness_version < 2.10.0)",
            )
        ]
    out: list[tuple[str, str, str]] = []
    out.extend(check_decision_packet(session))
    out.extend(check_technical_pass_allowed(session))
    out.extend(check_duration_vs_ta_long(session))
    if include_reports:
        out.extend(check_readme_quotes_decision(session))
    return out


def check_wave2_phase2_complete(session: Path) -> list[tuple[str, str, str]]:
    """2_parallel complete: packet + technical pass (no README)."""
    if not session_is_wave2_runtime(session):
        return []
    out: list[tuple[str, str, str]] = []
    out.extend(check_decision_packet(session))
    out.extend(check_technical_pass_allowed(session))
    return out


def check_wave2_phase4_complete(session: Path) -> list[tuple[str, str, str]]:
    """4_parallel complete: packet + README quotes."""
    if not session_is_wave2_runtime(session):
        return []
    out: list[tuple[str, str, str]] = []
    out.extend(check_decision_packet(session))
    out.extend(check_readme_quotes_decision(session))
    return out


def check_risk_bridge(session: Path) -> list[tuple[str, str, str]]:
    p = session / "registry/risk_bridge.json"
    if not p.exists():
        return [("SKIPPED", "risk_bridge content checks", "file missing")]
    data, err = load_json(p)
    if err or not isinstance(data, dict):
        return [("SKIPPED", "risk_bridge content checks", "unparseable")]
    out: list[tuple[str, str, str]] = []
    probs = data.get("scenario_probabilities")
    for status, check, detail in check_scenario_probability_keys(
        probs, extra_key_severity="WARN"
    ):
        name = {
            "scenario_probabilities_sum": "scenario_probabilities sum",
            "scenario_probabilities_keys": "scenario_probabilities keys",
            "scenario_probabilities_values": "scenario_probabilities values",
            "scenario_probabilities": "scenario_probabilities sum",
        }.get(check, check)
        out.append((status, name, detail))
    scenarios = (data.get("stress_test") or {}).get("scenarios") or []
    if len(scenarios) >= 5:
        out.append(("PASS", "stress scenario count", f"{len(scenarios)} >= 5"))
    else:
        out.append(
            (
                "FAIL",
                "stress scenario count",
                f"{len(scenarios)} < 5 (need 4 sector + 1 macro)",
            )
        )
    return out


def extract_scenario_prob_mass(probs: dict[str, Any]) -> tuple[float | None, list[str]]:
    """Sum bear/base/bull only (nested {value} allowed). Return (total, issues)."""
    issues: list[str] = []
    total = 0.0
    found = 0
    for k in SCENARIO_PROB_KEYS:
        if k not in probs:
            continue
        v = probs[k]
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            total += float(v)
            found += 1
        elif isinstance(v, dict) and "value" in v and isinstance(v["value"], (int, float)):
            total += float(v["value"])
            found += 1
        else:
            issues.append(f"{k} is not a number (or {{value}} number)")
    if found == 0:
        return None, issues or ["no bear/base/bull numeric masses"]
    return total, issues


def check_scenario_probability_keys(
    probs: object,
    *,
    extra_key_severity: str = "WARN",
) -> list[tuple[str, str, str]]:
    """Structural checks for risk_bridge scenario_probabilities."""
    out: list[tuple[str, str, str]] = []
    if not isinstance(probs, dict) or not probs:
        out.append(("FAIL", "scenario_probabilities", "missing or empty"))
        return out

    total, issues = extract_scenario_prob_mass(probs)
    if issues and total is None:
        out.append(("FAIL", "scenario_probabilities_sum", "; ".join(issues)))
    elif issues:
        out.append(("FAIL", "scenario_probabilities_values", "; ".join(issues)))
    elif total is None:
        out.append(("FAIL", "scenario_probabilities_sum", "missing bear/base/bull"))
    elif abs(total - 1.0) <= 0.01:
        out.append(("PASS", "scenario_probabilities_sum", f"{total:.3f} (bear/base/bull only)"))
    else:
        out.append(
            (
                "FAIL",
                "scenario_probabilities_sum",
                f"{total:.3f} != 1.0 +/- 0.01 — sum only bear/base/bull; "
                "put notes in scenario_probabilities_rationale sibling, not inside the map",
            )
        )

    extra = [k for k in probs if k not in SCENARIO_PROB_KEYS]
    if extra:
        sev = extra_key_severity if extra_key_severity in ("WARN", "FAIL", "PASS") else "WARN"
        out.append(
            (
                sev,
                "scenario_probabilities_keys",
                f"extra keys {extra!r} — map may contain ONLY bear/base/bull "
                f"(move rationale/_sum/_note to a sibling key)",
            )
        )
    else:
        out.append(("PASS", "scenario_probabilities_keys", "bear/base/bull only"))
    return out


def check_stress_coverage(session: Path) -> list[tuple[str, str, str]]:
    """Merge/coverage checks for Phase 2.5."""
    out: list[tuple[str, str, str]] = []
    raw = (
        list((session / "registry" / "raw").glob("stress_*.json"))
        if (session / "registry" / "raw").is_dir()
        else []
    )
    if len(raw) < MIN_STRESS_RAW:
        out.append(("FAIL", "stress_raw_count", f"{len(raw)} < {MIN_STRESS_RAW}"))
    else:
        out.append(("PASS", "stress_raw_count", f"{len(raw)} >= {MIN_STRESS_RAW}"))

    rb_path = session / "registry" / "risk_bridge.json"
    data, err = load_json(rb_path)
    if err:
        out.append(("FAIL", "risk_bridge", err))
        return out
    assert data is not None
    st = data.get("stress_test") if isinstance(data, dict) else None
    scenarios = st.get("scenarios") if isinstance(st, dict) else None
    n = len(scenarios) if isinstance(scenarios, list) else 0
    if n < MIN_STRESS_SCENARIOS:
        out.append(("FAIL", "stress_scenarios", f"{n} < {MIN_STRESS_SCENARIOS}"))
    else:
        out.append(("PASS", "stress_scenarios", f"{n} >= {MIN_STRESS_SCENARIOS}"))

    probs = data.get("scenario_probabilities") if isinstance(data, dict) else None
    out.extend(check_scenario_probability_keys(probs, extra_key_severity="WARN"))
    return out


def check_latest_quarter_risk_mapping(session: Path) -> list[tuple[str, str, str]]:
    """Soft structural: latest_quarter risks should appear in risk_bridge mapping fields if both exist."""
    out: list[tuple[str, str, str]] = []
    lq, e1 = load_json(session / "registry" / "latest_quarter.json")
    rb, e2 = load_json(session / "registry" / "risk_bridge.json")
    if e1 or e2:
        out.append(("SKIPPED", "lq_risk_mapping", "latest_quarter or risk_bridge missing"))
        return out
    assert isinstance(lq, dict) and isinstance(rb, dict)
    risks = lq.get("risks")
    if not isinstance(risks, list) or len(risks) == 0:
        out.append(("PASS", "lq_risk_mapping", "no latest_quarter.risks[]"))
        return out
    mapping = rb.get("latest_quarter_risk_mapping_summary")
    dropped = rb.get("dropped_risks")
    rb_risks = rb.get("risks")
    if mapping or (isinstance(rb_risks, list) and len(rb_risks) >= 1) or (isinstance(dropped, list)):
        out.append(
            (
                "PASS",
                "lq_risk_mapping",
                f"lq risks={len(risks)}; risk_bridge has risks/dropped/mapping fields",
            )
        )
    else:
        out.append(
            (
                "FAIL",
                "lq_risk_mapping",
                "latest_quarter.risks[] present but risk_bridge has no risks/dropped_risks/mapping",
            )
        )
    return out

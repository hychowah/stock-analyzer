"""Wave 2 decision-object gates (harness >= 2.10.0).

Duration action including pass. initiate illegal on a decision-useless cone.
Technical may emit pass. Legacy / missing version SKIPPED.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.kd_research.annuals import load_run_manifest_version, parse_semver
from scripts.kd_research.gates import load_json

WAVE2_SINCE = (2, 10, 0)
DURATION_ACTIONS = frozenset(
    {"initiate", "add", "hold", "trim", "sell", "short", "pass", "too_hard"}
)
INITIATE_BLOCKED_ON_WIDE = frozenset({"initiate", "add"})
PASS_DURATION = frozenset({"pass", "too_hard", "sell", "short"})
TECH_SIDES = frozenset({"long", "short", "pass"})


def session_is_wave2_runtime(session: Path) -> bool:
    parsed = parse_semver(load_run_manifest_version(session))
    if parsed is None:
        return False
    return parsed >= WAVE2_SINCE


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
    if action and action in text:
        atr_shares = ("atr" in text and "shares" in text)
        if atr_shares and "position size" in text:
            return [
                (
                    "WARN",
                    "readme_quotes_decision",
                    "README quotes the decision action but still leads ATR share-count as a size",
                )
            ]
        return [("PASS", "readme_quotes_decision", f"README quotes duration.action={action}")]
    return [
        (
            "WARN",
            "readme_quotes_decision",
            f"README does not quote duration.action={action} (Agent 11 must not invent a second verdict)",
        )
    ]


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

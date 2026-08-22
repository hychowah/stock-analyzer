"""Wave 3 epistemology gates (harness >= 2.11.0).

Unresolved destock cannot be silent duration-in-base. Related-party
concentration cannot hide at intensity=low. Changelog of earning-power
facts must not copy prior FV/MoS/WACC (F14/F16).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from scripts.kd_research.annuals import load_run_manifest_version, parse_semver
from scripts.kd_research.gates import load_json

WAVE3_SINCE = (2, 11, 0)
FORBIDDEN_CHANGELOG_KEYS = frozenset(
    {
        "fair_value",
        "fv_base",
        "fv_bear",
        "fv_bull",
        "margin_of_safety",
        "margin_of_safety_pct",
        "wacc",
        "scenario_probabilities",
        "prior_fair_value",
        "prior_mos",
        "prior_wacc",
    }
)
TV_RESPONSE_OK = frozenset(
    {"extend_years", "switch_primary", "residual_income", "lower_g", "extend"}
)


def session_is_wave3_runtime(session: Path) -> bool:
    parsed = parse_semver(load_run_manifest_version(session))
    if parsed is None:
        return False
    return parsed >= WAVE3_SINCE


def _as_float(val: Any) -> float | None:
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, dict):
        return _as_float(val.get("value"))
    return None


def _blob(obj: Any) -> str:
    return str(obj).lower()


def _unresolved_destock(brief: dict[str, Any]) -> bool:
    conflicts = brief.get("conflicts")
    if not isinstance(conflicts, list):
        return False
    for item in conflicts:
        if not isinstance(item, dict):
            continue
        if str(item.get("status") or "").lower() != "unresolved":
            continue
        text = _blob(item.get("id")) + " " + _blob(item.get("claim_a")) + " " + _blob(item.get("claim_b"))
        if "destock" in text and ("flatten" in text or "duration" in text or "demand" in text):
            return True
        if "destock" in text and "flatten" in text:
            return True
        if "destock" in text:
            return True
    return False


def _destock_in_base(vm: dict[str, Any]) -> bool:
    hooks = vm.get("operating_path_hooks")
    if isinstance(hooks, list):
        for h in hooks:
            if not isinstance(h, dict):
                continue
            blob = _blob(h)
            if "destock" in blob and ("base" in blob or "used_as" in blob):
                action = str(h.get("action") or h.get("used_as") or "").lower()
                if "base" in action or "destock" in action:
                    return True
    return "destock" in _blob(vm.get("fair_value")) and "base" in _blob(vm.get("fair_value"))


def check_destock_not_silent_duration(session: Path) -> list[tuple[str, str, str]]:
    brief, err = load_json(session / "registry" / "operating_path_brief.json")
    if err or not isinstance(brief, dict):
        return [("SKIPPED", "destock_base", "operating_path_brief.json missing")]
    if not _unresolved_destock(brief):
        return [("PASS", "destock_base", "no unresolved destock/flatten conflict")]
    vm, verr = load_json(session / "data" / "valuation_model.json")
    if verr or not isinstance(vm, dict):
        return [("SKIPPED", "destock_base", "valuation_model.json missing")]
    fv = vm.get("fair_value") if isinstance(vm.get("fair_value"), dict) else {}
    du = fv.get("decision_usefulness")
    if isinstance(du, dict):
        du = du.get("value")
    du_s = str(du or "").strip().lower()
    dec, _ = load_json(session / "registry" / "decision.json")
    action = ""
    if isinstance(dec, dict):
        dur = dec.get("duration") if isinstance(dec.get("duration"), dict) else {}
        action = str(dur.get("action") or "").strip().lower()
    if du_s == "low" or action in {"pass", "too_hard"}:
        return [
            (
                "PASS",
                "destock_base",
                f"unresolved destock with DU={du_s or 'unset'} action={action or 'unset'}",
            )
        ]
    if _destock_in_base(vm):
        return [("PASS", "destock_base", "destock encoded in base hooks")]
    return [
        (
            "FAIL",
            "destock_base",
            "unresolved flatten-vs-destock cannot be duration-in-base; "
            "put destock in base, or decision_usefulness=low, or duration.action=pass/too_hard",
        )
    ]


def check_tv_share_duration(session: Path) -> list[tuple[str, str, str]]:
    vm, err = load_json(session / "data" / "valuation_model.json")
    if err or not isinstance(vm, dict):
        return [("SKIPPED", "tv_share", "valuation_model.json missing")]
    tc = vm.get("terminal_consistency")
    if not isinstance(tc, dict):
        return [("SKIPPED", "tv_share", "terminal_consistency absent")]
    share = _as_float(tc.get("tv_share_of_ev_base"))
    if share is None or share <= 0.60:
        return [("PASS", "tv_share", f"tv_share={share}")]
    y8 = _as_float(tc.get("y8_growth")) or _as_float(tc.get("explicit_end_growth"))
    assumptions = vm.get("assumptions") if isinstance(vm.get("assumptions"), dict) else {}
    if y8 is None:
        y8 = _as_float(assumptions.get("y8_growth") or assumptions.get("year8_growth"))
    years = _as_float(tc.get("explicit_years") or assumptions.get("explicit_years"))
    resp = str(tc.get("response") or tc.get("high_tv_response") or "").strip().lower()
    if years is not None and years >= 10:
        return [("PASS", "tv_share", f"tv_share={share} explicit_years={years}")]
    if y8 is None or y8 < 0.08:
        return [("PASS", "tv_share", f"tv_share={share} y8_growth={y8}")]
    if resp in TV_RESPONSE_OK:
        return [("PASS", "tv_share", f"response={resp}")]
    return [
        (
            "FAIL",
            "tv_share",
            "TV share >60% with Y8 growth still ≥8% requires extend_years / "
            "switch_primary / residual_income (not 'below 75%, widen range')",
        )
    ]


def check_related_party_intensity(session: Path) -> list[tuple[str, str, str]]:
    mc, err = load_json(session / "registry" / "market_context.json")
    if err or not isinstance(mc, dict):
        return [("SKIPPED", "rp_intensity", "market_context.json missing")]
    intensity = str(mc.get("intensity") or "").strip().lower()
    if intensity != "low":
        return [("PASS", "rp_intensity", f"intensity={intensity}")]
    fdd, ferr = load_json(session / "registry" / "filing_deep_dive.json")
    blob = ""
    if not ferr and isinstance(fdd, dict):
        notes = fdd.get("footnotes")
        if isinstance(notes, dict):
            blob = _blob(notes.get("related_party_dual_class") or notes.get("related_party") or notes)
        elif isinstance(notes, list):
            blob = _blob(notes)
        else:
            blob = _blob(fdd.get("related_party") or "")
    if not blob:
        return [("SKIPPED", "rp_intensity", "no related-party footnote blob")]
    if "related" not in blob and "pepsi" not in blob and "preferred" not in blob:
        return [("PASS", "rp_intensity", "no related-party concentration language")]
    pcts = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*%", blob)]
    high = any(p >= 20.0 for p in pcts)
    rights = any(w in blob for w in ("board", "preferred", "series a", "series b", "two seats"))
    if high or rights:
        return [
            (
                "FAIL",
                "rp_intensity",
                "related-party revenue ≥20% or preferred/board rights cannot stay "
                "market_context.intensity=low (F3)",
            )
        ]
    return [("PASS", "rp_intensity", "intensity=low without ≥20% RP / board rights")]


def check_changelog_isolation(session: Path) -> list[tuple[str, str, str]]:
    brief, err = load_json(session / "registry" / "research_brief.json")
    if err or not isinstance(brief, dict):
        return [("SKIPPED", "changelog", "research_brief.json missing")]
    mode = str(brief.get("mode") or brief.get("research_mode") or "").strip().lower()
    prior = brief.get("prior_session_key") or brief.get("prior_run_id")
    if mode != "update" and not prior:
        return [("SKIPPED", "changelog", "initiate / no declared prior")]
    path = session / "registry" / "earning_power_changelog.json"
    data, derr = load_json(path)
    if derr or not isinstance(data, dict):
        return [
            (
                "FAIL",
                "changelog",
                "update/prior_session_key requires registry/earning_power_changelog.json "
                "(earning-power facts, not prior FV/MoS/WACC)",
            )
        ]
    blob_keys = {str(k).lower() for k in data.keys()}
    bad = blob_keys & FORBIDDEN_CHANGELOG_KEYS
    nested = data.get("prior") if isinstance(data.get("prior"), dict) else {}
    bad |= {str(k).lower() for k in nested.keys()} & FORBIDDEN_CHANGELOG_KEYS
    if bad:
        return [
            (
                "FAIL",
                "changelog.isolation",
                f"changelog must not copy prior valuation inputs {sorted(bad)} (F14/F16)",
            )
        ]
    facts = data.get("facts") if isinstance(data.get("facts"), dict) else data
    if not any(k in facts for k in ("nopat", "invested_capital", "share_count", "scorecard", "ic")):
        return [
            (
                "FAIL",
                "changelog.facts",
                "changelog needs earning-power facts (nopat/ic/share_count/scorecard)",
            )
        ]
    return [("PASS", "changelog", "facts-only changelog; prior FV not copied")]


def check_wave3_epistemology(session: Path) -> list[tuple[str, str, str]]:
    if not session_is_wave3_runtime(session):
        return [
            (
                "SKIPPED",
                "wave3_epistemology",
                "legacy/slim (harness_version < 2.11.0)",
            )
        ]
    out: list[tuple[str, str, str]] = []
    out.extend(check_destock_not_silent_duration(session))
    out.extend(check_tv_share_duration(session))
    out.extend(check_related_party_intensity(session))
    out.extend(check_changelog_isolation(session))
    return out

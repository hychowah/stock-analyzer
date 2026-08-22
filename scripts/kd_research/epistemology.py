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
WAVE4_SINCE = (2, 12, 0)
OLD_DESTOCK_IN_BEAR_PHRASES = (
    "destock-fade in bear",
    "destock analog lives in bear",
    "destock analog in bear",
    "destock analog lives in bear only",
)
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


def session_is_wave4_runtime(session: Path) -> bool:
    parsed = parse_semver(load_run_manifest_version(session))
    if parsed is None:
        return False
    return parsed >= WAVE4_SINCE


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
    """True only when a hook encodes destock on the *base* path.

    Do not scan fair_value: that object always contains the key ``base``.
    Bear-only destock (applies_in=bear / used_as bear) is not destock-in-base.
    """
    hooks = vm.get("operating_path_hooks")
    if not isinstance(hooks, list):
        return False
    for h in hooks:
        if not isinstance(h, dict):
            continue
        blob = _blob(h)
        if "destock" not in blob:
            continue
        applies = str(h.get("applies_in") or h.get("applies") or "").strip().lower()
        action = str(h.get("action") or h.get("used_as") or "").strip().lower()
        if "bear" in applies or "bear_only" in action or "bear" in action:
            continue
        if applies in {"base", "base_path"} or "base" in applies:
            return True
        if "used_as:base" in action or action.endswith(":base") or "base_path" in action:
            return True
    return False


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


def _collect_keys(obj: Any, acc: set[str] | None = None) -> set[str]:
    acc = acc if acc is not None else set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            acc.add(str(k).lower())
            _collect_keys(v, acc)
    elif isinstance(obj, list):
        for item in obj[:80]:
            _collect_keys(item, acc)
    return acc


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
    bad = _collect_keys(data) & FORBIDDEN_CHANGELOG_KEYS
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


def _mentions_trust_guides(obj: Any) -> bool:
    blob = _blob(obj)
    return "trust_guides_more" in blob or "trust_guides" in blob


def _has_met_only_or_cash_split(scorecard: Any) -> bool:
    if not isinstance(scorecard, dict):
        return False
    for k in ("met_only_hit_rate", "met_only", "cash_quality", "cash_organic_quality"):
        if scorecard.get(k) is not None:
            return True
    blob = _blob(scorecard)
    return "met_only" in blob or "met-only" in blob or (
        "cash" in blob and "quality" in blob
    )


def check_trust_guides_more(session: Path) -> list[tuple[str, str, str]]:
    """E2: beat must not imply trust_guides_more without a met-only / cash split."""
    vm, _ = load_json(session / "data" / "valuation_model.json")
    fdd, _ = load_json(session / "registry" / "filing_deep_dive.json")
    if not isinstance(vm, dict) and not isinstance(fdd, dict):
        return [("SKIPPED", "trust_guides_more", "valuation and FDD missing")]
    mentioned = _mentions_trust_guides(vm) or _mentions_trust_guides(fdd)
    if not mentioned:
        return [("PASS", "trust_guides_more", "no trust_guides_more claim")]
    scorecard = None
    if isinstance(fdd, dict):
        scorecard = fdd.get("management_scorecard")
    if _has_met_only_or_cash_split(scorecard):
        return [
            (
                "PASS",
                "trust_guides_more",
                "trust_guides_more with met_only / cash-quality split",
            )
        ]
    return [
        (
            "WARN",
            "trust_guides_more",
            "trust_guides_more without met_only or cash/organic quality split "
            "(beat is not a hit for trusting guides)",
        )
    ]


def _first_floats(text: Any) -> list[float]:
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", str(text or ""))]


def _override_raises(item: dict[str, Any]) -> bool:
    old = item.get("old")
    new = item.get("new")
    if old is None:
        old = item.get("old_assumption")
    if new is None:
        new = item.get("new_assumption")
    o_n, n_n = _as_float(old), _as_float(new)
    if o_n is None:
        fo = _first_floats(old)
        o_n = fo[-1] if fo else None
    if n_n is None:
        fn = _first_floats(new)
        n_n = fn[-1] if fn else None
    if o_n is not None and n_n is not None and n_n > o_n:
        return True
    reason = _blob(item.get("reason"))
    return any(w in reason for w in ("raise", "raised", "increase", "increased", "up from"))


def _walk_fcf(obj: Any) -> float | None:
    found: list[float] = []

    def walk(x: Any, key: str = "") -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v, str(k))
        elif _as_float(x) is not None and any(
            t in key.lower() for t in ("fcf", "free_cash", "free cash")
        ):
            found.append(float(_as_float(x)))  # type: ignore[arg-type]

    walk(obj)
    return found[0] if found else None


def _wc_deteriorating(lq: dict[str, Any]) -> bool:
    blob = _blob(lq.get("evidence_log") or "") + " " + _blob(lq.get("balance_sheet") or "")
    log = lq.get("evidence_log")
    if isinstance(log, list):
        for row in log:
            if not isinstance(row, dict):
                continue
            metric = str(row.get("metric") or "").lower()
            obs = str(row.get("observation") or "").lower()
            if any(t in metric or t in obs for t in ("inventory", "receivable", " ar", "dso")):
                if any(t in obs for t in ("+", "up", "increase", "rose", "build")):
                    return True
    return any(
        t in blob for t in ("inventory +", "inventories +", "ar +", "receivable +")
    )


def check_two_quarter_wc(session: Path) -> list[tuple[str, str, str]]:
    """E3: two-quarter raise while FCF/AR/inventory deteriorate → WARN."""
    vm, err = load_json(session / "data" / "valuation_model.json")
    if err or not isinstance(vm, dict):
        return [("SKIPPED", "two_quarter_wc", "valuation_model.json missing")]
    overrides = vm.get("overrides_applied")
    if not isinstance(overrides, list) or not overrides:
        return [("PASS", "two_quarter_wc", "no overrides_applied")]
    raises = [
        o
        for o in overrides
        if isinstance(o, dict)
        and "two_quarter" in str(o.get("rule") or "").lower()
        and _override_raises(o)
    ]
    if not raises:
        return [("PASS", "two_quarter_wc", "no two_quarter_rule raise")]
    lq, lerr = load_json(session / "registry" / "latest_quarter.json")
    if lerr or not isinstance(lq, dict):
        return [("SKIPPED", "two_quarter_wc", "latest_quarter.json missing")]
    fcf = _walk_fcf(lq.get("cash_flow") or lq)
    wc = _wc_deteriorating(lq)
    if fcf is not None and fcf < 0 and wc:
        return [
            (
                "WARN",
                "two_quarter_wc",
                "two_quarter_rule raised volume/growth while FCF is negative and "
                "AR/inventory deteriorated — force bear_only or reject the raise",
            )
        ]
    return [
        (
            "PASS",
            "two_quarter_wc",
            f"two_quarter raise present; fcf={fcf} wc_deteriorating={wc}",
        )
    ]


def _destock_conflict(brief: dict[str, Any]) -> bool:
    """Any destock conflict, resolved or unresolved. Does not change Wave 3."""
    conflicts = brief.get("conflicts")
    if not isinstance(conflicts, list):
        return False
    for item in conflicts:
        if not isinstance(item, dict):
            continue
        text = _blob(item.get("id")) + " " + _blob(item.get("claim_a")) + " " + _blob(item.get("claim_b"))
        if "destock" in text:
            return True
    return False


def _destock_only_in_bear(vm: dict[str, Any]) -> bool:
    if _destock_in_base(vm):
        return False
    hooks = vm.get("operating_path_hooks")
    if not isinstance(hooks, list):
        return False
    saw_bear = False
    for h in hooks:
        if not isinstance(h, dict):
            continue
        if "destock" not in _blob(h):
            continue
        applies = str(h.get("applies_in") or h.get("applies") or "").strip().lower()
        action = str(h.get("action") or h.get("used_as") or "").strip().lower()
        if "bear" in applies or "bear_only" in action or "bear" in action:
            saw_bear = True
    return saw_bear


def _hints_teach_destock_in_bear(brief: dict[str, Any]) -> bool:
    blob = _blob(brief.get("scenario_hints")) + " " + _blob(brief.get("recommended_for_agent5"))
    return any(p in blob for p in OLD_DESTOCK_IN_BEAR_PHRASES)


def _duration_legal_fields(session: Path, vm: dict[str, Any]) -> tuple[str, str]:
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
    return du_s, action


def check_destock_default(session: Path) -> list[tuple[str, str, str]]:
    """Wave 4: destock conflict of any status cannot park destock in bear."""
    if not session_is_wave4_runtime(session):
        return [
            (
                "SKIPPED",
                "destock_default",
                "legacy/slim (harness_version < 2.12.0)",
            )
        ]
    brief, err = load_json(session / "registry" / "operating_path_brief.json")
    if err or not isinstance(brief, dict):
        return [("SKIPPED", "destock_default", "operating_path_brief.json missing")]
    if not _destock_conflict(brief):
        return [("PASS", "destock_default", "no destock conflict")]
    vm, verr = load_json(session / "data" / "valuation_model.json")
    if verr or not isinstance(vm, dict):
        return [("SKIPPED", "destock_default", "valuation_model.json missing")]
    du_s, action = _duration_legal_fields(session, vm)
    if du_s == "low" or action in {"pass", "too_hard"}:
        return [
            (
                "PASS",
                "destock_default",
                f"destock conflict with DU={du_s or 'unset'} action={action or 'unset'}",
            )
        ]
    if _destock_in_base(vm):
        return [("PASS", "destock_default", "destock encoded in base hooks")]
    if _destock_only_in_bear(vm) or _hints_teach_destock_in_bear(brief):
        return [
            (
                "FAIL",
                "destock_default",
                "destock conflict cannot park destock in bear while duration stays "
                "in base (resolved-to-bear is not an escape); put destock in base, "
                "or decision_usefulness=low, or duration.action=pass/too_hard",
            )
        ]
    return [
        (
            "PASS",
            "destock_default",
            "destock conflict without destock-in-bear encoding",
        )
    ]


def _wc_releasing(lq: dict[str, Any]) -> bool:
    """Inventory/AR down (WC release) — inverse of _wc_deteriorating."""
    blob = _blob(lq.get("evidence_log") or "") + " " + _blob(lq.get("balance_sheet") or "")
    log = lq.get("evidence_log")
    if isinstance(log, list):
        for row in log:
            if not isinstance(row, dict):
                continue
            metric = str(row.get("metric") or "").lower()
            obs = str(row.get("observation") or "").lower()
            if any(t in metric or t in obs for t in ("inventory", "receivable", " ar", "dso")):
                if any(
                    t in obs
                    for t in ("-", "down", "decrease", "fell", "drop", "destock", "release")
                ):
                    return True
    return any(
        t in blob
        for t in (
            "inventory -",
            "inventories -",
            "ar -",
            "receivable -",
            "inventory down",
            "inventory fell",
            "destock",
        )
    )


def check_two_quarter_destock_inverse(session: Path) -> list[tuple[str, str, str]]:
    """Wave 4: raise + destock conflict + FCF≥0 + inventory down → WARN."""
    if not session_is_wave4_runtime(session):
        return [
            (
                "SKIPPED",
                "two_quarter_destock_inverse",
                "legacy/slim (harness_version < 2.12.0)",
            )
        ]
    brief, err = load_json(session / "registry" / "operating_path_brief.json")
    if err or not isinstance(brief, dict) or not _destock_conflict(brief):
        return [
            (
                "PASS",
                "two_quarter_destock_inverse",
                "no destock conflict",
            )
        ]
    vm, verr = load_json(session / "data" / "valuation_model.json")
    if verr or not isinstance(vm, dict):
        return [("SKIPPED", "two_quarter_destock_inverse", "valuation_model.json missing")]
    overrides = vm.get("overrides_applied")
    if not isinstance(overrides, list) or not overrides:
        return [("PASS", "two_quarter_destock_inverse", "no overrides_applied")]
    raises = [
        o
        for o in overrides
        if isinstance(o, dict)
        and "two_quarter" in str(o.get("rule") or "").lower()
        and _override_raises(o)
    ]
    if not raises:
        return [("PASS", "two_quarter_destock_inverse", "no two_quarter_rule raise")]
    lq, lerr = load_json(session / "registry" / "latest_quarter.json")
    if lerr or not isinstance(lq, dict):
        return [
            (
                "WARN",
                "two_quarter_destock_inverse",
                "two_quarter raise with destock conflict but latest_quarter missing "
                "— cannot bless the raise without FCF/WC",
            )
        ]
    fcf = _walk_fcf(lq.get("cash_flow") or lq)
    releasing = _wc_releasing(lq)
    if fcf is None and not releasing:
        return [
            (
                "WARN",
                "two_quarter_destock_inverse",
                "two_quarter raise with destock conflict but FCF/inventory not in "
                "latest_quarter — cannot bless the raise",
            )
        ]
    if fcf is not None and fcf >= 0 and releasing:
        return [
            (
                "WARN",
                "two_quarter_destock_inverse",
                "two_quarter_rule raised volume/growth while destock conflict is "
                "live, FCF ≥ 0, and inventory/AR down (WC release) — force "
                "bear_only or reject the raise",
            )
        ]
    return [
        (
            "PASS",
            "two_quarter_destock_inverse",
            f"two_quarter raise with destock; fcf={fcf} wc_releasing={releasing}",
        )
    ]


def check_wave4_destock_default(session: Path) -> list[tuple[str, str, str]]:
    if not session_is_wave4_runtime(session):
        return [
            (
                "SKIPPED",
                "wave4_destock_default",
                "legacy/slim (harness_version < 2.12.0)",
            )
        ]
    out: list[tuple[str, str, str]] = []
    out.extend(check_destock_default(session))
    out.extend(check_two_quarter_destock_inverse(session))
    return out


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
    out.extend(check_trust_guides_more(session))
    out.extend(check_two_quarter_wc(session))
    return out

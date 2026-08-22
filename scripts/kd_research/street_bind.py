"""Street-estimate calibration gates (harness >= 2.7.0).

Street FY+1/+2 consensus is a *reference* after Agent 5 independently builds
the revenue path from company evidence. Copying Street into base is FAIL-quality.
Being off Street is not FAIL; missing a must-respond when |delta| > 20% is FAIL.

Legacy sessions without street_estimates.json and harness < 2.7.0 SKIPPED.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.kd_research.annuals import load_run_manifest_version, parse_semver
from scripts.kd_research.gates import load_json, validate_hooks_list

STREET_SINCE = (2, 7, 0)
STREET_REL = "registry/street_estimates.json"
VM_REL = "data/valuation_model.json"

DELTA_THRESHOLD = 0.20
DELTA_EPS = 0.005
SOTP_GAP_THRESHOLD = 0.40
CONSTRUCTION_MIN_LEN = 40
DIVERGENCE_MIN_LEN = 40
STACK_JUSTIFY_MIN_LEN = 40
GAP_RATIONALE_MIN_LEN = 40

RESPONSE_ENUM = frozenset(
    {
        "reopen_path",
        "keep_independent_vs_street",
        "street_unusable",
        "guide_missing",
    }
)
DIAL_KEYS = (
    "volume_vs_guide",
    "gaap_om_vs_guide",
    "sbc_in_fcff",
    "wacc_vs_buildup",
)
DIAL_APPLIES = frozenset({"base", "bear_only", "none"})
PATH_COPY_NEEDLES = (
    "used_as:revenue_path",
    "used_as:street_mean",
    "used_as:consensus",
    "used_as:copy_street",
)


def street_path(session: Path) -> Path:
    return session / STREET_REL


def session_is_street_runtime(session: Path) -> bool:
    """True when harness_version >= 2.7.0 (omit-dials / both-methods law)."""
    parsed = parse_semver(load_run_manifest_version(session))
    if parsed is None:
        return False
    return parsed >= STREET_SINCE


def session_enforces_street(session: Path) -> bool:
    """True when Street fetch/bind gates apply."""
    if street_path(session).is_file():
        return True
    return session_is_street_runtime(session)


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
    years = data.get("years")
    if not isinstance(years, list):
        return None
    prefer = ("+1y", "fy+1", "fy+ 1", "next year")
    fallback: float | None = None
    for i, row in enumerate(years):
        if not isinstance(row, dict):
            continue
        rev = row.get("revenue")
        if not isinstance(rev, (int, float)):
            continue
        label = str(row.get("label") or "").strip().lower()
        if i == 1 or any(p in label for p in prefer) or label.endswith("+1y"):
            return float(rev)
        if fallback is None:
            fallback = float(rev)
        # vendor 0y then +1y
        if label in ("+1y", "1y", "next"):
            return float(rev)
    # if two years, second is FY+1 when first is 0y
    numeric = [
        float(r["revenue"])
        for r in years
        if isinstance(r, dict) and isinstance(r.get("revenue"), (int, float))
    ]
    if len(numeric) >= 2:
        return numeric[1]
    return fallback if len(numeric) == 1 else None


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


def check_street_bind(session: Path) -> list[tuple[str, str, str]]:
    """When Street file or new runtime + valuation: bind table, hooks, stacking, SOTP gap."""
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
    require_dials = session_is_street_runtime(session)

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
        out.extend(_check_conservatism_dials(vm, require=require_dials))
        out.extend(_check_sotp_gap(vm, require_if_both=require_dials))
        return out

    if not isinstance(bind, dict):
        out.append(
            (
                "FAIL",
                "street_bind",
                "valuation_model.street_bind object required when street_estimates.json exists (independent FY+1 vs Street calibration; do not copy Street into base)",
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
        out.append(("FAIL", "street_bind.base", "base (independent FY+1 revenue) required"))
        return out

    construction = bind.get("independent_construction")
    rationale = ""
    if isinstance(construction, dict):
        rationale = str(construction.get("rationale") or "")
    elif isinstance(construction, str):
        rationale = construction
    if len(rationale.strip()) < CONSTRUCTION_MIN_LEN:
        out.append(
            (
                "FAIL",
                "street_bind.independent_construction",
                "independent_construction.rationale must show the company-evidence stack (guide/segments/run-rate/RPO) — not 'use consensus'",
            )
        )
    else:
        out.append(("PASS", "street_bind.independent_construction", "present"))

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
        if abs(expected) > DELTA_THRESHOLD:
            div = str(bind.get("divergence_rationale") or "")
            resp = str(bind.get("response") or "").strip()
            if len(div.strip()) < DIVERGENCE_MIN_LEN or resp not in RESPONSE_ENUM:
                out.append(
                    (
                        "WARN",
                        "street_bind.delta_calibration",
                        "|delta_pct| > 20% vs Street FY+1 is a calibration note, not a "
                        "valuation skill miss. Record divergence_rationale / response if you have "
                        "them. Copying Street into the path remains FAIL.",
                    )
                )
            else:
                out.append(("PASS", "street_bind.divergence", f"response={resp}"))
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

    out.extend(_check_conservatism_dials(vm, require=require_dials))
    out.extend(_check_sotp_gap(vm, require_if_both=require_dials))
    return out


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


def _check_conservatism_dials(vm: dict[str, Any], *, require: bool) -> list[tuple[str, str, str]]:
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


def _check_sotp_gap(vm: dict[str, Any], *, require_if_both: bool = False) -> list[tuple[str, str, str]]:
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
    # delta_pct may be percent points (43.64) or fraction (0.436)
    if stored is not None:
        as_frac = stored / 100.0 if abs(stored) > 1.5 else stored
        if abs(as_frac - (cross - primary) / primary) > 0.02 and abs(stored - gap) > 0.02:
            # allow |cross-primary|/primary vs signed (cross-primary)/primary
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

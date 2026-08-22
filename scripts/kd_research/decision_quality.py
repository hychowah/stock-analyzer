"""Wave 1 decision-quality gates (harness >= 2.9.0).

Enforces already-written investment law: template masses, named-dial PFP,
decision_usefulness on wide cones, TSR ROC vs franchise_mos, branded-staple
cyclical tripwire, cash-generative-not-growth identity. Legacy / harness
< 2.9.0 SKIPPED. Never invents fair values.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from scripts.kd_research.annuals import load_run_manifest_version, parse_semver
from scripts.kd_research.gates import load_json
from scripts.kd_research.roic_identity import _cheap_class

WAVE1_SINCE = (2, 9, 0)
TEMPLATE_MASSES = frozenset({(0.30, 0.45, 0.25), (0.25, 0.50, 0.25)})
DU_OK = frozenset({"high", "medium", "low"})
STAPLE_NEEDLES = (
    "consumer defensive",
    "consumer staples",
    "farm products",
    "packaged foods",
    "household products",
)
BRANDED_NEEDLES = (
    "branded",
    "retail carton",
    "retail eggs",
    "cpg",
    "packaged meat",
    "brand franchise",
)
SPOT_NEEDLES = (
    "posted-price",
    "posted price",
    "spot-realized",
    "spot realized",
    "majority of revenue realized at",
    "unbranded",
    "commodity spot",
)
PFP_DIAL_NEEDLES = (
    "wacc",
    "discount rate",
    "terminal",
    "growth",
    "margin",
    " om",
    "om ",
    "multiple",
    "rotce",
    "roe",
    "ke ",
    "cost of equity",
    "g=",
    "g ",
)
PFP_MECHANICAL = (
    "price > base",
    "price>base",
    "price above base",
    "priced above base",
    "price > pw",
    "price>pw",
    "price > probability",
    "price below bull",
    "price < bull",
    "inside the grid",
    "inside the band",
    "price is inside",
)
COUNTERFACTUAL_TRIPLE = re.compile(
    r"0\.\d{1,2}\s*[/:]\s*0\.\d{1,2}\s*[/:]\s*0\.\d{1,2}"
)
AUDIT_DISCLAIMER_NEEDLES = (
    "process completeness",
    "not an investment recommendation",
    "not a buy list",
    "not investable",
    "not a buy",
    "completeness, not",
)


def session_is_wave1_runtime(session: Path) -> bool:
    parsed = parse_semver(load_run_manifest_version(session))
    if parsed is None:
        return False
    return parsed >= WAVE1_SINCE


def _as_float(val: Any) -> float | None:
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, dict):
        for k in ("value", "amount", "pct", "percent"):
            if k in val:
                return _as_float(val.get(k))
    if isinstance(val, str):
        s = val.strip().replace(",", "").replace("%", "")
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _mass_triple(probs: object) -> tuple[float, float, float] | None:
    if not isinstance(probs, dict):
        return None
    out: list[float] = []
    for k in ("bear", "base", "bull"):
        v = probs.get(k)
        if isinstance(v, dict):
            v = v.get("value")
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return None
        out.append(round(float(v), 2))
    return (out[0], out[1], out[2])


def _valuation(session: Path) -> dict[str, Any] | None:
    data, err = load_json(session / "data" / "valuation_model.json")
    if err or not isinstance(data, dict):
        return None
    return data


def _blob(obj: Any) -> str:
    try:
        return json.dumps(obj, default=str).lower()
    except (TypeError, ValueError):
        return str(obj).lower()


def _has_needle(blob: str, needles: tuple[str, ...]) -> bool:
    """Substring match that does not treat 'unbranded' as 'branded'."""
    for n in needles:
        if n == "branded":
            if re.search(r"(?<!un)branded", blob):
                return True
            continue
        if n in blob:
            return True
    return False


def _probability_method(vm: dict[str, Any]) -> str:
    fv = vm.get("fair_value") if isinstance(vm.get("fair_value"), dict) else {}
    raw = fv.get("probability_method")
    if isinstance(raw, dict):
        raw = raw.get("value") or raw.get("rationale") or ""
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    assumptions = vm.get("assumptions") if isinstance(vm.get("assumptions"), dict) else {}
    sp = assumptions.get("scenario_probabilities")
    if isinstance(sp, dict):
        for k in ("probability_method", "rationale", "counterfactual"):
            v = sp.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    sibling = vm.get("scenario_probabilities_rationale") or fv.get(
        "scenario_probabilities_rationale"
    )
    if isinstance(sibling, str):
        return sibling.strip()
    return ""


def _has_numeric_counterfactual(text: str, template: tuple[float, float, float]) -> bool:
    if not text:
        return False
    for m in COUNTERFACTUAL_TRIPLE.finditer(text):
        parts = re.split(r"[/:]", m.group(0))
        try:
            trip = tuple(round(float(p.strip()), 2) for p in parts if p.strip())
        except ValueError:
            continue
        if len(trip) == 3 and trip != template:
            return True
    return bool(re.search(r"bear\s*[=:]\s*0\.\d+", text, re.I))


def check_template_masses(session: Path) -> list[tuple[str, str, str]]:
    vm = _valuation(session)
    if vm is None:
        return [("SKIPPED", "template_masses", "valuation_model.json missing")]
    fv = vm.get("fair_value") if isinstance(vm.get("fair_value"), dict) else {}
    probs = fv.get("scenario_probabilities")
    if not isinstance(probs, dict):
        assumptions = vm.get("assumptions") if isinstance(vm.get("assumptions"), dict) else {}
        sp = assumptions.get("scenario_probabilities")
        if isinstance(sp, dict) and isinstance(sp.get("value"), dict):
            probs = sp["value"]
        elif isinstance(sp, dict):
            probs = sp
    triple = _mass_triple(probs)
    if triple is None:
        return [("SKIPPED", "template_masses", "no bear/base/bull masses")]
    if triple not in TEMPLATE_MASSES:
        return [("PASS", "template_masses", f"{triple} not a banned template")]
    method = _probability_method(vm)
    blob = method + " " + _blob(probs)
    if len(method) >= 20 and _has_numeric_counterfactual(blob, triple):
        return [
            (
                "PASS",
                "template_masses",
                f"{triple} justified with probability_method + counterfactual",
            )
        ]
    return [
        (
            "FAIL",
            "template_masses",
            f"{triple} is a template paste; need probability_method (≥20 chars) "
            "AND a numeric counterfactual mass (harness ≥ 2.9.0)",
        )
    ]


def extract_priced_for_perfection(vm: dict[str, Any] | None) -> tuple[Any, str]:
    """Return (flag, rationale) from reverse_engineering first, then top-level."""
    if not isinstance(vm, dict):
        return None, ""
    re_block = vm.get("reverse_engineering")
    candidates: list[Any] = []
    if isinstance(re_block, dict):
        candidates.append(re_block.get("priced_for_perfection"))
        rat = str(re_block.get("rationale") or "")
    else:
        rat = ""
    candidates.append(vm.get("priced_for_perfection"))
    flag: Any = None
    extra = ""
    for c in candidates:
        if c is None:
            continue
        if isinstance(c, bool):
            flag = c
            break
        if isinstance(c, dict):
            if "value" in c:
                flag = c.get("value")
            elif "flag" in c:
                flag = c.get("flag")
            extra = str(c.get("rationale") or "")
            if flag is not None:
                break
        if isinstance(c, str) and c.lower() in ("true", "false"):
            flag = c.lower() == "true"
            break
    rationale = extra or rat
    if isinstance(re_block, dict) and not rationale:
        implied = re_block.get("implied")
        if implied is not None:
            rationale = _blob(implied)
    return flag, rationale


def check_priced_for_perfection(session: Path) -> list[tuple[str, str, str]]:
    vm = _valuation(session)
    if vm is None:
        return [("SKIPPED", "priced_for_perfection", "valuation_model.json missing")]
    flag, rationale = extract_priced_for_perfection(vm)
    if flag is None:
        return [("SKIPPED", "priced_for_perfection", "PFP flag absent")]
    if not isinstance(flag, bool):
        return [
            (
                "FAIL",
                "priced_for_perfection",
                f"priced_for_perfection must be boolean; got {type(flag).__name__}",
            )
        ]
    low = rationale.lower()
    mechanical = any(n in low for n in PFP_MECHANICAL)
    has_dial = any(n in low for n in PFP_DIAL_NEEDLES)
    if mechanical and not has_dial:
        return [
            (
                "FAIL",
                "priced_for_perfection",
                "PFP rationale is mechanical price≷base/PW; name at least one dial "
                "(WACC, g, OM, multiple, ROTCE)",
            )
        ]
    if not rationale.strip() or len(rationale.strip()) < 24:
        return [
            (
                "FAIL",
                "priced_for_perfection",
                "PFP requires a named-dial rationale (≥24 chars)",
            )
        ]
    if not has_dial:
        return [
            (
                "FAIL",
                "priced_for_perfection",
                "PFP rationale must name a valuation dial (WACC/g/OM/multiple/ROTCE)",
            )
        ]
    return [("PASS", "priced_for_perfection", f"flag={flag} named-dial rationale")]


def _cone_needs_du(fv: dict[str, Any]) -> bool:
    base = _as_float(fv.get("base"))
    bear = _as_float(fv.get("bear"))
    bull = _as_float(fv.get("bull"))
    if base is None or base <= 0 or bear is None or bull is None:
        return False
    span = (bull - bear) / base
    return span > 1.0 or bear < 0.4 * base


def check_decision_usefulness(session: Path) -> list[tuple[str, str, str]]:
    vm = _valuation(session)
    if vm is None:
        return [("SKIPPED", "decision_usefulness", "valuation_model.json missing")]
    fv = vm.get("fair_value") if isinstance(vm.get("fair_value"), dict) else {}
    if not fv:
        return [("SKIPPED", "decision_usefulness", "fair_value missing")]
    du = fv.get("decision_usefulness")
    if isinstance(du, dict):
        du = du.get("value") or du.get("class")
    if not _cone_needs_du(fv):
        return [("PASS", "decision_usefulness", "cone below width trigger")]
    if not isinstance(du, str) or du.strip().lower() not in DU_OK:
        return [
            (
                "FAIL",
                "decision_usefulness",
                "(bull−bear)/base > 100% or bear < 0.4×base requires "
                "fair_value.decision_usefulness in {high,medium,low}",
            )
        ]
    return [("PASS", "decision_usefulness", du.strip().lower())]


def _roc_status(tsr: dict[str, Any]) -> str | None:
    flags = tsr.get("value_trap_flags")
    if isinstance(flags, list):
        for item in flags:
            if not isinstance(item, dict):
                continue
            name = str(item.get("flag") or item.get("id") or "").lower()
            if "roc_vs_cost" in name or name.replace(" ", "_") == "roc_vs_cost_of_capital":
                return str(item.get("status") or "").strip().lower()
    nested = tsr.get("roc_vs_cost_of_capital")
    if isinstance(nested, dict):
        return str(nested.get("status") or "").strip().lower()
    if isinstance(nested, str):
        return nested.strip().lower()
    return None


def check_roc_screen_vs_cheap_claim(session: Path) -> list[tuple[str, str, str]]:
    tsr, err = load_json(session / "registry" / "tsr_validation.json")
    if err or not isinstance(tsr, dict):
        return [("SKIPPED", "roc_vs_cheap_claim", "tsr_validation.json missing")]
    vm = _valuation(session)
    if vm is None:
        return [("SKIPPED", "roc_vs_cheap_claim", "valuation_model.json missing")]
    ident = vm.get("roic_identity")
    if not isinstance(ident, dict):
        return [("SKIPPED", "roc_vs_cheap_claim", "roic_identity absent")]
    cheap = _cheap_class(ident)
    bucket = str(ident.get("quality_bucket") or "").strip()
    status = _roc_status(tsr)
    if status != "fail":
        return [
            (
                "PASS",
                "roc_vs_cheap_claim",
                f"tsr roc status={status or 'absent'}; cheap_claim={cheap}",
            )
        ]
    if cheap == "franchise_mos" and bucket == "above_wacc":
        rebuttal = ident.get("roc_screen_rebuttal") or ident.get("agent12_rebuttal")
        if isinstance(rebuttal, dict):
            rebuttal = rebuttal.get("rationale") or rebuttal.get("value") or ""
        if not isinstance(rebuttal, str) or len(rebuttal.strip()) < 40:
            return [
                (
                    "WARN",
                    "roc_vs_cheap_claim",
                    "Agent 12 roc_vs_cost_of_capital=fail with cheap_claim=franchise_mos "
                    "and quality_bucket=above_wacc needs roc_screen_rebuttal "
                    "(≥40 chars naming mid-cycle NOPAT vs historical GAAP ROC)",
                )
            ]
        return [
            (
                "PASS",
                "roc_vs_cheap_claim",
                "roc fail rebutted with roc_screen_rebuttal",
            )
        ]
    return [
        (
            "PASS",
            "roc_vs_cheap_claim",
            f"roc fail with cheap_claim={cheap} bucket={bucket} "
            "(below/approx franchise_mos is the 2.8.0 ROIC gate, not this one)",
        )
    ]


def check_sector_identity_tripwire(session: Path) -> list[tuple[str, str, str]]:
    sc, err = load_json(session / "registry" / "sector_config.json")
    if err or not isinstance(sc, dict):
        return [("SKIPPED", "sector_identity_tripwire", "sector_config.json missing")]
    primary = str(sc.get("primary_sector") or "").strip().lower()
    if primary != "cyclical":
        return [("PASS", "sector_identity_tripwire", f"primary_sector={primary}")]
    blob = _blob(sc)
    staple = _has_needle(blob, STAPLE_NEEDLES)
    branded = _has_needle(blob, BRANDED_NEEDLES)
    spot = _has_needle(blob, SPOT_NEEDLES)
    if staple and branded and spot:
        return [
            (
                "SKIPPED",
                "sector_identity_tripwire",
                "mixed branded and spot/posted-price language; not a machine identity call",
            )
        ]
    if staple and branded and not spot:
        return [
            (
                "FAIL",
                "sector_identity_tripwire",
                "branded Consumer Defensive / Farm Products / CPG classified cyclical "
                "without majority spot/posted-price evidence (F21)",
            )
        ]
    if not staple:
        return [
            (
                "SKIPPED",
                "sector_identity_tripwire",
                "no on-disk staple/GICS strings; Mode B does not fetch a classifier",
            )
        ]
    return [
        (
            "PASS",
            "sector_identity_tripwire",
            f"cyclical with staple={staple} branded={branded} spot={spot}",
        )
    ]


def check_growth_cash_identity(session: Path) -> list[tuple[str, str, str]]:
    """A7: profitable branded consumer must not use primary_sector=growth.

    Does **not** classify from FCF/OM. Only FAILs a forbidden combo already
    on disk (growth + staple/CPG/branded-consumer language).
    """
    sc, err = load_json(session / "registry" / "sector_config.json")
    if err or not isinstance(sc, dict):
        return [("SKIPPED", "growth_cash_identity", "sector_config.json missing")]
    primary = str(sc.get("primary_sector") or "").strip().lower()
    if primary != "growth":
        return [("PASS", "growth_cash_identity", f"primary_sector={primary}")]
    blob = _blob(sc)
    staple = _has_needle(blob, STAPLE_NEEDLES)
    branded = _has_needle(blob, BRANDED_NEEDLES)
    if staple and branded:
        return [
            (
                "FAIL",
                "growth_cash_identity",
                "branded consumer / CPG / staples used primary_sector=growth; "
                "§5 wants native module (usually standard) + is_also_growth (A7)",
            )
        ]
    return [
        (
            "SKIPPED",
            "growth_cash_identity",
            "growth primary without on-disk branded-consumer/CPG language "
            "(Mode B does not infer identity from FCF)",
        )
    ]


def check_readme_audit_disclaimer(session: Path) -> list[tuple[str, str, str]]:
    reports = session / "reports"
    if not reports.is_dir():
        return [("SKIPPED", "readme_audit_disclaimer", "reports/ missing")]
    matches = list(reports.glob("00_*_README.md"))
    if not matches:
        return [("SKIPPED", "readme_audit_disclaimer", "README missing")]
    text = matches[0].read_text(encoding="utf-8", errors="replace")
    low = text.lower()
    if "audit" not in low or "pass" not in low:
        return [("PASS", "readme_audit_disclaimer", "no Audit PASS line yet")]
    if any(n in low for n in AUDIT_DISCLAIMER_NEEDLES):
        return [("PASS", "readme_audit_disclaimer", "completeness disclaimer present")]
    return [
        (
            "WARN",
            "readme_audit_disclaimer",
            "README mentions Audit PASS without stating it is process completeness, "
            "not an investment recommendation (A10; WARN so live archive is not FAIL)",
        )
    ]


def check_wave1_decision_quality(
    session: Path,
    *,
    include_reports: bool = True,
) -> list[tuple[str, str, str]]:
    """All Wave 1 machine gates. SKIPPED on harness < 2.9.0 / missing version."""
    if not session_is_wave1_runtime(session):
        return [
            (
                "SKIPPED",
                "wave1_decision_quality",
                "legacy/slim (harness_version < 2.9.0)",
            )
        ]
    out: list[tuple[str, str, str]] = []
    out.extend(check_template_masses(session))
    out.extend(check_priced_for_perfection(session))
    out.extend(check_decision_usefulness(session))
    out.extend(check_roc_screen_vs_cheap_claim(session))
    out.extend(check_sector_identity_tripwire(session))
    out.extend(check_growth_cash_identity(session))
    if include_reports:
        out.extend(check_readme_audit_disclaimer(session))
    return out

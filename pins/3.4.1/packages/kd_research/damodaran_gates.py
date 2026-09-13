"""Damodaran identities for harness >= 3.0.0. Older stamps SKIPPED.

3.1.0 constitution (A+B): the value slot is a DCF (or equity DCF / option);
exit/ARR/NAV/TTC×multiple are price; one iv_playbook from the router.
3.2.0 narrative substance (C): narrative_bind carries a story + a story→input
map + 3P buckets; truncation with p>0 must write the probability-weighted base.
3.4.0+: identity on classification.json; map keys are story carriers; 3P lives
on narrative_3p.json (lock = verdict PASS); Agent 5 writes story_input_bind
and buyer_dials. Overlay screens (option_screens, distressed_call) stay on the
bind, written by the 1e story specialist when the card requires them.
A v3-spec session with a valuation model but no parseable version is a FAIL
(root of trust), not a silent SKIP. Version-gated so history stays green.
3.0.0–3.0.1 keep omit-skip on terminal_consistency and playbook.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.kd_research.annuals import load_run_manifest_version, parse_semver
from packages.kd_research.check_core import load_json, session_since
from packages.kd_research.classification import (
    BUYER_CLASSES as CLASS_BUYER_CLASSES,
    CLASSIFICATION_SINCE,
    LIFE_CYCLE_STAGES as CLASS_LIFE_CYCLE_STAGES,
    PRIMARY_PLAYBOOKS as CLASS_PRIMARY_PLAYBOOKS,
    WHO_LEADS as CLASS_WHO_LEADS,
    load_classification,
)
from packages.kd_research.narrative_lock import NARRATIVE_3P_REL, STORY_CARRIERS


DAMODARAN_SINCE = (3, 0, 0)
CONSTITUTION_SINCE = (3, 1, 0)
NARRATIVE_SUBSTANCE_SINCE = (3, 2, 0)
TIER1_SINCE = (3, 3, 0)
STORY_PHASE_SINCE = CLASSIFICATION_SINCE  # 3.4.0
VM_REL = "data/valuation_model.json"
NARRATIVE_REL = "registry/narrative_bind.json"
SECTOR_REL = "registry/sector_config.json"
FINANCIALS = frozenset({"banking", "insurance"})
REIT_SECTORS = frozenset({"reit"})

PRIMARY_PLAYBOOKS = frozenset(
    {
        "mature_operating",
        "financial_service",
        "real_estate",
        "young_startup",
    }
)
SECTOR_PLAYBOOK = {
    "banking": "financial_service",
    "insurance": "financial_service",
    "reit": "real_estate",
}
# >= 3.3.0 router branches (ref 00-router.md q.1-3): the contingent-claim
# family and an asset-based floor become legal primaries.
EXTRA_PRIMARY_PLAYBOOKS = frozenset({"contingent_claim", "asset_based"})
OPTION_PLAYBOOK = "contingent_claim"
LIFE_CYCLE_STAGES = frozenset(
    {"idea", "young_growth", "scaling_growth", "mature", "decline", "not_applicable"}
)
WHO_LEADS = frozenset({"story", "numbers"})  # bind home on < 3.4.0
BUYER_CLASSES = frozenset(
    {
        "public_diversified",
        "private_undiversified",
        "ipo_or_public_buyer",
        "vc_pe",
        "not_applicable",
    }
)
ERP_METHODS = frozenset({"implied", "historical", "bottom_up", "not_applicable"})
BETA_METHODS = frozenset({"bottom_up", "regression", "peer", "fixed", "not_applicable"})
LEGAL_TV = frozenset(
    {
        "gordon",
        "gordon_growth",
        "stable_growth",
        "perpetuity",
        "liquidation",
        "excess_return",
    }
)
PRICE_TV_NEEDLES = ("exit", "multiple", "comps", "arr", "nav")
PRICE_MODEL_NEEDLES = (
    "nav",
    "affo",
    "arr_multiple",
    "exit_multiple",
    "ev_ebitda",
    "ev_ebit",
    "ttc_ev",
    "price_to_book",
)
BLEND_WORDS = ("average", "blend", "midpoint", "50/50", "50-50")
# Price-column roles (>= 3.2.0). A closed set, not a keyword denylist: the
# pricing ledger may only declare that it is a cross-check, never the value.
PRICING_ROLES = frozenset(
    {
        "cross_check",
        "relative_reference",
        "sanity_check",
        "reference_only",
    }
)
TRUTHY = frozenset({"v3"})


def _v3(session: Path) -> bool:
    return session_since(session, DAMODARAN_SINCE)


def _constitution(session: Path) -> bool:
    return session_since(session, CONSTITUTION_SINCE)


def _tier1(session: Path) -> bool:
    return session_since(session, TIER1_SINCE)


def _unstamped_v3(session: Path) -> bool:
    """A v3-spec session with a valuation model must carry a parseable version.

    Missing/garbled version on a v3 spec is a root-of-trust FAIL, not a skip.
    Legacy v2/slim sessions (no v3 spec) keep the SKIPPED path so immutable
    history and slim fixtures stay green.
    """
    manifest, err = load_json(session / "meta" / "run_manifest.json")
    if err or not isinstance(manifest, dict):
        return False
    if str(manifest.get("harness_spec") or "").strip().lower() not in TRUTHY:
        return False
    return parse_semver(load_run_manifest_version(session)) is None


def _vm(session: Path) -> dict[str, Any] | None:
    data, err = load_json(session / VM_REL)
    if err or not isinstance(data, dict):
        return None
    return data


def _bind(session: Path) -> dict[str, Any] | None:
    data, err = load_json(session / NARRATIVE_REL)
    if err or not isinstance(data, dict):
        return None
    return data


def _sector(session: Path) -> str:
    sc, err = load_json(session / SECTOR_REL)
    if err or not isinstance(sc, dict):
        return ""
    return str(sc.get("primary_sector") or "").strip().lower()


def _story_phase(session: Path) -> bool:
    return session_since(session, STORY_PHASE_SINCE)


def _identity(session: Path) -> dict[str, Any]:
    """Playbook / stage / buyer / contest home: classification on >= 3.4.0."""
    if _story_phase(session):
        card, err = load_classification(session)
        if err or not isinstance(card, dict):
            return {}
        return card
    return _bind(session) or {}


def _playbook(session: Path) -> str:
    return str(_identity(session).get("iv_playbook") or "").strip().lower()


def _norm(s: str) -> str:
    out = []
    prev_us = False
    for ch in s.lower():
        if ch.isalnum():
            out.append(ch)
            prev_us = False
        else:
            if not prev_us:
                out.append("_")
            prev_us = True
    return "".join(out).strip("_")


def _short(value: object, n: int) -> bool:
    """True when a required rationale/string is missing or too short."""
    return not (isinstance(value, str) and len(value.strip()) >= n)


def _as_float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _overlays(session: Path) -> set[str]:
    data = _identity(session)
    raw = data.get("overlays")
    if not isinstance(raw, list):
        return set()
    return {_norm(str(x)) for x in raw if str(x).strip()}


def _model_input_names(vm: dict[str, Any]) -> set[str]:
    """Names a story sentence may bind to: real inputs present in the model."""
    names: set[str] = set()

    def absorb(obj: object) -> None:
        if isinstance(obj, dict):
            for key, val in obj.items():
                norm = _norm(str(key))
                if norm:
                    names.add(norm)
                absorb(val)

    for key in (
        "assumptions",
        "wacc_buildup",
        "terminal_consistency",
        "roic_identity",
        "street_bind",
    ):
        absorb(vm.get(key))
    fcst = vm.get("explicit_forecast")
    if isinstance(fcst, dict):
        absorb(fcst.get("base") if isinstance(fcst.get("base"), dict) else fcst)
    return names


def check_damodaran_v3(session: Path) -> list[tuple[str, str, str]]:
    """Bundle of v3 identities when a valuation_model exists.

    A valuation model in a v3-spec session whose version stamp is missing or
    unparseable is a FAIL (the whole layer would otherwise be skippable by
    omitting one field). Legacy/slim (non-v3) sessions still SKIP.
    """
    vm = _vm(session)
    if vm is None:
        return []
    if not _v3(session):
        if _unstamped_v3(session):
            return [
                (
                    "FAIL",
                    "damodaran.version_root",
                    "v3 session has a valuation_model but no parseable "
                    "harness_version (root of trust)",
                )
            ]
        return [("SKIPPED", "damodaran.v3", "harness < 3.0.0")]
    out: list[tuple[str, str, str]] = []
    out.extend(_check_narrative_locked(session, vm))
    out.extend(_check_narrative_substance(session, vm))
    out.extend(_check_iv_playbook(session))
    out.extend(_check_story_input_bind(session, vm))
    out.extend(_check_bank_engine(session, vm))
    out.extend(_check_reit_engine(session, vm))
    out.extend(_check_growth_triad(vm))
    out.extend(_check_tv_method(session, vm))
    out.extend(_check_price_as_value(session, vm))
    out.extend(_check_p_fail_double_count(vm))
    out.extend(_check_ledgers_not_averaged(vm))
    out.extend(_check_truncation_writes_base(session, vm))
    out.extend(_check_possible_in_base(session, vm))
    out.extend(_check_lifecycle_stage(session))
    out.extend(_check_buyer_identity(session))
    out.extend(_check_market_contest(session))
    out.extend(_check_option_screens(session, vm))
    out.extend(_check_truncation_assessed(session, vm))
    out.extend(_check_market_neutral(session, vm))
    out.extend(_check_per_share_bridge(session, vm))
    return out


def _check_narrative_locked(
    session: Path, vm: dict[str, Any]
) -> list[tuple[str, str, str]]:
    data, err = load_json(session / NARRATIVE_REL)
    if err or not isinstance(data, dict):
        return [
            (
                "FAIL",
                "damodaran.narrative_locked",
                "harness ≥ 3.0.0 requires registry/narrative_bind.json before valuation",
            )
        ]
    if _story_phase(session):
        review, rerr = load_json(session / NARRATIVE_3P_REL)
        if rerr or not isinstance(review, dict):
            return [
                (
                    "FAIL",
                    "damodaran.narrative_locked",
                    "harness ≥ 3.4.0 lock is narrative_3p.verdict=PASS",
                )
            ]
        verdict = str(review.get("verdict") or "").strip().upper()
        if verdict != "PASS":
            return [
                (
                    "FAIL",
                    "damodaran.narrative_locked",
                    f"narrative_3p.verdict={verdict!r} must be PASS",
                )
            ]
        return [("PASS", "damodaran.narrative_locked", "3P PASS")]
    status = str(data.get("status") or "").strip().lower()
    if status != "locked":
        return [
            (
                "FAIL",
                "damodaran.narrative_locked",
                f"narrative_bind.status={status!r} must be locked",
            )
        ]
    return [("PASS", "damodaran.narrative_locked", "locked")]


def _check_narrative_substance(
    session: Path, vm: dict[str, Any]
) -> list[tuple[str, str, str]]:
    """≥ 3.2.0: the bind must carry a story, a story→input map, and 3P buckets.

    Closes the gap where a blank {ticker, status:"locked"} satisfied the
    Narrative-and-Numbers completeness test ("stories without numbers are fairy
    tales; numbers without stories are just modelling").
    """
    if not session_since(session, NARRATIVE_SUBSTANCE_SINCE):
        return []
    data = _bind(session)
    if data is None:
        return []  # _check_narrative_locked already FAILs a missing bind

    out: list[tuple[str, str, str]] = []
    story = data.get("story") if isinstance(data.get("story"), dict) else {}
    paragraph = str(story.get("paragraph") or "").strip()
    if len(paragraph) < 20:
        out.append(
            (
                "FAIL",
                "damodaran.narrative_story",
                "narrative_bind.story.paragraph must state the business story (>=20 chars)",
            )
        )

    mapping = data.get("map")
    if not isinstance(mapping, dict) or not mapping:
        out.append(
            (
                "FAIL",
                "damodaran.narrative_map",
                "narrative_bind.map must bind story sentences to named value inputs",
            )
        )
    elif session_since(session, STORY_PHASE_SINCE):
        bad = [
            str(key)
            for key, val in mapping.items()
            if _norm(str(key)) not in STORY_CARRIERS or val in (None, "", [], {})
        ]
        if bad:
            out.append(
                (
                    "FAIL",
                    "damodaran.narrative_map",
                    f"map keys must be story carriers: {bad[:5]}",
                )
            )
        elif len(mapping) < 3:
            out.append(
                (
                    "FAIL",
                    "damodaran.narrative_map",
                    "map must name at least 3 story carriers",
                )
            )
    else:
        known = _model_input_names(vm)
        unbound: list[str] = []
        for key, val in mapping.items():
            name = _norm(str(key))
            if not name or val in (None, "", [], {}):
                unbound.append(str(key))
                continue
            if not any(name in known_name or known_name in name for known_name in known):
                unbound.append(str(key))
        if unbound:
            out.append(
                (
                    "FAIL",
                    "damodaran.narrative_map",
                    f"map keys do not name a real model input: {unbound[:5]}",
                )
            )

    three = _three_p(session)
    if not isinstance(three, dict):
        out.append(
            (
                "FAIL",
                "damodaran.narrative_3p",
                "3P buckets must be an object with possible/plausible/probable lists",
            )
        )
    else:
        empty = [
            key
            for key in ("possible", "plausible", "probable")
            if not isinstance(three.get(key), list) or not three.get(key)
        ]
        if empty:
            out.append(
                (
                    "FAIL",
                    "damodaran.narrative_3p",
                    f"3p buckets must be non-empty lists: {empty}",
                )
            )

    if not out:
        out.append(
            ("PASS", "damodaran.narrative_substance", "story + map + 3p present")
        )
    return out


def _three_p(session: Path) -> dict[str, Any] | None:
    if _story_phase(session):
        review, err = load_json(session / NARRATIVE_3P_REL)
        if err or not isinstance(review, dict):
            return None
        nested = review.get("3p")
        if isinstance(nested, dict):
            return nested
        return review
    data = _bind(session) or {}
    three = data.get("3p")
    return three if isinstance(three, dict) else None


def _check_story_input_bind(
    session: Path, vm: dict[str, Any]
) -> list[tuple[str, str, str]]:
    """>= 3.4.0: Agent 5 maps story carriers onto real model inputs."""
    if not session_since(session, STORY_PHASE_SINCE):
        return []
    bind = _bind(session)
    if bind is None:
        return []
    mapping = bind.get("map") if isinstance(bind.get("map"), dict) else {}
    if not mapping:
        return []
    sib = vm.get("story_input_bind")
    if not isinstance(sib, dict) or not sib:
        return [
            (
                "FAIL",
                "damodaran.story_input_bind",
                "valuation_model.story_input_bind must map each story carrier to a model input",
            )
        ]
    known = _model_input_names(vm)
    missing: list[str] = []
    unbound: list[str] = []
    for key in mapping:
        carrier = _norm(str(key))
        target = sib.get(key)
        if target is None:
            target = sib.get(carrier)
        if not target:
            missing.append(carrier)
            continue
        name = _norm(str(target))
        if not any(name in known_name or known_name in name for known_name in known):
            unbound.append(f"{carrier}->{target}")
    if missing or unbound:
        return [
            (
                "FAIL",
                "damodaran.story_input_bind",
                f"unmapped carriers {missing[:5]} unbound targets {unbound[:5]}".strip(),
            )
        ]
    return [("PASS", "damodaran.story_input_bind", f"{len(mapping)} carrier(s)")]


def _allowed_playbooks(session: Path) -> frozenset[str]:
    if _story_phase(session):
        return CLASS_PRIMARY_PLAYBOOKS
    allowed = set(PRIMARY_PLAYBOOKS)
    if _tier1(session):
        allowed |= EXTRA_PRIMARY_PLAYBOOKS
    return frozenset(allowed)


def _check_iv_playbook(session: Path) -> list[tuple[str, str, str]]:
    if not _constitution(session):
        return []
    pb = _playbook(session)
    if not pb:
        return [
            (
                "FAIL",
                "damodaran.iv_playbook",
                "harness ≥ 3.1.0 requires iv_playbook from valuation_router "
                "(classification.json on ≥ 3.4.0)",
            )
        ]
    if pb not in _allowed_playbooks(session):
        return [
            (
                "FAIL",
                "damodaran.iv_playbook",
                f"iv_playbook={pb!r} is not a primary router id",
            )
        ]
    sector = _sector(session)
    expected = SECTOR_PLAYBOOK.get(sector)
    if expected and pb != expected:
        return [
            (
                "FAIL",
                "damodaran.iv_playbook",
                f"primary_sector={sector} requires iv_playbook={expected}, not {pb}",
            )
        ]
    return [("PASS", "damodaran.iv_playbook", pb)]


def _financials_object(session: Path) -> bool:
    if _sector(session) in FINANCIALS:
        return True
    return _playbook(session) == "financial_service"


def _check_bank_engine(
    session: Path, vm: dict[str, Any]
) -> list[tuple[str, str, str]]:
    if not _financials_object(session):
        return []
    wacc = vm.get("wacc_buildup") if isinstance(vm.get("wacc_buildup"), dict) else {}
    if wacc.get("applies") is True:
        return [
            (
                "FAIL",
                "damodaran.bank_engine",
                "financial_service must set wacc_buildup.applies=false (equity at ke)",
            )
        ]
    name = ""
    model = vm.get("model")
    if isinstance(model, dict):
        name = str(model.get("name") or "").strip().lower()
    banned = ("fcff", "ev_ebitda", "wacc_dcf", "firm_dcf")
    if any(b in name.replace(" ", "_") for b in banned):
        return [
            (
                "FAIL",
                "damodaran.bank_engine",
                f"financials model.name={name!r} must not be industrial FCFF/EV",
            )
        ]
    return [("PASS", "damodaran.bank_engine", "equity engine")]


def _check_reit_engine(
    session: Path, vm: dict[str, Any]
) -> list[tuple[str, str, str]]:
    if not _constitution(session):
        return []
    if _sector(session) not in REIT_SECTORS and _playbook(session) != "real_estate":
        return []
    wacc = vm.get("wacc_buildup") if isinstance(vm.get("wacc_buildup"), dict) else {}
    if wacc.get("applies") is False:
        return [
            (
                "FAIL",
                "damodaran.reit_engine",
                "real_estate is after-tax DCF; NAV/AFFO is price — do not skip WACC",
            )
        ]
    model = vm.get("model") if isinstance(vm.get("model"), dict) else {}
    name = _norm(str(model.get("name") or ""))
    if "nav" in name.split("_") or name in {"nav", "affo", "ffo"}:
        return [
            (
                "FAIL",
                "damodaran.reit_engine",
                f"model.name={model.get('name')!r} is price, not REIT value",
            )
        ]
    return [("PASS", "damodaran.reit_engine", "after-tax DCF")]


def _check_growth_triad(vm: dict[str, Any]) -> list[tuple[str, str, str]]:
    tc = vm.get("terminal_consistency")
    if not isinstance(tc, dict):
        return []
    method = str(tc.get("method") or "").strip().lower()
    if method not in {"gordon", "gordon_growth", "stable_growth"}:
        return []
    g = tc.get("g_n")
    if g is None:
        g = vm.get("g") or (vm.get("assumptions") or {}).get("g") if isinstance(vm.get("assumptions"), dict) else None
    rr = tc.get("reinvestment_rate")
    roc = tc.get("roc_n") or tc.get("return_on_capital")
    try:
        gv = float(g) if g is not None else None
        rrv = float(rr) if rr is not None else None
        rocv = float(roc) if roc is not None else None
    except (TypeError, ValueError):
        return [
            (
                "FAIL",
                "damodaran.growth_triad",
                "Gordon TV requires numeric g_n, reinvestment_rate, roc_n",
            )
        ]
    if gv is None or rrv is None or rocv is None:
        return [
            (
                "FAIL",
                "damodaran.growth_triad",
                "Gordon TV requires g_n, reinvestment_rate, roc_n on terminal_consistency",
            )
        ]
    if abs(rocv) < 1e-8:
        return [("FAIL", "damodaran.growth_triad", "roc_n is zero")]
    implied = rrv * rocv
    if abs(implied - gv) > 0.005:
        return [
            (
                "FAIL",
                "damodaran.growth_triad",
                f"g_n {gv} != RR×ROC {implied}",
            )
        ]
    rf = None
    wacc_b = vm.get("wacc_buildup") if isinstance(vm.get("wacc_buildup"), dict) else {}
    rf = wacc_b.get("rf") or wacc_b.get("risk_free")
    if rf is not None:
        try:
            if gv > float(rf) + 1e-9:
                return [
                    (
                        "FAIL",
                        "damodaran.g_vs_rf",
                        f"g_n {gv} > session rf {rf}",
                    )
                ]
        except (TypeError, ValueError):
            pass
    spread = tc.get("wacc_minus_g") or tc.get("ke_minus_g")
    if spread is not None:
        try:
            if float(spread) <= 0:
                return [
                    (
                        "FAIL",
                        "damodaran.gordon_spread",
                        "wacc_minus_g / ke_minus_g must be > 0",
                    )
                ]
        except (TypeError, ValueError):
            pass
    return [("PASS", "damodaran.growth_triad", "RR×ROC matches g_n")]


def _check_tv_method(session: Path, vm: dict[str, Any]) -> list[tuple[str, str, str]]:
    tc = vm.get("terminal_consistency")
    if not isinstance(tc, dict):
        if _constitution(session):
            return [
                (
                    "FAIL",
                    "damodaran.tv_method",
                    "harness ≥ 3.1.0 requires terminal_consistency (Gordon/liquidation/excess_return)",
                )
            ]
        return []
    method = str(tc.get("method") or "").strip().lower()
    norm = _norm(method)
    tokens = set(norm.split("_"))
    if tokens & set(PRICE_TV_NEEDLES):
        return [
            (
                "FAIL",
                "damodaran.tv_method",
                "exit multiple / ARR / NAV is price, not intrinsic TV",
            )
        ]
    if _constitution(session) and norm not in LEGAL_TV:
        return [
            (
                "FAIL",
                "damodaran.tv_method",
                f"terminal method {method!r} must be Gordon, liquidation, or excess_return",
            )
        ]
    if _constitution(session):
        return [("PASS", "damodaran.tv_method", norm)]
    return []


def _check_price_as_value(session: Path, vm: dict[str, Any]) -> list[tuple[str, str, str]]:
    if not _constitution(session):
        return []
    model = vm.get("model") if isinstance(vm.get("model"), dict) else {}
    name = _norm(str(model.get("name") or ""))
    for needle in PRICE_MODEL_NEEDLES:
        if needle in name:
            return [
                (
                    "FAIL",
                    "damodaran.price_as_value",
                    f"model.name={model.get('name')!r} is a pricing metric; fair_value.base must be DCF",
                )
            ]
    pricing = vm.get("pricing")
    if isinstance(pricing, dict):
        raw_used = str(pricing.get("used_as") or pricing.get("role") or "").strip()
        if session_since(session, NARRATIVE_SUBSTANCE_SINCE):
            if raw_used and _norm(raw_used) not in PRICING_ROLES:
                return [
                    (
                        "FAIL",
                        "damodaran.price_as_value",
                        f"pricing.used_as={raw_used!r} must be one of "
                        f"{sorted(PRICING_ROLES)} (never the value slot)",
                    )
                ]
        elif raw_used.lower() in {"fair_value", "fair_value.base", "decision", "value"}:
            return [
                (
                    "FAIL",
                    "damodaran.price_as_value",
                    "pricing column must not be used as fair_value.base",
                )
            ]
    return [("PASS", "damodaran.price_as_value", "value slot is not a multiple")]


def _check_p_fail_double_count(vm: dict[str, Any]) -> list[tuple[str, str, str]]:
    trunc = vm.get("truncation") if isinstance(vm.get("truncation"), dict) else {}
    try:
        p = float(trunc.get("p") or 0)
    except (TypeError, ValueError):
        p = 0.0
    if p <= 0:
        return []
    dials = vm.get("conservatism_dials")
    if isinstance(dials, list):
        for d in dials:
            if not isinstance(d, dict):
                continue
            if str(d.get("key") or "") == "wacc_vs_buildup" and str(d.get("applies_in") or "") == "base":
                return [
                    (
                        "FAIL",
                        "damodaran.p_fail_double_count",
                        "p_fail>0 cannot also pad WACC in base",
                    )
                ]
    return [("PASS", "damodaran.p_fail_double_count", "truncation not in WACC")]


def _check_ledgers_not_averaged(vm: dict[str, Any]) -> list[tuple[str, str, str]]:
    rec = vm.get("multi_method_reconciliation")
    if not isinstance(rec, dict):
        return []
    why = str(rec.get("why_primary_wins") or rec.get("rationale") or "").lower()
    if "average" in why and ("dcf" in why or "multiple" in why or "sotp" in why):
        return [
            (
                "FAIL",
                "damodaran.ledgers_not_averaged",
                "do not average DCF and a multiple into fair_value.base",
            )
        ]
    if any(w in why for w in BLEND_WORDS) and ("dcf" in why or "multiple" in why or "nav" in why):
        return [
            (
                "FAIL",
                "damodaran.ledgers_not_averaged",
                "do not blend DCF and a pricing multiple into fair_value.base",
            )
        ]
    return []


def _check_truncation_writes_base(
    session: Path, vm: dict[str, Any]
) -> list[tuple[str, str, str]]:
    """A truncation block with p>0 must write the probability-weighted base.

    ≥ 3.2.0 derives this from p — no writer-declared `material` flag can skip
    the overlay. Before 3.2.0 the check stays keyed on `material: true` so
    historical sessions are judged by the law they were run under.
    """
    trunc = vm.get("truncation") if isinstance(vm.get("truncation"), dict) else {}
    strict = session_since(session, NARRATIVE_SUBSTANCE_SINCE)
    if not strict and trunc.get("material") is not True:
        return []
    raw_p = trunc.get("p")
    if strict and raw_p not in (None, ""):
        try:
            p = float(raw_p)
        except (TypeError, ValueError):
            return [
                (
                    "FAIL",
                    "damodaran.truncation_base",
                    "truncation.p must be numeric",
                )
            ]
    else:
        try:
            p = float(raw_p or 0)
        except (TypeError, ValueError):
            p = 0.0
    if strict and p <= 0:
        return []
    try:
        gc = float(trunc.get("going_concern_upper_bound") or trunc.get("gc") or 0)
        fail = float(trunc.get("failure_payoff") or 0)
        expected = (1 - p) * gc + p * fail
    except (TypeError, ValueError):
        return [
            (
                "FAIL",
                "damodaran.truncation_base",
                "truncation with p>0 requires p, going_concern_upper_bound, failure_payoff",
            )
        ]
    fv = vm.get("fair_value") if isinstance(vm.get("fair_value"), dict) else {}
    try:
        base = float(fv.get("base"))
    except (TypeError, ValueError):
        return [("FAIL", "damodaran.truncation_base", "fair_value.base missing")]
    if abs(base - expected) > max(0.01, 0.005 * abs(expected)):
        return [
            (
                "FAIL",
                "damodaran.truncation_base",
                f"fair_value.base {base} != (1-p)×GC + p×fail {expected}",
            )
        ]
    return [("PASS", "damodaran.truncation_base", "base is truncated value")]


def _check_possible_in_base(
    session: Path, vm: dict[str, Any]
) -> list[tuple[str, str, str]]:
    three = _three_p(session) or {}
    possible = three.get("possible")
    if not isinstance(possible, list):
        if session_since(session, NARRATIVE_SUBSTANCE_SINCE) and three:
            return [
                (
                    "FAIL",
                    "damodaran.possible_in_base",
                    "3P possible must be a list",
                )
            ]
        return []
    fcst = vm.get("explicit_forecast") if isinstance(vm.get("explicit_forecast"), dict) else {}
    revs = fcst.get("base") if isinstance(fcst.get("base"), dict) else fcst
    rev_path = revs.get("revenue") if isinstance(revs, dict) else None
    if not isinstance(rev_path, list):
        return []
    for strand in possible:
        if not isinstance(strand, dict):
            continue
        if strand.get("revenue_in_dcf") not in (0, 0.0, None, False):
            return [
                (
                    "FAIL",
                    "damodaran.possible_in_base",
                    "3P possible strands must have revenue_in_dcf=0",
                )
            ]
    return []


def _check_lifecycle_stage(session: Path) -> list[tuple[str, str, str]]:
    """>= 3.3.0: name the life-cycle stage and why the story fits it.

    ref: knowledge-hub-narrative 00-router.md (wrong-stage veto) and
    knowledge-hub-dark-side SYNTHESIS.md section 3 (life-cycle matrix).
    """
    if not _tier1(session):
        return []
    ident = _identity(session)
    bind = _bind(session)
    if not ident and bind is None:
        return []
    out: list[tuple[str, str, str]] = []
    stages = CLASS_LIFE_CYCLE_STAGES if _story_phase(session) else LIFE_CYCLE_STAGES
    leads = CLASS_WHO_LEADS if _story_phase(session) else WHO_LEADS
    stage = _norm(str(ident.get("life_cycle_stage") or ""))
    if stage not in stages:
        out.append(
            (
                "FAIL",
                "damodaran.life_cycle_stage",
                f"life_cycle_stage={stage or None!r} must be one of {sorted(stages)}",
            )
        )
    who = _norm(str(ident.get("who_leads") or ""))
    if who not in leads:
        out.append(
            (
                "FAIL",
                "damodaran.life_cycle_stage",
                f"who_leads={who or None!r} must be {'|'.join(sorted(leads))}",
            )
        )
    fit_src = bind if _story_phase(session) else ident
    if fit_src is None or _short(fit_src.get("stage_fit"), 40):
        out.append(
            (
                "FAIL",
                "damodaran.stage_fit",
                "stage_fit must say why the story matches the life-cycle stage (>=40 chars)",
            )
        )
    if not out:
        out.append(("PASS", "damodaran.life_cycle_stage", stage))
    return out


def _check_buyer_identity(session: Path) -> list[tuple[str, str, str]]:
    """>= 3.3.0: public vs private marginal buyer (ref 00-router.md q.3).

    A private/undiversified buyer gets total beta and an illiquidity treatment;
    a diversified public buyer gets neither.
    """
    if not _tier1(session):
        return []
    ident = _identity(session)
    if not ident:
        return []
    buyer = ident.get("buyer") if isinstance(ident.get("buyer"), dict) else None
    if buyer is None:
        home = "classification.buyer" if _story_phase(session) else "narrative_bind.buyer"
        return [
            (
                "FAIL",
                "damodaran.buyer_identity",
                f"harness >= 3.3.0 requires {home} {{class, rationale}}",
            )
        ]
    out: list[tuple[str, str, str]] = []
    klass = _norm(str(buyer.get("class") or ""))
    classes = CLASS_BUYER_CLASSES if _story_phase(session) else BUYER_CLASSES
    if klass not in classes:
        out.append(
            (
                "FAIL",
                "damodaran.buyer_identity",
                f"buyer.class={klass or None!r} must be one of {sorted(classes)}",
            )
        )
    if _short(buyer.get("rationale"), 20):
        out.append(
            (
                "FAIL",
                "damodaran.buyer_identity",
                "buyer.rationale must name the marginal buyer (>=20 chars)",
            )
        )
    dials = buyer
    if _story_phase(session):
        vm = _vm(session) or {}
        model_dials = vm.get("buyer_dials")
        dials = model_dials if isinstance(model_dials, dict) else {}
    if klass == "private_undiversified":
        if dials.get("total_beta") is not True:
            out.append(
                (
                    "FAIL",
                    "damodaran.buyer_identity",
                    "private_undiversified requires total_beta=true"
                    + (" on valuation_model.buyer_dials" if _story_phase(session) else ""),
                )
            )
        ill = _as_float(dials.get("illiquidity_discount"))
        if ill is None or ill <= 0:
            out.append(
                (
                    "FAIL",
                    "damodaran.buyer_identity",
                    "private_undiversified requires numeric illiquidity_discount > 0"
                    + (" on valuation_model.buyer_dials" if _story_phase(session) else ""),
                )
            )
    if klass in {"public_diversified", "ipo_or_public_buyer"}:
        ill = _as_float(dials.get("illiquidity_discount"))
        if ill is None or abs(ill) > 1e-9:
            out.append(
                (
                    "FAIL",
                    "damodaran.buyer_identity",
                    "a diversified public buyer must state numeric illiquidity_discount = 0"
                    + (" on valuation_model.buyer_dials" if _story_phase(session) else ""),
                )
            )
    if klass == "vc_pe" and _short(dials.get("ke_stepdown"), 20):
        out.append(
            (
                "FAIL",
                "damodaran.buyer_identity",
                "vc_pe requires ke_stepdown (>=20 chars)"
                + (" on valuation_model.buyer_dials" if _story_phase(session) else ""),
            )
        )
    if not out:
        out.append(("PASS", "damodaran.buyer_identity", klass))
    return out


def _check_market_contest(session: Path) -> list[tuple[str, str, str]]:
    """>= 3.3.0: write which market inputs are accepted and which are contested.

    ref: dark-side 01-jedi.md proposition 2 (accept rf/ERP/weights; contest
    company cash flows).
    """
    if not _tier1(session):
        return []
    ident = _identity(session)
    if not ident:
        return []
    mc = ident.get("market_contest") if isinstance(ident.get("market_contest"), dict) else None
    if mc is None:
        home = "classification.market_contest" if _story_phase(session) else "narrative_bind.market_contest"
        return [
            (
                "FAIL",
                "damodaran.market_contest",
                f"harness >= 3.3.0 requires {home} (accept vs contest)",
            )
        ]
    out: list[tuple[str, str, str]] = []
    accept = mc.get("accept")
    contest = mc.get("contest")
    if not (isinstance(accept, list) and accept):
        out.append(("FAIL", "damodaran.market_contest", "market_contest.accept must be non-empty"))
    if not (isinstance(contest, list) and contest):
        out.append(("FAIL", "damodaran.market_contest", "market_contest.contest must be non-empty"))
    if isinstance(contest, list) and contest:
        blob = " ".join(str(x) for x in contest).lower()
        if not any(tok in blob for tok in ("cash", "earning", "margin", "cost", "production")):
            out.append(
                (
                    "FAIL",
                    "damodaran.market_contest",
                    "market_contest.contest must name company cash flow / earnings / margins",
                )
            )
    if _short(mc.get("rationale"), 20):
        out.append(
            ("FAIL", "damodaran.market_contest", "market_contest.rationale (>=20 chars) required")
        )
    if not out:
        out.append(("PASS", "damodaran.market_contest", "accept/contest declared"))
    return out


def _check_option_screens(
    session: Path, vm: dict[str, Any]
) -> list[tuple[str, str, str]]:
    """>= 3.3.0: option-like assets need exclusivity screens; a liquidation call
    replaces DCF equity (never added on top). ref: IV 02-engines.md, ch30.
    """
    if not _tier1(session):
        return []
    data = _bind(session)
    if data is None:
        return []
    overlays = _overlays(session)
    pb = _playbook(session)
    out: list[tuple[str, str, str]] = []
    if pb == OPTION_PLAYBOOK or "real_options" in overlays:
        screens = data.get("option_screens") if isinstance(data.get("option_screens"), dict) else None
        if screens is None:
            out.append(
                (
                    "FAIL",
                    "damodaran.option_screens",
                    "option-like asset requires option_screens {exclusivity, materiality, no_double_count}",
                )
            )
        else:
            for key in ("exclusivity", "materiality", "no_double_count"):
                if screens.get(key) is not True:
                    out.append(
                        ("FAIL", "damodaran.option_screens", f"option_screens.{key} must be true")
                    )
            if _short(screens.get("rationale"), 40):
                out.append(
                    (
                        "FAIL",
                        "damodaran.option_screens",
                        "option_screens.rationale (>=40 chars) required",
                    )
                )
    if "distressed_call" in overlays:
        dc = data.get("distressed_call") if isinstance(data.get("distressed_call"), dict) else None
        if dc is None:
            out.append(
                (
                    "FAIL",
                    "damodaran.distressed_call",
                    "distressed_call overlay requires narrative_bind.distressed_call",
                )
            )
        else:
            if dc.get("dcf_equity_near_zero") is not True:
                out.append(
                    (
                        "FAIL",
                        "damodaran.distressed_call",
                        "distressed_call.dcf_equity_near_zero must be true",
                    )
                )
            if dc.get("replaces_dcf_equity") is not True:
                out.append(
                    (
                        "FAIL",
                        "damodaran.distressed_call",
                        "the liquidation call REPLACES DCF equity; it is never added on top",
                    )
                )
        model = vm.get("model") if isinstance(vm.get("model"), dict) else {}
        name = _norm(str(model.get("name") or ""))
        if "call" not in name and "option" not in name:
            out.append(
                (
                    "FAIL",
                    "damodaran.distressed_call",
                    f"distressed_call requires an option/call model, got {model.get('name')!r}",
                )
            )
    if not out:
        out.append(("PASS", "damodaran.option_screens", "screens satisfied"))
    return out


def _check_truncation_assessed(
    session: Path, vm: dict[str, Any]
) -> list[tuple[str, str, str]]:
    """>= 3.3.0: failure/truncation must be answered on every name.

    p>0 uses the weighted-base gate; p=0 needs why_not_material.
    ref: dark-side 01-jedi.md proposition 6 (truncation is two-step).
    """
    if not _tier1(session):
        return []
    trunc = vm.get("truncation")
    if not isinstance(trunc, dict):
        return [
            (
                "FAIL",
                "damodaran.truncation_assessed",
                "harness >= 3.3.0 requires a truncation assessment "
                "(p=0 + why_not_material, or p>0 weighted base)",
            )
        ]
    raw = trunc.get("p")
    if raw in (None, ""):
        return [
            (
                "FAIL",
                "damodaran.truncation_assessed",
                "truncation.p must be numeric (0 when not material)",
            )
        ]
    try:
        p = float(raw)
    except (TypeError, ValueError):
        return [
            ("FAIL", "damodaran.truncation_assessed", "truncation.p must be numeric")
        ]
    if p <= 0 and _short(trunc.get("why_not_material"), 40):
        return [
            (
                "FAIL",
                "damodaran.truncation_assessed",
                "p=0 requires why_not_material (>=40 chars)",
            )
        ]
    return [("PASS", "damodaran.truncation_assessed", f"p={p}")]


def _check_market_neutral(
    session: Path, vm: dict[str, Any]
) -> list[tuple[str, str, str]]:
    """>= 3.3.0: market-neutral inputs and a currency match on the discount rate.

    ref: IV 02-engines.md (implied ERP, bottom-up beta) and checks
    consistency-triads section B.
    """
    if not _tier1(session):
        return []
    wacc = vm.get("wacc_buildup") if isinstance(vm.get("wacc_buildup"), dict) else {}
    if wacc.get("applies") is not True:
        return []
    out: list[tuple[str, str, str]] = []
    erp = _norm(str(wacc.get("erp_method") or ""))
    if erp not in ERP_METHODS:
        out.append(
            (
                "FAIL",
                "damodaran.erp_method",
                f"wacc_buildup.erp_method={erp or None!r} must be implied|historical|bottom_up|not_applicable",
            )
        )
    elif erp == "not_applicable":
        out.append(
            (
                "FAIL",
                "damodaran.erp_method",
                "erp_method=not_applicable is illegal when wacc_buildup.applies=true; "
                "pick implied, or use historical with erp_reject_implied_reason",
            )
        )
    elif erp == "historical" and _short(wacc.get("erp_reject_implied_reason"), 40):
        out.append(
            (
                "FAIL",
                "damodaran.erp_method",
                "historical ERP requires erp_reject_implied_reason (>=40 chars): why implied was rejected",
            )
        )
    beta = _norm(str(wacc.get("beta_method") or ""))
    if beta not in BETA_METHODS:
        out.append(
            (
                "FAIL",
                "damodaran.beta_method",
                f"wacc_buildup.beta_method={beta or None!r} must be bottom_up|regression|peer|fixed",
            )
        )
    elif beta == "not_applicable":
        out.append(
            (
                "FAIL",
                "damodaran.beta_method",
                "beta_method=not_applicable is illegal when wacc_buildup.applies=true; "
                "use bottom_up or give a beta_reason",
            )
        )
    elif beta != "bottom_up" and _short(wacc.get("beta_reason"), 40):
        out.append(
            (
                "FAIL",
                "damodaran.beta_method",
                "non-bottom-up beta requires beta_reason (>=40 chars)",
            )
        )
    dccy = str(wacc.get("discount_currency") or "").strip().upper()
    cccy = str(wacc.get("cash_flow_currency") or "").strip().upper()
    if not dccy or not cccy:
        out.append(
            (
                "FAIL",
                "damodaran.currency_match",
                "wacc_buildup requires discount_currency and cash_flow_currency",
            )
        )
    elif dccy != cccy and _short(wacc.get("fx_policy"), 20):
        out.append(
            (
                "FAIL",
                "damodaran.currency_match",
                "discount and cash-flow currencies differ; declare fx_policy (>=20 chars)",
            )
        )
    if not out:
        out.append(("PASS", "damodaran.market_neutral", f"erp={erp} beta={beta} ccy={dccy}"))
    return out


def _check_per_share_bridge(
    session: Path, vm: dict[str, Any]
) -> list[tuple[str, str, str]]:
    """>= 3.3.0: enterprise-to-equity per-share bridge.

    ref: IV inputs/per-share-bridge.md (cash at face, debt subtracted,
    options via OPM). Financials and option primaries are exempt.
    """
    if not _tier1(session):
        return []
    if _financials_object(session) or _playbook(session) == OPTION_PLAYBOOK:
        return []
    bridge = vm.get("per_share_bridge")
    if isinstance(bridge, dict) and bridge.get("applies") is False:
        if _short(bridge.get("not_applicable_reason"), 40):
            return [
                (
                    "FAIL",
                    "damodaran.per_share_bridge",
                    "per_share_bridge.applies=false needs not_applicable_reason (>=40 chars)",
                )
            ]
        return [("PASS", "damodaran.per_share_bridge", "not applicable")]
    if not isinstance(bridge, dict):
        return [
            (
                "FAIL",
                "damodaran.per_share_bridge",
                "harness >= 3.3.0 requires per_share_bridge "
                "(cash, debt, options, shares_used, rationale)",
            )
        ]
    out: list[tuple[str, str, str]] = []
    try:
        shares = float(bridge.get("shares_used"))
        if shares <= 0:
            raise ValueError
    except (TypeError, ValueError):
        out.append(
            ("FAIL", "damodaran.per_share_bridge", "per_share_bridge.shares_used must be > 0")
        )
    for key in ("net_debt_subtracted", "cash_added"):
        if key not in bridge:
            out.append(
                ("FAIL", "damodaran.per_share_bridge", f"per_share_bridge.{key} required (0 allowed)")
            )
    if _short(bridge.get("rationale"), 20):
        out.append(
            ("FAIL", "damodaran.per_share_bridge", "per_share_bridge.rationale (>=20 chars) required")
        )
    if not out:
        out.append(("PASS", "damodaran.per_share_bridge", "bridge present"))
    return out

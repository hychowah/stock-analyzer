"""Engine classification card (harness >= 3.4.0).

The orchestrator writes registry/classification.json after library bind and
KPI sector/region files, before Phase 0. This is the identity of the run:
job, life-cycle, one iv_playbook, overlays, buyer, market-contest map.

sector_config.json remains the KPI library. It does not choose the engine.
On harness >= 3.4.0 this card is the only identity. narrative_bind does not copy it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.kd_research.check_core import load_json, session_since

CLASSIFICATION_REL = "registry/classification.json"
CLASSIFICATION_SINCE = (3, 4, 0)

JOBS = frozenset({"first_valuation", "news", "restory", "pricing_only"})
LIFE_CYCLE_STAGES = frozenset(
    {"idea", "young_growth", "scaling_growth", "mature", "decline", "not_applicable"}
)
WHO_LEADS = frozenset({"story", "numbers", "not_applicable"})
PRIMARY_PLAYBOOKS = frozenset(
    {
        "mature_operating",
        "financial_service",
        "real_estate",
        "young_startup",
        "contingent_claim",
        "asset_based",
    }
)
BUYER_CLASSES = frozenset(
    {
        "public_diversified",
        "private_undiversified",
        "ipo_or_public_buyer",
        "vc_pe",
        "not_applicable",
    }
)
CLAIMS = frozenset(
    {"equity_dcf", "firm_dcf", "apv", "option", "pricing_only", "asset_based"}
)
# Object-level KPI sector still has to match these playbooks (a bank is a bank).
SECTOR_PLAYBOOK = {
    "banking": "financial_service",
    "insurance": "financial_service",
    "reit": "real_estate",
}


def classification_path(session: Path) -> Path:
    return session / CLASSIFICATION_REL


def session_enforces_classification(session: Path) -> bool:
    """True when new sessions must stamp the engine card."""
    if classification_path(session).is_file():
        return True
    return session_since(session, CLASSIFICATION_SINCE)


def load_classification(session: Path) -> tuple[dict[str, Any] | None, str | None]:
    data, err = load_json(classification_path(session))
    if err:
        if err == "missing":
            return None, f"missing {CLASSIFICATION_REL}"
        return None, err
    if not isinstance(data, dict):
        return None, "not an object"
    return data, None


def _short(value: object, n: int) -> bool:
    return not (isinstance(value, str) and len(value.strip()) >= n)


def _norm(value: object) -> str:
    return str(value or "").strip().lower()


def check_classification_card(session: Path) -> list[tuple[str, str, str]]:
    """Phase 0 / 1e entry: the engine card exists and is internally legal."""
    if not session_enforces_classification(session):
        return [
            (
                "SKIPPED",
                "classification",
                "legacy/slim (no classification.json; harness_version < 3.4.0)",
            )
        ]
    data, err = load_classification(session)
    if err or data is None:
        return [("FAIL", "classification", err or "missing")]

    out: list[tuple[str, str, str]] = []
    job = _norm(data.get("job"))
    if job not in JOBS:
        out.append(
            (
                "FAIL",
                "classification.job",
                f"job={job or None!r} must be one of {sorted(JOBS)}",
            )
        )
    stage = _norm(data.get("life_cycle_stage"))
    if stage not in LIFE_CYCLE_STAGES:
        out.append(
            (
                "FAIL",
                "classification.life_cycle_stage",
                f"life_cycle_stage={stage or None!r} must be a router stage",
            )
        )
    who = _norm(data.get("who_leads"))
    if who not in WHO_LEADS:
        out.append(
            (
                "FAIL",
                "classification.who_leads",
                f"who_leads={who or None!r} must be story|numbers|not_applicable",
            )
        )
    if _short(data.get("stage_rationale"), 40):
        out.append(
            (
                "FAIL",
                "classification.stage_rationale",
                "stage_rationale must say why this life-cycle stage (>=40 chars)",
            )
        )
    pb = _norm(data.get("iv_playbook"))
    if pb not in PRIMARY_PLAYBOOKS:
        out.append(
            (
                "FAIL",
                "classification.iv_playbook",
                f"iv_playbook={pb or None!r} is not a valuation_router primary id",
            )
        )
    overlays = data.get("overlays")
    if overlays is None:
        out.append(("FAIL", "classification.overlays", "overlays[] required (empty list OK)"))
    elif not isinstance(overlays, list):
        out.append(("FAIL", "classification.overlays", "overlays must be an array"))
    buyer = data.get("buyer") if isinstance(data.get("buyer"), dict) else None
    if buyer is None:
        out.append(("FAIL", "classification.buyer", "buyer {class, rationale} required"))
    else:
        klass = _norm(buyer.get("class"))
        if klass not in BUYER_CLASSES:
            out.append(
                (
                    "FAIL",
                    "classification.buyer",
                    f"buyer.class={klass or None!r} is not a legal buyer class",
                )
            )
        if _short(buyer.get("rationale"), 20):
            out.append(
                (
                    "FAIL",
                    "classification.buyer",
                    "buyer.rationale must be >=20 chars",
                )
            )
    contest = (
        data.get("market_contest")
        if isinstance(data.get("market_contest"), dict)
        else None
    )
    if contest is None:
        out.append(
            (
                "FAIL",
                "classification.market_contest",
                "market_contest {accept, contest, rationale} required",
            )
        )
    else:
        accept = contest.get("accept")
        fight = contest.get("contest")
        if not isinstance(accept, list) or not accept:
            out.append(
                (
                    "FAIL",
                    "classification.market_contest",
                    "market_contest.accept must be a non-empty list",
                )
            )
        if not isinstance(fight, list) or not fight:
            out.append(
                (
                    "FAIL",
                    "classification.market_contest",
                    "market_contest.contest must name company cash flows/margins",
                )
            )
        if _short(contest.get("rationale"), 20):
            out.append(
                (
                    "FAIL",
                    "classification.market_contest",
                    "market_contest.rationale must be >=20 chars",
                )
            )
    claim = _norm(data.get("claim"))
    if claim not in CLAIMS:
        out.append(
            (
                "FAIL",
                "classification.claim",
                f"claim={claim or None!r} must be one of {sorted(CLAIMS)}",
            )
        )
    if _short(data.get("engine_rationale"), 40):
        out.append(
            (
                "FAIL",
                "classification.engine_rationale",
                "engine_rationale must cite the router row (>=40 chars)",
            )
        )

    sector_path = session / "registry" / "sector_config.json"
    sc, sc_err = load_json(sector_path)
    if not sc_err and isinstance(sc, dict) and pb in PRIMARY_PLAYBOOKS:
        sector = _norm(sc.get("primary_sector"))
        expected = SECTOR_PLAYBOOK.get(sector)
        if expected and pb != expected:
            out.append(
                (
                    "FAIL",
                    "classification.sector_playbook",
                    f"primary_sector={sector} requires iv_playbook={expected}, not {pb}",
                )
            )

    if not out:
        out.append(("PASS", "classification", f"{job}/{pb}"))
    return out

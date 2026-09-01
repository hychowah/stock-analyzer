"""Harness >= 2.31.0: paid gather must be consumed, not re-researched."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from packages.kd_research.annuals import load_run_manifest_version, parse_semver
from packages.kd_research.gates import load_json

CONSUME_SINCE = (2, 31, 0)
MATERIAL_FDD_KEYS = (
    "sbc_unrecognized",
    "contingencies_legal",
    "related_party_dual_class",
    "debt_leases",
)


def session_is_consume_runtime(session: Path) -> bool:
    parsed = parse_semver(load_run_manifest_version(session))
    if parsed is None:
        return False
    return parsed >= CONSUME_SINCE


def _item_status(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("status") or "").strip().lower()
    return ""


def _material_fdd_keys(fdd: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    footnotes = fdd.get("footnotes") if isinstance(fdd.get("footnotes"), dict) else {}
    items = footnotes.get("items")
    if isinstance(items, dict):
        for key in MATERIAL_FDD_KEYS:
            if _item_status(items.get(key)) == "extracted":
                keys.append(key)
    elif isinstance(items, list):
        for it in items:
            if not isinstance(it, dict):
                continue
            name = str(it.get("id") or it.get("key") or it.get("name") or "").strip()
            if name in MATERIAL_FDD_KEYS and _item_status(it) == "extracted":
                keys.append(name)
    score = fdd.get("management_scorecard")
    if isinstance(score, dict):
        rows = score.get("items") or score.get("promises") or score.get("rows")
        if isinstance(rows, list) and any(isinstance(r, dict) for r in rows):
            keys.append("management_scorecard")
    return keys


def check_fdd_material_hooks(session: Path) -> list[tuple[str, str, str]]:
    if not session_is_consume_runtime(session):
        return [("SKIPPED", "fdd_material_hooks", "harness_version < 2.31.0")]
    fdd, err = load_json(session / "registry" / "filing_deep_dive.json")
    if err or not isinstance(fdd, dict):
        return [("SKIPPED", "fdd_material_hooks", "filing_deep_dive.json missing")]
    vm, verr = load_json(session / "data" / "valuation_model.json")
    if verr or not isinstance(vm, dict):
        return [("SKIPPED", "fdd_material_hooks", "valuation_model.json missing")]
    needed = _material_fdd_keys(fdd)
    if not needed:
        return [("PASS", "fdd_material_hooks", "no extracted material FDD items")]
    hooks = vm.get("filing_deep_dive_hooks")
    if not isinstance(hooks, list):
        return [
            (
                "FAIL",
                "fdd_material_hooks",
                f"extracted {needed} need non-noted_only filing_deep_dive_hooks",
            )
        ]
    missing: list[str] = []
    for key in needed:
        hit = False
        for h in hooks:
            if not isinstance(h, dict):
                continue
            src = str(h.get("from") or "").lower()
            action = str(h.get("action") or "").strip().lower()
            if key.replace("_", "") in src.replace("_", "") or key in src:
                if action and action != "noted_only":
                    hit = True
                    break
        if not hit:
            missing.append(key)
    if missing:
        return [
            (
                "FAIL",
                "fdd_material_hooks",
                "extracted FDD items need use-or-reject hooks (not noted_only): "
                + ", ".join(missing),
            )
        ]
    return [("PASS", "fdd_material_hooks", f"consumed {needed}")]


def check_2d_street_cite(session: Path) -> list[tuple[str, str, str]]:
    if not session_is_consume_runtime(session):
        return [("SKIPPED", "lq_street_cite", "harness_version < 2.31.0")]
    street, serr = load_json(session / "registry" / "street_estimates.json")
    if serr or not isinstance(street, dict) or street.get("unavailable") is True:
        return [("SKIPPED", "lq_street_cite", "street_estimates missing/unavailable")]
    lq, lerr = load_json(session / "registry" / "latest_quarter.json")
    if lerr or not isinstance(lq, dict):
        return [("SKIPPED", "lq_street_cite", "latest_quarter.json missing")]
    blob = json.dumps(lq).lower()
    talks_consensus = any(
        n in blob for n in ("consensus", "vs street", "street fy", "beat", "missed consensus")
    )
    if not talks_consensus:
        return [("PASS", "lq_street_cite", "no consensus beat/miss language")]
    if "street_estimates" in blob:
        return [("PASS", "lq_street_cite", "cites street_estimates.json")]
    return [
        (
            "FAIL",
            "lq_street_cite",
            "latest_quarter beat/miss vs consensus must cite registry/street_estimates.json "
            "(do not web-hunt a second Street table)",
        )
    ]


def check_1d_ind_background(session: Path) -> list[tuple[str, str, str]]:
    if not session_is_consume_runtime(session):
        return [("SKIPPED", "1d_ind_background", "harness_version < 2.31.0")]
    path = session / "registry" / "raw" / "oppath_ind.json"
    if not path.is_file():
        return [("SKIPPED", "1d_ind_background", "oppath_ind.json missing")]
    data, err = load_json(path)
    if err or not isinstance(data, dict):
        return [("FAIL", "1d_ind_background", err or "not an object")]
    ids = data.get("background_round_ids")
    gaps = data.get("named_gaps")
    sources = data.get("sources")
    if isinstance(sources, dict):
        if not ids:
            ids = sources.get("background_round_ids")
        if not gaps:
            gaps = sources.get("named_gaps")
    if isinstance(ids, list) and ids:
        return [("PASS", "1d_ind_background", f"{len(ids)} background round id(s)")]
    if isinstance(gaps, list) and gaps:
        return [("PASS", "1d_ind_background", f"{len(gaps)} named_gaps")]
    blob = json.dumps(data).lower()
    if "background.json" in blob or "phase0" in blob:
        return [("PASS", "1d_ind_background", "cited background/phase0 in sources")]
    return [
        (
            "FAIL",
            "1d_ind_background",
            "oppath_ind.json needs background_round_ids or named_gaps "
            "(or a source citing background.json / phase0)",
        )
    ]


def check_stress_legal_dollar(session: Path) -> list[tuple[str, str, str]]:
    if not session_is_consume_runtime(session):
        return [("SKIPPED", "stress_legal_dollar", "harness_version < 2.31.0")]
    rb, err = load_json(session / "registry" / "risk_bridge.json")
    if err or not isinstance(rb, dict):
        return [("SKIPPED", "stress_legal_dollar", "risk_bridge.json missing")]
    st = rb.get("stress_test") if isinstance(rb.get("stress_test"), dict) else {}
    scenarios = st.get("scenarios")
    if not isinstance(scenarios, list):
        return [("PASS", "stress_legal_dollar", "no scenarios")]
    bad: list[str] = []
    for sc in scenarios:
        if not isinstance(sc, dict):
            continue
        blob = json.dumps(sc).lower()
        legalish = any(n in blob for n in ("litig", "lawsuit", "contingen", "legal $", "settlement"))
        dollarish = "$" in blob or "million" in blob or "billion" in blob
        if not (legalish and dollarish):
            continue
        cited = (
            "filing_deep_dive" in blob
            or "contingencies_legal" in blob
            or "unknown" in blob
            or (isinstance(sc.get("deep_dive_refs"), list) and sc.get("deep_dive_refs"))
        )
        if not cited:
            bad.append(str(sc.get("name") or "unnamed"))
    if bad:
        return [
            (
                "FAIL",
                "stress_legal_dollar",
                "legal/contingent dollar claims must cite FDD contingencies_legal "
                f"or set unknown: {bad[:4]}",
            )
        ]
    return [("PASS", "stress_legal_dollar", "no uncited legal dollar claims")]

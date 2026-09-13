"""Consume gather artifacts in later-phase work (hooks, FDD/MC content).

Harness >= 2.31.0: paid gather must be consumed, not re-researched.
FDD/MC hook shape and intensity also live here (any harness that writes those files).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from packages.kd_research.check_core import load_json, session_since, validate_hooks_list

CONSUME_SINCE = (2, 31, 0)
MATERIAL_FDD_KEYS = (
    "sbc_unrecognized",
    "contingencies_legal",
    "related_party_dual_class",
    "debt_leases",
)


def session_is_consume_runtime(session: Path) -> bool:
    return session_since(session, CONSUME_SINCE)


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


def check_filing_deep_dive_hooks(session: Path) -> list[tuple[str, str, str]]:
    """When FDD + valuation exist, require non-empty filing_deep_dive_hooks (F8)."""
    fdd = session / "registry" / "filing_deep_dive.json"
    vm_path = session / "data" / "valuation_model.json"
    if not fdd.exists():
        return [("SKIPPED", "filing_deep_dive_hooks", "filing_deep_dive.json absent")]
    if not vm_path.exists():
        return [("SKIPPED", "filing_deep_dive_hooks", "valuation_model.json missing")]
    data, err = load_json(vm_path)
    if err:
        return [("FAIL", "filing_deep_dive_hooks", f"valuation_model unparseable: {err}")]
    assert isinstance(data, dict)
    hooks = data.get("filing_deep_dive_hooks")
    return validate_hooks_list(
        hooks,
        check_id="filing_deep_dive_hooks",
        empty_detail=(
            "valuation_model must have non-empty filing_deep_dive_hooks[] "
            "when registry/filing_deep_dive.json exists"
        ),
    )


def check_market_context_hooks_intensity(
    hooks: Any,
    intensity: str | None,
) -> list[tuple[str, str, str]]:
    """High/medium intensity must not be all noted_only (hollow region treatment)."""
    if not isinstance(hooks, list) or not hooks:
        return []
    if intensity not in ("medium", "high"):
        return []
    actions = []
    for h in hooks:
        if isinstance(h, dict):
            actions.append(str(h.get("action") or "").strip().lower())
    if actions and all(a == "noted_only" for a in actions):
        return [
            (
                "FAIL",
                "market_context_hooks intensity",
                f"intensity={intensity} but all market_context_hooks are noted_only",
            )
        ]
    return [
        (
            "PASS",
            "market_context_hooks intensity",
            f"intensity={intensity}; not all noted_only",
        )
    ]


def check_market_context(session: Path) -> list[tuple[str, str, str]]:
    """Optional market_context: SKIPPED if absent; validate when present."""
    from packages.kd_research.check_core import SCHEMAS, jsonschema

    out: list[tuple[str, str, str]] = []
    rel = "registry/market_context.json"
    p = session / rel
    if not p.exists():
        return [
            (
                "SKIPPED",
                "market_context",
                "file absent (legacy/pre-cutover OK; new sessions should write market_context.json)",
            )
        ]
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return [("FAIL", "market_context parse", str(e))]

    required = [
        "ticker",
        "session_date",
        "primary_region",
        "intensity",
        "confidence",
        "module_file",
        "signals",
        "rationale",
        "requires_manual_review",
    ]
    missing = [k for k in required if k not in data]
    if missing:
        return [("FAIL", "market_context keys", f"missing {missing}")]

    intensity = data.get("intensity")
    if intensity not in ("low", "medium", "high"):
        return [("FAIL", "market_context intensity", f"invalid intensity={intensity!r}")]

    region = data.get("primary_region")
    allowed_regions = {"us", "hk_china", "korea", "japan", "eu_uk", "other"}
    if region not in allowed_regions:
        return [("FAIL", "market_context primary_region", f"invalid primary_region={region!r}")]

    rationale = data.get("rationale")
    if not (isinstance(rationale, str) and len(rationale.strip()) >= 20):
        return [("FAIL", "market_context rationale", "need non-empty rationale (>=20 chars)")]

    signals = data.get("signals")
    if not (isinstance(signals, list) and len(signals) >= 1):
        return [("FAIL", "market_context signals", "need non-empty signals[]")]

    schema_path = SCHEMAS / "market_context.schema.json"
    if jsonschema is not None and schema_path.exists():
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        errors = sorted(
            jsonschema.Draft7Validator(schema).iter_errors(data),
            key=lambda e: list(e.path),
        )
        if errors:
            msgs = [f"{'/'.join(str(x) for x in e.path)}: {e.message}" for e in errors[:5]]
            return [("FAIL", "schema: market_context", "; ".join(msgs))]
        out.append(("PASS", "schema: market_context", ""))
    else:
        reason = (
            "jsonschema not installed (run with vendor/mcp/yfinance-market-mcp/.venv/bin/python)"
            if jsonschema is None
            else f"no schema {schema_path.name}"
        )
        out.append(("SKIPPED", "schema: market_context", reason))

    out.append(("PASS", "market_context content", f"region={region} intensity={intensity}"))

    vm_path = session / "data/valuation_model.json"
    if not vm_path.exists():
        out.append(("SKIPPED", "market_context_hooks", "valuation_model.json missing"))
        return out
    try:
        vm = json.loads(vm_path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        out.append(("FAIL", "market_context_hooks", f"valuation_model unparseable: {e}"))
        return out
    hooks = vm.get("market_context_hooks")
    for row in validate_hooks_list(
        hooks,
        check_id="market_context_hooks",
        empty_detail=(
            "valuation_model must have non-empty market_context_hooks[] when market_context.json exists"
        ),
    ):
        out.append(row)
        if row[0] == "FAIL":
            return out
    out.extend(check_market_context_hooks_intensity(hooks, intensity))
    return out


def check_filing_deep_dive_content(session: Path) -> list[tuple[str, str, str]]:
    """Extra structural gates for deep-dive content (beyond schema keys)."""
    out: list[tuple[str, str, str]] = []
    rel = "registry/filing_deep_dive.json"
    p = session / rel
    if not p.exists():
        return [
            (
                "SKIPPED",
                "filing_deep_dive content",
                "file missing (covered by exists check when --full)",
            )
        ]
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return [("FAIL", "filing_deep_dive content", f"unparseable: {e}")]

    ok = True
    footnotes = data.get("footnotes") or {}
    items = footnotes.get("items") if isinstance(footnotes, dict) else None
    if not isinstance(items, list) or len(items) < 1:
        out.append(("FAIL", "filing_deep_dive: footnotes.items", "need non-empty items[]"))
        ok = False
    else:
        out.append(("PASS", "filing_deep_dive: footnotes.items", f"{len(items)} item(s)"))

    arc = data.get("strategy_arc") or {}
    if not isinstance(arc, dict) or not arc.get("stated_priorities_by_year") or not arc.get("rationale"):
        out.append(
            ("FAIL", "filing_deep_dive: strategy_arc", "need stated_priorities_by_year + rationale")
        )
        ok = False
    else:
        years = arc.get("years_covered") or []
        out.append(("PASS", "filing_deep_dive: strategy_arc", f"years_covered={years!r}"))

    sc = data.get("management_scorecard") or {}
    sc_items = sc.get("items") if isinstance(sc, dict) else None
    summary = sc.get("credibility_summary") if isinstance(sc, dict) else None
    if not isinstance(sc_items, list) or len(sc_items) < 1:
        out.append(
            ("FAIL", "filing_deep_dive: management_scorecard.items", "need non-empty items[]")
        )
        ok = False
    else:
        labeled = all(
            isinstance(i, dict)
            and i.get("source_type") in ("filing", "transcript", "filing+transcript")
            for i in sc_items
        )
        if not labeled:
            out.append(
                (
                    "FAIL",
                    "filing_deep_dive: scorecard source_type",
                    "each item needs source_type filing|transcript|filing+transcript",
                )
            )
            ok = False
        else:
            out.append(
                (
                    "PASS",
                    "filing_deep_dive: management_scorecard.items",
                    f"{len(sc_items)} graded item(s)",
                )
            )

    if not isinstance(summary, dict) or not summary.get("rationale") or not summary.get("valuation_implication"):
        out.append(
            (
                "FAIL",
                "filing_deep_dive: credibility_summary",
                "need rationale + valuation_implication",
            )
        )
        ok = False
    else:
        out.append(("PASS", "filing_deep_dive: credibility_summary", ""))

    sources = data.get("sources") or {}
    filings = sources.get("filings") if isinstance(sources, dict) else None
    if not isinstance(filings, list) or len(filings) < 1:
        out.append(("FAIL", "filing_deep_dive: sources.filings", "need at least one filing path"))
        ok = False
    else:
        out.append(("PASS", "filing_deep_dive: sources.filings", f"{len(filings)} filing(s)"))

    if isinstance(sources, dict):
        if "transcripts" not in sources and not (sources.get("gaps") or []):
            out.append(
                (
                    "FAIL",
                    "filing_deep_dive: sources.transcripts",
                    "declare transcripts[] (possibly empty) or document gap in sources.gaps",
                )
            )
            ok = False
        else:
            tr = sources.get("transcripts") or []
            out.append(
                (
                    "PASS",
                    "filing_deep_dive: sources.transcripts",
                    f"{len(tr)} transcript entr(y/ies)",
                )
            )

    if ok:
        out.append(("PASS", "filing_deep_dive content gates", ""))
    return out

"""Phase evidence gates for preflight and merge coverage.

Investment purpose: block valuation/reports on incomplete evidence so later
phases do not invent decision-grade numbers. Shared by preflight_phase.py.

Phase IDs align with templates/phase_status.schema.json and
harness/design_phase_status_and_exemplars.md §A.3.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Relative paths under session root. "optional" means missing → WARN not FAIL
# for that path when listed in optional_paths for the gate.

# Files that must exist and (if .json) parse before entering a phase.
PHASE_ENTRY_REQUIRED: dict[str, list[str]] = {
    "orch": [],
    "0": [
        "registry/sector_config.json",
        "registry/market_context.json",
    ],
    "1_parallel": [
        "registry/sector_config.json",
    ],
    "1b": [
        "data/sp_financials.csv",
        "registry/sec_filings.json",
    ],
    "1c": [
        "registry/sec_filings.json",
    ],
    "1d": [
        "data/sp_financials.csv",
        "registry/latest_quarter.json",
        "registry/filing_deep_dive.json",
    ],
    "2_parallel": [
        "registry/sector_config.json",
        "registry/market_context.json",
        "data/sp_financials.csv",
        "registry/sec_filings.json",
        "registry/latest_quarter.json",
        "registry/filing_deep_dive.json",
    ],
    "2_5": [
        "data/valuation_model.json",
        "registry/latest_quarter.json",
        "registry/filing_deep_dive.json",
    ],
    "3": [
        "data/valuation_model.json",
    ],
    "4_parallel": [
        "data/valuation_model.json",
        "registry/risk_bridge.json",
        "registry/technical.json",
        "registry/tsr_validation.json",
    ],
    "5": [
        "reports",  # special: three report files checked separately
    ],
    "done": [
        "registry/audit.json",
    ],
}

# Optional for new-session quality; missing is WARN (or FAIL if strict_new_session).
PHASE_ENTRY_OPTIONAL: dict[str, list[str]] = {
    "0": ["registry/research_brief.json"],
    "2_parallel": ["registry/research_brief.json", "registry/news_sentiment.json"],
    "2_5": ["registry/background.json"],
    "4_parallel": ["registry/filing_deep_dive.json", "registry/market_context.json"],
}

# Completeness when marking a phase complete (subset used by merge checks).
PHASE_COMPLETE_GLOBS: dict[str, list[str]] = {
    "0": [
        "registry/background.json",
        "registry/raw/phase0_*.json",
    ],
    "1d": [
        "registry/operating_path_brief.json",
        "registry/raw/oppath_*.json",
    ],
    "2_5": [
        "registry/risk_bridge.json",
        "registry/raw/stress_*.json",
    ],
}

REPORT_GLOBS = (
    "reports/00_{ticker}_README.md",
    "reports/01_{ticker}_fundamental.md",
    "reports/02_{ticker}_technical.md",
)

REPORT_MIN_BYTES = 2 * 1024
MIN_STRESS_RAW = 5
MIN_STRESS_SCENARIOS = 5


def load_json(path: Path) -> tuple[Any | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as e:  # noqa: BLE001
        return None, f"unparseable: {e}"


def check_path(session: Path, rel: str) -> tuple[str, str]:
    """Return (status, detail) with status PASS|FAIL for a relative path."""
    if "*" in rel:
        matches = list(session.glob(rel))
        if not matches:
            return "FAIL", f"no files match {rel}"
        return "PASS", f"{len(matches)} file(s) match {rel}"

    p = session / rel
    if rel == "reports":
        return "FAIL", "use check_reports()"

    if not p.exists():
        return "FAIL", "missing"

    if p.suffix == ".json":
        _, err = load_json(p)
        if err:
            return "FAIL", err
        return "PASS", "exists+parse"

    if p.is_file() and p.stat().st_size == 0:
        return "FAIL", "empty file"
    return "PASS", "exists"


def check_reports(session: Path, ticker: str) -> list[tuple[str, str, str]]:
    """List of (status, check_id, detail) for the three reports."""
    out: list[tuple[str, str, str]] = []
    t = ticker.upper()
    for pattern in REPORT_GLOBS:
        rel = pattern.format(ticker=t)
        p = session / rel
        if not p.exists():
            # try without assuming exact case of ticker in filename
            alt = list((session / "reports").glob(Path(rel).name.replace(t, "*"))) if (session / "reports").is_dir() else []
            # simpler: glob 00_*_README.md etc
            stem = Path(rel).name
            prefix = stem.split("_")[0]
            matches = list((session / "reports").glob(f"{prefix}_*_*.md")) if (session / "reports").is_dir() else []
            if prefix == "00":
                matches = list((session / "reports").glob("00_*_README.md"))
            elif prefix == "01":
                matches = list((session / "reports").glob("01_*_fundamental.md"))
            elif prefix == "02":
                matches = list((session / "reports").glob("02_*_technical.md"))
            if not matches:
                out.append(("FAIL", f"report:{rel}", "missing"))
                continue
            p = max(matches, key=lambda x: x.stat().st_size)
        if p.stat().st_size < REPORT_MIN_BYTES:
            out.append(("FAIL", f"report:{p.name}", f"{p.stat().st_size} bytes < {REPORT_MIN_BYTES}"))
        else:
            out.append(("PASS", f"report:{p.name}", f"{p.stat().st_size} bytes"))
    return out


SCENARIO_PROB_KEYS = ("bear", "base", "bull")
MOS_CONSISTENCY_EPS = 0.1  # |pct - 100*frac| tolerance


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
    """Structural checks for risk_bridge scenario_probabilities.

    - Sum only bear/base/bull (ignores _sum/_note meta that previously double-counted).
    - Extra keys → WARN by default (promote to FAIL when archives are clean).
    - Non-numeric values under bear/base/bull → FAIL.
    """
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


def check_mos_units(fair_value: object) -> list[tuple[str, str, str]]:
    """MoS unit hygiene for valuation_model.fair_value.

    - If both margin_of_safety (fraction) and margin_of_safety_pct present:
      FAIL when abs(pct - 100*frac) > eps.
    - If only *_pct and 0 < |x| <= 1.5: WARN (likely fraction stored in pct field).
    - Missing dual fields: no FAIL (legacy OK).
    """
    out: list[tuple[str, str, str]] = []
    if not isinstance(fair_value, dict):
        out.append(("SKIPPED", "mos_units", "fair_value missing or not object"))
        return out

    frac = fair_value.get("margin_of_safety")
    pct = fair_value.get("margin_of_safety_pct")

    if isinstance(frac, (int, float)) and isinstance(pct, (int, float)):
        expected = 100.0 * float(frac)
        if abs(float(pct) - expected) <= MOS_CONSISTENCY_EPS:
            out.append(
                (
                    "PASS",
                    "mos_units_dual",
                    f"fraction={frac} pct={pct} (consistent within {MOS_CONSISTENCY_EPS})",
                )
            )
        else:
            out.append(
                (
                    "FAIL",
                    "mos_units_dual",
                    f"pct={pct} vs 100*fraction={expected:.4f} — "
                    "write margin_of_safety as signed fraction and "
                    "margin_of_safety_pct as 100*fraction (never put 0-1 in *_pct)",
                )
            )
        return out

    if isinstance(pct, (int, float)) and not isinstance(frac, (int, float)):
        ap = abs(float(pct))
        if 0 < ap <= 1.5:
            out.append(
                (
                    "WARN",
                    "mos_units_pct_field",
                    f"margin_of_safety_pct={pct} looks like a fraction in a *_pct field; "
                    "store percent points (e.g. 29.2) and optionally margin_of_safety fraction",
                )
            )
        else:
            out.append(("PASS", "mos_units_pct_field", f"margin_of_safety_pct={pct}"))
        return out

    if isinstance(frac, (int, float)) and not isinstance(pct, (int, float)):
        out.append(
            (
                "WARN",
                "mos_units_fraction_only",
                f"margin_of_safety={frac} present without margin_of_safety_pct — "
                "prefer both fields for cross-session comparability",
            )
        )
        return out

    out.append(("SKIPPED", "mos_units", "no margin_of_safety fields"))
    return out


def check_valuation_decision_quality(session: Path) -> list[tuple[str, str, str]]:
    """Session-level MoS unit checks from data/valuation_model.json."""
    data, err = load_json(session / "data" / "valuation_model.json")
    if err:
        return [("SKIPPED", "mos_units", f"valuation_model.json {err}")]
    if not isinstance(data, dict):
        return [("SKIPPED", "mos_units", "valuation_model not an object")]
    return check_mos_units(data.get("fair_value"))


def check_stress_coverage(session: Path) -> list[tuple[str, str, str]]:
    """Merge/coverage checks for Phase 2.5."""
    out: list[tuple[str, str, str]] = []
    raw = list((session / "registry" / "raw").glob("stress_*.json")) if (session / "registry" / "raw").is_dir() else []
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


def check_phase0_coverage(session: Path) -> list[tuple[str, str, str]]:
    """Raw + merged background presence for Phase 0 complete."""
    out: list[tuple[str, str, str]] = []
    bg, err = load_json(session / "registry" / "background.json")
    if err:
        out.append(("FAIL", "background.json", err))
    else:
        rounds = bg.get("rounds") if isinstance(bg, dict) else None
        n = len(rounds) if isinstance(rounds, list) else 0
        if n < 1:
            out.append(("FAIL", "background.rounds", "empty"))
        else:
            out.append(("PASS", "background.rounds", f"{n} round(s)"))

    raw = list((session / "registry" / "raw").glob("phase0_*.json")) if (session / "registry" / "raw").is_dir() else []
    if len(raw) < 1:
        out.append(("FAIL", "phase0_raw_count", "no registry/raw/phase0_*.json"))
    else:
        out.append(("PASS", "phase0_raw_count", f"{len(raw)} file(s)"))

    # Decision-grade: downstream_relevance on raw when present
    missing_rel = 0
    checked = 0
    for p in raw:
        data, e = load_json(p)
        if e or not isinstance(data, dict):
            continue
        checked += 1
        rel = data.get("downstream_relevance")
        if not (isinstance(rel, str) and rel.strip()):
            # some raws store under findings only — also accept rounds wrapper
            missing_rel += 1
    if checked:
        if missing_rel == checked:
            out.append(
                (
                    "FAIL",
                    "phase0_downstream_relevance",
                    f"all {checked} raw returns missing non-empty downstream_relevance",
                )
            )
        elif missing_rel:
            out.append(
                (
                    "WARN",
                    "phase0_downstream_relevance",
                    f"{missing_rel}/{checked} raw returns missing downstream_relevance",
                )
            )
        else:
            out.append(("PASS", "phase0_downstream_relevance", f"{checked} raw(s) tagged"))

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
    # Accept either explicit mapping summary or non-empty risks/dropped_risks covering count
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


# --- Specialist-quality process gates (outcomes, not spawn APIs) ---

HOOK_REQUIRED_KEYS = ("from", "action", "reason")
HOOK_REASON_MIN_LEN = 10

# Path-anchored tokens: avoid bare English false positives (e.g. "background").
AGENT4_FORBIDDEN_TOKENS = (
    "filing_deep_dive",
    "fdd_year",
    "valuation_model",
    "registry/background",
    "background.json",
    "latest_quarter",
    "market_context.json",
    "sec_filings",
    "sp_financials",
    "operating_path_brief",
    "oppath_",
    "revenue_growth.json",
    "industry_trend.json",
    "operating_leverage.json",
)

# Primary artifacts for phase_status complete / lag checks (agent_id -> rel paths).
PHASE_PRIMARY_ARTIFACTS: dict[str, list[str]] = {
    "phase0_swarm": ["registry/background.json"],
    "2a": ["data/sp_financials.csv"],
    "2b": ["registry/sec_filings.json"],
    "2c": ["registry/news_sentiment.json"],
    "2d": ["registry/latest_quarter.json"],
    "2e": ["registry/filing_deep_dive.json"],
    "1d_rev": ["registry/raw/oppath_rev.json"],
    "1d_ind": ["registry/raw/oppath_ind.json"],
    "1d_ol": ["registry/raw/oppath_ol.json"],
    "1d_merge": ["registry/operating_path_brief.json"],
    "4": ["registry/technical.json"],
    "5": ["data/valuation_model.json"],
    "12": ["registry/tsr_validation.json"],
    "phase25_swarm": ["registry/risk_bridge.json"],
    "6": ["charts"],  # special: any charts dir with files
    "7": ["reports"],  # special: fundamental report checked via glob elsewhere
    "8": ["reports"],
    "11": ["reports"],
    "13": ["registry/audit.json"],
}

HANDOFF_SECTION_PATTERNS = (
    re.compile(r"(?im)^\s*#+\s*what i did\b"),
    re.compile(r"(?im)^\s*#+\s*data issues"),
    re.compile(r"(?im)^\s*#+\s*assumptions"),
    re.compile(r"(?im)^\s*#+\s*for downstream"),
)


def validate_hooks_list(
    hooks: Any,
    *,
    check_id: str,
    empty_detail: str,
) -> list[tuple[str, str, str]]:
    """Structural validation for valuation hook arrays (MC / FDD)."""
    out: list[tuple[str, str, str]] = []
    if not (isinstance(hooks, list) and len(hooks) >= 1):
        out.append(("FAIL", check_id, empty_detail))
        return out
    bad: list[str] = []
    for i, h in enumerate(hooks):
        if not isinstance(h, dict):
            bad.append(f"[{i}] not object")
            continue
        for k in HOOK_REQUIRED_KEYS:
            if k not in h or (isinstance(h.get(k), str) and not str(h.get(k)).strip()):
                bad.append(f"[{i}].{k}")
        reason = h.get("reason")
        if isinstance(reason, str) and len(reason.strip()) < HOOK_REASON_MIN_LEN:
            bad.append(f"[{i}].reason too short")
    if bad:
        out.append(("FAIL", f"{check_id} shape", "; ".join(bad[:8])))
        return out
    out.append(("PASS", check_id, f"{len(hooks)} hook(s)"))
    return out


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


def check_agent4_isolation(session: Path, *, full: bool = False) -> list[tuple[str, str, str]]:
    """Post-hoc: technical artifact/handoff must not cite fundamental session paths."""
    texts: list[tuple[str, str]] = []
    tech = session / "registry" / "technical.json"
    if tech.exists():
        try:
            texts.append((str(tech.relative_to(session)), tech.read_text(encoding="utf-8", errors="replace")))
        except OSError as e:
            return [("FAIL", "agent4_isolation", f"cannot read technical.json: {e}")]
    handoff_dir = session / "registry" / "handoffs"
    if handoff_dir.is_dir():
        for p in sorted(handoff_dir.glob("4*.md")):
            try:
                texts.append((str(p.relative_to(session)), p.read_text(encoding="utf-8", errors="replace")))
            except OSError:
                continue
    if not texts:
        return [("SKIPPED", "agent4_isolation", "no technical.json or handoffs/4*.md")]

    hits: list[str] = []
    for rel, text in texts:
        lower = text.lower()
        for tok in AGENT4_FORBIDDEN_TOKENS:
            if tok.lower() in lower:
                hits.append(f"{rel}:{tok}")
    if not hits:
        return [("PASS", "agent4_isolation", f"scanned {len(texts)} file(s)")]
    detail = "; ".join(hits[:12])
    status = "FAIL" if full else "WARN"
    return [(status, "agent4_isolation", detail)]


def check_handoff_headers(text: str) -> list[str]:
    """Return names of missing handoff section headers (empty = all present)."""
    missing: list[str] = []
    labels = ("What I did", "Data issues", "Assumptions", "For downstream")
    for label, pat in zip(labels, HANDOFF_SECTION_PATTERNS):
        if not pat.search(text):
            missing.append(label)
    return missing


def primary_artifact_exists(session: Path, agent_id: str) -> bool | None:
    """True/False if agent has a known primary artifact; None if unmapped."""
    rels = PHASE_PRIMARY_ARTIFACTS.get(agent_id)
    if not rels:
        return None
    for rel in rels:
        if rel == "charts":
            d = session / "charts"
            if d.is_dir() and any(d.iterdir()):
                return True
            continue
        if rel == "reports":
            d = session / "reports"
            if d.is_dir() and any(d.glob("*.md")):
                return True
            continue
        if (session / rel).exists():
            return True
    return False


def check_phase_status_disk(session: Path, data: dict[str, Any]) -> list[tuple[str, str, str]]:
    """phase_status complete ⇒ artifacts; lag WARN when files exist but agent pending."""
    out: list[tuple[str, str, str]] = []
    phases = data.get("phases")
    if not isinstance(phases, list):
        return out

    for ph in phases:
        if not isinstance(ph, dict):
            continue
        phase_id = ph.get("phase_id")
        phase_status = ph.get("status")
        agents = ph.get("agents") or []
        if not isinstance(agents, list):
            continue

        if phase_status == "complete":
            for ag in agents:
                if not isinstance(ag, dict):
                    continue
                aid = ag.get("agent_id")
                if not aid or ag.get("status") == "skipped":
                    continue
                exists = primary_artifact_exists(session, str(aid))
                if exists is False:
                    out.append(
                        (
                            "FAIL",
                            "phase_status complete artifact",
                            f"phase {phase_id} complete but agent {aid} primary artifact missing",
                        )
                    )
                handoff = ag.get("handoff")
                if isinstance(handoff, str) and handoff.strip():
                    hp = session / handoff if not Path(handoff).is_absolute() else Path(handoff)
                    # also try relative to session
                    if not hp.exists():
                        hp2 = session / handoff.lstrip("./")
                        hp = hp2 if hp2.exists() else hp
                    if not hp.exists():
                        out.append(
                            (
                                "FAIL",
                                "phase_status complete handoff",
                                f"phase {phase_id} agent {aid} handoff path missing: {handoff}",
                            )
                        )

        # lag: primary on disk but agent still pending/in_progress
        for ag in agents:
            if not isinstance(ag, dict):
                continue
            aid = ag.get("agent_id")
            st = ag.get("status")
            if not aid or st not in ("pending", "in_progress"):
                continue
            if primary_artifact_exists(session, str(aid)) is True:
                out.append(
                    (
                        "WARN",
                        "phase_status lag",
                        f"agent {aid} status={st} but primary artifact exists on disk",
                    )
                )

    if not any(c.startswith("phase_status") for _, c, _ in out):
        out.append(("PASS", "phase_status disk", "no complete/lag issues"))
    return out


def check_llm_model_identity(
    session: Path,
    *,
    strict: bool = True,
) -> list[tuple[str, str, str]]:
    """Require orchestrator_model stamped at scaffold (manifest), not invented late.

    ``strict=True`` (preflight / active sessions): missing → FAIL.
    ``strict=False`` (legacy completed runs in check_session): missing → WARN.
    """
    from scripts.kd_research.provenance import load_manifest_models  # noqa: WPS433

    info = load_manifest_models(session)
    if not info.get("present"):
        msg = (
            "meta/run_manifest.json missing — re-scaffold with "
            "--orchestrator-model (stamp LLM id at session start)"
        )
        return [("FAIL" if strict else "WARN", "orchestrator_model", msg)]
    if info.get("parse_error"):
        return [("FAIL", "orchestrator_model", "run_manifest.json unreadable")]
    orch = info.get("orchestrator_model")
    if not orch:
        legacy = bool(info.get("immutable")) or str(info.get("status") or "") in {
            "completed",
            "finalized",
            "exported",
        }
        if legacy and not strict:
            return [
                (
                    "WARN",
                    "orchestrator_model",
                    "missing (legacy completed OK); new runs must stamp at scaffold",
                )
            ]
        return [
            (
                "FAIL",
                "orchestrator_model",
                "missing/empty — re-scaffold with --orchestrator-model; "
                "do not invent the model id after a long context",
            )
        ]
    sub = info.get("default_subagent_model")
    detail = f"orchestrator={orch}"
    if sub:
        detail += f" subagent={sub}"
    else:
        detail += " subagent=(unset)"
    return [("PASS", "orchestrator_model", detail)]


def entry_checks(
    session: Path,
    phase_id: str,
    *,
    ticker: str | None = None,
    strict_optional: bool = False,
    subagent_id: str | None = None,
    agent_id: str | None = None,  # deprecated alias for subagent_id
) -> list[tuple[str, str, str]]:
    """Return list of (status, check_id, detail) for entering phase_id."""
    if phase_id not in PHASE_ENTRY_REQUIRED and phase_id not in ("0",):
        return [("FAIL", "phase_id", f"unknown phase_id={phase_id!r}")]

    results: list[tuple[str, str, str]] = []
    # LLM identity first: must be on disk from scaffold (avoids late hallucination)
    results.extend(check_llm_model_identity(session, strict=True))
    # Phase graph: order + allowed subagent (before file evidence)
    from scripts.kd_research.phase_graph import check_phase_graph_entry  # noqa: WPS433

    results.extend(
        check_phase_graph_entry(
            session,
            phase_id,
            subagent_id=subagent_id if subagent_id is not None else agent_id,
        )
    )

    required = PHASE_ENTRY_REQUIRED.get(phase_id, [])
    for rel in required:
        if rel == "reports":
            t = ticker or _infer_ticker(session)
            results.extend(check_reports(session, t))
            continue
        status, detail = check_path(session, rel)
        results.append((status, rel, detail))

    for rel in PHASE_ENTRY_OPTIONAL.get(phase_id, []):
        status, detail = check_path(session, rel)
        if status == "PASS":
            results.append(("PASS", f"optional:{rel}", detail))
        elif strict_optional:
            results.append(("FAIL", f"optional:{rel}", detail))
        else:
            results.append(("SKIPPED", f"optional:{rel}", f"{detail} (optional for legacy)"))

    # Phase-specific extras when entering reports / audit
    if phase_id == "4_parallel":
        results.extend(check_stress_coverage(session))
        results.extend(check_latest_quarter_risk_mapping(session))
    if phase_id == "2_parallel":
        from scripts.kd_research.operating_path import (  # noqa: WPS433
            BRIEF_REL,
            session_enforces_1d,
        )

        if session_enforces_1d(session):
            status, detail = check_path(session, BRIEF_REL)
            results.append((status, BRIEF_REL, detail))
            from scripts.kd_research.operating_path import check_operating_path_hooks

            vm = session / "data" / "valuation_model.json"
            if vm.is_file():
                results.extend(check_operating_path_hooks(session))
    if phase_id == "2_5":
        # valuation must parse with fair_value-ish keys soft-check
        vm, err = load_json(session / "data" / "valuation_model.json")
        if err:
            results.append(("FAIL", "valuation_model_content", err))
        elif isinstance(vm, dict):
            if "fair_value" not in vm and "model" not in vm:
                results.append(("FAIL", "valuation_model_content", "missing fair_value/model keys"))
            else:
                results.append(("PASS", "valuation_model_content", "core keys present"))
            # FDD consumption required before stress when deep dive exists
            results.extend(check_filing_deep_dive_hooks(session))

    return results


def check_1c_year_dive_complete(session: Path) -> list[tuple[str, str, str]]:
    """1c complete: FDD always; year-dives + excerpts only on new runtime."""
    from scripts.kd_research.annuals import (  # noqa: WPS433
        fiscal_year_from_year_dive_path,
        list_annuals,
        normalize_fiscal_year,
        session_enforces_year_dives,
        year_dive_files,
    )
    from scripts.kd_research.excerpt_check import (  # noqa: WPS433
        check_year_dive_document,
        load_year_dive,
    )

    out: list[tuple[str, str, str]] = []
    status, detail = check_path(session, "registry/filing_deep_dive.json")
    out.append((status, "registry/filing_deep_dive.json", detail))

    files = year_dive_files(session)
    enforce = session_enforces_year_dives(session)
    if not enforce and not files:
        out.append(
            (
                "SKIPPED",
                "1c_year_dives",
                "legacy/slim session (no fdd_year_*.json; harness_version < 2.5.0)",
            )
        )
        return out

    annuals = list_annuals(session)
    if not annuals:
        out.append(("FAIL", "1c_year_dives", "no annuals listed in sec_filings/raw_sec"))
        return out

    if not files:
        out.append(
            (
                "FAIL",
                "1c_year_dives",
                f"need registry/raw/fdd_year_*.json for {len(annuals)} annual(s)",
            )
        )
        return out

    years_have: set[int] = set()
    for yp in files:
        doc, err = load_year_dive(yp)
        rel = f"registry/raw/{yp.name}"
        if err or doc is None:
            out.append(("FAIL", rel, err or "unparseable"))
            continue
        out.extend(check_year_dive_document(session, doc, rel=rel))
        y = normalize_fiscal_year(doc.get("fiscal_year")) or fiscal_year_from_year_dive_path(yp)
        if y is not None:
            years_have.add(y)

    years_need = {a["fiscal_year"] for a in annuals if a.get("fiscal_year") is not None}
    missing_years = sorted(years_need - years_have)
    if missing_years:
        out.append(("FAIL", "1c_year_dives", f"missing year-dives for FY {missing_years}"))
    elif years_need:
        out.append(("PASS", "1c_year_dives", f"{len(files)} year-dive(s) cover {sorted(years_need)}"))

    fdd, fdd_err = load_json(session / "registry" / "filing_deep_dive.json")
    if fdd_err or not isinstance(fdd, dict):
        return out

    rechecks = fdd.get("verify_rechecks")
    if not isinstance(rechecks, list) or len(rechecks) < 3:
        out.append(
            (
                "FAIL",
                "1c_verify_rechecks",
                "need ≥3 verify_rechecks[] {path,value} on filing_deep_dive.json",
            )
        )
    else:
        bad = [
            i
            for i, r in enumerate(rechecks)
            if not (isinstance(r, dict) and r.get("path") and r.get("value") is not None)
        ]
        if bad:
            out.append(("FAIL", "1c_verify_rechecks", f"entries missing path/value: {bad}"))
        else:
            out.append(("PASS", "1c_verify_rechecks", f"{len(rechecks)} re-read(s)"))

    arc = fdd.get("strategy_arc") if isinstance(fdd.get("strategy_arc"), dict) else {}
    covered = {normalize_fiscal_year(y) for y in (arc.get("years_covered") or [])}
    covered.discard(None)
    if years_have and covered and covered != years_have:
        out.append(
            (
                "FAIL",
                "1c_years_covered",
                f"strategy_arc.years_covered={sorted(covered)} != year-dives {sorted(years_have)}",
            )
        )
    elif years_have and covered:
        out.append(("PASS", "1c_years_covered", f"{sorted(covered)}"))

    return out


def complete_checks(session: Path, phase_id: str) -> list[tuple[str, str, str]]:
    """Checks before marking a phase complete (merge/coverage)."""
    if phase_id == "0":
        return check_phase0_coverage(session)
    if phase_id == "1_parallel":
        out: list[tuple[str, str, str]] = []
        for rel in (
            "data/sp_financials.csv",
            "registry/sec_filings.json",
            "registry/news_sentiment.json",
        ):
            status, detail = check_path(session, rel)
            out.append((status, rel, detail))
        return out
    if phase_id == "1c":
        return check_1c_year_dive_complete(session)
    if phase_id == "1d":
        from scripts.kd_research.operating_path import check_1d_complete  # noqa: WPS433

        return check_1d_complete(session)
    if phase_id == "2_parallel":
        out = []
        for rel in (
            "registry/technical.json",
            "data/valuation_model.json",
            "registry/tsr_validation.json",
        ):
            status, detail = check_path(session, rel)
            out.append((status, rel, detail))
        out.extend(check_filing_deep_dive_hooks(session))
        from scripts.kd_research.operating_path import check_operating_path_hooks  # noqa: WPS433

        out.extend(check_operating_path_hooks(session))
        return out
    if phase_id == "2_5":
        return check_stress_coverage(session) + check_latest_quarter_risk_mapping(session)
    if phase_id == "4_parallel":
        t = _infer_ticker(session)
        return check_reports(session, t)
    return [("SKIPPED", "complete_checks", f"no merge gate for phase {phase_id}")]


def _infer_ticker(session: Path) -> str:
    # archive/research/TICKER/DATE
    parts = session.resolve().parts
    if len(parts) >= 2:
        return parts[-2]
    return "TICKER"

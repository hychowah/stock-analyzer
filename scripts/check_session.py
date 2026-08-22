#!/usr/bin/env python3
"""Structural checker for a research session (light contracts only).

This validates STRUCTURE and PROVENANCE, not financial truth:
  - required files exist (core set, or full set with --full)
  - JSON files parse and validate against templates/*.schema.json
    (when the `jsonschema` package is importable; otherwise hand-rolled
    key checks run and schema validation reports SKIPPED)
  - judgment numbers carry a non-empty `rationale`
  - compute_script fields point at files that exist on disk
  - sector_config consistency (confidence < 0.70 -> standard + manual review)
  - market_context.json optional (absent -> SKIPPED for legacy sessions); when present,
    schema/keys + non-empty market_context_hooks on valuation_model; medium/high intensity
    rejects all-noted_only hooks
  - when filing_deep_dive.json + valuation exist: non-empty filing_deep_dive_hooks (F8)
  - new-runtime year-dives (`registry/raw/fdd_year_*.json`): section walk + excerpt-in-source; SKIPPED on legacy/slim
  - phase_status.json optional (absent -> SKIPPED for legacy); when present, schema/keys
    + all designed phase_ids present; complete vs disk + lag WARN
  - Agent 4 isolation: technical artifact/handoff must not cite fundamental paths (--full FAIL)
  - handoffs include swarm leads (phase0/phase25 aliases); section headers WARN
  - JSON ticker/session_date match the folder
  - scenario_probabilities sums to 1.0 (+/- 0.01)
  - at least 5 stress scenarios
  - report files are non-trivial (> 2 KB)
  - audit verdict is PASS (--full; the audit's own verdict gates the session)

Every check reports PASS / FAIL / WARN / SKIPPED(reason). Exit code is non-zero
if any check FAILs (WARN does not fail the process). Financial cross-checks (report numbers vs registry,
external fact-checking) are the audit agent's job, not this script's.

Tip: run with the yfinance venv python for full schema validation:
  yfinance-market-mcp/.venv/bin/python scripts/check_session.py ...

Usage:
    python3 scripts/check_session.py --ticker JPM --date 2026-07-25 [--full]
    python3 scripts/check_session.py --session-dir archive/research/JPM/2026-07-25 [--full]

Resolves --ticker/--date via archive/research first, then legacy root/<TICKER>/<DATE>.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = PROJECT_ROOT / "templates"

# Paths into other research sessions (cross-session contamination signal)
_OTHER_SESSION_PATH_RE = re.compile(
    r"archive[/\\]research[/\\](?P<ticker>[A-Za-z0-9][A-Za-z0-9._-]*)[/\\]"
    r"(?P<sk>\d{4}-\d{2}-\d{2}(?:__[A-Za-z0-9][A-Za-z0-9._-]{0,80})?)",
    re.IGNORECASE,
)

try:
    import jsonschema  # type: ignore
except ImportError:
    jsonschema = None

TOLERANCE = 2 * 1024  # reports smaller than this are considered stubs

# file -> (schema name, fallback required top-level keys)
CORE_FILES: dict[str, tuple[str, list[str]]] = {
    "registry/sector_config.json": ("sector_config", ["ticker", "session_date", "primary_sector", "confidence", "rationale"]),
    "registry/latest_quarter.json": ("latest_quarter", ["ticker", "fiscal_period", "sources"]),
    "data/valuation_model.json": ("valuation_model", ["ticker", "model", "fair_value", "assumptions", "compute_script"]),
}

FULL_FILES: dict[str, tuple[str, list[str]]] = {
    **CORE_FILES,
    "registry/background.json": ("background", ["ticker", "rounds"]),
    "registry/news_sentiment.json": ("news_sentiment", ["ticker", "items"]),
    "registry/sec_filings.json": ("sec_filings", ["ticker", "filings"]),
    "registry/filing_deep_dive.json": (
        "filing_deep_dive",
        ["ticker", "session_date", "footnotes", "strategy_arc", "management_scorecard", "sources"],
    ),
    "registry/technical.json": ("technical", ["ticker", "indicators", "levels", "compute_script"]),
    "registry/tsr_validation.json": ("tsr_validation", ["ticker", "tsr", "compute_script"]),
    "registry/risk_bridge.json": ("risk_bridge", ["ticker", "scenario_probabilities", "stress_test"]),
    "registry/audit.json": ("audit", ["verdict", "checks"]),
}

REPORTS = ["reports/00_{t}_README.md", "reports/01_{t}_fundamental.md", "reports/02_{t}_technical.md"]

results: list[tuple[str, str, str]] = []  # (status, check, detail)


def record(status: str, check: str, detail: str = "") -> None:
    results.append((status, check, detail))


def _missing_rationales(obj: object, path: str = "") -> list[str]:
    """Return paths of judgment dicts missing a non-empty rationale.

    A judgment dict is any dict that has a numeric 'probability' or 'weight',
    or both 'value' and 'basis' keys.
    """
    missing: list[str] = []
    if isinstance(obj, dict):
        keys = set(obj)
        is_judgment = (
            ("probability" in keys and isinstance(obj.get("probability"), (int, float)))
            or ("weight" in keys and isinstance(obj.get("weight"), (int, float)))
            or ("value" in keys and "basis" in keys)
        )
        if is_judgment and not (isinstance(obj.get("rationale"), str) and obj["rationale"].strip()):
            missing.append(path or "<root>")
        for k, v in obj.items():
            missing.extend(_missing_rationales(v, f"{path}.{k}" if path else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            missing.extend(_missing_rationales(v, f"{path}[{i}]"))
    return missing


def _compute_scripts(obj: object) -> list[str]:
    found: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "compute_script" and isinstance(v, str):
                found.append(v)
            else:
                found.extend(_compute_scripts(v))
    elif isinstance(obj, list):
        for v in obj:
            found.extend(_compute_scripts(v))
    return found


def check_file(session: Path, rel: str, schema_name: str, required_keys: list[str]) -> None:
    p = session / rel
    if not p.exists():
        record("FAIL", f"exists: {rel}", "file missing")
        return
    try:
        data = json.loads(p.read_text())
    except Exception as e:  # noqa: BLE001
        record("FAIL", f"parse: {rel}", str(e))
        return
    record("PASS", f"exists+parse: {rel}")

    schema_path = TEMPLATES / f"{schema_name}.schema.json"
    if jsonschema is not None and schema_path.exists():
        schema = json.loads(schema_path.read_text())
        errors = sorted(jsonschema.Draft7Validator(schema).iter_errors(data), key=lambda e: list(e.path))
        if errors:
            msgs = [f"{'/'.join(str(x) for x in e.path) or '<root>'}: {e.message}" for e in errors[:5]]
            record("FAIL", f"schema: {rel}", "; ".join(msgs))
        else:
            record("PASS", f"schema: {rel}")
    else:
        reason = "jsonschema not installed (run with yfinance-market-mcp/.venv/bin/python)" if jsonschema is None else f"no template {schema_path.name}"
        record("SKIPPED", f"schema: {rel}", reason)
        missing = [k for k in required_keys if k not in data]
        if missing:
            record("FAIL", f"keys: {rel}", f"missing {missing}")
        else:
            record("PASS", f"keys: {rel}")

    bad = _missing_rationales(data)
    if bad:
        record("FAIL", f"rationale: {rel}", f"missing/empty rationale at {bad[:5]}")
    else:
        record("PASS", f"rationale: {rel}")

    for script in _compute_scripts(data):
        sp = Path(script)
        if not sp.is_absolute():
            sp = session / script
        if sp.exists():
            record("PASS", f"compute_script exists: {script}")
        else:
            record("FAIL", f"compute_script exists: {script}", "file not found")


def check_identity(session: Path, ticker: str, session_date: str) -> None:
    p = session / "registry/sector_config.json"
    if not p.exists():
        record("SKIPPED", "identity/consistency", "sector_config.json missing")
        return
    try:
        sc = json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        record("SKIPPED", "identity/consistency", "sector_config.json unparseable")
        return
    ok = True
    if sc.get("ticker") and sc["ticker"].upper() != ticker.upper():
        record("FAIL", "identity: ticker", f"json says {sc['ticker']}, folder says {ticker}")
        ok = False
    # session_date in JSON is as-of YYYY-MM-DD; folder may be date__slug
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.kd_research.paths import parse_session_key  # noqa: WPS433

    asof, _ = parse_session_key(session_date)
    if sc.get("session_date") and sc["session_date"] != asof and sc["session_date"] != session_date:
        record(
            "FAIL",
            "identity: session_date",
            f"json says {sc['session_date']}, folder as-of/key says {asof}/{session_date}",
        )
        ok = False
    conf = sc.get("confidence")
    if isinstance(conf, (int, float)) and conf < 0.70:
        if sc.get("primary_sector") != "standard" or sc.get("requires_manual_review") is not True:
            record("FAIL", "confidence gate", f"confidence {conf} < 0.70 requires primary_sector=standard and requires_manual_review=true")
            ok = False
    if ok:
        record("PASS", "identity + confidence gate")


def check_risk_bridge(session: Path) -> None:
    p = session / "registry/risk_bridge.json"
    if not p.exists():
        record("SKIPPED", "risk_bridge content checks", "file missing")
        return
    try:
        data = json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        record("SKIPPED", "risk_bridge content checks", "unparseable")
        return
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.kd_research.gates import check_scenario_probability_keys  # noqa: WPS433

    probs = data.get("scenario_probabilities")
    for status, check, detail in check_scenario_probability_keys(probs, extra_key_severity="WARN"):
        # Map helper ids to legacy check names where useful
        name = {
            "scenario_probabilities_sum": "scenario_probabilities sum",
            "scenario_probabilities_keys": "scenario_probabilities keys",
            "scenario_probabilities_values": "scenario_probabilities values",
            "scenario_probabilities": "scenario_probabilities sum",
        }.get(check, check)
        record(status, name, detail)
    scenarios = (data.get("stress_test") or {}).get("scenarios") or []
    if len(scenarios) >= 5:
        record("PASS", "stress scenario count", f"{len(scenarios)} >= 5")
    else:
        record("FAIL", "stress scenario count", f"{len(scenarios)} < 5 (need 4 sector + 1 macro)")


def check_valuation_mos_units(session: Path) -> None:
    """Soft/conditional MoS unit checks — WARN does not fail the process."""
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.kd_research.gates import check_valuation_decision_quality  # noqa: WPS433

    for status, check, detail in check_valuation_decision_quality(session):
        record(status, check, detail)


def check_reports(session: Path, ticker: str) -> None:
    for tmpl in REPORTS:
        rel = tmpl.format(t=ticker.upper())
        p = session / rel
        if not p.exists():
            record("FAIL", f"exists: {rel}", "file missing")
        elif p.stat().st_size < TOLERANCE:
            record("FAIL", f"size: {rel}", f"{p.stat().st_size} bytes < {TOLERANCE} (stub?)")
        else:
            record("PASS", f"exists+size: {rel}", f"{p.stat().st_size} bytes")


def check_audit_verdict(session: Path) -> None:
    p = session / "registry/audit.json"
    if not p.exists():
        record("FAIL", "audit verdict", "audit.json missing — Phase 5 not run")
        return
    try:
        verdict = json.loads(p.read_text()).get("verdict")
    except Exception as e:  # noqa: BLE001
        record("FAIL", "audit verdict", f"unparseable: {e}")
        return
    if verdict == "PASS":
        record("PASS", "audit verdict", "PASS")
    else:
        record("FAIL", "audit verdict", f"{verdict!r} — session not complete until audit passes or issues are waived in the README")


# (agent_id, glob patterns under registry/handoffs/)
HANDOFF_SPECS: list[tuple[str, list[str]]] = [
    ("2a", ["2a_*.md", "2a.md"]),
    ("2b", ["2b_*.md", "2b.md"]),
    ("2c", ["2c_*.md", "2c.md"]),
    ("2d", ["2d_*.md", "2d.md"]),
    ("2e", ["2e_*.md", "2e.md"]),
    ("4", ["4_*.md", "4.md"]),
    ("5", ["5_*.md", "5.md"]),
    ("12", ["12_*.md", "12.md"]),
    ("6", ["6_*.md", "6.md"]),
    ("7", ["7_*.md", "7.md"]),
    ("8", ["8_*.md", "8.md"]),
    ("11", ["11_*.md", "11.md"]),
    ("13", ["13_*.md", "13.md"]),
    # Swarm leads (aliases used in fixtures: phase0_background.md, phase25_stress.md)
    ("phase0_swarm", ["phase0_swarm*.md", "phase0_*.md", "phase0.md"]),
    ("phase25_swarm", ["phase25_swarm*.md", "phase25_*.md", "phase25.md", "2_5_*.md"]),
]
HANDOFF_SPECS_1D: list[tuple[str, list[str]]] = [
    ("1d_rev", ["1d_rev*.md"]),
    ("1d_ind", ["1d_ind*.md"]),
    ("1d_ol", ["1d_ol*.md"]),
    ("1d_merge", ["1d_merge*.md", "1d_operating_path*.md"]),
]
HANDOFF_AGENTS = [a for a, _ in HANDOFF_SPECS]
HANDOFF_MIN_BYTES = 300


def check_handoffs(session: Path) -> None:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.kd_research.gates import check_handoff_headers  # noqa: WPS433
    from scripts.kd_research.operating_path import session_enforces_1d  # noqa: WPS433

    d = session / "registry/handoffs"
    if not d.is_dir():
        record("FAIL", "handoffs", "registry/handoffs/ missing — every agent must write one")
        return
    specs = list(HANDOFF_SPECS)
    if session_enforces_1d(session):
        specs.extend(HANDOFF_SPECS_1D)
    for agent, patterns in specs:
        matches: list[Path] = []
        for pat in patterns:
            matches.extend(d.glob(pat))
        # de-dupe
        matches = sorted({p.resolve() for p in matches}, key=lambda p: p.name)
        if not matches:
            record("FAIL", f"handoff: agent {agent}", "file missing")
            continue
        best = max(matches, key=lambda p: p.stat().st_size)
        if best.stat().st_size < HANDOFF_MIN_BYTES:
            record("FAIL", f"handoff: agent {agent}", f"< {HANDOFF_MIN_BYTES} bytes (stub?)")
            continue
        record("PASS", f"handoff: agent {agent}", best.name)
        try:
            text = best.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        missing = check_handoff_headers(text)
        if missing:
            record(
                "WARN",
                f"handoff headers: {agent}",
                f"missing sections: {', '.join(missing)}",
            )


def check_market_context(session: Path) -> None:
    """Optional market_context: SKIPPED if absent (legacy); validate when present.

    New sessions should write registry/market_context.json (AGENTS.md §5b).
    Absence must not FAIL old session folders. When present and valuation exists,
    require non-empty market_context_hooks (intensity=low may be a single noted_only).
    """
    rel = "registry/market_context.json"
    p = session / rel
    if not p.exists():
        record(
            "SKIPPED",
            "market_context",
            "file absent (legacy/pre-cutover OK; new sessions should write market_context.json)",
        )
        return
    try:
        data = json.loads(p.read_text())
    except Exception as e:  # noqa: BLE001
        record("FAIL", "market_context parse", str(e))
        return

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
        record("FAIL", "market_context keys", f"missing {missing}")
        return

    intensity = data.get("intensity")
    if intensity not in ("low", "medium", "high"):
        record("FAIL", "market_context intensity", f"invalid intensity={intensity!r}")
        return

    region = data.get("primary_region")
    allowed_regions = {"us", "hk_china", "korea", "japan", "eu_uk", "other"}
    if region not in allowed_regions:
        record("FAIL", "market_context primary_region", f"invalid primary_region={region!r}")
        return

    rationale = data.get("rationale")
    if not (isinstance(rationale, str) and len(rationale.strip()) >= 20):
        record("FAIL", "market_context rationale", "need non-empty rationale (>=20 chars)")
        return

    signals = data.get("signals")
    if not (isinstance(signals, list) and len(signals) >= 1):
        record("FAIL", "market_context signals", "need non-empty signals[]")
        return

    schema_path = TEMPLATES / "market_context.schema.json"
    if jsonschema is not None and schema_path.exists():
        schema = json.loads(schema_path.read_text())
        errors = sorted(jsonschema.Draft7Validator(schema).iter_errors(data), key=lambda e: list(e.path))
        if errors:
            msgs = [f"{'/'.join(str(x) for x in e.path)}: {e.message}" for e in errors[:5]]
            record("FAIL", "schema: market_context", "; ".join(msgs))
            return
        record("PASS", "schema: market_context")
    else:
        reason = (
            "jsonschema not installed (run with yfinance-market-mcp/.venv/bin/python)"
            if jsonschema is None
            else f"no template {schema_path.name}"
        )
        record("SKIPPED", "schema: market_context", reason)

    record("PASS", "market_context content", f"region={region} intensity={intensity}")

    vm_path = session / "data/valuation_model.json"
    if not vm_path.exists():
        record("SKIPPED", "market_context_hooks", "valuation_model.json missing")
        return
    try:
        vm = json.loads(vm_path.read_text())
    except Exception as e:  # noqa: BLE001
        record("FAIL", "market_context_hooks", f"valuation_model unparseable: {e}")
        return
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.kd_research.gates import (  # noqa: WPS433
        check_market_context_hooks_intensity,
        validate_hooks_list,
    )

    hooks = vm.get("market_context_hooks")
    for status, check, detail in validate_hooks_list(
        hooks,
        check_id="market_context_hooks",
        empty_detail=(
            "valuation_model must have non-empty market_context_hooks[] when market_context.json exists"
        ),
    ):
        record(status, check, detail)
        if status == "FAIL":
            return
    for status, check, detail in check_market_context_hooks_intensity(hooks, intensity):
        record(status, check, detail)


def check_research_brief(session: Path) -> None:
    """Optional research_brief: SKIPPED if absent (legacy); validate when present."""
    rel = "registry/research_brief.json"
    p = session / rel
    if not p.exists():
        record(
            "SKIPPED",
            "research_brief",
            "file absent (legacy OK; new sessions write research_brief.json before Phase 0)",
        )
        return
    try:
        data = json.loads(p.read_text())
    except Exception as e:  # noqa: BLE001
        record("FAIL", "research_brief parse", str(e))
        return

    required = [
        "ticker",
        "session_date",
        "company_name",
        "investment_objective",
        "must_answer_questions",
        "peers",
        "benchmarks",
        "currency",
        "research_depth",
        "rationale",
    ]
    missing = [k for k in required if k not in data]
    if missing:
        record("FAIL", "research_brief keys", f"missing {missing}")
        return

    depth = data.get("research_depth")
    if depth not in ("standard", "deep"):
        record("FAIL", "research_brief research_depth", f"invalid research_depth={depth!r}")
        return

    questions = data.get("must_answer_questions")
    if not (isinstance(questions, list) and len(questions) >= 3):
        record("FAIL", "research_brief must_answer_questions", "need >=3 questions")
        return

    rationale = data.get("rationale")
    if not (isinstance(rationale, str) and len(rationale.strip()) >= 20):
        record("FAIL", "research_brief rationale", "need non-empty rationale (>=20 chars)")
        return

    schema_path = TEMPLATES / "research_brief.schema.json"
    if jsonschema is not None and schema_path.exists():
        schema = json.loads(schema_path.read_text())
        errors = sorted(jsonschema.Draft7Validator(schema).iter_errors(data), key=lambda e: list(e.path))
        if errors:
            msgs = [f"{'/'.join(str(x) for x in e.path) or '<root>'}: {e.message}" for e in errors[:5]]
            record("FAIL", "schema: research_brief", "; ".join(msgs))
            return
        record("PASS", "schema: research_brief")
    else:
        reason = (
            "jsonschema not installed (run with yfinance-market-mcp/.venv/bin/python)"
            if jsonschema is None
            else f"no template {schema_path.name}"
        )
        record("SKIPPED", "schema: research_brief", reason)

    record(
        "PASS",
        "research_brief content",
        f"depth={depth} questions={len(questions)}",
    )


def write_session_acceptance(
    session: Path,
    ticker: str,
    session_date: str,
    out_path: Path | None = None,
) -> Path:
    """Write registry/session_acceptance.json from current check results."""
    from datetime import datetime, timezone

    checks = [
        {
            "id": check,
            "description": check,
            "status": status,
            "detail": detail or "",
        }
        for status, check, detail in results
    ]
    n_fail = sum(1 for s, _, _ in results if s == "FAIL")
    overall = "FAIL" if n_fail else "PASS"
    # PARTIAL if any SKIPPED on core identity? keep simple: FAIL vs PASS
    payload = {
        "ticker": ticker.upper(),
        "session_date": session_date,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "overall": overall,
        "checks": checks,
        "notes": (
            "Structural/provenance only — financial truth is owned by Phase 5 audit. "
            "Investment package readiness = overall PASS plus audit verdict PASS."
        ),
    }
    path = out_path or (session / "registry" / "session_acceptance.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def check_phase_status(session: Path) -> None:
    """Optional phase_status: SKIPPED if absent (legacy); validate when present.

    New sessions get registry/phase_status.json from scaffold (resume map).
    Absence must not FAIL old session folders. When present: required keys,
    designed phase_ids, agent rows, and schema when jsonschema is available.
    """
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.kd_research.operating_path import designed_phase_ids  # noqa: WPS433
    from scripts.kd_research.phase_status import PHASE_IDS  # noqa: WPS433

    designed = designed_phase_ids(session)

    rel = "registry/phase_status.json"
    p = session / rel
    if not p.exists():
        record(
            "SKIPPED",
            "phase_status",
            "file absent (legacy/pre-cutover OK; new sessions scaffold phase_status.json)",
        )
        return
    try:
        data = json.loads(p.read_text())
    except Exception as e:  # noqa: BLE001
        record("FAIL", "phase_status parse", str(e))
        return

    required = [
        "ticker",
        "session_date",
        "schema_version",
        "updated_at",
        "current_phase",
        "phases",
    ]
    missing = [k for k in required if k not in data]
    if missing:
        record("FAIL", "phase_status keys", f"missing {missing}")
        return

    if not isinstance(data.get("schema_version"), int) or data["schema_version"] < 1:
        record("FAIL", "phase_status schema_version", f"need int >= 1, got {data.get('schema_version')!r}")
        return

    current = data.get("current_phase")
    if current not in PHASE_IDS:
        record("FAIL", "phase_status current_phase", f"invalid current_phase={current!r}")
        return

    phases = data.get("phases")
    if not isinstance(phases, list) or len(phases) < 1:
        record("FAIL", "phase_status phases", "need non-empty phases[]")
        return

    seen_ids: list[str] = []
    allowed_status = {"pending", "in_progress", "complete", "failed", "blocked", "skipped"}
    for i, ph in enumerate(phases):
        if not isinstance(ph, dict):
            record("FAIL", "phase_status phases shape", f"phases[{i}] not object")
            return
        pid = ph.get("phase_id")
        if pid not in PHASE_IDS:
            record("FAIL", "phase_status phase_id", f"phases[{i}].phase_id={pid!r} invalid")
            return
        seen_ids.append(pid)
        st = ph.get("status")
        if st not in allowed_status:
            record("FAIL", "phase_status phase status", f"phases[{i}].status={st!r}")
            return
        agents = ph.get("agents")
        if not isinstance(agents, list):
            record("FAIL", "phase_status agents", f"phases[{i}].agents must be array")
            return
        for j, ag in enumerate(agents):
            if not isinstance(ag, dict) or not ag.get("agent_id"):
                record("FAIL", "phase_status agent row", f"phases[{i}].agents[{j}] need agent_id")
                return
            if ag.get("status") not in allowed_status:
                record(
                    "FAIL",
                    "phase_status agent status",
                    f"phases[{i}].agents[{j}].status={ag.get('status')!r}",
                )
                return

    missing_phases = [pid for pid in designed if pid not in seen_ids]
    if missing_phases:
        record("FAIL", "phase_status phase coverage", f"missing phase_id(s): {missing_phases}")
        return

    schema_path = TEMPLATES / "phase_status.schema.json"
    if jsonschema is not None and schema_path.exists():
        schema = json.loads(schema_path.read_text())
        errors = sorted(jsonschema.Draft7Validator(schema).iter_errors(data), key=lambda e: list(e.path))
        if errors:
            msgs = [f"{'/'.join(str(x) for x in e.path) or '<root>'}: {e.message}" for e in errors[:5]]
            record("FAIL", "schema: phase_status", "; ".join(msgs))
            return
        record("PASS", "schema: phase_status")
    else:
        reason = (
            "jsonschema not installed (run with yfinance-market-mcp/.venv/bin/python)"
            if jsonschema is None
            else f"no template {schema_path.name}"
        )
        record("SKIPPED", "schema: phase_status", reason)

    record(
        "PASS",
        "phase_status content",
        f"current_phase={current} phases={len(phases)} schema_version={data['schema_version']}",
    )

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.kd_research.gates import check_phase_status_disk  # noqa: WPS433
    from scripts.kd_research.phase_graph import check_phase_status_graph  # noqa: WPS433

    for status, check, detail in check_phase_status_disk(session, data):
        record(status, check, detail)
    for status, check, detail in check_phase_status_graph(session):
        record(status, check, detail)


def check_filing_deep_dive_hooks_session(session: Path) -> None:
    """Machine gate for F8: valuation must consume FDD when deep dive exists."""
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.kd_research.gates import check_filing_deep_dive_hooks  # noqa: WPS433

    for status, check, detail in check_filing_deep_dive_hooks(session):
        record(status, check, detail)


def check_agent4_isolation_session(session: Path, *, full: bool = False) -> None:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.kd_research.gates import check_agent4_isolation  # noqa: WPS433

    for status, check, detail in check_agent4_isolation(session, full=full):
        record(status, check, detail)


def check_operating_path(session: Path) -> None:
    """New-runtime 1d brief + hooks; SKIPPED on legacy/slim."""
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.kd_research.operating_path import (  # noqa: WPS433
        check_1d_complete,
        check_operating_path_hooks,
        session_enforces_1d,
        worker_files,
        brief_path,
    )

    if not session_enforces_1d(session) and not worker_files(session) and not brief_path(session).is_file():
        record("SKIPPED", "operating_path_1d", "legacy/slim (no oppath files; harness_version < 2.6.0)")
        return
    for status, check, detail in check_1d_complete(session):
        record(status, check, detail)
    vm = session / "data" / "valuation_model.json"
    if vm.is_file():
        for status, check, detail in check_operating_path_hooks(session):
            record(status, check, detail)


def check_wave3_epistemology_session(session: Path) -> None:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.kd_research.epistemology import check_wave3_epistemology  # noqa: WPS433

    for status, check, detail in check_wave3_epistemology(session):
        record(status, check, detail)


def check_wave4_destock_session(session: Path) -> None:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.kd_research.epistemology import check_wave4_destock_default  # noqa: WPS433

    for status, check, detail in check_wave4_destock_default(session):
        record(status, check, detail)


def check_wave2_decision_session(session: Path) -> None:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.kd_research.decision import check_wave2_decision  # noqa: WPS433

    for status, check, detail in check_wave2_decision(session):
        record(status, check, detail)


def check_decision_quality_session(session: Path) -> None:
    """Wave 1 decision-quality gates; SKIPPED on harness < 2.9.0."""
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.kd_research.decision_quality import (  # noqa: WPS433
        check_wave1_decision_quality,
    )

    for status, check, detail in check_wave1_decision_quality(session):
        record(status, check, detail)


def check_roic_identity_session(session: Path) -> None:
    """New-runtime owner-earnings ROIC identity; SKIPPED on legacy."""
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.kd_research.roic_identity import (  # noqa: WPS433
        check_roic_identity,
        session_is_roic_runtime,
    )

    vm = session / "data" / "valuation_model.json"
    if not session_is_roic_runtime(session) and not (
        vm.is_file() and "roic_identity" in vm.read_text(encoding="utf-8", errors="replace")
    ):
        record("SKIPPED", "roic_identity", "legacy/slim (no roic_identity; harness_version < 2.8.0)")
        return
    if vm.is_file():
        for status, check, detail in check_roic_identity(session):
            record(status, check, detail)
    elif session_is_roic_runtime(session):
        record("SKIPPED", "roic_identity", "valuation_model.json missing")


def check_street_bind_session(session: Path) -> None:
    """New-runtime Street fetch + Agent 5 calibration bind; SKIPPED on legacy."""
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.kd_research.street_bind import (  # noqa: WPS433
        check_street_bind,
        check_street_fetch,
        session_enforces_street,
        street_path,
    )

    if not session_enforces_street(session) and not street_path(session).is_file():
        record("SKIPPED", "street_bind", "legacy/slim (no street_estimates.json; harness_version < 2.7.0)")
        return
    if street_path(session).is_file():
        check_file(
            session,
            "registry/street_estimates.json",
            "street_estimates",
            ["ticker", "session_date", "source", "fiscal_convention", "years"],
        )
    for status, check, detail in check_street_fetch(session):
        record(status, check, detail)
    vm = session / "data" / "valuation_model.json"
    if vm.is_file():
        for status, check, detail in check_street_bind(session):
            record(status, check, detail)


def check_year_dives(session: Path) -> None:
    """New-runtime year-reader files + excerpt-in-source; SKIPPED on legacy/slim."""
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.kd_research.annuals import session_enforces_year_dives, year_dive_files
    from scripts.kd_research.gates import check_1c_year_dive_complete

    files = year_dive_files(session)
    if not session_enforces_year_dives(session) and not files:
        record("SKIPPED", "year_dives", "legacy/slim (no fdd_year_*.json; harness_version < 2.5.0)")
        return
    for status, check, detail in check_1c_year_dive_complete(session):
        # FDD existence is already covered by --full file list
        if check == "registry/filing_deep_dive.json":
            continue
        record(status, check, detail)


def check_filing_deep_dive(session: Path) -> None:
    """Extra structural gates for deep-dive content (beyond schema keys)."""
    rel = "registry/filing_deep_dive.json"
    p = session / rel
    if not p.exists():
        record("SKIPPED", "filing_deep_dive content", "file missing (covered by exists check when --full)")
        return
    try:
        data = json.loads(p.read_text())
    except Exception as e:  # noqa: BLE001
        record("FAIL", "filing_deep_dive content", f"unparseable: {e}")
        return

    ok = True
    footnotes = data.get("footnotes") or {}
    items = footnotes.get("items") if isinstance(footnotes, dict) else None
    if not isinstance(items, list) or len(items) < 1:
        record("FAIL", "filing_deep_dive: footnotes.items", "need non-empty items[]")
        ok = False
    else:
        record("PASS", "filing_deep_dive: footnotes.items", f"{len(items)} item(s)")

    arc = data.get("strategy_arc") or {}
    if not isinstance(arc, dict) or not arc.get("stated_priorities_by_year") or not arc.get("rationale"):
        record("FAIL", "filing_deep_dive: strategy_arc", "need stated_priorities_by_year + rationale")
        ok = False
    else:
        years = arc.get("years_covered") or []
        record("PASS", "filing_deep_dive: strategy_arc", f"years_covered={years!r}")

    sc = data.get("management_scorecard") or {}
    sc_items = sc.get("items") if isinstance(sc, dict) else None
    summary = sc.get("credibility_summary") if isinstance(sc, dict) else None
    if not isinstance(sc_items, list) or len(sc_items) < 1:
        record("FAIL", "filing_deep_dive: management_scorecard.items", "need non-empty items[]")
        ok = False
    else:
        labeled = all(
            isinstance(i, dict) and i.get("source_type") in ("filing", "transcript", "filing+transcript")
            for i in sc_items
        )
        if not labeled:
            record("FAIL", "filing_deep_dive: scorecard source_type", "each item needs source_type filing|transcript|filing+transcript")
            ok = False
        else:
            record("PASS", "filing_deep_dive: management_scorecard.items", f"{len(sc_items)} graded item(s)")

    if not isinstance(summary, dict) or not summary.get("rationale") or not summary.get("valuation_implication"):
        record("FAIL", "filing_deep_dive: credibility_summary", "need rationale + valuation_implication")
        ok = False
    else:
        record("PASS", "filing_deep_dive: credibility_summary")

    sources = data.get("sources") or {}
    filings = sources.get("filings") if isinstance(sources, dict) else None
    if not isinstance(filings, list) or len(filings) < 1:
        record("FAIL", "filing_deep_dive: sources.filings", "need at least one filing path")
        ok = False
    else:
        record("PASS", "filing_deep_dive: sources.filings", f"{len(filings)} filing(s)")

    # Transcripts may be empty/missing with explicit gap — require key present or gaps note
    if isinstance(sources, dict):
        if "transcripts" not in sources and not (sources.get("gaps") or []):
            record(
                "FAIL",
                "filing_deep_dive: sources.transcripts",
                "declare transcripts[] (possibly empty) or document gap in sources.gaps",
            )
            ok = False
        else:
            tr = sources.get("transcripts") or []
            record("PASS", "filing_deep_dive: sources.transcripts", f"{len(tr)} transcript entr(y/ies)")

    if ok:
        record("PASS", "filing_deep_dive content gates")


def check_session_isolation(session: Path, *, full: bool = False) -> None:
    """Cross-session isolation: prior runs must not feed this session's valuation.

    Intra-session paths under this folder are fine. Citations to
    archive/research/<TICKER>/<other_session_key>/ in valuation-facing artifacts
    are WARN (default) or FAIL with --full.
    """
    iso = session / "registry" / "session_isolation.json"
    if iso.is_file():
        try:
            data = json.loads(iso.read_text(encoding="utf-8"))
            mode = data.get("mode") or "isolated"
            rules = data.get("rules") if isinstance(data.get("rules"), dict) else {}
            if rules.get("prior_valuation_as_input") is True:
                record(
                    "WARN",
                    "session_isolation policy",
                    "prior_valuation_as_input=true — unusual; risk of anchoring",
                )
            elif rules.get("intra_session_share") is False:
                record(
                    "WARN",
                    "session_isolation policy",
                    "intra_session_share=false — breaks normal phase handoffs",
                )
            else:
                record("PASS", "session_isolation policy", f"mode={mode}")
        except Exception as e:  # noqa: BLE001
            record("FAIL", "session_isolation parse", str(e))
    else:
        record(
            "SKIPPED",
            "session_isolation",
            "registry/session_isolation.json absent (legacy OK; new scaffolds write it)",
        )

    session_key = session.name
    ticker = session.parent.name.upper()
    allow: set[str] = set()
    if iso.is_file():
        try:
            data = json.loads(iso.read_text(encoding="utf-8"))
            for k in data.get("allow_prior_session_keys") or []:
                if isinstance(k, str) and k.strip():
                    allow.add(k.strip())
        except Exception:  # noqa: BLE001
            pass

    scan_rels = [
        "data/valuation_model.json",
        "registry/risk_bridge.json",
        "meta/prediction_snapshot.json",
        "registry/handoffs/5_valuation.md",
        "registry/handoffs/7_fundamental_report.md",
        "registry/handoffs/7_fundamental.md",
        "registry/handoffs/13_audit.md",
    ]
    # Reports if present
    for p in (session / "reports").glob("*.md") if (session / "reports").is_dir() else []:
        scan_rels.append(str(p.relative_to(session)).replace("\\", "/"))

    hits: list[str] = []
    for rel in scan_rels:
        path = session / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in _OTHER_SESSION_PATH_RE.finditer(text):
            other_t = m.group("ticker").upper()
            other_sk = m.group("sk")
            if other_t != ticker:
                continue
            if other_sk == session_key:
                continue
            if other_sk in allow:
                continue
            hits.append(f"{rel} → {other_t}/{other_sk}")

    if not hits:
        record("PASS", "cross-session valuation isolation", "no foreign session paths in valuation-facing artifacts")
        return

    sample = "; ".join(hits[:5])
    more = f" (+{len(hits) - 5} more)" if len(hits) > 5 else ""
    detail = (
        f"prior session path(s) cited (risk of FV anchoring): {sample}{more}. "
        "Valuation must use this session only; compare-after is post-audit only."
    )
    if full:
        record("FAIL", "cross-session valuation isolation", detail)
    else:
        record("WARN", "cross-session valuation isolation", detail)


def check_meta_artifacts(session: Path) -> None:
    """Optional meta/ prediction snapshot + run_manifest (archive layout).

    Absence is SKIPPED for legacy sessions. When present, require basic keys.
    """
    meta = session / "meta"
    if not meta.is_dir():
        record(
            "SKIPPED",
            "meta/",
            "absent (legacy OK; new sessions scaffold meta/ + post-Phase-5 snapshot)",
        )
        return
    snap = meta / "prediction_snapshot.json"
    man = meta / "run_manifest.json"
    if not snap.exists() and not man.exists():
        record("SKIPPED", "meta content", "meta/ empty — run build_prediction_snapshot.py after Phase 5")
        return
    if man.exists():
        try:
            data = json.loads(man.read_text())
            for k in ("run_id", "ticker", "session_date"):
                if k not in data:
                    record("FAIL", "run_manifest keys", f"missing {k}")
                    break
            else:
                record("PASS", "run_manifest", data.get("run_id", ""))
            # Provenance identity: new scaffolds/finalize always stamp these.
            # Legacy manifests may lack them → WARN (does not fail process).
            hv = data.get("harness_version")
            hsha = data.get("harness_git_sha")
            if not hv or not str(hv).strip():
                record(
                    "WARN",
                    "run_manifest harness_version",
                    "missing — re-run finalize_session / scaffold; source harness/VERSION",
                )
            else:
                record("PASS", "run_manifest harness_version", str(hv))
            if not hsha or not str(hsha).strip():
                record(
                    "WARN",
                    "run_manifest harness_git_sha",
                    "missing — finalize should stamp git HEAD or 'unknown'",
                )
            else:
                dirty = data.get("harness_dirty")
                record(
                    "PASS",
                    "run_manifest harness_git_sha",
                    f"{hsha} dirty={dirty}",
                )
            # LLM model identity: required at scaffold for active runs; WARN for
            # legacy completed sessions that pre-date enforcement.
            from scripts.kd_research.gates import check_llm_model_identity  # noqa: WPS433

            legacy_done = bool(data.get("immutable")) or str(data.get("status") or "") in {
                "completed",
                "finalized",
                "exported",
            }
            for st, cid, detail in check_llm_model_identity(session, strict=not legacy_done):
                record(st, f"run_manifest {cid}", detail)
        except Exception as e:  # noqa: BLE001
            record("FAIL", "run_manifest parse", str(e))
    else:
        record("SKIPPED", "run_manifest", "file missing")
    if snap.exists():
        try:
            data = json.loads(snap.read_text())
            for k in ("run_id", "ticker", "session_date", "fair_value"):
                if k not in data:
                    record("FAIL", "prediction_snapshot keys", f"missing {k}")
                    break
            else:
                record("PASS", "prediction_snapshot", data.get("run_id", ""))
            prov = data.get("provenance") if isinstance(data.get("provenance"), dict) else {}
            if not prov.get("harness_version") or not prov.get("harness_git_sha"):
                record(
                    "WARN",
                    "prediction_snapshot provenance",
                    "harness_version/git missing — re-run finalize_session to stamp identity",
                )
            else:
                record(
                    "PASS",
                    "prediction_snapshot provenance",
                    f"v={prov.get('harness_version')} git={prov.get('harness_git_sha')}",
                )
            om = prov.get("orchestrator_model")
            if not om or not str(om).strip():
                record(
                    "WARN",
                    "prediction_snapshot orchestrator_model",
                    "missing in provenance — re-scaffold new runs with --orchestrator-model",
                )
            else:
                record(
                    "PASS",
                    "prediction_snapshot orchestrator_model",
                    str(om),
                )
        except Exception as e:  # noqa: BLE001
            record("FAIL", "prediction_snapshot parse", str(e))
    else:
        record("SKIPPED", "prediction_snapshot", "file missing")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker")
    ap.add_argument("--date")
    ap.add_argument("--session-dir")
    ap.add_argument("--full", action="store_true", help="require all Phase 0-5 artifacts")
    ap.add_argument(
        "--write-acceptance",
        nargs="?",
        const="registry/session_acceptance.json",
        default=None,
        help=(
            "After checks, write session_acceptance.json (default path under session: "
            "registry/session_acceptance.json). Optional explicit relative/absolute path."
        ),
    )
    args = ap.parse_args()

    if args.session_dir:
        session = Path(args.session_dir).expanduser().resolve()
        # archive/research/TICKER/SESSION_KEY → ticker is parent.name
        ticker = session.parent.name
        session_date = session.name  # may be date__slug; identity uses as-of parse
    elif args.ticker and args.date:
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        from scripts.kd_research.paths import resolve_session  # noqa: WPS433

        resolved = resolve_session(args.ticker, args.date)
        if resolved is None:
            print(
                f"Session folder not found for {args.ticker.upper()} {args.date} "
                f"(checked archive/research/ and legacy root/)"
            )
            return 2
        session = resolved
        ticker = args.ticker
        session_date = args.date
    else:
        ap.error("pass --session-dir or both --ticker and --date")

    if not session.exists():
        print(f"Session folder not found: {session}")
        return 2

    files = FULL_FILES if args.full else CORE_FILES
    for rel, (schema_name, keys) in files.items():
        check_file(session, rel, schema_name, keys)
    check_identity(session, ticker, session_date)
    # Optional for legacy sessions; always run so absence is SKIPPED not silent.
    check_market_context(session)
    check_research_brief(session)
    check_phase_status(session)
    check_session_isolation(session, full=bool(args.full))
    check_meta_artifacts(session)
    # FDD hooks / Agent 4: always evaluate when files present; severity for Agent 4 depends on --full
    check_filing_deep_dive_hooks_session(session)
    check_agent4_isolation_session(session, full=bool(args.full))
    if args.full:
        check_filing_deep_dive(session)
        check_year_dives(session)
        check_operating_path(session)
        check_street_bind_session(session)
        check_roic_identity_session(session)
        check_decision_quality_session(session)
        check_wave2_decision_session(session)
        from scripts.kd_research.decision import check_wave6_reopen  # noqa: WPS433

        for status, check, detail in check_wave6_reopen(session):
            record(status, check, detail)
        check_wave3_epistemology_session(session)
        check_wave4_destock_session(session)
        check_risk_bridge(session)
        check_valuation_mos_units(session)
        check_reports(session, ticker)
        check_audit_verdict(session)
        check_handoffs(session)
    else:
        record("SKIPPED", "risk_bridge/report/audit/handoff/deep-dive checks", "run with --full after Phase 5")

    n_fail = sum(1 for s, _, _ in results if s == "FAIL")
    n_warn = sum(1 for s, _, _ in results if s == "WARN")
    n_skip = sum(1 for s, _, _ in results if s == "SKIPPED")
    for status, check, detail in results:
        line = f"[{status:7s}] {check}"
        if detail:
            line += f" — {detail}"
        print(line)
    n_pass = len(results) - n_fail - n_skip - n_warn
    print(f"\n{n_pass} passed, {n_fail} failed, {n_warn} warned, {n_skip} skipped")
    print(f"session: {session}")
    if n_warn:
        print("Note: WARN is signal for next runs / humans; exit code ignores WARN (FAIL only).")

    if args.write_acceptance is not None:
        out = Path(args.write_acceptance)
        if not out.is_absolute():
            out = session / out
        written = write_session_acceptance(session, ticker, session_date, out_path=out)
        print(f"wrote acceptance: {written}")

    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())

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
    schema/keys + non-empty market_context_hooks on valuation_model
  - phase_status.json optional (absent -> SKIPPED for legacy); when present, schema/keys
    + all designed phase_ids present
  - JSON ticker/session_date match the folder
  - scenario_probabilities sums to 1.0 (+/- 0.01)
  - at least 5 stress scenarios
  - report files are non-trivial (> 2 KB)
  - audit verdict is PASS (--full; the audit's own verdict gates the session)

Every check reports PASS / FAIL / SKIPPED(reason). Exit code is non-zero
if any check FAILs. Financial cross-checks (report numbers vs registry,
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
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = PROJECT_ROOT / "templates"

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
    if sc.get("session_date") and sc["session_date"] != session_date:
        record("FAIL", "identity: session_date", f"json says {sc['session_date']}, folder says {session_date}")
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
    probs = data.get("scenario_probabilities")
    if isinstance(probs, dict) and probs:
        total = sum(v for v in probs.values() if isinstance(v, (int, float)))
        if abs(total - 1.0) <= 0.01:
            record("PASS", "scenario_probabilities sum", f"{total:.3f}")
        else:
            record("FAIL", "scenario_probabilities sum", f"{total:.3f} != 1.0 +/- 0.01")
    else:
        record("FAIL", "scenario_probabilities sum", "missing or empty")
    scenarios = (data.get("stress_test") or {}).get("scenarios") or []
    if len(scenarios) >= 5:
        record("PASS", "stress scenario count", f"{len(scenarios)} >= 5")
    else:
        record("FAIL", "stress scenario count", f"{len(scenarios)} < 5 (need 4 sector + 1 macro)")


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


HANDOFF_AGENTS = ["2a", "2b", "2c", "2d", "2e", "4", "5", "12", "6", "7", "8", "11", "13"]
HANDOFF_MIN_BYTES = 300


def check_handoffs(session: Path) -> None:
    d = session / "registry/handoffs"
    if not d.is_dir():
        record("FAIL", "handoffs", "registry/handoffs/ missing — every agent must write one")
        return
    for agent in HANDOFF_AGENTS:
        matches = [p for p in d.glob(f"{agent}_*.md")] + [p for p in d.glob(f"{agent}.md")]
        if not matches:
            record("FAIL", f"handoff: agent {agent}", "file missing")
        elif max(p.stat().st_size for p in matches) < HANDOFF_MIN_BYTES:
            record("FAIL", f"handoff: agent {agent}", f"< {HANDOFF_MIN_BYTES} bytes (stub?)")
        else:
            record("PASS", f"handoff: agent {agent}")


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
    hooks = vm.get("market_context_hooks")
    if not (isinstance(hooks, list) and len(hooks) >= 1):
        record(
            "FAIL",
            "market_context_hooks",
            "valuation_model must have non-empty market_context_hooks[] when market_context.json exists",
        )
        return
    bad = []
    for i, h in enumerate(hooks):
        if not isinstance(h, dict):
            bad.append(f"[{i}] not object")
            continue
        for k in ("from", "action", "reason"):
            if k not in h or (isinstance(h.get(k), str) and not str(h.get(k)).strip()):
                bad.append(f"[{i}].{k}")
        reason = h.get("reason")
        if isinstance(reason, str) and len(reason.strip()) < 10:
            bad.append(f"[{i}].reason too short")
    if bad:
        record("FAIL", "market_context_hooks shape", "; ".join(bad[:8]))
        return
    record("PASS", "market_context_hooks", f"{len(hooks)} hook(s)")


def check_phase_status(session: Path) -> None:
    """Optional phase_status: SKIPPED if absent (legacy); validate when present.

    New sessions get registry/phase_status.json from scaffold (resume map).
    Absence must not FAIL old session folders. When present: required keys,
    designed phase_ids, agent rows, and schema when jsonschema is available.
    """
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.kd_research.phase_status import PHASE_IDS  # noqa: WPS433

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

    missing_phases = [pid for pid in PHASE_IDS if pid not in seen_ids]
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
    args = ap.parse_args()

    if args.session_dir:
        session = Path(args.session_dir).expanduser().resolve()
        # archive/research/TICKER/DATE → ticker is parent.name; same for legacy ROOT/TICKER/DATE
        ticker = session.parent.name
        session_date = session.name
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
    check_phase_status(session)
    check_meta_artifacts(session)
    if args.full:
        check_filing_deep_dive(session)
        check_risk_bridge(session)
        check_reports(session, ticker)
        check_audit_verdict(session)
        check_handoffs(session)
    else:
        record("SKIPPED", "risk_bridge/report/audit/handoff/deep-dive checks", "run with --full after Phase 5")

    n_fail = sum(1 for s, _, _ in results if s == "FAIL")
    n_skip = sum(1 for s, _, _ in results if s == "SKIPPED")
    for status, check, detail in results:
        line = f"[{status:7s}] {check}"
        if detail:
            line += f" — {detail}"
        print(line)
    print(f"\n{len(results) - n_fail - n_skip} passed, {n_fail} failed, {n_skip} skipped")
    print(f"session: {session}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())

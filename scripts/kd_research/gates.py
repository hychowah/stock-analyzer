"""Phase evidence gates for preflight and merge coverage.

Investment purpose: block valuation/reports on incomplete evidence so later
phases do not invent decision-grade numbers. Shared by preflight_phase.py.

Phase IDs align with templates/phase_status.schema.json and
harness/design_phase_status_and_exemplars.md §A.3.
"""

from __future__ import annotations

import json
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
    if isinstance(probs, dict):
        try:
            total = sum(float(probs[k]) for k in ("bear", "base", "bull") if k in probs)
            # also allow nested value objects
            if total == 0:
                total = 0.0
                for k in ("bear", "base", "bull"):
                    v = probs.get(k)
                    if isinstance(v, dict) and "value" in v:
                        total += float(v["value"])
                    elif isinstance(v, (int, float)):
                        total += float(v)
            if abs(total - 1.0) <= 0.01:
                out.append(("PASS", "scenario_probabilities_sum", f"{total:.3f}"))
            else:
                out.append(("FAIL", "scenario_probabilities_sum", f"{total:.3f} != 1.0"))
        except (TypeError, ValueError) as e:
            out.append(("FAIL", "scenario_probabilities_sum", str(e)))
    else:
        out.append(("FAIL", "scenario_probabilities_sum", "missing"))

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


def entry_checks(
    session: Path,
    phase_id: str,
    *,
    ticker: str | None = None,
    strict_optional: bool = False,
) -> list[tuple[str, str, str]]:
    """Return list of (status, check_id, detail) for entering phase_id."""
    if phase_id not in PHASE_ENTRY_REQUIRED and phase_id not in ("0",):
        return [("FAIL", "phase_id", f"unknown phase_id={phase_id!r}")]

    results: list[tuple[str, str, str]] = []
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
    if phase_id == "2_5":
        # valuation must parse with fair_value-ish keys soft-check
        vm, err = load_json(session / "data" / "valuation_model.json")
        if err:
            results.append(("FAIL", "valuation_model_content", err))
        elif isinstance(vm, dict) and not (vm.get("fair_value") or vm.get("model")):
            results.append(("FAIL", "valuation_model_content", "missing fair_value/model keys"))
        elif isinstance(vm, dict):
            results.append(("PASS", "valuation_model_content", "core keys present"))

    return results


def complete_checks(session: Path, phase_id: str) -> list[tuple[str, str, str]]:
    """Checks before marking a phase complete (merge/coverage)."""
    if phase_id == "0":
        return check_phase0_coverage(session)
    if phase_id == "2_5":
        return check_stress_coverage(session) + check_latest_quarter_risk_mapping(session)
    return [("SKIPPED", "complete_checks", f"no merge gate for phase {phase_id}")]


def _infer_ticker(session: Path) -> str:
    # archive/research/TICKER/DATE
    parts = session.resolve().parts
    if len(parts) >= 2:
        return parts[-2]
    return "TICKER"

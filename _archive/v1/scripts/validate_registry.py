#!/usr/bin/env python3
"""Validate registry JSON files against schemas and cross-file consistency.

Usage:
    yfinance-market-mcp/.venv/bin/python scripts/validate_registry.py \
        --ticker AAPL --date 2026-07-19

Or point directly at a session folder:
    scripts/validate_registry.py --session-dir AAPL/2026-07-19
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

from jsonschema import validate, ValidationError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"


def _load_schema(name: str) -> dict:
    path = TEMPLATES_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Schema not found: {path}")
    return json.loads(path.read_text())


def _validate_file(file_path: Path, schema: dict) -> list[str]:
    errors: list[str] = []
    if not file_path.exists():
        return [f"Missing file: {file_path}"]
    try:
        data = json.loads(file_path.read_text())
    except json.JSONDecodeError as e:
        return [f"Invalid JSON in {file_path}: {e}"]

    try:
        validate(instance=data, schema=schema)
    except ValidationError as e:
        errors.append(f"{file_path}: {e.message} (path: {list(e.path)})")
    return errors


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


def _check_kd_artifacts(session_dir: Path) -> list[str]:
    """Check artifacts produced by the kimi-datasource harness."""
    errors: list[str] = []
    registry_dir = session_dir / "registry"
    data_dir = session_dir / "data"

    for path in (
        data_dir / "sp_financials.csv",
        registry_dir / "sec_filings.json",
        registry_dir / "trajectory_review.json",
    ):
        if not path.exists():
            errors.append(f"Missing kimi-datasource artifact: {path}")

    # sp_financials.csv should have at least annual + some quarterly rows.
    sp_path = data_dir / "sp_financials.csv"
    if sp_path.exists():
        try:
            rows = list(csv.DictReader(sp_path.open(encoding="utf-8")))
            if len(rows) < 5:
                errors.append(f"sp_financials.csv has only {len(rows)} rows; expected at least 5")
        except Exception as e:
            errors.append(f"Could not read sp_financials.csv: {e}")

    return errors


def _cross_check(session_dir: Path) -> list[str]:
    """Run cross-file consistency checks beyond JSON schema validation."""
    errors: list[str] = []
    registry_dir = session_dir / "registry"
    data_dir = session_dir / "data"

    errors.extend(_check_kd_artifacts(session_dir))

    vm_path = data_dir / "valuation_model.json"
    lq_path = registry_dir / "latest_quarter.json"
    tech_path = registry_dir / "technical.json"
    rb_path = registry_dir / "risk_bridge.json"

    if vm_path.exists() and lq_path.exists():
        vm = json.loads(vm_path.read_text())
        lq = json.loads(lq_path.read_text())

        vm_debt = _safe_float(vm.get("inputs", {}).get("total_debt_usd"))
        lq_debt = _safe_float(lq.get("balance_sheet", {}).get("total_debt"))
        if vm_debt and lq_debt:
            lq_debt_usd = lq_debt * 1e6
            if abs(vm_debt - lq_debt_usd) / max(vm_debt, 1) > 0.05:
                errors.append(f"Debt mismatch: valuation_model {vm_debt/1e6:.1f}M vs latest_quarter {lq_debt:.1f}M")

        vm_fcf = _safe_float(vm.get("inputs", {}).get("ttm_reported_fcf_usd"))
        lq_fcf = _safe_float(lq.get("cash_flow", {}).get("ttm_free_cash_flow"))
        if vm_fcf and lq_fcf:
            lq_fcf_usd = lq_fcf * 1e6
            if abs(vm_fcf - lq_fcf_usd) / max(vm_fcf, 1) > 0.01:
                errors.append(f"TTM FCF mismatch: valuation_model {vm_fcf/1e6:.1f}M vs latest_quarter {lq_fcf:.1f}M")

        # Stop-loss sanity
        if tech_path.exists():
            tech = json.loads(tech_path.read_text())
            entry = _safe_float(tech.get("trade_levels", {}).get("entry_zone", {}).get("preferred"))
            stop = _safe_float(tech.get("trade_levels", {}).get("stop_loss"))
            if entry and stop and stop >= entry:
                errors.append(f"stop_loss {stop:.2f} is above preferred entry {entry:.2f}")

        # Risk-bridge scenario probabilities
        if rb_path.exists():
            rb = json.loads(rb_path.read_text())
            probs = rb.get("scenario_probabilities", {})
            if probs and abs(sum(_safe_float(v) or 0 for v in probs.values()) - 1.0) > 0.01:
                errors.append(f"Scenario probabilities do not sum to 1.0: {probs}")
            stress = rb.get("stress_test", {}).get("scenarios", [])
            if len(stress) < 5:
                errors.append(f"Only {len(stress)} stress scenarios found; AGENTS.md requires 4 sector + 1 macro")

    return errors


def validate_session(session_dir: Path) -> int:
    registry_dir = session_dir / "registry"
    data_dir = session_dir / "data"
    if not registry_dir.exists():
        print(f"ERROR: registry directory not found: {registry_dir}", file=sys.stderr)
        return 1

    files_to_schemas = {
        registry_dir / "sector_config.json": _load_schema("sector_config.schema.json"),
        registry_dir / "latest_quarter.json": _load_schema("latest_quarter.schema.json"),
        registry_dir / "risk_bridge.json": _load_schema("risk_bridge.schema.json"),
    }

    all_errors: list[str] = []
    for file_path, schema in files_to_schemas.items():
        errors = _validate_file(file_path, schema)
        if errors:
            all_errors.extend(errors)
        else:
            print(f"OK   schema {file_path.relative_to(PROJECT_ROOT)}")

    # Required data artifacts (no strict schema yet, just presence + JSON validity)
    for file_path in (
        data_dir / "valuation_model.json",
        registry_dir / "technical.json",
        registry_dir / "tsr_validation.json",
    ):
        if not file_path.exists():
            all_errors.append(f"Missing artifact: {file_path}")
        else:
            try:
                json.loads(file_path.read_text())
                print(f"OK   artifact {file_path.relative_to(PROJECT_ROOT)}")
            except json.JSONDecodeError as e:
                all_errors.append(f"Invalid JSON in {file_path}: {e}")

    all_errors.extend(_cross_check(session_dir))

    if all_errors:
        print("\nValidation errors:", file=sys.stderr)
        for err in all_errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("\nAll registry files are valid and cross-checks passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate registry JSON files")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--session-dir", help="Path to <TICKER>/<DATE>/ session folder")
    group.add_argument("--ticker", help="Ticker symbol (requires --date)")
    parser.add_argument("--date", help="Session date YYYY-MM-DD (requires --ticker)")
    args = parser.parse_args()

    if args.session_dir:
        session_dir = Path(args.session_dir).expanduser().resolve()
    else:
        if not args.date:
            parser.error("--date is required when using --ticker")
        session_dir = PROJECT_ROOT / args.ticker.upper() / args.date

    return validate_session(session_dir)


if __name__ == "__main__":
    sys.exit(main())

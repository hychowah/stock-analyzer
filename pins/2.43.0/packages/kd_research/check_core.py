"""Shared check I/O, result shape, and version compare.

Investment purpose: one place for (status, id, detail) rows, JSON-as-data,
and harness_version floors so domain modules do not import gates for I/O.
Writer JSON remains packages.kd_research.registry_io.load_json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, NamedTuple

from packages.kd_research.annuals import load_run_manifest_version, parse_semver
from packages.kd_research.paths import PROJECT_ROOT

try:
    import jsonschema  # type: ignore
except ImportError:
    jsonschema = None

SCHEMAS = PROJECT_ROOT / "harness" / "schemas"
REPORT_MIN_BYTES = 2 * 1024

HOOK_REQUIRED_KEYS = ("from", "action", "reason")
HOOK_REASON_MIN_LEN = 10


class Check(NamedTuple):
    """One machine-check row. Unpacks as (status, id, detail)."""

    status: str
    id: str
    detail: str


def load_json(path: Path) -> tuple[Any | None, str | None]:
    """Read UTF-8 JSON. Missing or unparseable is data, not an exception."""
    if not path.exists():
        return None, "missing"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as e:  # noqa: BLE001
        return None, f"unparseable: {e}"


def session_since(session: Path, ver: tuple[int, int, int]) -> bool:
    """True when meta/run_manifest harness_version >= ver. Unparseable → False."""
    parsed = parse_semver(load_run_manifest_version(session))
    if parsed is None:
        return False
    return parsed >= ver


def validate_hooks_list(
    hooks: Any,
    *,
    check_id: str,
    empty_detail: str,
) -> list[tuple[str, str, str]]:
    """Structural validation for valuation hook arrays (MC / FDD / Street)."""
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


def infer_ticker(session: Path) -> str:
    parts = session.resolve().parts
    if len(parts) >= 2:
        return parts[-2]
    return "TICKER"


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


def report_rows(session: Path, ticker: str, *, exact: bool) -> list[tuple[str, str, str]]:
    """Three report files. exact=True uses exists:/size: ids; False uses report: + glob."""
    out: list[tuple[str, str, str]] = []
    t = ticker.upper()
    templates = (
        "reports/00_{t}_README.md",
        "reports/01_{t}_fundamental.md",
        "reports/02_{t}_technical.md",
    )
    for tmpl in templates:
        rel = tmpl.format(t=t)
        p = session / rel
        if exact:
            if not p.exists():
                out.append(("FAIL", f"exists: {rel}", "file missing"))
            elif p.stat().st_size < REPORT_MIN_BYTES:
                out.append(
                    (
                        "FAIL",
                        f"size: {rel}",
                        f"{p.stat().st_size} bytes < {REPORT_MIN_BYTES} (stub?)",
                    )
                )
            else:
                out.append(("PASS", f"exists+size: {rel}", f"{p.stat().st_size} bytes"))
            continue
        glob_rel = (
            "reports/00_*_README.md"
            if rel.startswith("reports/00_")
            else "reports/01_*_fundamental.md"
            if rel.startswith("reports/01_")
            else "reports/02_*_technical.md"
        )
        if not p.exists():
            matches = (
                list((session / "reports").glob(Path(glob_rel).name))
                if (session / "reports").is_dir()
                else []
            )
            if not matches:
                out.append(("FAIL", f"report:{rel}", "missing"))
                continue
            p = max(matches, key=lambda x: x.stat().st_size)
        if p.stat().st_size < REPORT_MIN_BYTES:
            out.append(("FAIL", f"report:{p.name}", f"{p.stat().st_size} bytes < {REPORT_MIN_BYTES}"))
        else:
            out.append(("PASS", f"report:{p.name}", f"{p.stat().st_size} bytes"))
    return out


def check_reports(session: Path, ticker: str | None = None) -> list[tuple[str, str, str]]:
    """List of (status, check_id, detail) for the three reports (glob fallback)."""
    return report_rows(session, ticker or infer_ticker(session), exact=False)


def check_reports_exact(session: Path) -> list[tuple[str, str, str]]:
    return report_rows(session, infer_ticker(session), exact=True)


def _missing_rationales(obj: object, path: str = "") -> list[str]:
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


def check_structured_file(
    session: Path,
    rel: str,
    schema_name: str,
    required_keys: list[str],
) -> list[tuple[str, str, str]]:
    """Exists + parse + schema/keys + rationale + compute_script paths."""
    out: list[tuple[str, str, str]] = []
    p = session / rel
    if not p.exists():
        out.append(("FAIL", f"exists: {rel}", "file missing"))
        return out
    try:
        data = json.loads(p.read_text())
    except Exception as e:  # noqa: BLE001
        out.append(("FAIL", f"parse: {rel}", str(e)))
        return out
    out.append(("PASS", f"exists+parse: {rel}", ""))

    schema_path = SCHEMAS / f"{schema_name}.schema.json"
    if jsonschema is not None and schema_path.exists():
        schema = json.loads(schema_path.read_text())
        errors = sorted(
            jsonschema.Draft7Validator(schema).iter_errors(data),
            key=lambda e: list(e.path),
        )
        if errors:
            msgs = [f"{'/'.join(str(x) for x in e.path) or '<root>'}: {e.message}" for e in errors[:5]]
            out.append(("FAIL", f"schema: {rel}", "; ".join(msgs)))
        else:
            out.append(("PASS", f"schema: {rel}", ""))
    else:
        reason = (
            "jsonschema not installed (run with vendor/mcp/yfinance-market-mcp/.venv/bin/python)"
            if jsonschema is None
            else f"no schema {schema_path.name}"
        )
        out.append(("SKIPPED", f"schema: {rel}", reason))
        missing = [k for k in required_keys if k not in data]
        if missing:
            out.append(("FAIL", f"keys: {rel}", f"missing {missing}"))
        else:
            out.append(("PASS", f"keys: {rel}", ""))

    bad = _missing_rationales(data)
    if bad:
        out.append(("FAIL", f"rationale: {rel}", f"missing/empty rationale at {bad[:5]}"))
    else:
        out.append(("PASS", f"rationale: {rel}", ""))

    for script in _compute_scripts(data):
        sp = Path(script)
        if not sp.is_absolute():
            sp = session / script
        if sp.exists():
            out.append(("PASS", f"compute_script exists: {script}", ""))
        else:
            out.append(("FAIL", f"compute_script exists: {script}", "file not found"))
    return out


def structured_file(
    rel: str,
    schema_name: str,
    required_keys: tuple[str, ...] | list[str],
):
    """Bind one artifact to a session→rows function for the check catalog."""
    keys = list(required_keys)

    def run(session: Path) -> list[tuple[str, str, str]]:
        return check_structured_file(session, rel, schema_name, keys)

    run.__name__ = f"check_file_{rel.replace('/', '_').replace('.', '_')}"
    run.__qualname__ = run.__name__
    return run

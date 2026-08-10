#!/usr/bin/env python3
"""Mode B baseline verify: unit tests + policy checks.

Usage:
    python3 scripts/eng_verify.py
    python3 scripts/eng_verify.py --quick
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Paths Mode B must never treat as writable product state for completed research.
IMMUTABLE_PREFIXES = (
    "archive/research/",
    "archive/outcomes/",
)


def _run(cmd: list[str], *, cwd: Path) -> int:
    print("+", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(cwd))
    return int(proc.returncode)


def check_eng_tree(root: Path) -> list[str]:
    errs: list[str] = []
    required = [
        root / "eng" / "AGENTS.md",
        root / "eng" / "HARNESS_MAP.md",
        root / "eng" / "runbook.md",
        root / "packages" / "catalog_api" / "__init__.py",
        root / "apps" / "analysis_web" / "app.py",
    ]
    for p in required:
        if not p.is_file():
            errs.append(f"missing required file: {p.relative_to(root)}")
    # Mode B must not be named build/ at top level as the harness home
    if (root / "build" / "AGENTS.md").is_file():
        errs.append(
            "found build/AGENTS.md — Mode B harness must live under eng/ "
            "(top-level build/ is gitignored)"
        )
    return errs


def check_reserved_names_importable() -> list[str]:
    errs: list[str] = []
    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        from scripts.kd_research.paths import ROOT_RESERVED_NAMES
    except Exception as e:  # noqa: BLE001
        return [f"cannot import ROOT_RESERVED_NAMES: {e}"]
    for name in ("eng", "packages", "apps", "programs", "docs"):
        if name not in ROOT_RESERVED_NAMES:
            errs.append(f"ROOT_RESERVED_NAMES missing {name!r}")
    return errs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--quick",
        action="store_true",
        help="Skip pytest; only structural/policy checks",
    )
    ap.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help="Project root (default: repo root)",
    )
    args = ap.parse_args(argv)
    root = args.project_root.resolve()

    print("== eng_verify: structural ==")
    errs = check_eng_tree(root) + check_reserved_names_importable()
    if errs:
        for e in errs:
            print(f"FAIL: {e}")
        return 1
    print("OK structural + reserved names")

    print("== eng_verify: immutability policy (documented) ==")
    for p in IMMUTABLE_PREFIXES:
        print(f"  deny writes: {p}")
    print("OK policy listed (enforced by process + future hooks)")

    if args.quick:
        print("eng_verify: PASS (quick)")
        return 0

    print("== eng_verify: pytest ==")
    tests = [
        "scripts/tests/test_reserved_names.py",
        "scripts/tests/test_catalog_api.py",
        "scripts/tests/test_archive_paths.py",
        "scripts/tests/test_analysis_web.py",
    ]
    existing = [t for t in tests if (root / t).is_file()]
    if not existing:
        print("WARN: no eng-related tests found")
        return 0
    code = _run([sys.executable, "-m", "pytest", *existing, "-q"], cwd=root)
    if code != 0:
        print("eng_verify: FAIL (pytest)")
        return code
    print("eng_verify: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

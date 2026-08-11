#!/usr/bin/env python3
"""Mode B baseline verify: unit tests + policy checks.

Usage:
    python3 scripts/eng_verify.py
    python3 scripts/eng_verify.py --quick
    python3 scripts/eng_verify.py --skip-version-check
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
        root / "harness" / "RESEARCH_AGENTS.md",
        root / "harness" / "VERSION",
    ]
    for p in required:
        if not p.is_file():
            errs.append(f"missing required file: {p.relative_to(root)}")
    # Root AGENTS should stay a short router (progressive disclosure)
    agents = root / "AGENTS.md"
    if agents.is_file():
        nlines = len(agents.read_text(encoding="utf-8", errors="replace").splitlines())
        if nlines > 150:
            errs.append(
                f"root AGENTS.md is {nlines} lines (want ≤150 router); "
                "full law belongs in harness/RESEARCH_AGENTS.md"
            )
        body = agents.read_text(encoding="utf-8", errors="replace")
        if "harness/RESEARCH_AGENTS.md" not in body:
            errs.append("root AGENTS.md must point Mode A at harness/RESEARCH_AGENTS.md")
        if "eng/AGENTS.md" not in body:
            errs.append("root AGENTS.md must point Mode B at eng/AGENTS.md")
    # Mode B must not be named build/ at top level as the harness home
    if (root / "build" / "AGENTS.md").is_file():
        errs.append(
            "found build/AGENTS.md — Mode B harness must live under eng/ "
            "(top-level build/ is gitignored)"
        )
    # VERSION file must parse
    sys.path.insert(0, str(root))
    try:
        from scripts.kd_research.provenance import load_harness_identity

        ident = load_harness_identity(root)
        if not ident.get("harness_version") or ident["harness_version"].endswith("unversioned"):
            errs.append(
                "harness/VERSION missing or unversioned — set harness_version (semver)"
            )
    except Exception as e:  # noqa: BLE001
        errs.append(f"cannot load harness/VERSION: {e}")
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


def _git_ok(root: Path) -> bool:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return out.returncode == 0 and "true" in (out.stdout or "").lower()
    except (OSError, subprocess.TimeoutExpired):
        return False


def _git_ref_exists(root: Path, ref: str) -> bool:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", ref],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return out.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _changed_paths_vs_base(root: Path, base: str) -> list[str]:
    """Union of committed (base...HEAD), staged/unstaged diffs, and untracked files."""
    paths: set[str] = set()
    cmds = [
        ["git", "-C", str(root), "diff", "--name-only", f"{base}...HEAD"],
        ["git", "-C", str(root), "diff", "--name-only", "HEAD"],
        ["git", "-C", str(root), "diff", "--name-only", "--cached"],
        # New files (e.g. harness/VERSION) are not in diff until staged
        ["git", "-C", str(root), "ls-files", "--others", "--exclude-standard"],
    ]
    for cmd in cmds:
        try:
            out = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if out.returncode != 0:
            continue
        for line in (out.stdout or "").splitlines():
            line = line.strip()
            if line:
                paths.add(line.replace("\\", "/"))
    return sorted(paths)


def check_harness_version_bump(root: Path) -> list[str]:
    """If Mode A research-runtime paths changed vs main, harness/VERSION must change too."""
    errs: list[str] = []
    if not _git_ok(root):
        print("  skip version-bump check (not a git work tree)")
        return errs

    base = None
    for cand in ("main", "master", "origin/main", "origin/master"):
        if _git_ref_exists(root, cand):
            base = cand
            break
    if base is None:
        print("  skip version-bump check (no main/master base ref)")
        return errs

    sys.path.insert(0, str(root))
    from scripts.kd_research.provenance import (  # noqa: WPS433
        VERSION_PATH_POSIX,
        paths_require_version_bump,
    )

    changed = _changed_paths_vs_base(root, base)
    needs_bump, runtime_changed = paths_require_version_bump(changed)
    if not needs_bump:
        print(f"  OK no research-runtime path changes vs {base}")
        return errs

    version_changed = VERSION_PATH_POSIX in changed
    if not version_changed:
        sample = ", ".join(runtime_changed[:8])
        more = f" (+{len(runtime_changed) - 8} more)" if len(runtime_changed) > 8 else ""
        errs.append(
            "Mode A research-runtime paths changed without bumping harness/VERSION. "
            f"Base={base}. Changed (sample): {sample}{more}. "
            "Bump harness_version in harness/VERSION (semver) and include that file "
            "in the same change set before ship."
        )
    else:
        print(
            f"  OK harness/VERSION changed with {len(runtime_changed)} "
            f"research-runtime path(s) vs {base}"
        )
    return errs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--quick",
        action="store_true",
        help="Skip pytest; only structural/policy checks",
    )
    ap.add_argument(
        "--skip-version-check",
        action="store_true",
        help="Skip research-runtime → harness/VERSION bump gate",
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
    print("OK structural + reserved names + harness/VERSION")

    print("== eng_verify: immutability policy (documented) ==")
    for p in IMMUTABLE_PREFIXES:
        print(f"  deny writes: {p}")
    print("OK policy listed (enforced by process + future hooks)")

    print("== eng_verify: Mode A version bump (W1) ==")
    if args.skip_version_check:
        print("  skipped (--skip-version-check)")
    else:
        verrs = check_harness_version_bump(root)
        if verrs:
            for e in verrs:
                print(f"FAIL: {e}")
            return 1

    if args.quick:
        print("eng_verify: PASS (quick)")
        return 0

    print("== eng_verify: pytest ==")
    tests = [
        "scripts/tests/test_reserved_names.py",
        "scripts/tests/test_catalog_api.py",
        "scripts/tests/test_archive_paths.py",
        "scripts/tests/test_analysis_web.py",
        "scripts/tests/test_render_markdown.py",
        "scripts/tests/test_catalog_atomic.py",
        "scripts/tests/test_router_agents.py",
        "scripts/tests/test_provenance.py",
        "scripts/tests/test_session_isolation_check.py",
        "scripts/tests/test_phase_graph.py",
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

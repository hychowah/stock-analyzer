"""Shocked-path apply for Phase 2.5 (harness >= 2.44.0).

The merged shock list on risk_bridge.stress_test.scenarios is the Apply input.
Each row is shock + probability + liquidity_path + narrative. This module
calls fair_value_under once per row and writes one applied block
(stressed_fv, derived haircut, numeric restates_bear). Raw stress_*.json
files stay the gather archive; they are not a second source of FV.

fair_value_under(overrides) is the only way to ask "what is FV if these
named assumptions change." Base FV is fair_value_under({}). shock_surface.dials
are the engine contract (current value, optional lo/hi). The 4x4 sensitivity
grid is display, not the stress engine.

Merge shocks first (no haircuts). Then run apply. Reverse-stress is another
fair_value_under walk, not a heatmap cell.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from packages.kd_research.check_core import load_json, session_since
from packages.kd_research.paths import require_session

STRESS_BOOK_SINCE = (2, 44, 0)
UNDER_TIMEOUT_S = 120
RESTATES_BEAR_EPS = 0.05
REVERSE_STEPS = 12
BASE_MATCH_ABS = 0.05
BASE_MATCH_REL = 0.01


def session_is_stress_book_runtime(session: Path) -> bool:
    return session_since(session, STRESS_BOOK_SINCE)


def as_number(val: Any) -> float | None:
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, dict):
        return as_number(val.get("value"))
    return None


def haircut_from_values(base: float, stressed: float) -> float:
    """Signed fraction: 1 - stressed/base. Positive is a downside haircut."""
    if base == 0:
        raise ValueError("base FV is 0")
    return 1.0 - (stressed / base)


def restates_bear_numeric(
    stressed_fv: float,
    base: float,
    bear: float,
    *,
    eps: float = RESTATES_BEAR_EPS,
) -> bool:
    """True when stressed FV is the bear print under another name."""
    if base <= 0:
        return False
    return abs(stressed_fv - bear) / base < eps


def parse_under_stdout(stdout: str) -> float:
    """Last JSON object on stdout must contain fair_value."""
    text = (stdout or "").strip()
    if not text:
        raise ValueError("empty --under stdout")
    last = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            last = json.loads(line)
        except json.JSONDecodeError:
            continue
    if last is None:
        try:
            last = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"--under stdout is not JSON: {exc}") from exc
    if not isinstance(last, dict):
        raise ValueError("--under stdout JSON must be an object")
    fv = as_number(last.get("fair_value"))
    if fv is None:
        raise ValueError("--under JSON missing numeric fair_value")
    return fv


def run_fair_value_under(
    script: Path,
    overrides: dict[str, Any],
    *,
    python_exe: str | None = None,
) -> float:
    """Run `python valuation.py --under '{...}'` and return fair_value."""
    if not script.is_file():
        raise FileNotFoundError(f"compute script missing: {script}")
    exe = python_exe or sys.executable
    payload = json.dumps(overrides, separators=(",", ":"))
    proc = subprocess.run(
        [exe, str(script), "--under", payload],
        capture_output=True,
        text=True,
        timeout=UNDER_TIMEOUT_S,
        cwd=str(script.parent),
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()[:400]
        raise RuntimeError(
            f"{script.name} --under exited {proc.returncode}: {err or 'no stderr'}"
        )
    return parse_under_stdout(proc.stdout)


def _compute_script_path(session: Path, vm: dict[str, Any]) -> Path | None:
    rel = vm.get("compute_script")
    if not isinstance(rel, str) or not rel.strip():
        return None
    rel = rel.replace("\\", "/").lstrip("/")
    p = session / rel
    if p.is_file():
        return p
    alt = session / "data" / "compute" / Path(rel).name
    return alt if alt.is_file() else p


def shock_dials(vm: dict[str, Any]) -> dict[str, dict[str, float]] | None:
    """Named dials with current value. lo/hi optional for reverse-stress."""
    ss = vm.get("shock_surface")
    if not isinstance(ss, dict):
        return None
    dials = ss.get("dials")
    if not isinstance(dials, dict) or not dials:
        return None
    out: dict[str, dict[str, float]] = {}
    for name, spec in dials.items():
        if not isinstance(name, str) or not name.strip():
            continue
        if isinstance(spec, dict):
            val = as_number(spec.get("value"))
            if val is None:
                continue
            row: dict[str, float] = {"value": val}
            lo = as_number(spec.get("lo"))
            hi = as_number(spec.get("hi"))
            if lo is not None:
                row["lo"] = lo
            if hi is not None:
                row["hi"] = hi
            out[name] = row
        else:
            val = as_number(spec)
            if val is not None:
                out[name] = {"value": val}
    return out or None


def surface_values(vm: dict[str, Any]) -> dict[str, float] | None:
    dials = shock_dials(vm)
    if not dials:
        return None
    return {k: d["value"] for k, d in dials.items()}


def _shock_of(doc: dict[str, Any]) -> dict[str, Any] | None:
    shock = doc.get("shock")
    if isinstance(shock, dict) and shock:
        return shock
    return None


def _base_bear(vm: dict[str, Any]) -> tuple[float | None, float | None]:
    fv = vm.get("fair_value") if isinstance(vm.get("fair_value"), dict) else {}
    return as_number(fv.get("base")), as_number(fv.get("bear"))


def merged_overrides(vm: dict[str, Any], shock: dict[str, Any]) -> dict[str, float]:
    """Replace-not-delta: start from current dials, overwrite named keys."""
    current = surface_values(vm)
    if current is None:
        raise ValueError("shock_surface.dials missing")
    unknown = sorted(set(shock) - set(current))
    if unknown:
        raise ValueError(f"shock keys not on shock_surface.dials: {unknown}")
    out = dict(current)
    for key, raw in shock.items():
        n = as_number(raw)
        if n is None:
            raise ValueError(f"shock[{key!r}] is not a number")
        out[str(key)] = n
    return out


def apply_one(
    session: Path,
    scenario: dict[str, Any],
    vm: dict[str, Any],
    *,
    python_exe: str | None = None,
) -> dict[str, Any]:
    """Return the applied block for one merged scenario. Does not invent shocks."""
    base, bear = _base_bear(vm)
    if base is None or base <= 0:
        raise ValueError("valuation_model.fair_value.base missing")
    shock = _shock_of(scenario)
    if shock is None:
        raise ValueError("merged scenario missing shock object")
    overrides = merged_overrides(vm, shock)
    script = _compute_script_path(session, vm)
    if script is None or not script.is_file():
        raise FileNotFoundError("valuation compute_script missing")
    stressed = run_fair_value_under(script, overrides, python_exe=python_exe)
    hair = haircut_from_values(base, stressed)
    numeric = False
    if bear is not None:
        numeric = restates_bear_numeric(stressed, base, bear)
    return {
        "stressed_fv": stressed,
        "fair_value_haircut_pct": hair,
        "restates_bear": numeric,
        "compute_script": str(script.relative_to(session)).replace("\\", "/"),
    }


def apply_session(
    session: Path,
    *,
    python_exe: str | None = None,
) -> list[dict[str, Any]]:
    """Apply the merged shock list. Writes one applied block per scenario.

    risk_bridge.json must already hold merged shocks (no guessed haircuts).
    Raw stress_*.json files are not read for FV.
    """
    vm, err = load_json(session / "data" / "valuation_model.json")
    if err or not isinstance(vm, dict):
        raise FileNotFoundError(f"valuation_model.json: {err or 'missing'}")
    rb_path = session / "registry" / "risk_bridge.json"
    rb, rerr = load_json(rb_path)
    if rerr or not isinstance(rb, dict):
        raise FileNotFoundError(
            "merge risk_bridge.json before apply "
            "(shocks only; haircuts come from fair_value_under)"
        )
    st = rb.get("stress_test")
    if not isinstance(st, dict):
        st = {}
        rb["stress_test"] = st
    scenarios = st.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("risk_bridge.stress_test.scenarios missing")
    summaries: list[dict[str, Any]] = []
    for sc in scenarios:
        if not isinstance(sc, dict):
            continue
        applied = apply_one(session, sc, vm, python_exe=python_exe)
        sc["applied"] = applied
        summaries.append({"name": sc.get("name") or sc.get("scenario_id"), **applied})
    st["reverse_stress"] = compute_reverse_stress(
        session, vm, python_exe=python_exe
    )
    rb_path.write_text(json.dumps(rb, indent=2) + "\n", encoding="utf-8")
    return summaries


def _freeze_price(session: Path) -> float | None:
    snap, err = load_json(session / "data" / "price_snapshot.json")
    if err or not isinstance(snap, dict):
        return None
    return as_number(snap.get("close") or snap.get("price") or snap.get("last"))


def _bisect_to_freeze(
    script: Path,
    base_vals: dict[str, float],
    key: str,
    current: float,
    target: float,
    freeze: float,
    *,
    python_exe: str | None,
) -> tuple[float, float] | None:
    """Walk current → target. Return (dial, fv) at first fv <= freeze."""

    def fv_at(x: float) -> float:
        ov = dict(base_vals)
        ov[key] = x
        return run_fair_value_under(script, ov, python_exe=python_exe)

    lo, hi = (current, target) if current < target else (target, current)
    f_lo = fv_at(lo)
    f_hi = fv_at(hi)
    if f_lo > freeze and f_hi > freeze:
        return None
    # Prefer the endpoint closer to current that still crosses.
    best_x = lo if f_lo <= freeze else hi
    best_f = f_lo if f_lo <= freeze else f_hi
    a, b = current, target
    fa = fv_at(a)
    for _ in range(REVERSE_STEPS):
        mid = (a + b) / 2.0
        fm = fv_at(mid)
        if fm <= freeze:
            best_x, best_f = mid, fm
            b = mid
        else:
            a, fa = mid, fm
            if fa <= freeze:
                best_x, best_f = a, fa
    return best_x, best_f


def compute_reverse_stress(
    session: Path,
    vm: dict[str, Any],
    *,
    python_exe: str | None = None,
) -> dict[str, Any]:
    """Smallest one-factor fair_value_under move that puts FV at or below freeze."""
    freeze = _freeze_price(session)
    if freeze is None or freeze <= 0:
        return {
            "none": True,
            "reason": "no freeze price on data/price_snapshot.json",
        }
    dials = shock_dials(vm)
    script = _compute_script_path(session, vm)
    if not dials or script is None or not script.is_file():
        return {
            "none": True,
            "freeze_price": freeze,
            "reason": "shock_surface.dials or compute_script missing",
        }
    base_vals = {k: d["value"] for k, d in dials.items()}
    hits: list[tuple[float, str, float, float]] = []
    for key, spec in dials.items():
        lo = spec.get("lo")
        hi = spec.get("hi")
        cur = spec["value"]
        if lo is None or hi is None:
            continue
        for end in (lo, hi):
            if end == cur:
                continue
            found = _bisect_to_freeze(
                script, base_vals, key, cur, end, freeze, python_exe=python_exe
            )
            if found is None:
                continue
            x, fv = found
            hits.append((abs(x - cur), key, x, fv))
    if not hits:
        return {
            "none": True,
            "erases": "mos_vs_freeze",
            "freeze_price": freeze,
            "reason": "no one-factor fair_value_under walk puts FV at or below freeze",
            "compute": "fair_value_under",
        }
    _delta, key, x, fv = min(hits, key=lambda t: t[0])
    return {
        "none": False,
        "erases": "mos_vs_freeze",
        "freeze_price": freeze,
        "dials": {key: x},
        "stressed_fv": fv,
        "compute": "fair_value_under",
    }


def check_shock_surface(session: Path) -> list[tuple[str, str, str]]:
    if not session_is_stress_book_runtime(session):
        return [
            (
                "SKIPPED",
                "shock_surface",
                "legacy/slim (harness_version < 2.44.0)",
            )
        ]
    vm, err = load_json(session / "data" / "valuation_model.json")
    if err or not isinstance(vm, dict):
        return [("FAIL", "shock_surface", "valuation_model.json required")]
    dials = shock_dials(vm)
    if not dials:
        return [
            (
                "FAIL",
                "shock_surface",
                "valuation_model.shock_surface.dials must map native dials "
                "to {value, lo?, hi?} (replace-not-delta)",
            )
        ]
    script = _compute_script_path(session, vm)
    if script is None or not script.is_file():
        return [("FAIL", "shock_surface", "compute_script missing")]
    base, _bear = _base_bear(vm)
    if base is None or base <= 0:
        return [("FAIL", "shock_surface", "fair_value.base missing")]
    try:
        under = run_fair_value_under(script, {})
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        return [
            (
                "FAIL",
                "shock_surface.under",
                f"fair_value_under({{}}) failed: {exc}",
            )
        ]
    if abs(under - base) > max(BASE_MATCH_ABS, abs(base) * BASE_MATCH_REL):
        return [
            (
                "FAIL",
                "shock_surface.under",
                f"fair_value_under({{}}) {under} must equal fair_value.base {base}",
            )
        ]
    return [("PASS", "shock_surface", f"{len(dials)} dial(s); --under {{}} matches base")]


def check_stress_applied(session: Path) -> list[tuple[str, str, str]]:
    if not session_is_stress_book_runtime(session):
        return [
            (
                "SKIPPED",
                "stress_applied",
                "legacy/slim (harness_version < 2.44.0)",
            )
        ]
    vm, verr = load_json(session / "data" / "valuation_model.json")
    rb, rerr = load_json(session / "registry" / "risk_bridge.json")
    if verr or not isinstance(vm, dict):
        return [("FAIL", "stress_applied", "valuation_model.json required")]
    if rerr or not isinstance(rb, dict):
        return [("FAIL", "stress_applied", "risk_bridge.json required")]
    base, _bear = _base_bear(vm)
    if base is None or base <= 0:
        return [("FAIL", "stress_applied", "fair_value.base missing")]
    st = rb.get("stress_test") if isinstance(rb.get("stress_test"), dict) else {}
    scenarios = st.get("scenarios") if isinstance(st, dict) else None
    if not isinstance(scenarios, list) or len(scenarios) < 5:
        return [("FAIL", "stress_applied", "need >=5 merged scenarios")]
    missing: list[str] = []
    guessed: list[str] = []
    for sc in scenarios:
        if not isinstance(sc, dict):
            continue
        name = str(sc.get("name") or "unnamed")
        shock = _shock_of(sc)
        applied = sc.get("applied") if isinstance(sc.get("applied"), dict) else {}
        sfv = as_number(applied.get("stressed_fv"))
        if shock is None:
            guessed.append(name)
        if sfv is None:
            missing.append(name)
            continue
        hair = as_number(applied.get("fair_value_haircut_pct"))
        expect = haircut_from_values(base, sfv)
        if hair is not None and abs(hair) > 1.0:
            hair = hair / 100.0
        if hair is None or abs(hair - expect) > 0.02:
            return [
                (
                    "FAIL",
                    "stress_applied.haircut",
                    f"{name}: applied haircut is display of 1-stressed_fv/base "
                    f"(got {hair}, expect {expect:.4f})",
                )
            ]
    if guessed:
        return [
            (
                "FAIL",
                "stress_applied.shock",
                "merged scenarios need a shock object (no guessed haircut): "
                f"{guessed[:4]}",
            )
        ]
    if missing:
        return [
            (
                "FAIL",
                "stress_applied",
                "run python -m packages.kd_research.stress_apply after merge "
                f"so each scenario has stressed_fv: {missing[:4]}",
            )
        ]
    rev = st.get("reverse_stress") if isinstance(st, dict) else None
    if not isinstance(rev, dict):
        return [
            (
                "FAIL",
                "stress_applied.reverse",
                "stress_test.reverse_stress required (none:true is legal)",
            )
        ]
    compute = str(rev.get("compute") or "")
    if rev.get("none") is not True and compute != "fair_value_under":
        return [
            (
                "FAIL",
                "stress_applied.reverse",
                "reverse_stress must come from fair_value_under, not the 4x4 grid",
            )
        ]
    return [("PASS", "stress_applied", f"{len(scenarios)} shocked-path scenarios")]


def main(argv: list[str] | None = None) -> int:
    import argparse

    from packages.kd_research.decision import UnappliedStressError, compute_stress_bind
    from packages.kd_research.paths import archive_root

    p = argparse.ArgumentParser(
        description="Apply Agent 5 fair_value_under to merged Phase 2.5 shocks."
    )
    p.add_argument("--ticker", required=True)
    p.add_argument("--date", required=True, help="session_key")
    p.add_argument("--archive-root", dest="archive", default=None)
    p.add_argument(
        "--bind-print",
        action="store_true",
        help="print compute_stress_bind JSON (does not edit decision.json)",
    )
    p.add_argument("--skip-apply", action="store_true")
    args = p.parse_args(argv)
    out_dir = Path(args.archive) if args.archive else archive_root()
    session = require_session(args.ticker, args.date, out_dir)
    if not args.skip_apply:
        apply_session(session)
    if args.bind_print:
        vm, _ = load_json(session / "data" / "valuation_model.json")
        rb, _ = load_json(session / "registry" / "risk_bridge.json")
        if not isinstance(vm, dict) or not isinstance(rb, dict):
            print("missing valuation_model or risk_bridge", file=sys.stderr)
            return 1
        try:
            print(json.dumps(compute_stress_bind(rb, vm), indent=2))
        except UnappliedStressError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

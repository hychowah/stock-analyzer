"""Join historical management promises (guidance) to realized actuals.

Used by Agent 2e for the management scorecard. Pure functions — no network.
Outcomes for open-ended ranges use inclusive bounds; the agent may override
with rationale when definitions differ (e.g. company non-GAAP vs GAAP).
"""

from __future__ import annotations

from typing import Any, Iterable


Outcome = str  # met | beat | miss | abandoned | too_early | unknown


def grade_range_promise(
    *,
    low: float | None,
    high: float | None,
    actual: float | None,
    higher_is_better: bool = True,
    tolerance_frac: float = 0.0,
) -> Outcome:
    """Grade a numeric guide against an actual.

    - If actual is None → ``unknown``
    - If both low and high set: actual in [low*(1-t), high*(1+t)] → ``met``;
      above high → ``beat`` if higher_is_better else ``miss``;
      below low → ``miss`` if higher_is_better else ``beat``.
    - If only high (ceiling, e.g. opex "below X"): actual <= high → met else miss
      (higher_is_better=False for cost ceilings is typical).
    - If only low (floor): actual >= low → met else miss when higher_is_better.
    """
    if actual is None:
        return "unknown"
    t = max(0.0, tolerance_frac)

    if low is not None and high is not None:
        lo = low * (1.0 - t) if low >= 0 else low * (1.0 + t)
        hi = high * (1.0 + t) if high >= 0 else high * (1.0 - t)
        # For negative guides, expand outward carefully — use absolute pad.
        if low < 0 or high < 0:
            span = abs(high - low)
            lo = low - span * t
            hi = high + span * t
        if lo <= actual <= hi:
            return "met"
        if actual > hi:
            return "beat" if higher_is_better else "miss"
        return "miss" if higher_is_better else "beat"

    if high is not None and low is None:
        hi = high * (1.0 + t) if high >= 0 else high
        if higher_is_better:
            # Unusual: ceiling as "at least this good" — treat as upper target
            if actual <= hi:
                return "met"
            return "beat"
        # Cost / opex ceiling
        if actual <= hi:
            return "met"
        return "miss"

    if low is not None and high is None:
        lo = low * (1.0 - t) if low >= 0 else low
        if higher_is_better:
            # Floor guide (e.g. revenue at least X)
            if actual < lo:
                return "miss"
            # Comfortably above floor → beat; otherwise met
            if actual > lo * (1.0 + max(t, 0.05)):
                return "beat"
            return "met"
        # Floor on a cost metric is rare: below floor is better
        if actual <= lo:
            return "met"
        return "miss"

    return "unknown"


def grade_point_promise(
    *,
    target: float | None,
    actual: float | None,
    higher_is_better: bool = True,
    tolerance_frac: float = 0.02,
) -> Outcome:
    """Grade a single-point guide (e.g. 'approximately $10B')."""
    if target is None or actual is None:
        return "unknown"
    tol = abs(target) * tolerance_frac
    if abs(actual - target) <= tol:
        return "met"
    if actual > target:
        return "beat" if higher_is_better else "miss"
    return "miss" if higher_is_better else "beat"


def hit_rate(outcomes: Iterable[str]) -> dict[str, Any]:
    """Compute quantitative hit rate over met|beat|miss only.

    ``beat`` counts as a hit (management delivered at least the guide).
    Returns ``{value, n, n_hit, n_miss}`` with value None if n==0.
    """
    counted = [o for o in outcomes if o in ("met", "beat", "miss")]
    n = len(counted)
    if n == 0:
        return {"value": None, "n": 0, "n_hit": 0, "n_miss": 0}
    n_hit = sum(1 for o in counted if o in ("met", "beat"))
    n_miss = sum(1 for o in counted if o == "miss")
    return {
        "value": n_hit / n,
        "n": n,
        "n_hit": n_hit,
        "n_miss": n_miss,
    }


def join_promises_to_actuals(
    promises: list[dict[str, Any]],
    actuals_by_period: dict[str, dict[str, float]],
    *,
    default_tolerance_frac: float = 0.0,
) -> list[dict[str, Any]]:
    """Join promise rows to actuals and attach computed ``outcome``.

    Each promise dict should include:
      - promise_id, promise_class, stated, stated_when, source_type
      - period: key into actuals_by_period (e.g. \"FY2025\", \"2025\")
      - metric: key inside that period's actuals dict (e.g. \"revenue\", \"capex\")
      - low, high, and/or target (optional floats)
      - higher_is_better (optional bool)
      - optional: too_early (bool), abandoned (bool)

    Actuals missing → outcome ``unknown`` unless too_early/abandoned flags set.
    Existing ``outcome`` is overwritten with the computed grade (caller may still
    override later with agent rationale).
    """
    rows: list[dict[str, Any]] = []
    for p in promises:
        row = dict(p)
        if row.get("abandoned"):
            row["outcome"] = "abandoned"
            row.setdefault("actual", None)
            rows.append(row)
            continue
        if row.get("too_early"):
            row["outcome"] = "too_early"
            row.setdefault("actual", None)
            rows.append(row)
            continue

        period = row.get("period")
        metric = row.get("metric")
        actual = None
        if period and metric and period in actuals_by_period:
            actual = actuals_by_period[period].get(metric)
        row["actual"] = actual

        hib = row.get("higher_is_better", True)
        tol = float(row.get("tolerance_frac", default_tolerance_frac))
        low = row.get("low")
        high = row.get("high")
        target = row.get("target")

        if target is not None and low is None and high is None:
            outcome = grade_point_promise(
                target=float(target),
                actual=float(actual) if actual is not None else None,
                higher_is_better=bool(hib),
                tolerance_frac=tol if tol > 0 else 0.02,
            )
        else:
            outcome = grade_range_promise(
                low=float(low) if low is not None else None,
                high=float(high) if high is not None else None,
                actual=float(actual) if actual is not None else None,
                higher_is_better=bool(hib),
                tolerance_frac=tol,
            )
        row["outcome"] = outcome
        if actual is not None and (low is not None or high is not None or target is not None):
            ref = target if target is not None else (
                (float(low) + float(high)) / 2.0 if low is not None and high is not None
                else (low if low is not None else high)
            )
            try:
                row["delta"] = float(actual) - float(ref)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                row["delta"] = None
        rows.append(row)
    return rows


def scorecard_summary(
    items: list[dict[str, Any]],
    *,
    pattern: str,
    valuation_implication: str,
    rationale: str,
    basis: str,
    transcript_coverage: str = "",
) -> dict[str, Any]:
    """Build ``credibility_summary`` block with scripted hit_rate_quantitative."""
    quant_classes = {
        "revenue",
        "opex",
        "opinc",
        "capex",
        "margin",
        "segment_loss",
        "capital_returns",
    }
    outcomes = [
        str(i.get("outcome"))
        for i in items
        if i.get("promise_class") in quant_classes
        or i.get("promise_class") is None
    ]
    # Prefer only rows that look quantitative (have actual or met/beat/miss)
    outcomes = [
        str(i.get("outcome"))
        for i in items
        if i.get("outcome") in ("met", "beat", "miss")
    ]
    hr = hit_rate(outcomes)
    hit_block: dict[str, Any] = {
        "value": hr["value"],
        "n": hr["n"],
        "rationale": (
            f"Hit rate counts met+beat over met/beat/miss quantitative rows "
            f"(n={hr['n']}, hits={hr['n_hit']}, misses={hr['n_miss']})."
        ),
        "basis": "packages/kd_research/promise_vs_actual.py::hit_rate on scorecard items",
    }
    return {
        "hit_rate_quantitative": hit_block,
        "pattern": pattern,
        "valuation_implication": valuation_implication,
        "rationale": rationale,
        "basis": basis,
        "transcript_coverage": transcript_coverage,
    }

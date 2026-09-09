"""Select by |value|, then order signed descending (gains top, losses bottom)."""

from __future__ import annotations

from typing import Any, Iterable


def _num(raw: Any) -> float:
    try:
        n = float(raw)
    except (TypeError, ValueError):
        return 0.0
    if n != n or n in (float("inf"), float("-inf")):
        return 0.0
    return n


def signed_bar_rows(
    pairs: Iterable[tuple[str, float]],
    *,
    top_n: int = 20,
    other_label: str = "other",
) -> list[dict[str, Any]]:
    """Keep the largest names by |value|; display gains at top, losses at bottom.

    Remainder nets into ``other`` (omitted when empty or zero). Bar width is
    peak-normalized among the displayed rows, including ``other``.
    """
    by: dict[str, float] = {}
    for name, value in pairs:
        key = str(name)
        by[key] = by.get(key, 0.0) + _num(value)
    ranked = sorted(by.items(), key=lambda p: abs(p[1]), reverse=True)
    top, rest = ranked[:top_n], ranked[top_n:]
    displayed: list[tuple[str, float]] = list(top)
    if rest:
        net = sum(v for _, v in rest)
        if net != 0.0:
            displayed.append((other_label, net))
    displayed.sort(key=lambda p: (-p[1], p[0]))
    peak = max((abs(v) for _, v in displayed), default=0.0)
    out: list[dict[str, Any]] = []
    for name, pl in displayed:
        sign = "pos" if pl > 0 else ("neg" if pl < 0 else "zero")
        out.append(
            {
                "name": name,
                "pl": pl,
                "bar_pct": (100.0 * abs(pl) / peak) if peak > 0 else 0.0,
                "sign": sign,
            }
        )
    return out

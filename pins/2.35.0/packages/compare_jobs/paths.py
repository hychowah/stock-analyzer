"""Compare packet paths under archive/comparisons/ (not Mode A session paths)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from packages.kd_research.paths import (
    COMPARE_ID_RE,
    DATE_DIR_RE,
    archive_root,
    parse_compare_id,
    session_dir_nonempty,
)


def comparisons_root(output_dir: Path | str | None = None) -> Path:
    """Return archive/comparisons/ — append-only session-valuation-audit packets."""
    return archive_root(output_dir) / "comparisons"


def ticker_comparisons(ticker: str, output_dir: Path | str | None = None) -> Path:
    return comparisons_root(output_dir) / str(ticker).strip().upper()


def compare_id(ticker: str, packet_key: str) -> str:
    return f"compare:{str(ticker).strip().upper()}:{packet_key}"


def make_compare_packet_key(
    asof: str,
    session_a: str,
    session_b: str,
    replicate: int | None = None,
) -> str:
    if not DATE_DIR_RE.match(asof):
        raise ValueError(f"asof must be YYYY-MM-DD, got {asof!r}")
    a = str(session_a).strip()
    b = str(session_b).strip()
    if not a or not b:
        raise ValueError("session_a and session_b are required")
    if "/" in a or "\\" in a or "/" in b or "\\" in b:
        raise ValueError("session keys must not contain path separators")
    key = f"{asof}__{a}_vs_{b}"
    if replicate is None or replicate < 2:
        return key
    return f"{key}__r{int(replicate)}"


def compare_packet_dir(
    ticker: str,
    packet_key: str,
    output_dir: Path | str | None = None,
) -> Path:
    return ticker_comparisons(ticker, output_dir) / packet_key


def allocate_compare_key(
    ticker: str,
    session_a: str,
    session_b: str,
    *,
    asof: str | None = None,
    output_dir: Path | str | None = None,
) -> str:
    day = asof or date.today().isoformat()
    if not DATE_DIR_RE.match(day):
        raise ValueError(f"asof must be YYYY-MM-DD, got {day!r}")
    plain = make_compare_packet_key(day, session_a, session_b)
    if not session_dir_nonempty(compare_packet_dir(ticker, plain, output_dir)):
        return plain
    for n in range(2, 1000):
        candidate = make_compare_packet_key(day, session_a, session_b, replicate=n)
        if not session_dir_nonempty(compare_packet_dir(ticker, candidate, output_dir)):
            return candidate
    raise RuntimeError(
        f"Could not allocate compare packet for {ticker.upper()} {session_a} vs {session_b}"
    )

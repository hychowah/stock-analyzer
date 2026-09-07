"""In-flight Analyze names for the Runs banner.

pages.py must not import research_jobs. This module returns [{ticker, href}].
"""

from __future__ import annotations

from typing import Any

from apps.analysis_web.config import archive_root

_LIVE = frozenset({"running", "queued"})


def running_analyzes(*, cap: int = 3) -> tuple[list[dict[str, str]], int]:
    """Live Analyze jobs as ticker links. extra is count beyond cap."""
    from packages.research_jobs.jobs import list_analyzes

    rows: list[dict[str, Any]] = list_analyzes(archive_root(), refresh=False)
    live = [
        j
        for j in rows
        if str(j.get("status") or "") in _LIVE
        and str(j.get("ticker") or "").strip()
        and str(j.get("analyze_id") or "").strip()
    ]
    extra = max(0, len(live) - cap)
    out: list[dict[str, str]] = []
    for job in live[:cap]:
        ticker = str(job.get("ticker") or "").strip()
        aid = str(job.get("analyze_id") or "").strip()
        out.append({"ticker": ticker, "href": f"/analyze/{aid}"})
    return out, extra

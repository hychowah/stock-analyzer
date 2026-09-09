"""Walk both job planes. The next UI process is the recovery agent.

Does not kill Grok. Does not live in supervise.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def reconcile_jobs(archive_root: Path) -> dict[str, list[dict[str, Any]]]:
    """Refresh Analyze and Compare; continue interrupted starts."""
    from packages.compare_jobs.jobs import reconcile_compare_jobs
    from packages.research_jobs.jobs import reconcile_analyze_jobs

    return {
        "analyze": reconcile_analyze_jobs(archive_root),
        "compare": reconcile_compare_jobs(archive_root),
    }

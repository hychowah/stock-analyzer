"""Mode A Analyze jobs (append-only archive/research_jobs/).

FastAPI/Mode B schedules; Grok writes archive/research. Does not invent FV.
"""

from __future__ import annotations

from packages.research_jobs.jobs import (
    AnalyzeArchiveRootError,
    AnalyzeBusy,
    AnalyzeDiscardRefused,
    AnalyzeError,
    AnalyzeGrokMissing,
    AnalyzeNotFound,
    AnalyzeResumeConflict,
    AnalyzeRunbookMissing,
    AnalyzeTickerError,
    AnalyzeValidationError,
    FakeAnalyzeSpawnBackend,
    cancel_analyze,
    discard_analyze,
    env_archive_is_non_default,
    get_analyze,
    refuse_http_analyze,
    list_analyzes,
    reconcile_analyze_jobs,
    resume_analyze,
    start_analyze,
)

__all__ = [
    "AnalyzeArchiveRootError",
    "AnalyzeBusy",
    "AnalyzeDiscardRefused",
    "AnalyzeError",
    "AnalyzeGrokMissing",
    "AnalyzeNotFound",
    "AnalyzeResumeConflict",
    "AnalyzeRunbookMissing",
    "AnalyzeTickerError",
    "AnalyzeValidationError",
    "FakeAnalyzeSpawnBackend",
    "cancel_analyze",
    "discard_analyze",
    "env_archive_is_non_default",
    "get_analyze",
    "refuse_http_analyze",
    "list_analyzes",
    "reconcile_analyze_jobs",
    "resume_analyze",
    "start_analyze",
]

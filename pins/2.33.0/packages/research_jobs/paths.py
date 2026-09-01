"""Analyze job paths under archive/research_jobs/ (not Mode A session paths)."""

from __future__ import annotations

from pathlib import Path

from packages.kd_research.paths import ANALYZE_ID_RE, archive_root, parse_analyze_id

UI_SCHEDULED_HEADING = "## UI-scheduled runs (read this first)"


def research_jobs_root(output_dir: Path | str | None = None) -> Path:
    """Return archive/research_jobs/ — Analyze control plane (not a catalog source)."""
    return archive_root(output_dir) / "research_jobs"


def ticker_jobs(ticker: str, output_dir: Path | str | None = None) -> Path:
    return research_jobs_root(output_dir) / str(ticker).strip().upper()


def analyze_id(ticker: str, session_key: str) -> str:
    return f"analyze:{str(ticker).strip().upper()}:{session_key}"


def analyze_job_dir(
    ticker: str,
    session_key: str,
    output_dir: Path | str | None = None,
) -> Path:
    return ticker_jobs(ticker, output_dir) / session_key

"""Process identity for the Analysis UI (boot git SHA, not catalog).

Captured once per ``create_app()`` so /health and SSE hello stay stable
until this interpreter is replaced. A later ``git commit`` must not change
the SHA this process reports — that would loop live.js reloads without a
new UI.

Not a catalog fingerprint. ``harness_version=live`` jobs use the workspace
tree; this module does not freeze or re-spawn them.
"""

from __future__ import annotations

from packages.kd_research.provenance import git_head_sha


def boot_git_sha() -> str | None:
    """Git HEAD at process boot. None if git is unreadable."""
    return git_head_sha()

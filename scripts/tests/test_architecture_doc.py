"""ARCHITECTURE.md is the human map; it must exist and name live packages/apps."""

from __future__ import annotations

import unittest
from pathlib import Path

from packages.kd_research.paths import PROJECT_ROOT as ROOT

ARCH = ROOT / "ARCHITECTURE.md"

# Stable contract with ARCHITECTURE.md. Rename only with a matching edit here.
REQUIRED_HEADINGS = (
    "## What this system is",
    "## Two modes",
    "## The data plane",
    "## How a research run happens",
    "## How the product reads research",
    "## Code map",
    "## The website",
    "## Identity",
    "## Invariants",
    "## Keeping this document current",
)

ARCHIVE_PLANES = (
    "archive/research/",
    "archive/outcomes/",
    "archive/catalog/",
    "archive/library/",
    "archive/comparisons/",
    "archive/research_jobs/",
)


def _top_level_dirs(parent: Path) -> list[str]:
    names: list[str] = []
    if not parent.is_dir():
        return names
    for p in sorted(parent.iterdir()):
        if not p.is_dir():
            continue
        if p.name.startswith(".") or p.name.startswith("__"):
            continue
        names.append(p.name)
    return names


class ArchitectureDocTests(unittest.TestCase):
    def test_file_exists_and_has_required_headings(self):
        self.assertTrue(ARCH.is_file(), "ARCHITECTURE.md missing at repo root")
        text = ARCH.read_text(encoding="utf-8")
        self.assertGreater(len(text.splitlines()), 80)
        for heading in REQUIRED_HEADINGS:
            self.assertIn(heading, text, f"missing heading: {heading}")

    def test_names_every_package_and_app(self):
        text = ARCH.read_text(encoding="utf-8")
        for name in _top_level_dirs(ROOT / "packages"):
            self.assertIn(
                name,
                text,
                f"packages/{name} is not named in ARCHITECTURE.md",
            )
        for name in _top_level_dirs(ROOT / "apps"):
            self.assertIn(
                name,
                text,
                f"apps/{name} is not named in ARCHITECTURE.md",
            )

    def test_names_archive_planes_and_modes(self):
        text = ARCH.read_text(encoding="utf-8")
        for plane in ARCHIVE_PLANES:
            self.assertIn(plane, text, f"data plane {plane} missing")
        self.assertIn("Mode A", text)
        self.assertIn("Mode B", text)
        self.assertIn("research:{TICKER}:{session_key}", text)

    def test_router_and_mode_b_point_here(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        eng = (ROOT / "eng" / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("ARCHITECTURE.md", agents)
        self.assertIn("ARCHITECTURE.md", eng)
        self.assertIn("Keep `ARCHITECTURE.md` current", agents)
        self.assertIn("Keep `ARCHITECTURE.md` current", eng)

    def test_commit_duty_is_explicit(self):
        text = ARCH.read_text(encoding="utf-8")
        self.assertIn("Duty on every commit", text)
        self.assertIn("same change set", text)


if __name__ == "__main__":
    unittest.main()

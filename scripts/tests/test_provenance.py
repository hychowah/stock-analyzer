"""Tests for harness VERSION identity and provenance capture."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.kd_research.provenance import (  # noqa: E402
    VERSION_PATH_POSIX,
    capture_harness_provenance,
    is_research_runtime_path,
    load_harness_identity,
    paths_require_version_bump,
)


class LoadIdentityTests(unittest.TestCase):
    def test_load_from_repo_version_file(self):
        ident = load_harness_identity(ROOT)
        self.assertTrue(ident["harness_version"])
        self.assertFalse(ident["harness_version"].endswith("unversioned"))
        self.assertTrue(ident["harness_spec"])

    def test_load_json_version_in_temp(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "harness").mkdir()
            (root / "harness" / "VERSION").write_text(
                json.dumps({"harness_version": "9.8.7", "harness_spec": "v9"}),
                encoding="utf-8",
            )
            ident = load_harness_identity(root)
            self.assertEqual(ident["harness_version"], "9.8.7")
            self.assertEqual(ident["harness_spec"], "v9")

    def test_load_plain_text_version(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "harness").mkdir()
            (root / "harness" / "VERSION").write_text("3.2.1\n", encoding="utf-8")
            ident = load_harness_identity(root)
            self.assertEqual(ident["harness_version"], "3.2.1")


class CaptureTests(unittest.TestCase):
    def test_capture_always_has_identity_fields(self):
        prov = capture_harness_provenance(ROOT)
        self.assertIn("harness_version", prov)
        self.assertTrue(prov["harness_version"])
        self.assertTrue(prov["harness_git_sha"])  # real sha or "unknown"
        self.assertIn(prov["harness_dirty"], (True, False))
        self.assertEqual(prov["harness_spec"], load_harness_identity(ROOT)["harness_spec"])

    def test_capture_unknown_sha_when_git_missing(self):
        with mock.patch(
            "scripts.kd_research.provenance.git_head_sha", return_value=None
        ), mock.patch(
            "scripts.kd_research.provenance.git_is_dirty", return_value=None
        ):
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                (root / "harness").mkdir()
                (root / "harness" / "VERSION").write_text(
                    '{"harness_version":"1.0.0","harness_spec":"v1"}',
                    encoding="utf-8",
                )
                prov = capture_harness_provenance(root)
                self.assertEqual(prov["harness_git_sha"], "unknown")
                self.assertIs(prov["harness_dirty"], True)
                self.assertEqual(prov["harness_version"], "1.0.0")


class RuntimePathTests(unittest.TestCase):
    def test_research_runtime_paths(self):
        self.assertTrue(is_research_runtime_path("harness/RESEARCH_AGENTS.md"))
        self.assertTrue(is_research_runtime_path("scripts/kd_research/gates.py"))
        self.assertTrue(is_research_runtime_path("templates/audit.schema.json"))
        self.assertTrue(is_research_runtime_path("sector_banking.md"))
        self.assertTrue(is_research_runtime_path("region_us.md"))
        self.assertFalse(is_research_runtime_path("harness/research/README.md"))
        self.assertFalse(is_research_runtime_path("apps/analysis_web/app.py"))
        self.assertFalse(is_research_runtime_path("eng/AGENTS.md"))

    def test_version_bump_required(self):
        needs, paths = paths_require_version_bump(
            ["harness/RESEARCH_AGENTS.md", "apps/analysis_web/app.py"]
        )
        self.assertTrue(needs)
        self.assertIn("harness/RESEARCH_AGENTS.md", paths)

    def test_version_only_change_does_not_require_bump_logic(self):
        # VERSION alone is not "runtime without version"
        needs, paths = paths_require_version_bump([VERSION_PATH_POSIX])
        self.assertFalse(needs)
        self.assertEqual(paths, [])

    def test_ui_only_no_bump(self):
        needs, _ = paths_require_version_bump(
            ["apps/analysis_web/app.py", "packages/catalog_api/client.py"]
        )
        self.assertFalse(needs)


class ScaffoldManifestTests(unittest.TestCase):
    def test_scaffold_writes_version_and_sha(self):
        from scripts.scaffold_session import scaffold

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # minimal files for provenance hashes
            (root / "harness").mkdir()
            (root / "harness" / "VERSION").write_text(
                json.dumps({"harness_version": "2.1.0", "harness_spec": "v2"}),
                encoding="utf-8",
            )
            (root / "AGENTS.md").write_text("# router\n", encoding="utf-8")
            (root / "harness" / "RESEARCH_AGENTS.md").write_text("# law\n", encoding="utf-8")
            (root / "harness" / "agent_prompts.md").write_text("# p\n", encoding="utf-8")

            with mock.patch(
                "scripts.scaffold_session.capture_harness_provenance",
                return_value={
                    "harness_version": "2.1.0",
                    "harness_spec": "v2",
                    "harness_git_sha": "abc123def",
                    "harness_dirty": False,
                    "agents_md_sha256": "aa",
                    "research_agents_sha256": "bb",
                    "prompts_sha256": "cc",
                    "version_file_sha256": "dd",
                },
            ):
                session = scaffold("TESTV", "2099-01-01", output_dir=str(root))
            man = json.loads((session / "meta" / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(man["harness_version"], "2.1.0")
            self.assertEqual(man["harness_git_sha"], "abc123def")
            self.assertIs(man["harness_dirty"], False)


if __name__ == "__main__":
    unittest.main()

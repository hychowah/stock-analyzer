"""Pin resolve, publish, spawn_env, identity (no Grok)."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.paths import PROJECT_ROOT as ROOT
from packages.kd_research.provenance import capture_harness_provenance, load_harness_identity

from packages.harness_pin.pin import (
    LIVE,
    PinError,
    UnknownVersion,
    list_versions,
    publish,
    resolve,
)


def _write_mini_runtime(ws: Path, version: str) -> None:
    (ws / "harness").mkdir(parents=True)
    (ws / "packages").mkdir()
    (ws / "scripts").mkdir()
    (ws / "AGENTS.md").write_text("# router\n", encoding="utf-8")
    (ws / "harness" / "VERSION").write_text(
        json.dumps({"harness_version": version, "harness_spec": "v2"}),
        encoding="utf-8",
    )
    (ws / "harness" / "RESEARCH_AGENTS.md").write_text("# law\n", encoding="utf-8")
    (ws / "harness" / "agent_prompts.md").write_text(
        "conventions\n\n### Agent orchestrator\nbody\n",
        encoding="utf-8",
    )
    (ws / "scripts" / "scaffold_session.py").write_text("# stub\n", encoding="utf-8")


class HarnessPinTests(unittest.TestCase):
    def test_list_includes_live_first(self) -> None:
        names = list_versions(ROOT)
        self.assertEqual(names[0], LIVE)
        ident = load_harness_identity(ROOT)
        if (ROOT / "pins" / ident["harness_version"]).is_dir():
            self.assertIn(ident["harness_version"], names)

    def test_resolve_live(self) -> None:
        pin = resolve("live", workspace=ROOT)
        self.assertEqual(pin.version, LIVE)
        self.assertEqual(pin.root, ROOT)
        env = pin.spawn_env({"PYTHONPATH": "/old", "KEEP": "1"}, ROOT / "archive")
        self.assertEqual(env["PYTHONPATH"], str(ROOT))
        self.assertEqual(env["KEEP"], "1")
        self.assertTrue(str(env["ARCHIVE_ROOT"]).endswith("archive") or "archive" in env["ARCHIVE_ROOT"])

    def test_resolve_unknown(self) -> None:
        with self.assertRaises(UnknownVersion):
            resolve("9.9.9", workspace=ROOT)
        with self.assertRaises(UnknownVersion):
            resolve("not-a-version", workspace=ROOT)

    def test_publish_and_resolve_tmp(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            _write_mini_runtime(ws, "3.1.4")
            dest = publish(ws)
            self.assertEqual(dest, ws / "pins" / "3.1.4")
            self.assertTrue((dest / "PIN.json").is_file())
            self.assertTrue((dest / "harness" / "VERSION").is_file())
            self.assertFalse((dest / "pins").exists())
            meta = json.loads((dest / "PIN.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["harness_version"], "3.1.4")
            pin = resolve("3.1.4", workspace=ws)
            self.assertEqual(pin.root, dest)
            ident = pin.identity()
            self.assertEqual(ident["harness_version"], "3.1.4")
            self.assertIs(ident["harness_dirty"], False)
            self.assertEqual(ident["harness_git_sha"], meta["copied_from_sha"])
            with self.assertRaises(PinError):
                publish(ws)
            names = list_versions(ws)
            self.assertEqual(names, [LIVE, "3.1.4"])

    def test_identity_does_not_git_probe_pin_folder(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            _write_mini_runtime(ws, "4.0.0")
            dest = publish(ws)
            meta = json.loads((dest / "PIN.json").read_text(encoding="utf-8"))
            meta["copied_from_sha"] = "abc123deadbeef"
            (dest / "PIN.json").write_text(json.dumps(meta) + "\n", encoding="utf-8")
            pin = resolve("4.0.0", workspace=ws)
            ident = pin.identity()
            self.assertEqual(ident["harness_git_sha"], "abc123deadbeef")
            self.assertIs(ident["harness_dirty"], False)

    def test_live_capture_still_has_git_fields(self) -> None:
        prov = capture_harness_provenance(ROOT)
        self.assertTrue(prov["harness_git_sha"])
        self.assertIn(prov["harness_dirty"], (True, False))


if __name__ == "__main__":
    unittest.main()

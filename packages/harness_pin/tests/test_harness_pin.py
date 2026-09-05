"""Pin resolve, publish, spawn_env, identity (no Grok)."""

from __future__ import annotations

import inspect
import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.paths import PROJECT_ROOT as ROOT
from packages.kd_research.provenance import capture_harness_provenance, load_harness_identity

from packages.harness_pin.pin import (
    COPY_REL,
    LIVE,
    PinError,
    UnknownVersion,
    list_versions,
    publish,
    resolve,
)

_SCAFFOLD_STUB = """\
import argparse
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--ticker")
p.add_argument("--date")
p.add_argument("--output-dir")
p.add_argument("--orchestrator-model")
p.add_argument("--skip-ticker-check", action="store_true")
p.add_argument("--slug")
p.add_argument("--subagent-model")
p.add_argument("--notes")
p.add_argument("--no-auto-replicate", action="store_true")
args = p.parse_args()
root = Path(args.output_dir) / "research" / args.ticker.upper() / args.date
root.mkdir(parents=True)
(root / "from_script").write_text("1", encoding="utf-8")
print(f"Session scaffolded: {root}")
"""


def _write_mini_runtime(ws: Path, version: str) -> None:
    (ws / "harness").mkdir(parents=True)
    (ws / "packages" / "kd_research").mkdir(parents=True)
    (ws / "packages" / "kd_research" / "tests").mkdir()
    (ws / "packages" / "catalog_api").mkdir()
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
    (ws / "packages" / "__init__.py").write_text("# packages\n", encoding="utf-8")
    (ws / "packages" / "kd_research" / "__init__.py").write_text(
        "# kd_research\n", encoding="utf-8"
    )
    (ws / "packages" / "kd_research" / "tests" / "test_skip.py").write_text(
        "# not copied\n", encoding="utf-8"
    )
    (ws / "packages" / "catalog_api" / "__init__.py").write_text(
        "# not copied\n", encoding="utf-8"
    )
    (ws / "scripts" / "eng_verify.py").write_text("# not copied\n", encoding="utf-8")
    for rel in COPY_REL:
        if not rel.startswith("scripts/"):
            continue
        path = ws / rel
        if path.name == "scaffold_session.py":
            path.write_text(_SCAFFOLD_STUB, encoding="utf-8")
        elif not path.exists():
            path.write_text("# stub\n", encoding="utf-8")


class HarnessPinTests(unittest.TestCase):
    def test_list_includes_live_first(self) -> None:
        names = list_versions(ROOT)
        self.assertEqual(names[0], LIVE)
        ident = load_harness_identity(ROOT)
        pin_dir = ROOT / "pins" / ident["harness_version"]
        if pin_dir.is_dir() and (pin_dir / "PIN.json").is_file():
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

    def test_resolve_published_requires_pin_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            _write_mini_runtime(ws, "3.1.4")
            dest = ws / "pins" / "3.1.4"
            dest.mkdir(parents=True)
            (dest / "harness").mkdir()
            (dest / "harness" / "VERSION").write_text(
                json.dumps({"harness_version": "3.1.4", "harness_spec": "v2"}),
                encoding="utf-8",
            )
            with self.assertRaises(UnknownVersion):
                resolve("3.1.4", workspace=ws)

    def test_publish_has_no_force(self) -> None:
        self.assertNotIn("force", inspect.signature(publish).parameters)

    def test_publish_and_resolve_tmp(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            _write_mini_runtime(ws, "3.1.4")
            dest = publish(ws)
            self.assertEqual(dest, ws / "pins" / "3.1.4")
            self.assertTrue((dest / "PIN.json").is_file())
            self.assertTrue((dest / "harness" / "VERSION").is_file())
            self.assertTrue((dest / "packages" / "__init__.py").is_file())
            self.assertTrue((dest / "packages" / "kd_research" / "__init__.py").is_file())
            self.assertTrue((dest / "scripts" / "scaffold_session.py").is_file())
            self.assertFalse((dest / "pins").exists())
            self.assertFalse((dest / "packages" / "catalog_api").exists())
            self.assertFalse((dest / "scripts" / "eng_verify.py").exists())
            self.assertFalse((dest / "packages" / "kd_research" / "tests").exists())
            meta = json.loads((dest / "PIN.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["harness_version"], "3.1.4")
            self.assertEqual(meta["contents"], list(COPY_REL))
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
            self.assertEqual(ident["copied_from_sha"], "abc123deadbeef")
            self.assertIs(ident["harness_dirty"], False)

    def test_live_capture_still_has_git_fields(self) -> None:
        prov = capture_harness_provenance(ROOT)
        self.assertTrue(prov["harness_git_sha"])
        self.assertIn(prov["harness_dirty"], (True, False))
        pin = resolve("live", workspace=ROOT)
        ident = pin.identity()
        self.assertEqual(ident["harness_git_sha"], prov["harness_git_sha"])
        self.assertEqual(ident["harness_dirty"], prov["harness_dirty"])

    def test_scaffold_research_live_and_published_run_script(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            archive = ws / "archive"
            archive.mkdir()
            _write_mini_runtime(ws, "5.0.0")
            live = resolve("live", workspace=ws)
            session = live.scaffold_research(
                "META", "2026-09-05", archive, orchestrator_model="grok-4.5"
            )
            self.assertTrue((session / "from_script").is_file())
            dest = publish(ws)
            self.assertTrue((dest / "scripts" / "scaffold_session.py").is_file())
            pin = resolve("5.0.0", workspace=ws)
            self.assertEqual(pin.version, "5.0.0")
            published_session = pin.scaffold_research(
                "COHR", "2026-09-05", archive, orchestrator_model="grok-4.5"
            )
            self.assertTrue((published_session / "from_script").is_file())
            self.assertNotEqual(session, published_session)


if __name__ == "__main__":
    unittest.main()

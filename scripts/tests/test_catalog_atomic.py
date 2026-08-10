"""Atomic catalog publish + incremental patch tests."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.kd_research.registry_io import atomic_write_text  # noqa: E402
from scripts.rebuild_catalog import patch_run_into_catalog, rebuild  # noqa: E402


class AtomicWriteTests(unittest.TestCase):
    def test_atomic_write_text(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "out.json"
            atomic_write_text(p, '{"ok": true}\n')
            self.assertEqual(p.read_text(), '{"ok": true}\n')
            atomic_write_text(p, '{"ok": false}\n')
            self.assertEqual(json.loads(p.read_text())["ok"], False)


class CatalogPatchTests(unittest.TestCase):
    def test_patch_upserts_run(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # Point helpers at temp project by monkeypatching ensure_archive_tree usage:
            # rebuild/patch use ensure_archive_tree() without output_dir — they use PROJECT_ROOT.
            # So we invoke _row path logic by calling rebuild with a custom approach:
            # Instead, unit-test patch against real project archive if present, else skip.
            from scripts.kd_research import paths as paths_mod

            # Create fake project layout under td and temporarily override PROJECT_ROOT
            old = paths_mod.PROJECT_ROOT
            try:
                paths_mod.PROJECT_ROOT = root
                # also rebuild_catalog imports ensure_archive_tree which uses PROJECT_ROOT
                sess = root / "archive" / "research" / "ZZZ" / "2026-01-01"
                (sess / "registry").mkdir(parents=True)
                (sess / "meta").mkdir(parents=True)
                (sess / "meta" / "prediction_snapshot.json").write_text(
                    json.dumps(
                        {
                            "audit_verdict": "PASS",
                            "fair_value": {"base": 10, "bear": 5, "bull": 15},
                            "margin_of_safety_pct": 1.0,
                            "primary_sector": "standard",
                        }
                    ),
                    encoding="utf-8",
                )
                # seed empty indexes then patch
                cat = root / "archive" / "catalog"
                cat.mkdir(parents=True)
                (cat / "runs_index.json").write_text(
                    json.dumps({"schema_version": 2, "updated_at": "t0", "runs": []}) + "\n"
                )
                (cat / "tickers_index.json").write_text(
                    json.dumps({"schema_version": 2, "updated_at": "t0", "tickers": {}}) + "\n"
                )

                # rebuild_catalog.ensure_archive_tree uses PROJECT_ROOT via paths
                result = patch_run_into_catalog("ZZZ", "2026-01-01", sess)
                self.assertEqual(result["mode"], "patch")
                self.assertEqual(result["n_runs"], 1)
                runs = json.loads((cat / "runs_index.json").read_text())["runs"]
                self.assertEqual(runs[0]["run_id"], "research:ZZZ:2026-01-01")
                # second patch updates in place
                (sess / "meta" / "prediction_snapshot.json").write_text(
                    json.dumps(
                        {
                            "audit_verdict": "FAIL",
                            "fair_value": {"base": 11},
                            "margin_of_safety_pct": 2.0,
                        }
                    ),
                    encoding="utf-8",
                )
                result2 = patch_run_into_catalog("ZZZ", "2026-01-01", sess)
                self.assertEqual(result2["n_runs"], 1)
                runs2 = json.loads((cat / "runs_index.json").read_text())["runs"]
                self.assertEqual(runs2[0]["audit_verdict"], "FAIL")
            finally:
                paths_mod.PROJECT_ROOT = old


if __name__ == "__main__":
    unittest.main()

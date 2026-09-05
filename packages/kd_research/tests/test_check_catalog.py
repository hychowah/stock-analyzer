"""Check catalog wiring: when-tags, unique ids, PATH_EXTRAS for workflow_spec."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.check_catalog import (
    PATH_EXTRAS,
    CheckRow,
    catalog_rows,
    run_catalog,
)
from packages.kd_research.check_catalog import _build_rows  # noqa: PLC2701
from packages.kd_research.gates import entry_checks
from packages.kd_research.library import BIND_REL, LIBRARY_SINCE
from packages.kd_research.operating_path import BRIEF_REL, OPPATH_SINCE
from packages.kd_research.street_bind import STREET_REL, STREET_SINCE
from packages.kd_research.workflow_spec import build_workflow_spec


def _stamp(session: Path, model: str = "grok-4.5") -> None:
    (session / "meta").mkdir(parents=True, exist_ok=True)
    (session / "meta" / "run_manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "run_id": "research:X:2026-01-01",
                "ticker": "X",
                "session_date": "2026-01-01",
                "orchestrator_model": model,
                "default_subagent_model": model,
                "harness_version": "2.33.0",
            }
        )
        + "\n",
        encoding="utf-8",
    )


class CheckCatalogTests(unittest.TestCase):
    def tearDown(self) -> None:
        import packages.kd_research.check_catalog as cc

        cc._ROWS = None

    def test_unknown_phase_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s)
            rows = entry_checks(s, "not_a_phase")
            self.assertEqual(rows[0][0], "FAIL")
            self.assertEqual(rows[0][1], "phase_id")

    def test_ids_unique(self) -> None:
        ids = [r.id for r in catalog_rows()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_synthetic_row_only_on_tagged_when(self) -> None:
        import packages.kd_research.check_catalog as cc

        def fake_run(_session: Path):
            return [("PASS", "synthetic_catalog", "ok")]

        extra = CheckRow("synthetic_catalog", frozenset({"2_parallel:entry"}), fake_run)
        cc._ROWS = _build_rows() + (extra,)
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s)
            entry_ids = {r[1] for r in run_catalog(s, "2_parallel:entry")}
            complete_ids = {r[1] for r in run_catalog(s, "2_parallel:complete")}
            self.assertIn("synthetic_catalog", entry_ids)
            self.assertNotIn("synthetic_catalog", complete_ids)

    def test_duplicate_id_raises(self) -> None:
        from packages.kd_research.check_catalog import _require_unique

        rows = _build_rows()
        dup = rows + (CheckRow(rows[0].id, frozenset({"0:entry"}), lambda _s: []),)
        with self.assertRaises(RuntimeError):
            _require_unique(dup)

    def test_path_extras_match_domain_constants(self) -> None:
        by = {(p.phase, p.rel): p for p in PATH_EXTRAS}
        self.assertEqual(by[("1_parallel", BIND_REL)].since, LIBRARY_SINCE)
        self.assertTrue(by[("1_parallel", BIND_REL)].required)
        self.assertEqual(by[("2_parallel", BRIEF_REL)].since, OPPATH_SINCE)
        self.assertEqual(by[("2_parallel", STREET_REL)].since, STREET_SINCE)
        self.assertFalse(by[("2_parallel", STREET_REL)].required)

    def test_workflow_spec_reads_path_extras(self) -> None:
        spec = build_workflow_spec()
        p2 = next(p for p in spec["phases"] if p["id"] == "2_parallel")
        paths = {row["path"] for row in p2["entry"]}
        self.assertIn(STREET_REL, paths)
        self.assertIn(BRIEF_REL, paths)
        p1 = next(p for p in spec["phases"] if p["id"] == "1_parallel")
        self.assertIn(BIND_REL, {row["path"] for row in p1["entry"]})
        src = Path(__file__).resolve().parents[1] / "workflow_spec.py"
        text = src.read_text(encoding="utf-8")
        self.assertNotIn("from packages.kd_research.street_bind import STREET_SINCE", text)
        self.assertIn("PATH_EXTRAS", text)

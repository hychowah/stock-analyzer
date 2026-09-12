"""Check catalog wiring: when-tags, unique ids, node extras for workflow_spec."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.check_catalog import (
    CheckRow,
    catalog_rows,
    run_catalog,
)
from packages.kd_research.check_catalog import _build_rows  # noqa: PLC2701
from packages.kd_research.gates import entry_checks
from packages.kd_research.library import BIND_REL, LIBRARY_SINCE
from packages.kd_research.operating_path import BRIEF_REL
from packages.kd_research.phase_graph import PHASE_GRAPH, PRICE_SNAPSHOT_REL, PRICE_SNAPSHOT_SINCE
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

    def test_session_full_exclusive_of_session_core(self) -> None:
        from packages.kd_research.check_catalog import WHEN_SESSION_CORE, WHEN_SESSION_FULL

        def fake_run(_session: Path):
            return [("PASS", "synthetic_session_full", "ok")]

        import packages.kd_research.check_catalog as cc

        extra = CheckRow("synthetic_session_full", frozenset({WHEN_SESSION_FULL}), fake_run)
        cc._ROWS = _build_rows() + (extra,)
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s)
            full_ids = {r[1] for r in run_catalog(s, WHEN_SESSION_FULL)}
            core_ids = {r[1] for r in run_catalog(s, WHEN_SESSION_CORE)}
            self.assertIn("synthetic_session_full", full_ids)
            self.assertNotIn("synthetic_session_full", core_ids)

    def test_live_session_tags(self) -> None:
        from packages.kd_research.check_catalog import WHEN_SESSION_CORE, WHEN_SESSION_FULL, catalog_rows

        by_id = {r.id: r.when for r in catalog_rows()}
        self.assertIn(WHEN_SESSION_FULL, by_id["street_entry"])
        self.assertNotIn(WHEN_SESSION_FULL, by_id["street_bind_2p"])
        self.assertEqual(by_id["agent4_core"], frozenset({WHEN_SESSION_CORE}))
        self.assertEqual(by_id["agent4_full"], frozenset({WHEN_SESSION_FULL}))
        self.assertEqual(by_id["wave1_full"], frozenset({WHEN_SESSION_FULL}))
        self.assertIn(WHEN_SESSION_FULL, by_id["cash_quality"])
        self.assertIn("2_parallel:complete", by_id["shock_surface_2p"])
        self.assertIn(WHEN_SESSION_FULL, by_id["shock_surface_2p"])
        self.assertIn("2_5:complete", by_id["stress_applied_25"])
        self.assertIn(WHEN_SESSION_FULL, by_id["stress_applied_25"])
        self.assertIn("4_parallel:complete", by_id["stress_bind_4p"])
        self.assertIn(WHEN_SESSION_FULL, by_id["stress_bind_4p"])
        self.assertIn("4_parallel:complete", by_id["stress_card_4p"])
        self.assertIn(WHEN_SESSION_FULL, by_id["stress_card_4p"])
        core_ids = {r.id for r in catalog_rows() if WHEN_SESSION_CORE in r.when}
        full_only = {
            r.id
            for r in catalog_rows()
            if WHEN_SESSION_FULL in r.when and WHEN_SESSION_CORE not in r.when
        }
        self.assertEqual(core_ids & full_only, set())

    def test_catalog_runs_are_named_functions(self) -> None:
        for row in catalog_rows():
            self.assertNotEqual(row.run.__name__, "<lambda>", row.id)
            self.assertFalse(hasattr(row, "since"))

    def test_street_hygiene_is_its_own_row(self) -> None:
        by_id = {r.id: r.when for r in catalog_rows()}
        self.assertIn("2_parallel:complete", by_id["street_hygiene"])
        self.assertIn("2_parallel:entry", by_id["street_hygiene"])
        self.assertIn("session_full", by_id["street_hygiene"])

    def test_catalog_source_does_not_import_gates(self) -> None:
        src = Path(__file__).resolve().parents[1] / "check_catalog.py"
        text = src.read_text(encoding="utf-8")
        self.assertNotIn("packages.kd_research.gates", text)

    def test_path_extras_live_on_the_node(self) -> None:
        by_phase = {n.phase_id: n for n in PHASE_GRAPH}
        extras_1p = {vp.rel: vp for vp in by_phase["1_parallel"].entry_versioned}
        extras_2p = {vp.rel: vp for vp in by_phase["2_parallel"].entry_versioned}
        self.assertEqual(extras_1p[BIND_REL].since, LIBRARY_SINCE)
        self.assertTrue(extras_1p[BIND_REL].required)
        self.assertNotIn(BRIEF_REL, extras_2p)
        self.assertEqual(extras_2p[STREET_REL].since, STREET_SINCE)
        self.assertFalse(extras_2p[STREET_REL].required)
        self.assertEqual(extras_2p[PRICE_SNAPSHOT_REL].since, PRICE_SNAPSHOT_SINCE)
        self.assertTrue(extras_2p[PRICE_SNAPSHOT_REL].required)

    def test_workflow_spec_reads_node_entry(self) -> None:
        spec = build_workflow_spec()
        p2 = next(p for p in spec["phases"] if p["id"] == "2_parallel")
        paths = {row["path"] for row in p2["entry"]}
        self.assertIn(STREET_REL, paths)
        self.assertIn(BRIEF_REL, paths)
        p1 = next(p for p in spec["phases"] if p["id"] == "1_parallel")
        self.assertIn(BIND_REL, {row["path"] for row in p1["entry"]})
        src = Path(__file__).resolve().parents[1] / "workflow_spec.py"
        text = src.read_text(encoding="utf-8")
        self.assertNotIn("from packages.kd_research.gates import", text)
        self.assertNotIn("PATH_EXTRAS", text)
        self.assertIn("dump_entry_rows", text)

"""Phase 1d version floor, complete gate, and Agent 5 hook rules."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.kd_research.gates import complete_checks, entry_checks  # noqa: E402
from scripts.kd_research.operating_path import (  # noqa: E402
    check_1d_complete,
    check_operating_path_hooks,
    designed_phase_ids,
    session_enforces_1d,
)
from scripts.kd_research.phase_graph import (  # noqa: E402
    check_phase_graph_entry,
    normalize_subagent_id,
    prerequisites_for,
    subagent_allowed_in_phase,
)
from scripts.kd_research.phase_status import build_phase_status_skeleton  # noqa: E402


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, str):
        path.write_text(obj, encoding="utf-8")
    else:
        path.write_text(json.dumps(obj), encoding="utf-8")


def _stamp(session: Path, version: str | None) -> None:
    man = {"status": "scaffolded", "orchestrator_model": "grok-4.5", "default_subagent_model": "grok-4.5"}
    if version:
        man["harness_version"] = version
    _write(session / "meta" / "run_manifest.json", man)


def _brief() -> dict:
    return {
        "ticker": "X",
        "session_date": "2026-01-01",
        "sources": {"workers": ["registry/raw/oppath_rev.json", "registry/raw/oppath_ind.json", "registry/raw/oppath_ol.json"]},
        "conflicts": [
            {
                "id": "fade_vs_flatten",
                "claim_a": "destock fade",
                "claim_b": "flatten mid",
                "status": "unresolved",
            }
        ],
        "rejected_shapes": [{"shape": "om_28_35", "why_rejected": "opex floor"}],
        "verify_rechecks": [
            {"path": "data/sp_financials.csv", "value": 1},
            {"path": "registry/latest_quarter.json", "value": 2},
            {"path": "registry/raw/oppath_rev.json", "value": 3},
        ],
    }


class VersionFloorTests(unittest.TestCase):
    def test_legacy_no_version_does_not_enforce(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, None)
            self.assertFalse(session_enforces_1d(s))
            self.assertNotIn("1d", designed_phase_ids(s))
            self.assertNotIn("1d", prerequisites_for("2_parallel", s))

    def test_new_runtime_enforces(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.6.0")
            self.assertTrue(session_enforces_1d(s))
            self.assertIn("1d", designed_phase_ids(s))
            self.assertIn("1d", prerequisites_for("2_parallel", s))

    def test_files_force_enforce_even_on_old_version(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.5.0")
            _write(s / "registry/operating_path_brief.json", _brief())
            self.assertTrue(session_enforces_1d(s))


class GraphBindingTests(unittest.TestCase):
    def test_aliases(self) -> None:
        self.assertEqual(normalize_subagent_id("revenue_growth"), "1d_rev")
        self.assertEqual(normalize_subagent_id("industry_trend"), "1d_ind")
        self.assertEqual(normalize_subagent_id("operating_leverage"), "1d_ol")
        self.assertEqual(normalize_subagent_id("oppath"), "1d_merge")
        ok, _ = subagent_allowed_in_phase("1d_rev", "1d")
        self.assertTrue(ok)
        ok, _ = subagent_allowed_in_phase("5", "1d")
        self.assertFalse(ok)
        ok, _ = subagent_allowed_in_phase("1d_merge", "2_parallel")
        self.assertFalse(ok)

    def test_skeleton_includes_1d(self) -> None:
        data = build_phase_status_skeleton("X", "2026-01-01")
        ids = [p["phase_id"] for p in data["phases"]]
        self.assertIn("1d", ids)
        self.assertEqual(ids[ids.index("1c") + 1], "1d")
        self.assertEqual(ids[ids.index("1d") + 1], "2_parallel")
        agents = next(p["agents"] for p in data["phases"] if p["phase_id"] == "1d")
        self.assertEqual(
            [a["agent_id"] for a in agents],
            ["1d_rev", "1d_ind", "1d_ol", "1d_merge"],
        )


class CompleteAndHooksTests(unittest.TestCase):
    def test_complete_fails_without_brief(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.6.0")
            rows = check_1d_complete(s)
            self.assertTrue(any(r[0] == "FAIL" and "operating_path_brief" in r[1] for r in rows), rows)

    def test_complete_passes_with_workers_and_rechecks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.6.0")
            for stem in ("rev", "ind", "ol"):
                _write(
                    s / f"registry/raw/oppath_{stem}.json",
                    {"ticker": "X", "session_date": "2026-01-01", "lens": "revenue_growth", "findings": ["a"]},
                )
            _write(s / "registry/operating_path_brief.json", _brief())
            rows = complete_checks(s, "1d")
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertEqual(fails, [], fails)

    def test_hooks_fail_when_all_noted_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _write(s / "registry/operating_path_brief.json", _brief())
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "operating_path_hooks": [
                        {"from": "brief", "action": "noted_only", "reason": "Acknowledged the brief only."}
                    ],
                },
            )
            rows = check_operating_path_hooks(s)
            self.assertTrue(any(r[0] == "FAIL" and "noted_only" in r[1] for r in rows), rows)

    def test_hooks_pass_used_as(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _write(s / "registry/operating_path_brief.json", _brief())
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "operating_path_hooks": [
                        {
                            "from": "registry/operating_path_brief.json",
                            "action": "used_as:dnc_growth_path",
                            "old": "steep fade",
                            "new": "flatten mid",
                            "reason": "Industry duration vs destock analog mapped to base flatten.",
                        }
                    ],
                },
            )
            rows = check_operating_path_hooks(s)
            self.assertFalse(any(r[0] == "FAIL" for r in rows), rows)

    def test_2_parallel_entry_requires_brief_on_new_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.6.0")
            data = build_phase_status_skeleton("X", "2026-01-01")
            for pid in ("orch", "0", "1_parallel", "1b", "1c", "1d"):
                for ph in data["phases"]:
                    if ph["phase_id"] == pid:
                        ph["status"] = "complete"
                        for ag in ph["agents"]:
                            ag["status"] = "complete"
            data["current_phase"] = "2_parallel"
            _write(s / "registry/phase_status.json", data)
            for rel in (
                "registry/sector_config.json",
                "registry/market_context.json",
                "registry/sec_filings.json",
                "registry/latest_quarter.json",
                "registry/filing_deep_dive.json",
            ):
                _write(s / rel, {"ticker": "X", "session_date": "2026-01-01"})
            _write(s / "data/sp_financials.csv", "ticker,item\nX,1\n")
            rows = entry_checks(s, "2_parallel", ticker="X", subagent_id="5")
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertTrue(any("operating_path_brief" in r[1] for r in fails), fails)

    def test_legacy_2_parallel_entry_skips_brief(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.5.0")
            data = build_phase_status_skeleton("X", "2026-01-01")
            # drop 1d row to mimic a 2.5.0 session file
            data["phases"] = [p for p in data["phases"] if p["phase_id"] != "1d"]
            for pid in ("orch", "0", "1_parallel", "1b", "1c"):
                for ph in data["phases"]:
                    if ph["phase_id"] == pid:
                        ph["status"] = "complete"
                        for ag in ph["agents"]:
                            ag["status"] = "complete"
            data["current_phase"] = "2_parallel"
            _write(s / "registry/phase_status.json", data)
            for rel in (
                "registry/sector_config.json",
                "registry/market_context.json",
                "registry/sec_filings.json",
                "registry/latest_quarter.json",
                "registry/filing_deep_dive.json",
            ):
                _write(s / rel, {"ticker": "X", "session_date": "2026-01-01"})
            _write(s / "data/sp_financials.csv", "ticker,item\nX,1\n")
            rows = check_phase_graph_entry(s, "2_parallel", subagent_id="5")
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertEqual(fails, [], fails)
            rows2 = entry_checks(s, "2_parallel", ticker="X", subagent_id="5")
            fails2 = [r for r in rows2 if r[0] == "FAIL"]
            self.assertEqual(fails2, [], fails2)


if __name__ == "__main__":
    unittest.main()

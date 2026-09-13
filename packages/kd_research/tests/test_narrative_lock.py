"""Phase 1e story lock gates (harness >= 3.4.0)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.narrative_lock import check_1e_complete, session_enforces_narrative
from packages.kd_research.phase_graph import graph_for_session, normalize_subagent_id
from packages.kd_research.tests.test_classification import _card, _stamp, _write


def _bind(**overrides: object) -> dict:
    payload: dict = {
        "ticker": "X",
        "stage_fit": "History-based story for a scaled profitable same-business firm.",
        "story": {"paragraph": "A compact going-concern story about this mature firm."},
        "map": {
            "tam": "core market grows with the economy",
            "target_om": "mid-cycle operating margin holds",
            "kc_path": "cost of capital fades toward mature peers",
        },
        "evidence_hooks": [
            {
                "from": "operating_path_brief.conflicts",
                "action": "map",
                "map_key": "tam",
                "reason": "Industry demand path is the TAM sentence.",
            },
            {
                "from": "filing_deep_dive.strategy_arc",
                "action": "reject",
                "reason": "New-segment pitch is merely possible, parked out of base.",
            },
        ],
    }
    payload.update(overrides)
    return payload


def _review(**overrides: object) -> dict:
    payload: dict = {
        "ticker": "X",
        "verdict": "PASS",
        "possible": ["adjacent geography"],
        "plausible": ["modest share gain"],
        "probable": ["in-line growth with reinvestment"],
        "fairy_tale": False,
        "wrong_stage": False,
        "iron_triangle": "pass",
        "rationale": "Constraints hold; reactions named; growth/reinvestment/risk cohere.",
    }
    payload.update(overrides)
    return payload


class NarrativeLockTests(unittest.TestCase):
    def test_legacy_skips_without_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.3.0")
            self.assertFalse(session_enforces_narrative(s))
            rows = check_1e_complete(s)
            self.assertTrue(any(r[0] == "SKIPPED" for r in rows), rows)

    def test_complete_requires_critic_pass(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.4.0")
            _write(s / "registry/classification.json", _card())
            _write(s / "registry/narrative_bind.json", _bind())
            _write(s / "registry/narrative_3p.json", _review(verdict="FAIL"))
            rows = check_1e_complete(s)
            self.assertTrue(any(r[0] == "FAIL" and r[1] == "1e.3p_verdict" for r in rows), rows)

    def test_complete_pass(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.4.0")
            _write(s / "registry/classification.json", _card())
            _write(s / "registry/narrative_bind.json", _bind())
            _write(s / "registry/narrative_3p.json", _review())
            rows = check_1e_complete(s)
            self.assertFalse(any(r[0] == "FAIL" for r in rows), rows)

    def test_noted_only_hooks_fail(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.4.0")
            _write(s / "registry/classification.json", _card())
            _write(
                s / "registry/narrative_bind.json",
                _bind(
                    evidence_hooks=[
                        {
                            "from": "operating_path_brief",
                            "action": "noted_only",
                            "reason": "saw it, did nothing with it",
                        }
                    ]
                ),
            )
            _write(s / "registry/narrative_3p.json", _review())
            rows = check_1e_complete(s)
            self.assertTrue(any(r[0] == "FAIL" and "evidence_hooks" in r[1] for r in rows), rows)

    def test_model_field_map_keys_fail(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.4.0")
            _write(s / "registry/classification.json", _card())
            _write(
                s / "registry/narrative_bind.json",
                _bind(
                    map={
                        "assumptions.revenue_cagr": "growth",
                        "wacc": "risk",
                        "terminal_g": "tv",
                    }
                ),
            )
            _write(s / "registry/narrative_3p.json", _review())
            rows = check_1e_complete(s)
            self.assertTrue(any(r[0] == "FAIL" and r[1] == "1e.map" for r in rows), rows)

    def test_required_finding_ids(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.4.1")
            _write(s / "registry/classification.json", _card())
            _write(
                s / "registry/filing_deep_dive.json",
                {
                    "footnotes": {
                        "items": {"sbc_unrecognized": {"status": "extracted"}}
                    },
                    "strategy_arc": {"priorities": ["keep the core"]},
                },
            )
            _write(
                s / "registry/operating_path_brief.json",
                {"conflicts": [{"id": "flatten_vs_destock", "claim_a": "flatten"}]},
            )
            _write(s / "registry/narrative_bind.json", _bind())
            _write(s / "registry/narrative_3p.json", _review())
            rows = check_1e_complete(s)
            self.assertTrue(any(r[0] == "FAIL" and "evidence_hooks" in r[1] for r in rows), rows)
            _write(
                s / "registry/narrative_bind.json",
                _bind(
                    evidence_hooks=[
                        {
                            "from": "fdd.sbc_unrecognized",
                            "action": "map",
                            "map_key": "target_om",
                            "reason": "SBC stays in expenses.",
                        },
                        {
                            "from": "fdd.strategy_arc",
                            "action": "reject",
                            "reason": "Adjacent segment is possible only.",
                        },
                        {
                            "from": "oppath.brief",
                            "action": "map",
                            "map_key": "tam",
                            "reason": "Demand path is the TAM sentence.",
                        },
                        {
                            "from": "oppath.conflict.flatten_vs_destock",
                            "action": "reject",
                            "reason": "Destock analog stays in bear.",
                        },
                    ]
                ),
            )
            rows2 = check_1e_complete(s)
            self.assertFalse(any(r[0] == "FAIL" for r in rows2), rows2)

    def test_aliases_and_graph(self) -> None:
        self.assertEqual(normalize_subagent_id("narrative"), "story")
        self.assertEqual(normalize_subagent_id("1e_3p"), "3p")
        g = graph_for_session(None)
        self.assertEqual(g["1e"].priors, ("0", "1b", "1c", "1d"))
        self.assertEqual(g["2_parallel"].priors_for("5"), ("1e",))

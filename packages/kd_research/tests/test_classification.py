"""Engine classification card gates (harness >= 3.4.0)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.classification import (
    CLASSIFICATION_REL,
    check_classification_card,
    session_enforces_classification,
)
from packages.kd_research.damodaran_gates import check_damodaran_v3


def _stamp(session: Path, version: str) -> None:
    (session / "meta").mkdir(parents=True, exist_ok=True)
    (session / "meta" / "run_manifest.json").write_text(
        json.dumps({"harness_version": version, "ticker": "X", "session_date": "2026-01-01"})
        + "\n",
        encoding="utf-8",
    )


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _card(**overrides: object) -> dict:
    payload: dict = {
        "ticker": "X",
        "job": "first_valuation",
        "life_cycle_stage": "mature",
        "who_leads": "numbers",
        "stage_rationale": "Scaled profitable same-business history is usable for a numbers-led DCF.",
        "iv_playbook": "mature_operating",
        "overlays": [],
        "buyer": {
            "class": "public_diversified",
            "rationale": "Listed name; marginal investor is diversified.",
        },
        "market_contest": {
            "accept": ["rf", "implied_erp", "market_weights"],
            "contest": ["company cash flows", "operating margins"],
            "rationale": "Company assignment: contest earnings path, accept market rates.",
        },
        "claim": "firm_dcf",
        "engine_rationale": "Listed non-financial, EBIT>0, stable leverage → mature_operating firm DCF.",
    }
    payload.update(overrides)
    return payload


class ClassificationTests(unittest.TestCase):
    def test_legacy_skips(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.3.0")
            self.assertFalse(session_enforces_classification(s))
            rows = check_classification_card(s)
            self.assertTrue(any(r[0] == "SKIPPED" for r in rows), rows)

    def test_missing_card_fails_on_340(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.4.0")
            rows = check_classification_card(s)
            self.assertTrue(any(r[0] == "FAIL" and r[1] == "classification" for r in rows), rows)

    def test_valid_card_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.4.0")
            _write(s / CLASSIFICATION_REL, _card())
            rows = check_classification_card(s)
            self.assertFalse(any(r[0] == "FAIL" for r in rows), rows)

    def test_bank_sector_rejects_operating_playbook(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.4.0")
            _write(s / CLASSIFICATION_REL, _card())
            _write(
                s / "registry/sector_config.json",
                {"primary_sector": "banking", "ticker": "X"},
            )
            rows = check_classification_card(s)
            self.assertTrue(
                any(r[0] == "FAIL" and r[1] == "classification.sector_playbook" for r in rows),
                rows,
            )

    def test_playbook_comes_from_classification_not_bind(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "3.4.1")
            _write(s / CLASSIFICATION_REL, _card())
            _write(
                s / "registry/narrative_bind.json",
                {
                    "ticker": "X",
                    "iv_playbook": "young_startup",
                    "stage_fit": "x" * 40,
                    "story": {"paragraph": "A compact going-concern story about this mature firm."},
                    "map": {
                        "tam": "core market grows with GDP",
                        "target_om": "mid-cycle margin holds",
                        "kc_path": "fade to industry WACC",
                    },
                },
            )
            _write(
                s / "registry/narrative_3p.json",
                {
                    "ticker": "X",
                    "verdict": "PASS",
                    "possible": ["adjacent product"],
                    "plausible": ["share gain"],
                    "probable": ["in-line growth"],
                },
            )
            _write(
                s / "data/valuation_model.json",
                {
                    "ticker": "X",
                    "model": {"name": "dcf", "rationale": "mature operating fcff model"},
                    "fair_value": {"base": 10, "bear": 8, "bull": 12},
                    "assumptions": {"revenue_cagr": 0.04, "wacc": 0.09},
                    "story_input_bind": {
                        "tam": "revenue_cagr",
                        "target_om": "revenue_cagr",
                        "kc_path": "wacc",
                    },
                    "buyer_dials": {"illiquidity_discount": 0},
                    "terminal_consistency": {"method": "gordon"},
                    "truncation": {"p": 0, "why_not_material": "x" * 40},
                    "per_share_bridge": {
                        "shares_used": 1,
                        "net_debt_subtracted": 0,
                        "cash_added": 0,
                        "rationale": "primary shares at session date",
                    },
                    "wacc_buildup": {
                        "applies": True,
                        "wacc": 0.09,
                        "erp_method": "implied",
                        "beta_method": "bottom_up",
                        "discount_currency": "USD",
                        "cash_flow_currency": "USD",
                    },
                },
            )
            rows = check_damodaran_v3(s)
            self.assertFalse(
                any(r[0] == "FAIL" and "classification_match" in r[1] for r in rows),
                rows,
            )
            self.assertTrue(
                any(r[0] == "PASS" and r[1] == "damodaran.iv_playbook" and "mature_operating" in r[2] for r in rows),
                rows,
            )

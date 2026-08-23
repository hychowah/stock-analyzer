"""Wave 4 destock-default gates (harness >= 2.12.0)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.kd_research.epistemology import (  # noqa: E402
    _destock_in_base,
    check_destock_default,
    check_destock_not_silent_duration,
    check_two_quarter_destock_inverse,
    check_wave3_epistemology,
    check_wave4_destock_default,
)


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj) if not isinstance(obj, str) else obj, encoding="utf-8")


def _stamp(session: Path, version: str | None) -> None:
    man: dict = {"status": "scaffolded", "orchestrator_model": "grok-4.5"}
    if version:
        man["harness_version"] = version
    _write(session / "meta" / "run_manifest.json", man)


def _brief(destock_status: str = "resolved") -> dict:
    return {
        "ticker": "X",
        "session_date": "2026-01-01",
        "sources": {"workers": ["a", "b", "c"]},
        "conflicts": [
            {
                "id": "flatten_vs_destock",
                "claim_a": "flatten mid-cycle",
                "claim_b": "destock analog FY2024",
                "status": destock_status,
            }
        ],
        "rejected_shapes": [],
        "verify_rechecks": [
            {"path": "x", "value": 1},
            {"path": "y", "value": 2},
            {"path": "z", "value": 3},
        ],
    }


def _vm(*, destock_hook: dict | None, du: str = "high") -> dict:
    hooks = []
    if destock_hook is not None:
        hooks.append(destock_hook)
    else:
        hooks.append({"from": "conflicts.flatten", "action": "used_as:growth_path", "reason": "base is duration"})
    return {
        "ticker": "X",
        "model": {"name": "dcf"},
        "fair_value": {"base": 100, "bear": 80, "bull": 120, "decision_usefulness": du},
        "assumptions": {},
        "compute_script": "data/compute/v.py",
        "sensitivity": {},
        "operating_path_hooks": hooks,
    }


BEAR_HOOK = {
    "from": "conflicts.flatten_vs_destock",
    "action": "used_as:bear_only",
    "applies_in": "bear_only",
    "reason": "destock analog lives in bear only",
    "new": "Y1–Y2 keep printed duration; destock analog lives in bear only",
}

BASE_HOOK = {
    "from": "conflicts.flatten_vs_destock",
    "action": "used_as:base",
    "applies_in": "base",
    "reason": "Y1 destock/quality-reset on the base path (run-rate ex destock); duration only in bull",
    "new": "Y1 destock/quality-reset on the base path (run-rate ex destock); duration only in bull",
}


class PromptLawTests(unittest.TestCase):
    def test_1d_merge_retired_promoter_phrase_stays_gone(self) -> None:
        text = (ROOT / "harness" / "agent_prompts.md").read_text(encoding="utf-8")
        self.assertNotIn(
            "propose destock-fade in bear, duration/company-guide in base/bull",
            text,
        )
        # Live 2.18 prompt law (Street Y1 + destock-in-bear) is in test_wave10.

    def test_pair0_still_has_a_destock_in_base_detector(self) -> None:
        hook = {
            "from": "x",
            "action": "used_as:base",
            "applies_in": "base",
            "new": "Y1 destock/quality-reset on the base path",
            "reason": "destock default is base",
        }
        self.assertTrue(_destock_in_base({"operating_path_hooks": [hook]}))

    def test_version_at_least_212(self) -> None:
        from scripts.kd_research.annuals import parse_semver

        payload = json.loads((ROOT / "harness" / "VERSION").read_text(encoding="utf-8"))
        parsed = parse_semver(payload.get("harness_version"))
        self.assertIsNotNone(parsed)
        self.assertGreaterEqual(parsed, (2, 12, 0))


class DestockDefaultTests(unittest.TestCase):
    def test_211_skips_wave4(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.11.0")
            rows = check_wave4_destock_default(s)
            self.assertEqual(rows[0][0], "SKIPPED", rows)

    def test_resolved_destock_bear_only_fails_at_212(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.12.0")
            _write(s / "registry/operating_path_brief.json", _brief("resolved"))
            _write(s / "data/valuation_model.json", _vm(destock_hook=BEAR_HOOK))
            _write(
                s / "registry/decision.json",
                {"ticker": "X", "duration": {"action": "initiate", "rationale": "Buying duration at 30 percent MoS."}},
            )
            rows = check_destock_default(s)
            self.assertEqual(rows[0][0], "FAIL", rows)

    def test_resolved_destock_bear_only_hold_still_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.12.0")
            _write(s / "registry/operating_path_brief.json", _brief("resolved"))
            _write(s / "data/valuation_model.json", _vm(destock_hook=BEAR_HOOK))
            _write(
                s / "registry/decision.json",
                {"ticker": "X", "duration": {"action": "hold", "rationale": "Holding the duration story."}},
            )
            rows = check_destock_default(s)
            self.assertEqual(rows[0][0], "FAIL", rows)

    def test_resolved_destock_bear_only_passes_wave3_at_211(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.11.0")
            _write(s / "registry/operating_path_brief.json", _brief("resolved"))
            _write(s / "data/valuation_model.json", _vm(destock_hook=BEAR_HOOK))
            _write(
                s / "registry/decision.json",
                {"ticker": "X", "duration": {"action": "initiate", "rationale": "Buying duration."}},
            )
            rows = check_destock_not_silent_duration(s)
            self.assertEqual(rows[0][0], "PASS", rows)
            self.assertIn("no unresolved", rows[0][2])

    def test_destock_in_base_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.12.0")
            _write(s / "registry/operating_path_brief.json", _brief("unresolved"))
            _write(s / "data/valuation_model.json", _vm(destock_hook=BASE_HOOK))
            _write(
                s / "registry/decision.json",
                {"ticker": "X", "duration": {"action": "initiate", "rationale": "Base is destock reset."}},
            )
            rows = check_destock_default(s)
            self.assertEqual(rows[0][0], "PASS", rows)
            self.assertTrue(_destock_in_base(_vm(destock_hook=BASE_HOOK)))

    def test_pass_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.12.0")
            _write(s / "registry/operating_path_brief.json", _brief("resolved"))
            _write(s / "data/valuation_model.json", _vm(destock_hook=BEAR_HOOK, du="low"))
            _write(
                s / "registry/decision.json",
                {"ticker": "X", "duration": {"action": "pass", "rationale": "Unresolved destock is not a buy."}},
            )
            rows = check_destock_default(s)
            self.assertEqual(rows[0][0], "PASS", rows)

    def test_hints_old_default_fail(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.12.0")
            brief = _brief("resolved")
            brief["scenario_hints"] = {
                "bear": "destock-fade in bear",
                "base": "duration/company-guide in base",
            }
            _write(s / "registry/operating_path_brief.json", brief)
            _write(s / "data/valuation_model.json", _vm(destock_hook=None))
            _write(
                s / "registry/decision.json",
                {"ticker": "X", "duration": {"action": "initiate", "rationale": "Guide duration in base."}},
            )
            rows = check_destock_default(s)
            self.assertEqual(rows[0][0], "FAIL", rows)

    def test_no_destock_conflict_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.12.0")
            _write(
                s / "registry/operating_path_brief.json",
                {
                    "ticker": "X",
                    "session_date": "2026-01-01",
                    "sources": {"workers": ["a", "b", "c"]},
                    "conflicts": [],
                    "rejected_shapes": [],
                    "verify_rechecks": [
                        {"path": "x", "value": 1},
                        {"path": "y", "value": 2},
                        {"path": "z", "value": 3},
                    ],
                },
            )
            _write(s / "data/valuation_model.json", _vm(destock_hook=None))
            rows = check_destock_default(s)
            self.assertEqual(rows[0][0], "PASS", rows)

    def test_wave3_suite_still_skips_on_210(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.10.0")
            rows = check_wave3_epistemology(s)
            self.assertEqual(rows[0][0], "SKIPPED")


class DestockInverseTests(unittest.TestCase):
    def test_raise_with_wc_release_warns(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.12.0")
            _write(s / "registry/operating_path_brief.json", _brief("unresolved"))
            vm = _vm(destock_hook=BASE_HOOK)
            vm["overrides_applied"] = [
                {
                    "rule": "two_quarter_rule",
                    "old": 0.04,
                    "new": 0.12,
                    "reason": "raised Y1 growth on two prints",
                }
            ]
            _write(s / "data/valuation_model.json", vm)
            _write(
                s / "registry/latest_quarter.json",
                {
                    "ticker": "X",
                    "cash_flow": {"fcf": 400.0},
                    "evidence_log": [
                        {
                            "metric": "inventory",
                            "observation": "inventory down 18% (destock release)",
                            "materiality": "high",
                        }
                    ],
                },
            )
            rows = check_two_quarter_destock_inverse(s)
            self.assertEqual(rows[0][0], "WARN", rows)

    def test_raise_without_destock_conflict_no_warn(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.12.0")
            _write(
                s / "registry/operating_path_brief.json",
                {
                    "ticker": "X",
                    "session_date": "2026-01-01",
                    "sources": {"workers": ["a", "b", "c"]},
                    "conflicts": [],
                    "rejected_shapes": [],
                    "verify_rechecks": [
                        {"path": "x", "value": 1},
                        {"path": "y", "value": 2},
                        {"path": "z", "value": 3},
                    ],
                },
            )
            vm = _vm(destock_hook=None)
            vm["overrides_applied"] = [
                {"rule": "two_quarter_rule", "old": 0.04, "new": 0.12, "reason": "raised"}
            ]
            _write(s / "data/valuation_model.json", vm)
            _write(
                s / "registry/latest_quarter.json",
                {"ticker": "X", "cash_flow": {"fcf": 400.0}},
            )
            rows = check_two_quarter_destock_inverse(s)
            self.assertEqual(rows[0][0], "PASS", rows)

    def test_raise_missing_lq_warns_when_destock(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.12.0")
            _write(s / "registry/operating_path_brief.json", _brief("resolved"))
            vm = _vm(destock_hook=BASE_HOOK)
            vm["overrides_applied"] = [
                {"rule": "two_quarter_rule", "old": 0.04, "new": 0.12, "reason": "raised"}
            ]
            _write(s / "data/valuation_model.json", vm)
            rows = check_two_quarter_destock_inverse(s)
            self.assertEqual(rows[0][0], "WARN", rows)


if __name__ == "__main__":
    unittest.main()

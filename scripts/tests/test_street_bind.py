"""Street calibration gates: independent FY+1 vs consensus (not copy)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.kd_research.gates import complete_checks  # noqa: E402
from scripts.kd_research.street_bind import (  # noqa: E402
    check_street_bind,
    check_street_fetch,
    fy1_street_revenue,
    session_enforces_street,
)


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


def _street_file(*, revenue_0=100.0, revenue_1=174.0, unavailable=False) -> dict:
    d: dict = {
        "ticker": "X",
        "session_date": "2026-01-01",
        "source": "yfinance.revenue_estimate",
        "fiscal_convention": "company_fy",
        "years": [
            {"label": "0y", "revenue": revenue_0, "eps": 11.0},
            {"label": "+1y", "revenue": revenue_1, "eps": 19.5},
        ],
    }
    if unavailable:
        d["unavailable"] = True
        d["years"] = []
    return d


def _hook(action="used_as:calibration_check") -> dict:
    return {
        "from": "street_estimates.years[+1y].revenue",
        "action": action,
        "reason": "Independent stack vs Street FY+1 used as calibration after the path was built.",
    }


def _bind(base: float, street: float, **extra) -> dict:
    delta = (base - street) / street
    d = {
        "guide": 154.0,
        "street": street,
        "base": base,
        "delta_pct": delta,
        "independent_construction": {
            "rationale": "FY+1 base from company AI floor plus software run-rate plus non-AI sequential, not consensus mean."
        },
    }
    d.update(extra)
    return d


def _dials(*applies: str) -> list[dict]:
    keys = ("volume_vs_guide", "gaap_om_vs_guide", "sbc_in_fcff", "wacc_vs_buildup")
    if not applies:
        applies = ("none", "none", "bear_only", "none")
    return [{"key": k, "applies_in": a} for k, a in zip(keys, applies)]


def _vm(**kwargs) -> dict:
    d = {
        "ticker": "X",
        "model": {"name": "dcf", "rationale": "fixture model choice justified here"},
        "fair_value": {"base": 100.0},
        "compute_script": "data/compute/valuation.py",
        "street_hooks": [_hook()],
        "street_bind": _bind(158.0, 174.0),
        "conservatism_dials": _dials(),
    }
    d.update(kwargs)
    return d


class VersionFloorTests(unittest.TestCase):
    def test_legacy_no_file_does_not_enforce(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.6.0")
            self.assertFalse(session_enforces_street(s))
            rows = check_street_fetch(s)
            self.assertEqual(rows[0][0], "SKIPPED")

    def test_new_runtime_enforces(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.7.0")
            self.assertTrue(session_enforces_street(s))
            rows = check_street_fetch(s)
            self.assertEqual(rows[0][0], "FAIL")

    def test_file_forces_enforce_on_old_version(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.6.0")
            _write(s / "registry/street_estimates.json", _street_file())
            self.assertTrue(session_enforces_street(s))
            rows = check_street_fetch(s)
            self.assertEqual(rows[0][0], "PASS")


class FetchTests(unittest.TestCase):
    def test_unavailable_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.7.0")
            _write(s / "registry/street_estimates.json", _street_file(unavailable=True))
            rows = check_street_fetch(s)
            self.assertEqual(rows[0][0], "PASS")
            self.assertIn("unavailable", rows[0][2])

    def test_fetch_log_failure_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.7.0")
            _write(
                s / "registry/data_fetch_log.json",
                {"ticker": "X", "failed": ["Street FY estimates unavailable: yfinance revenue_estimate error"]},
            )
            rows = check_street_fetch(s)
            self.assertEqual(rows[0][0], "PASS")


class BindTests(unittest.TestCase):
    def _sess(self, vm: dict | None, street: dict | None = None, version="2.7.0") -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        _stamp(s, version)
        if street is not None:
            _write(s / "registry/street_estimates.json", street)
        if vm is not None:
            _write(s / "data/valuation_model.json", vm)
        return s

    def test_fy1_second_year(self) -> None:
        self.assertEqual(fy1_street_revenue(_street_file()), 174.0)

    def test_pass_independent_near_street(self) -> None:
        s = self._sess(_vm(), _street_file())
        rows = check_street_bind(s)
        fails = [r for r in rows if r[0] == "FAIL"]
        self.assertEqual(fails, [], fails)

    def test_fail_missing_bind(self) -> None:
        vm = _vm()
        del vm["street_bind"]
        s = self._sess(vm, _street_file())
        rows = check_street_bind(s)
        self.assertTrue(any(r[0] == "FAIL" and r[1] == "street_bind" for r in rows))

    def test_fail_copy_action(self) -> None:
        vm = _vm(street_hooks=[_hook("used_as:revenue_path_base")])
        s = self._sess(vm, _street_file())
        rows = check_street_bind(s)
        self.assertTrue(any("copy" in r[1] for r in rows if r[0] == "FAIL"))

    def test_fail_all_noted_only(self) -> None:
        vm = _vm(street_hooks=[_hook("noted_only")])
        s = self._sess(vm, _street_file())
        rows = check_street_bind(s)
        self.assertTrue(any("noted_only" in r[1] for r in rows if r[0] == "FAIL"))

    def test_fail_delta_identity(self) -> None:
        bind = _bind(158.0, 174.0)
        bind["delta_pct"] = 0.99
        s = self._sess(_vm(street_bind=bind), _street_file())
        rows = check_street_bind(s)
        self.assertTrue(any(r[1] == "street_bind.delta_pct" and r[0] == "FAIL" for r in rows))

    def test_large_gap_without_response_fails(self) -> None:
        # 123.5 vs 174 is about -29%
        bind = _bind(123.5, 174.0)
        s = self._sess(_vm(street_bind=bind), _street_file())
        rows = check_street_bind(s)
        self.assertTrue(any("divergence" in r[1] or r[1].endswith("response") for r in rows if r[0] == "FAIL"))

    def test_large_gap_with_reopen_passes(self) -> None:
        bind = _bind(
            123.5,
            174.0,
            divergence_rationale=(
                "Independent stack missed the AI guide floor; reopen path from 8-K AI "
                "plus software plus non-AI rather than pasting Street."
            ),
            response="reopen_path",
        )
        s = self._sess(_vm(street_bind=bind), _street_file())
        rows = check_street_bind(s)
        fails = [r for r in rows if r[0] == "FAIL"]
        self.assertEqual(fails, [], fails)

    def test_short_construction_fails(self) -> None:
        bind = _bind(158.0, 174.0)
        bind["independent_construction"] = {"rationale": "consensus"}
        s = self._sess(_vm(street_bind=bind), _street_file())
        rows = check_street_bind(s)
        self.assertTrue(any("independent_construction" in r[1] and r[0] == "FAIL" for r in rows))

    def test_stacking_three_base_without_justification_fails(self) -> None:
        vm = _vm(
            conservatism_dials=[
                {"key": "volume_vs_guide", "applies_in": "base"},
                {"key": "gaap_om_vs_guide", "applies_in": "base"},
                {"key": "sbc_in_fcff", "applies_in": "base"},
                {"key": "wacc_vs_buildup", "applies_in": "bear_only"},
            ]
        )
        s = self._sess(vm, _street_file())
        rows = check_street_bind(s)
        self.assertTrue(any("stacking" in r[1] and r[0] == "FAIL" for r in rows))

    def test_sotp_gap_without_rationale_fails(self) -> None:
        vm = _vm(
            multi_method_reconciliation={
                "primary_fv_for_decision": 122.0,
                "cross_check_fv": 175.0,
                "delta_pct": 43.4,
                "why_primary_wins": "short",
            }
        )
        s = self._sess(vm, _street_file())
        rows = check_street_bind(s)
        self.assertTrue(any("sotp_dcf_gap" in r[1] and r[0] == "FAIL" for r in rows))

    def test_omitted_dials_fails_on_new_runtime(self) -> None:
        vm = _vm()
        del vm["conservatism_dials"]
        s = self._sess(vm, _street_file())
        rows = check_street_bind(s)
        self.assertTrue(any(r[0] == "FAIL" and r[1] == "conservatism_dials" for r in rows), rows)

    def test_omitted_dials_skipped_on_legacy_with_file(self) -> None:
        vm = _vm()
        del vm["conservatism_dials"]
        s = self._sess(vm, _street_file(), version="2.6.0")
        rows = check_street_bind(s)
        self.assertTrue(any(r[0] == "SKIPPED" and r[1] == "conservatism_dials" for r in rows), rows)
        self.assertFalse(any(r[0] == "FAIL" and r[1] == "conservatism_dials" for r in rows), rows)

    def test_street_column_mismatch_fails(self) -> None:
        bind = _bind(158.0, 158.0)  # pretend street=base while file is 174
        s = self._sess(_vm(street_bind=bind), _street_file())
        rows = check_street_bind(s)
        self.assertTrue(any(r[0] == "FAIL" and r[1] == "street_bind.street" for r in rows), rows)

    def test_street_unusable_skips_identity(self) -> None:
        bind = _bind(
            158.0,
            158.0,
            response="street_unusable",
            divergence_rationale="Vendor FY mix is calendar vs company FY so consensus is unusable for bind.",
        )
        s = self._sess(_vm(street_bind=bind), _street_file())
        rows = check_street_bind(s)
        self.assertFalse(any(r[0] == "FAIL" and r[1] == "street_bind.street" for r in rows), rows)

    def test_sotp_and_dcf_without_reconciliation_fails(self) -> None:
        vm = _vm(model={"name": "dcf+sotp", "rationale": "fixture model choice justified here"})
        s = self._sess(vm, _street_file())
        rows = check_street_bind(s)
        self.assertTrue(any(r[0] == "FAIL" and r[1] == "sotp_dcf_gap" for r in rows), rows)

    def test_1_parallel_complete_includes_street_on_new_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _stamp(s, "2.7.0")
            _write(s / "data/sp_financials.csv", "ticker,x\nX,1\n")
            _write(s / "registry/sec_filings.json", {"ticker": "X", "filings": [{"form": "10-K", "filing_date": "2026-01-01", "url": "u", "sections": {}}]})
            _write(s / "registry/news_sentiment.json", {"ticker": "X", "items": [{"date": "2026-01-01", "headline": "h", "source": "s", "sentiment": "neutral"}]})
            rows = complete_checks(s, "1_parallel")
            self.assertTrue(any(r[0] == "FAIL" and "street" in r[1] for r in rows))
            _write(s / "registry/street_estimates.json", _street_file())
            rows = complete_checks(s, "1_parallel")
            self.assertFalse(any(r[0] == "FAIL" and "street" in r[1] for r in rows), rows)


class StreetSchemaTests(unittest.TestCase):
    def test_unavailable_empty_years_valid(self) -> None:
        try:
            import jsonschema  # type: ignore
        except ImportError:
            self.skipTest("jsonschema not installed")
        schema = json.loads((ROOT / "templates" / "street_estimates.schema.json").read_text(encoding="utf-8"))
        jsonschema.Draft7Validator(schema).validate(_street_file(unavailable=True))

    def test_available_empty_years_invalid(self) -> None:
        try:
            import jsonschema  # type: ignore
        except ImportError:
            self.skipTest("jsonschema not installed")
        schema = json.loads((ROOT / "templates" / "street_estimates.schema.json").read_text(encoding="utf-8"))
        bad = _street_file()
        bad["years"] = []
        errors = list(jsonschema.Draft7Validator(schema).iter_errors(bad))
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()

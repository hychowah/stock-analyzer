"""ForecastTable named layouts, identity gate, fundamental table restatement."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.forecast_table import (
    ForecastTable,
    check_explicit_forecast,
    check_fundamental_forecast_table,
)


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, str):
        path.write_text(obj, encoding="utf-8")
    else:
        path.write_text(json.dumps(obj), encoding="utf-8")


class ForecastTableLayoutTests(unittest.TestCase):
    def _root(self) -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        _write(
            s / "meta/run_manifest.json",
            {"harness_version": "2.43.0", "orchestrator_model": "grok-4.5"},
        )
        return s

    def test_meta_parallel_arrays(self) -> None:
        s = self._root()
        _write(
            s / "data/compute/valuation_result.json",
            {
                "currency": "USD",
                "scenarios": {
                    "base": {
                        "revenues": [254e9, 300e9],
                        "oi": [86e9, 103e9],
                        "om": [0.34, 0.345],
                        "capex": [137.5e9, 115e9],
                        "fcff": [-42e9, -10e9],
                    },
                    "bear": {
                        "revenues": [230e9, 248e9],
                        "oi": [69e9, 75e9],
                        "om": [0.30, 0.305],
                        "capex": [145e9, 125e9],
                        "fcff": [-63e9, -28e9],
                    },
                    "bull": {
                        "revenues": [260e9, 320e9],
                        "oi": [100e9, 120e9],
                        "om": [0.38, 0.39],
                        "capex": [120e9, 90e9],
                        "fcff": [-20e9, 10e9],
                    },
                },
            },
        )
        table = ForecastTable.from_session(s)
        self.assertIsNotNone(table)
        assert table is not None
        self.assertEqual(table.source, "scenarios")
        self.assertEqual(table.currency, "USD")
        ids = [r.id for r in table.rows]
        self.assertIn("revenue", ids)
        self.assertIn("fcff", ids)
        rev = next(r for r in table.rows if r.id == "revenue")
        self.assertAlmostEqual(rev.values["base"][0], 254e9)
        self.assertEqual(table.years, ["Y1", "Y2"])

    def test_cohr_dcf_years(self) -> None:
        s = self._root()
        _write(
            s / "data/compute/valuation_result.json",
            {
                "dcf": {
                    "base": {
                        "years": [
                            {"fy": 2027, "revenue": 10e9, "ebit": 1.3e9, "om": 0.13, "capex": 1.4e9, "fcff": -0.3e9},
                            {"fy": 2028, "revenue": 11.8e9, "ebit": 1.4e9, "om": 0.12, "capex": 1.2e9, "fcff": 0.5e9},
                        ]
                    }
                }
            },
        )
        table = ForecastTable.from_session(s)
        self.assertIsNotNone(table)
        assert table is not None
        self.assertEqual(table.source, "dcf_years")
        self.assertEqual(table.years, ["2027", "2028"])
        rev = next(r for r in table.rows if r.id == "revenue")
        self.assertAlmostEqual(rev.values["base"][0], 10e9)

    def test_adyen_paths(self) -> None:
        s = self._root()
        _write(
            s / "data/compute/valuation_result.json",
            {
                "paths": {
                    "base": [
                        {"fy": 2026, "nr": 2.87e9, "ebitda_m": 0.52, "fcff": 0.9e9, "capex_pct": 0.07},
                        {"fy": 2027, "nr": 3.4e9, "ebitda_m": 0.53, "fcff": 1.2e9, "capex_pct": 0.05},
                    ]
                }
            },
        )
        table = ForecastTable.from_session(s)
        self.assertIsNotNone(table)
        assert table is not None
        self.assertEqual(table.source, "paths")
        ids = [r.id for r in table.rows]
        self.assertIn("revenue", ids)
        self.assertIn("fcff", ids)
        self.assertIn("ebitda_margin", ids)
        self.assertNotIn("capex", ids)
        self.assertIn("capex_pct", ids)

    def test_acgl_like_miss_is_none(self) -> None:
        s = self._root()
        _write(
            s / "data/compute/valuation_result.json",
            {
                "model": "excess_return",
                "book": {"2025": 95.0},
                "roe": {"base": 0.13},
            },
        )
        self.assertIsNone(ForecastTable.from_session(s))

    def test_does_not_invent_profit_from_margin(self) -> None:
        s = self._root()
        _write(
            s / "data/compute/valuation_result.json",
            {
                "scenarios": {
                    "base": {"revenues": [100.0, 110.0], "om": [0.3, 0.31]},
                }
            },
        )
        table = ForecastTable.from_session(s)
        assert table is not None
        ids = [r.id for r in table.rows]
        self.assertIn("revenue", ids)
        self.assertIn("operating_margin", ids)
        self.assertNotIn("operating_profit", ids)


class ExplicitForecastGateTests(unittest.TestCase):
    def _root(self, version: str = "2.43.0") -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        _write(
            s / "meta/run_manifest.json",
            {"harness_version": version, "orchestrator_model": "grok-4.5"},
        )
        return s

    def test_legacy_without_object_skipped(self) -> None:
        s = self._root("2.42.0")
        _write(s / "data/valuation_model.json", {"ticker": "X", "model": {"name": "dcf"}})
        rows = check_explicit_forecast(s)
        self.assertEqual(rows[0][0], "SKIPPED", rows)

    def test_243_missing_fails(self) -> None:
        s = self._root("2.43.0")
        _write(s / "data/valuation_model.json", {"ticker": "X", "model": {"name": "dcf"}})
        rows = check_explicit_forecast(s)
        self.assertEqual(rows[0][0], "FAIL", rows)

    def test_applies_false_needs_reason(self) -> None:
        s = self._root()
        _write(
            s / "data/valuation_model.json",
            {
                "explicit_forecast": {
                    "applies": False,
                    "not_applicable_reason": "short",
                    "native_analog": "insurance_roe",
                }
            },
        )
        rows = check_explicit_forecast(s)
        self.assertEqual(rows[0][0], "FAIL", rows)

    def test_identity_match_passes(self) -> None:
        s = self._root()
        _write(
            s / "data/valuation_model.json",
            {
                "explicit_forecast": {
                    "applies": True,
                    "currency": "USD",
                    "base": {"revenue": [254e9, 300e9], "fcff": [-42e9, -10e9]},
                    "bear": {"revenue": [230e9, 248e9], "fcff": [-63e9, -28e9]},
                    "bull": {"revenue": [260e9, 320e9], "fcff": [-20e9, 10e9]},
                }
            },
        )
        _write(
            s / "data/compute/valuation_result.json",
            {
                "scenarios": {
                    "base": {"revenues": [254e9, 300e9], "fcff": [-42e9, -10e9]},
                    "bear": {"revenues": [230e9, 248e9], "fcff": [-63e9, -28e9]},
                    "bull": {"revenues": [260e9, 320e9], "fcff": [-20e9, 10e9]},
                }
            },
        )
        rows = check_explicit_forecast(s)
        self.assertEqual(rows[0][0], "PASS", rows)
        table = ForecastTable.from_session(s)
        assert table is not None
        self.assertEqual(table.source, "explicit_forecast")

    def test_identity_mismatch_fails(self) -> None:
        s = self._root()
        _write(
            s / "data/valuation_model.json",
            {
                "explicit_forecast": {
                    "applies": True,
                    "base": {"revenue": [1.0, 2.0], "fcff": [1.0, 2.0]},
                }
            },
        )
        _write(
            s / "data/compute/valuation_result.json",
            {"scenarios": {"base": {"revenues": [9e9, 10e9], "fcff": [1.0, 2.0]}}},
        )
        rows = check_explicit_forecast(s)
        self.assertEqual(rows[0][0], "FAIL", rows)
        self.assertEqual(rows[0][1], "explicit_forecast.identity")


class FundamentalTableCheckTests(unittest.TestCase):
    def _root(self, version: str = "2.43.0") -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        s = Path(td.name)
        _write(
            s / "meta/run_manifest.json",
            {"harness_version": version, "orchestrator_model": "grok-4.5"},
        )
        return s

    def test_legacy_skipped(self) -> None:
        s = self._root("2.42.0")
        rows = check_fundamental_forecast_table(s)
        self.assertEqual(rows[0][0], "SKIPPED")

    def test_table_match_passes(self) -> None:
        s = self._root()
        _write(
            s / "data/valuation_model.json",
            {
                "explicit_forecast": {
                    "applies": True,
                    "base": {"revenue": [254e9, 300e9], "fcff": [-42e9, -10e9]},
                }
            },
        )
        _write(
            s / "reports/01_X_fundamental.md",
            """# X

## Forecast path

| | Y1 | Y2 |
|---|---|---|
| Revenue | $254.0B | $300.0B |
| Free cash flow | $-42.0B | $-10.0B |
""",
        )
        rows = check_fundamental_forecast_table(s)
        self.assertEqual(rows[0][0], "PASS", rows)

    def test_missing_table_fails(self) -> None:
        s = self._root()
        _write(
            s / "data/valuation_model.json",
            {
                "explicit_forecast": {
                    "applies": True,
                    "base": {"revenue": [254e9, 300e9], "fcff": [-42e9, -10e9]},
                }
            },
        )
        _write(s / "reports/01_X_fundamental.md", "# X\n\nNo numbers here.\n")
        rows = check_fundamental_forecast_table(s)
        self.assertEqual(rows[0][0], "FAIL", rows)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for annual listing, excerpt-in-source, and 1c year-dive gates."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.kd_research.paths import PROJECT_ROOT as ROOT

from packages.kd_research.annuals import (
    is_annual_form,
    list_annuals,
    normalize_fiscal_year,
    parse_semver,
    session_enforces_year_dives,
)
from packages.kd_research.excerpt_check import excerpt_in_text
from packages.kd_research.gates import check_1c_year_dive_complete, complete_checks

SOURCE = (
    "Item 1. Business\nWe sell widgets in North America and Europe.\n"
    "Item 1A. Risk Factors\nCompetition may reduce margins.\n"
    "Item 3. Legal Proceedings\nNo material litigation expected.\n"
    "Item 7. MD&A\nWe expect revenue of approximately 10 billion.\n"
    "Note 11 Income Taxes\nEffective tax rate was 14.7 percent.\n"
    "Unrecognized compensation cost related to unvested awards was 119 million.\n"
)


def _write(p: Path, obj: object) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, (dict, list)):
        p.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    else:
        p.write_text(str(obj), encoding="utf-8")


def _year_doc(*, excerpt_ok: bool = True) -> dict:
    ex = (
        "Unrecognized compensation cost related to unvested awards was 119 million."
        if excerpt_ok
        else "This sentence is not in the filing at all whatsoever."
    )
    return {
        "ticker": "X",
        "fiscal_year": 2025,
        "form": "10-K",
        "path": "data/raw_sec/10-K_2025.txt",
        "sections_walked": [
            "business",
            "risk_factors",
            "legal",
            "md_and_a",
            "notes",
            "related_party",
        ],
        "priorities": ["widgets"],
        "outlook_promises": [
            {
                "stated": "revenue approximately 10 billion",
                "excerpt": "We expect revenue of approximately 10 billion.",
            }
        ],
        "footnotes": {
            "items": [
                {
                    "id": "sbc_unrecognized",
                    "status": "extracted",
                    "excerpt": "Unrecognized compensation cost related to unvested awards was 119 million.",
                    "downstream_use": "dilution",
                }
            ]
        },
        "key_figures": [
            {
                "id": "etr",
                "value": 14.7,
                "unit": "percent",
                "excerpt": ex,
                "source_path": "data/raw_sec/10-K_2025.txt",
            }
        ],
        "gaps": [],
    }


def _fdd(*, years: list = None, rechecks: int = 3) -> dict:
    years = years if years is not None else [2025]
    return {
        "ticker": "X",
        "session_date": "2026-01-01",
        "sources": {"filings": [{"form": "10-K", "path": "data/raw_sec/10-K_2025.txt"}]},
        "footnotes": {"items": [{"id": "sbc_unrecognized", "status": "extracted", "downstream_use": "dilution"}]},
        "strategy_arc": {
            "years_covered": years,
            "stated_priorities_by_year": [
                {"year": y, "priorities": ["widgets"], "basis": "data/raw_sec/10-K_2025.txt"}
                for y in years
            ],
            "continuity": {"value": 0.8, "rationale": "Same widget franchise.", "basis": "Item 1"},
            "rationale": "Continuity of widget strategy across the covered years.",
        },
        "management_scorecard": {
            "items": [
                {
                    "promise_id": "rev",
                    "promise_class": "revenue",
                    "stated": "10B",
                    "stated_when": "FY25",
                    "source_type": "filing",
                    "outcome": "too_early",
                    "rationale": "Still inside the year.",
                    "basis": "outlook",
                }
            ],
            "credibility_summary": {
                "pattern": "insufficient_history",
                "valuation_implication": "widen_range",
                "rationale": "Only one graded year so far.",
                "basis": "scorecard",
            },
        },
        "verify_rechecks": [
            {"path": "data/raw_sec/10-K_2025.txt", "value": 14.7, "id": f"r{i}"}
            for i in range(rechecks)
        ],
    }


def _new_session(td: Path, *, version: str = "2.5.0") -> Path:
    s = td
    _write(
        s / "meta" / "run_manifest.json",
        {"harness_version": version, "orchestrator_model": "grok-4.5", "ticker": "X"},
    )
    _write(
        s / "registry" / "sec_filings.json",
        {
            "ticker": "X",
            "filings": [
                {
                    "form": "10-K",
                    "filing_date": "2026-02-01",
                    "fiscal_period": "FY2025",
                    "path": "data/raw_sec/10-K_2025.txt",
                    "url": "https://example.invalid/10k",
                    "sections": {},
                }
            ],
        },
    )
    _write(s / "data" / "raw_sec" / "10-K_2025.txt", SOURCE)
    return s


class SemverAndForms(unittest.TestCase):
    def test_parse_semver(self) -> None:
        self.assertEqual(parse_semver("2.5.0"), (2, 5, 0))
        self.assertIsNone(parse_semver("unversioned"))

    def test_is_annual_form(self) -> None:
        self.assertTrue(is_annual_form("10-K"))
        self.assertTrue(is_annual_form("20-F"))
        self.assertTrue(is_annual_form("integrated report 2025"))
        self.assertFalse(is_annual_form("10-Q"))
        self.assertFalse(is_annual_form("8-K"))

    def test_normalize_year(self) -> None:
        self.assertEqual(normalize_fiscal_year("FY2025"), 2025)
        self.assertEqual(normalize_fiscal_year(2024), 2024)


class ExcerptCheck(unittest.TestCase):
    def test_whitespace_tolerant(self) -> None:
        self.assertTrue(
            excerpt_in_text(
                "Effective   tax rate was\n14.7 percent.",
                SOURCE,
            )
        )
        self.assertFalse(excerpt_in_text("totally fabricated excerpt here", SOURCE))


class AnnualsAndEnforce(unittest.TestCase):
    def test_list_annuals_prefers_txt(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = _new_session(Path(td))
            found = list_annuals(s)
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]["fiscal_year"], 2025)
            self.assertTrue(found[0]["path"].endswith(".txt"))

    def test_legacy_does_not_enforce(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = _new_session(Path(td), version="2.4.0")
            self.assertFalse(session_enforces_year_dives(s))

    def test_new_runtime_enforces(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = _new_session(Path(td), version="2.5.0")
            self.assertTrue(session_enforces_year_dives(s))


class OneCComplete(unittest.TestCase):
    def test_legacy_skipped_without_year_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = _new_session(Path(td), version="2.4.0")
            _write(s / "registry" / "filing_deep_dive.json", _fdd())
            rows = complete_checks(s, "1c")
            self.assertTrue(any(r[0] == "PASS" and "filing_deep_dive" in r[1] for r in rows), rows)
            self.assertTrue(any(r[0] == "SKIPPED" and "year_dives" in r[1] for r in rows), rows)
            self.assertFalse(any(r[0] == "FAIL" for r in rows), rows)

    def test_slim_no_manifest_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = Path(td)
            _write(s / "registry" / "filing_deep_dive.json", _fdd())
            rows = check_1c_year_dive_complete(s)
            self.assertTrue(any(r[0] == "SKIPPED" for r in rows), rows)
            self.assertFalse(any(r[0] == "FAIL" and "year_dives" in r[1] for r in rows), rows)

    def test_new_runtime_fails_without_year_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = _new_session(Path(td), version="2.5.0")
            _write(s / "registry" / "filing_deep_dive.json", _fdd())
            rows = complete_checks(s, "1c")
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertTrue(any("year_dives" in r[1] for r in fails), rows)

    def test_new_runtime_passes_with_valid_year_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = _new_session(Path(td), version="2.5.0")
            _write(s / "registry" / "raw" / "fdd_year_FY2025.json", _year_doc())
            _write(s / "registry" / "filing_deep_dive.json", _fdd())
            rows = complete_checks(s, "1c")
            fails = [r for r in rows if r[0] == "FAIL"]
            self.assertEqual(fails, [], fails)

    def test_excerpt_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = _new_session(Path(td), version="2.5.0")
            _write(s / "registry" / "raw" / "fdd_year_FY2025.json", _year_doc(excerpt_ok=False))
            _write(s / "registry" / "filing_deep_dive.json", _fdd())
            rows = complete_checks(s, "1c")
            self.assertTrue(any(r[0] == "FAIL" and "excerpt" in r[1] for r in rows), rows)

    def test_missing_rechecks_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            s = _new_session(Path(td), version="2.5.0")
            _write(s / "registry" / "raw" / "fdd_year_FY2025.json", _year_doc())
            _write(s / "registry" / "filing_deep_dive.json", _fdd(rechecks=1))
            rows = complete_checks(s, "1c")
            self.assertTrue(any(r[0] == "FAIL" and "verify_rechecks" in r[1] for r in rows), rows)

    def test_schema_year_dive_minimal(self) -> None:
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")
        schema = json.loads((ROOT / "harness/schemas/filing_year_dive.schema.json").read_text())
        jsonschema.Draft7Validator(schema).validate(_year_doc())


if __name__ == "__main__":
    unittest.main()

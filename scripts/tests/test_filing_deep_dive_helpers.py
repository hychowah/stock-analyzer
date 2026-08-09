"""Unit tests for filing deep-dive extract/compare helpers (no network)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.kd_research.note_extract import (  # noqa: E402
    build_footnote_items,
    excerpt,
    find_notes_for_checklist,
    parse_guidance_outlook_block,
    split_notes,
)
from scripts.kd_research.promise_vs_actual import (  # noqa: E402
    grade_point_promise,
    grade_range_promise,
    hit_rate,
    join_promises_to_actuals,
    scorecard_summary,
)

# Representative fixture: note headings + Item 3 + outlook language (not a real filing).
FIXTURE_10K = """
ITEM 1. BUSINESS
We sell ads and devices.

ITEM 3. LEGAL PROCEEDINGS
We are subject to various legal proceedings including youth-related litigation
in multiple U.S. states. Outcomes are uncertain and could be material.

ITEM 8. FINANCIAL STATEMENTS AND SUPPLEMENTARY DATA

NOTES TO CONSOLIDATED FINANCIAL STATEMENTS

Note 1. Summary of Significant Accounting Policies
Organization and basis of presentation. We are a Delaware corporation.

Note 2. Revenue
Disaggregation of revenue. Advertising revenue was $180,000 million and other
revenue was $5,000 million for the year ended December 31, 2025. Revenue by
geography: United States 40%, Europe 25%, Rest of World 35%.

Note 3. Segment Information
We have two segments: Family of Apps and Reality Labs. Family of Apps operating
income was $100,000 million. Reality Labs operating loss was $(18,000) million.

Note 12. Stock-Based Compensation
Total stock-based compensation was $20,000 million. Unrecognized stock-based
compensation expense was $25,000 million as of December 31, 2025, expected to
be recognized over a weighted-average period of 2.5 years.

Note 13. Long-Term Debt
Long-term debt outstanding was $50,000 million. Maturities: 2027 $5,000; 2028
$8,000; thereafter $37,000.

Note 14. Leases
We have operating and finance leases for data centers and offices.

Note 15. Commitments and Contingencies
We have purchase commitments for network infrastructure of $40,000 million.
Legal contingencies are discussed further in Item 3.

Note 16. Income Taxes
Our effective tax rate was 18%. Uncertain tax positions were $11,000 million.

Note 17. Stockholders' Equity
We have dual-class common stock. Class B shares have 10 votes per share.
"""

FIXTURE_OUTLOOK = """
CFO Outlook Commentary
We expect third quarter 2026 total revenue to be in the range of $61-64 billion.
We now expect full year 2026 total expenses to be in the range of $165-169 billion.
We expect 2026 capital expenditures to be in the range of $130-145 billion.
"""


class TestNoteExtract(unittest.TestCase):
    def test_split_notes_finds_numbered_notes(self) -> None:
        notes = split_notes(FIXTURE_10K)
        numbers = [n["number"] for n in notes]
        self.assertIn("2", numbers)
        self.assertIn("12", numbers)
        rev = next(n for n in notes if n["number"] == "2")
        self.assertIn("Advertising revenue", rev["body"])
        self.assertEqual(rev["title"].split()[0], "Revenue")

    def test_find_notes_for_checklist_maps_ids(self) -> None:
        mapped = find_notes_for_checklist(FIXTURE_10K)
        self.assertTrue(mapped["revenue_disaggregation"])
        self.assertTrue(mapped["sbc_unrecognized"])
        self.assertIn("Unrecognized stock-based", mapped["sbc_unrecognized"][0]["body"])
        self.assertTrue(mapped["segment"])
        self.assertTrue(mapped["income_taxes"])

    def test_build_footnote_items_extracted_and_structure(self) -> None:
        items = build_footnote_items(
            FIXTURE_10K,
            form="10-K",
            fiscal_year=2025,
            path="data/raw_sec/fixture-10k.txt",
        )
        by_id = {i["id"]: i for i in items}
        self.assertEqual(by_id["revenue_disaggregation"]["status"], "extracted")
        self.assertEqual(by_id["sbc_unrecognized"]["status"], "extracted")
        self.assertIn("25,000", by_id["sbc_unrecognized"]["excerpt"] or "")
        self.assertEqual(by_id["debt_leases"]["status"], "extracted")
        self.assertLessEqual(len(by_id["revenue_disaggregation"]["excerpt"] or ""), 820)
        # All checklist ids present
        self.assertGreaterEqual(len(items), 8)
        for it in items:
            self.assertIn(it["status"], ("extracted", "missing", "partial", "not_applicable"))
            self.assertIn("downstream_use", it)

    def test_contingencies_can_use_item3_when_needed(self) -> None:
        # Strip contingency note title match by renaming — still have Item 3.
        text = FIXTURE_10K.replace(
            "Note 15. Commitments and Contingencies",
            "Note 15. Other Guarantees",
        )
        items = build_footnote_items(text, form="10-K", fiscal_year=2025, path="x")
        cont = next(i for i in items if i["id"] == "contingencies_legal")
        # May match via "Legal" in other notes or Item 3 — must not be silent missing if Item 3 exists
        self.assertEqual(cont["status"], "extracted")
        self.assertTrue(cont.get("excerpt"))

    def test_excerpt_respects_max(self) -> None:
        long = "word " * 500
        ex = excerpt(long, 100)
        self.assertLessEqual(len(ex), 110)
        self.assertTrue(ex.endswith("[…]") or len(ex) <= 100)

    def test_parse_guidance_outlook_block(self) -> None:
        lines = parse_guidance_outlook_block(FIXTURE_OUTLOOK)
        kinds = {L["kind"] for L in lines}
        self.assertIn("revenue", kinds)
        self.assertIn("capex", kinds)
        self.assertTrue(any("61-64" in L["line"] or "61" in L["line"] for L in lines))


class TestPromiseVsActual(unittest.TestCase):
    def test_grade_range_met_beat_miss(self) -> None:
        self.assertEqual(
            grade_range_promise(low=61.0, high=64.0, actual=62.5, higher_is_better=True),
            "met",
        )
        self.assertEqual(
            grade_range_promise(low=61.0, high=64.0, actual=70.0, higher_is_better=True),
            "beat",
        )
        self.assertEqual(
            grade_range_promise(low=61.0, high=64.0, actual=50.0, higher_is_better=True),
            "miss",
        )

    def test_grade_opex_ceiling(self) -> None:
        # Cost ceiling: lower actual is better
        self.assertEqual(
            grade_range_promise(low=None, high=169.0, actual=166.0, higher_is_better=False),
            "met",
        )
        self.assertEqual(
            grade_range_promise(low=None, high=169.0, actual=180.0, higher_is_better=False),
            "miss",
        )

    def test_grade_point_promise(self) -> None:
        self.assertEqual(
            grade_point_promise(target=100.0, actual=100.5, tolerance_frac=0.02),
            "met",
        )
        self.assertEqual(
            grade_point_promise(target=100.0, actual=120.0, higher_is_better=True),
            "beat",
        )

    def test_join_promises_to_actuals_produces_outcomes(self) -> None:
        promises = [
            {
                "promise_id": "fy2025_revenue",
                "promise_class": "revenue",
                "stated": "FY2025 revenue $195-205B",
                "stated_when": "Q4'24 EX-99.1",
                "source_type": "filing",
                "period": "FY2025",
                "metric": "revenue",
                "low": 195.0,
                "high": 205.0,
                "higher_is_better": True,
                "rationale": "placeholder",
                "basis": "fixture",
            },
            {
                "promise_id": "fy2025_capex",
                "promise_class": "capex",
                "stated": "capex $60-70B",
                "stated_when": "Q4'24 EX-99.1",
                "source_type": "filing+transcript",
                "period": "FY2025",
                "metric": "capex",
                "low": 60.0,
                "high": 70.0,
                "higher_is_better": False,  # overspending vs capex guide = miss if above
                "rationale": "placeholder",
                "basis": "fixture",
            },
            {
                "promise_id": "ai_milestone",
                "promise_class": "strategic_milestone",
                "stated": "personal superintelligence progress",
                "stated_when": "FY24 call",
                "source_type": "transcript",
                "too_early": True,
                "rationale": "vision",
                "basis": "transcript",
            },
        ]
        actuals = {"FY2025": {"revenue": 200.0, "capex": 72.0}}
        rows = join_promises_to_actuals(promises, actuals)
        by_id = {r["promise_id"]: r for r in rows}
        self.assertEqual(by_id["fy2025_revenue"]["outcome"], "met")
        self.assertEqual(by_id["fy2025_revenue"]["actual"], 200.0)
        # capex 72 > 70 with higher_is_better False → miss
        self.assertEqual(by_id["fy2025_capex"]["outcome"], "miss")
        self.assertEqual(by_id["ai_milestone"]["outcome"], "too_early")
        # Source labels preserved (filings + transcripts path)
        self.assertEqual(by_id["fy2025_capex"]["source_type"], "filing+transcript")
        self.assertEqual(by_id["ai_milestone"]["source_type"], "transcript")

    def test_hit_rate_and_scorecard_summary(self) -> None:
        hr = hit_rate(["met", "beat", "miss", "too_early", "unknown"])
        self.assertEqual(hr["n"], 3)
        self.assertAlmostEqual(hr["value"], 2 / 3)
        items = [
            {"outcome": "met", "promise_class": "revenue"},
            {"outcome": "miss", "promise_class": "capex"},
            {"outcome": "beat", "promise_class": "revenue"},
        ]
        summary = scorecard_summary(
            items,
            pattern="mixed",
            valuation_implication="widen_range",
            rationale="Mixed delivery on guides with one capex miss.",
            basis="fixture rows",
            transcript_coverage="1 call used as secondary",
        )
        self.assertAlmostEqual(summary["hit_rate_quantitative"]["value"], 2 / 3)
        self.assertEqual(summary["pattern"], "mixed")
        self.assertTrue(
            "transcript" in summary["transcript_coverage"].lower()
            or "call" in summary["transcript_coverage"].lower()
        )


class TestSchemaValidatesMinimalDeepDive(unittest.TestCase):
    """Schema smoke: minimal well-formed deep-dive validates when jsonschema available."""

    def test_minimal_document(self) -> None:
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")

        schema = json.loads((ROOT / "templates/filing_deep_dive.schema.json").read_text())
        doc = {
            "ticker": "TEST",
            "session_date": "2026-08-03",
            "sources": {
                "filings": [
                    {"form": "10-K", "path": "data/raw_sec/test-10k.txt", "fiscal_period": "FY2025"}
                ],
                "transcripts": [
                    {
                        "period": "Q2'26",
                        "path": "data/transcripts/q2_2026.txt",
                        "status": "available",
                    }
                ],
                "gaps": [],
            },
            "footnotes": {
                "items": [
                    {
                        "id": "revenue_disaggregation",
                        "status": "extracted",
                        "downstream_use": "growth",
                        "excerpt": "Advertising 95%",
                    }
                ]
            },
            "strategy_arc": {
                "years_covered": [2023, 2024, 2025],
                "stated_priorities_by_year": [
                    {
                        "year": 2025,
                        "priorities": ["AI infrastructure", "ads AI"],
                        "basis": "data/raw_sec/test-10k.txt Item 1",
                    }
                ],
                "continuity": {
                    "value": 0.7,
                    "rationale": "Same ad franchise with rising AI reinvestment emphasis.",
                    "basis": "3y Item 1 comparison",
                },
                "rationale": "Strategy shifted from efficiency narrative toward AI capex while core ads moat stayed constant.",
            },
            "management_scorecard": {
                "items": [
                    {
                        "promise_id": "fy25_rev",
                        "promise_class": "revenue",
                        "stated": "$195-205B",
                        "stated_when": "Q4'24",
                        "source_type": "filing",
                        "outcome": "met",
                        "rationale": "Actual $200B inside guide.",
                        "basis": "EX-99.1 + 10-K",
                    }
                ],
                "credibility_summary": {
                    "pattern": "mixed",
                    "valuation_implication": "no_change",
                    "rationale": "Limited sample but revenue guide met; capex history thinner.",
                    "basis": "scorecard items",
                },
            },
        }
        jsonschema.Draft7Validator(schema).validate(doc)


if __name__ == "__main__":
    unittest.main()

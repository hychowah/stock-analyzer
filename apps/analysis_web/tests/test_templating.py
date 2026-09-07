"""Display helpers: Downside % is (price - fv_bear) / price * 100."""

from __future__ import annotations

import unittest

from apps.analysis_web.templating import (
    downside_pct,
    downside_title,
    fmt_num,
    headline_view,
    nav_for_path,
)


class DownsidePctTests(unittest.TestCase):
    def test_price_above_bear(self):
        self.assertAlmostEqual(downside_pct(100.0, 70.0), 30.0)

    def test_at_bear(self):
        self.assertAlmostEqual(downside_pct(70.0, 70.0), 0.0)

    def test_price_below_bear(self):
        self.assertAlmostEqual(downside_pct(60.0, 70.0), (60.0 - 70.0) / 60.0 * 100.0)

    def test_meta_fixture(self):
        self.assertAlmostEqual(downside_pct(400.0, 350.0), 12.5)

    def test_missing_or_zero_price(self):
        self.assertIsNone(downside_pct(None, 70.0))
        self.assertIsNone(downside_pct(100.0, None))
        self.assertIsNone(downside_pct(0, 70.0))
        self.assertIsNone(downside_pct("n/a", 70.0))
        self.assertIsNone(downside_pct(True, 70.0))

    def test_title(self):
        self.assertEqual(
            downside_title(400.0, 350.0, "as-of"),
            f"as-of · {fmt_num(400.0)} → bear {fmt_num(350.0)}",
        )
        self.assertEqual(downside_title(None, 350.0), "")
        self.assertEqual(downside_title(0, 350.0), "")


class HeadlineViewTests(unittest.TestCase):
    def test_projects_labels_and_formatted_cells(self):
        packet = {
            "sessions": ["2026-08-03", "2026-08-10"],
            "fields": [
                {
                    "field": "asof_price",
                    "values": {"2026-08-03": 400.0, "2026-08-10": 480.0},
                },
                {
                    "field": "fv_base",
                    "values": {"2026-08-03": 500.0, "2026-08-10": 600.0},
                },
                {
                    "field": "audit_verdict",
                    "values": {"2026-08-03": "PASS", "2026-08-10": None},
                },
            ],
        }
        view = headline_view(packet)
        self.assertEqual(view["sessions"], ["2026-08-03", "2026-08-10"])
        by_label = {row["label"]: row["cells"] for row in view["rows"]}
        self.assertEqual(by_label["As-of"], ["400.00", "480.00"])
        self.assertEqual(by_label["FV base"], ["500.00", "600.00"])
        self.assertEqual(by_label["Audit"], ["PASS", "—"])

    def test_none_packet(self):
        self.assertIsNone(headline_view(None))
        self.assertIsNone(headline_view({}))


class NavForPathTests(unittest.TestCase):
    def test_closed_set(self):
        self.assertEqual(nav_for_path("/")["current"], "runs")
        self.assertEqual(nav_for_path("/runs")["current"], "runs")
        self.assertEqual(nav_for_path("/runs/research:META:2026-08-03")["current"], "runs")
        self.assertEqual(nav_for_path("/artifact")["current"], "runs")
        self.assertEqual(nav_for_path("/analyze")["current"], "analyze")
        self.assertEqual(nav_for_path("/analyze/new")["current"], "analyze")
        self.assertEqual(nav_for_path("/analyze-artifact")["current"], "analyze")
        self.assertEqual(nav_for_path("/compares")["current"], "compare")
        self.assertEqual(nav_for_path("/compare-artifact")["current"], "compare")
        self.assertEqual(nav_for_path("/portfolio")["current"], "portfolio")
        self.assertEqual(nav_for_path("/harness")["current"], "harness")
        self.assertEqual(nav_for_path("/architecture")["current"], "architecture")
        self.assertEqual(nav_for_path("/experiments")["current"], "experiments")
        self.assertEqual(nav_for_path("/calibration")["current"], "calibration")
        self.assertEqual(nav_for_path("/health")["current"], "health")

    def test_unknown_and_api_are_empty(self):
        self.assertEqual(nav_for_path("/this-path-does-not-exist")["current"], "")
        self.assertEqual(nav_for_path("/api/runs")["current"], "")

    def test_menu_label(self):
        self.assertEqual(nav_for_path("/")["menu"], "Menu")
        self.assertEqual(nav_for_path("/analyze")["menu"], "Menu · Analyze")
        self.assertEqual(nav_for_path("/compares/x")["menu"], "Menu · Compare")
        self.assertEqual(nav_for_path("/nope")["menu"], "Menu")

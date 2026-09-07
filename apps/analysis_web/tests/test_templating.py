"""Display helpers: Downside % is (price - fv_bear) / price * 100."""

from __future__ import annotations

import unittest

from apps.analysis_web.templating import (
    downside_pct,
    downside_title,
    fmt_num,
    headline_view,
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

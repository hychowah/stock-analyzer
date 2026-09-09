"""Select by |value|, then order signed descending."""

from __future__ import annotations

import unittest

from apps.analysis_web.services.signed_bars import signed_bar_rows


class SignedBarRowsTests(unittest.TestCase):
    def test_select_by_abs_then_gains_top_losses_bottom(self):
        rows = signed_bar_rows(
            [("a", 100.0), ("b", -90.0), ("c", 10.0)],
            top_n=2,
        )
        names = [r["name"] for r in rows]
        self.assertEqual(names, ["a", "other", "b"])
        self.assertAlmostEqual(rows[0]["pl"], 100.0, places=5)
        self.assertAlmostEqual(rows[1]["pl"], 10.0, places=5)
        self.assertAlmostEqual(rows[2]["pl"], -90.0, places=5)
        self.assertEqual(rows[0]["sign"], "pos")
        self.assertEqual(rows[2]["sign"], "neg")
        self.assertGreater(rows[0]["bar_pct"], rows[1]["bar_pct"])

    def test_other_omitted_when_nothing_left(self):
        rows = signed_bar_rows([("gain", 50.0), ("loss", -20.0)], top_n=20)
        self.assertEqual([r["name"] for r in rows], ["gain", "loss"])

    def test_coalesces_duplicate_names(self):
        rows = signed_bar_rows([("META", 10.0), ("META", -3.0)])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "META")
        self.assertAlmostEqual(rows[0]["pl"], 7.0, places=5)

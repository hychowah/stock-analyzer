"""Unit tests for analysis_web markdown sanitizer."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from apps.analysis_web.services.render_markdown import (  # noqa: E402
    render_json_pretty,
    render_markdown,
)


class RenderMarkdownTests(unittest.TestCase):
    def test_heading(self):
        html = render_markdown("# Hello META\n")
        self.assertIn("<h1>", html)
        self.assertIn("Hello META", html)

    def test_strips_script(self):
        # Raw HTML in source is not executed (html=False → escaped text or stripped tags)
        html = render_markdown(
            'Hi <script>alert(1)</script>\n\n[x](javascript:alert(1))\n\n'
            '<img src=x onerror=alert(1)>\n'
        )
        # No live HTML tags/handlers (escaped text like &lt;img …&gt; is OK)
        self.assertNotIn("<script>", html.lower())
        self.assertNotIn("<img", html.lower())
        self.assertNotIn('href="javascript:', html.lower())
        self.assertIn("<p>", html)

    def test_table(self):
        md = "| a | b |\n| --- | --- |\n| 1 | 2 |\n"
        html = render_markdown(md)
        self.assertIn("<table>", html)
        self.assertIn("<td>", html)

    def test_json_pretty(self):
        out = render_json_pretty(b'{"z":1,"a":2}')
        self.assertIn('"a": 2', out)
        self.assertIn("\n", out)


if __name__ == "__main__":
    unittest.main()

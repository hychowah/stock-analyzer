"""Unit tests for analysis_web markdown sanitizer."""

from __future__ import annotations

import unittest

from apps.analysis_web.services.render_markdown import (
    render_json_pretty,
    render_markdown,
)


class RenderMarkdownTests(unittest.TestCase):
    def test_heading(self):
        html = render_markdown("# Hello META\n")
        self.assertIn("<h1", html)
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

    def test_heading_ids_match_in_doc_anchors(self):
        html = render_markdown(
            "## Keeping this document current\n\n"
            "See [duty](#keeping-this-document-current).\n"
        )
        self.assertIn('id="keeping-this-document-current"', html)
        self.assertIn('href="#keeping-this-document-current"', html)

    def test_duplicate_heading_ids(self):
        html = render_markdown("## Hello\n\n## Hello\n")
        self.assertIn('id="hello"', html)
        self.assertIn('id="hello-1"', html)

    def test_mermaid_fence_becomes_pre_mermaid(self):
        html = render_markdown("```mermaid\nflowchart TB\n  A-->B\n```\n")
        self.assertIn('class="mermaid"', html)
        self.assertIn("flowchart TB", html)
        self.assertNotIn("language-mermaid", html)

    def test_mermaid_fence_strips_html(self):
        html = render_markdown(
            "```mermaid\nflowchart TB\n"
            "  A[\"<script>alert(1)</script>\"]\n"
            "  B[<img src=x onerror=alert(1)>]\n```\n"
        )
        self.assertIn('class="mermaid"', html)
        self.assertNotIn("<script>", html.lower())
        self.assertNotIn("<img", html.lower())

    def test_python_fence_stays_code(self):
        html = render_markdown("```python\nprint(1)\n```\n")
        self.assertIn("language-python", html)
        self.assertNotIn('class="mermaid"', html)

    def test_json_pretty(self):
        out = render_json_pretty(b'{"z":1,"a":2}')
        self.assertIn('"a": 2', out)
        self.assertIn("\n", out)


if __name__ == "__main__":
    unittest.main()

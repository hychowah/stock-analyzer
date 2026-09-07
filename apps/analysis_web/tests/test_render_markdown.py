"""Unit tests for analysis_web markdown sanitizer."""

from __future__ import annotations

import unittest

from apps.analysis_web.services.render_markdown import (
    render_json_pretty,
    render_markdown,
    render_session_report,
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

    def test_render_markdown_stays_str_without_run_id(self):
        html = render_markdown("# Hello META\n")
        self.assertIsInstance(html, str)
        self.assertNotIn("run_id", render_markdown.__code__.co_varnames)


class RenderSessionReportTests(unittest.TestCase):
    def test_title_from_first_h1_not_duplicated_in_body(self):
        doc = render_session_report(
            "# CIO cover\n\n## Thesis\n\nBody.\n",
            run_id="research:META:2026-08-03",
            relpath="reports/00_META_README.md",
        )
        self.assertEqual(doc["title"], "CIO cover")
        self.assertNotIn("<h1", doc["html"])
        self.assertEqual(doc["toc"][0]["text"], "Thesis")
        self.assertEqual(doc["toc"][0]["id"], "thesis")
        self.assertEqual(doc["toc"][0]["level"], 2)

    def test_title_falls_back_to_relpath(self):
        doc = render_session_report(
            "No heading, just prose.\n",
            run_id="research:META:2026-08-03",
            relpath="reports/notes.md",
        )
        self.assertEqual(doc["title"], "reports/notes.md")
        self.assertIn("<p>", doc["html"])

    def test_sibling_md_resolved_against_relpath_dir(self):
        doc = render_session_report(
            "# Cover\n\nSee [fundamental](01_META_fundamental.md).\n",
            run_id="research:META:2026-08-03",
            relpath="reports/00_META_README.md",
        )
        html = doc["html"]
        self.assertIn("/artifact?run_id=research%3AMETA%3A2026-08-03", html)
        self.assertIn("path=reports%2F01_META_fundamental.md", html)
        self.assertNotIn('href="01_META_fundamental.md"', html)

    def test_dot_slash_and_already_prefixed_path(self):
        doc = render_session_report(
            "# Cover\n\n[a](./01_foo.md) [b](reports/01_foo.md)\n",
            run_id="research:META:2026-08-03",
            relpath="reports/00_META_README.md",
        )
        html = doc["html"]
        self.assertEqual(html.count("path=reports%2F01_foo.md"), 2)
        self.assertNotIn("reports%2Freports%2F", html)
        self.assertNotIn('href="reports/01_foo.md"', html)

    def test_parent_and_non_allowlisted_hrefs_are_dropped(self):
        doc = render_session_report(
            "# Cover\n\n[escape](../meta/foo.md) [deny](../../etc/passwd.md)\n",
            run_id="research:META:2026-08-03",
            relpath="reports/00_META_README.md",
        )
        html = doc["html"]
        self.assertNotIn("../", html)
        self.assertNotIn("passwd", html)
        self.assertNotIn("meta/foo.md", html)
        self.assertNotIn("run_id=", html)

    def test_hash_and_http_hrefs_left_alone(self):
        doc = render_session_report(
            "# Cover\n\nSee [here](#thesis) and [sec](https://www.sec.gov/x.md).\n\n## Thesis\n",
            run_id="research:META:2026-08-03",
            relpath="reports/00_META_README.md",
        )
        html = doc["html"]
        self.assertIn('href="#thesis"', html)
        self.assertIn('href="https://www.sec.gov/x.md"', html)
        self.assertNotIn("/artifact?run_id=", html)

    def test_href_base_is_a_parameter(self):
        doc = render_session_report(
            "# Cover\n\n[f](01_foo.md)\n",
            run_id="research:META:2026-08-03",
            relpath="reports/00_META_README.md",
            href_base="/compare-artifact",
            id_query="compare_id",
        )
        self.assertIn("/compare-artifact?compare_id=", doc["html"])
        self.assertNotIn("run_id=", doc["html"])
        self.assertNotIn("/artifact?", doc["html"])


if __name__ == "__main__":
    unittest.main()

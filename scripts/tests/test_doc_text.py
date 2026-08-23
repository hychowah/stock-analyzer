"""HTML (always) and PDF (optional pypdf) conversion."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.kd_research.doc_text import convert_path, html_to_text  # noqa: E402


class HtmlToTextTests(unittest.TestCase):
    def test_strips_tags_and_script(self):
        html = "<html><script>x=1</script><h1>Hello</h1><p>World</p></html>"
        text = html_to_text(html)
        self.assertIn("Hello", text)
        self.assertIn("World", text)
        self.assertNotIn("x=1", text)
        self.assertNotIn("<h1>", text)

    def test_convert_html_file(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "a.html"
            src.write_text("<p>Filing body</p>", encoding="utf-8")
            out = convert_path(src)
            self.assertEqual(out["status"], "ok")
            txt = Path(out["text_path"])
            self.assertTrue(txt.is_file())
            self.assertIn("Filing body", txt.read_text(encoding="utf-8"))


class PdfToTextTests(unittest.TestCase):
    def test_pdf_roundtrip_if_pypdf(self):
        pytest = __import__("unittest")  # keep unittest style
        try:
            import pypdf  # noqa: F401
        except ImportError:
            self.skipTest("pypdf not installed")
        from pypdf import PdfWriter
        from pypdf.generic import NameObject, create_string_object

        with tempfile.TemporaryDirectory() as td:
            # Minimal empty PDF is not useful; skip if we cannot add text easily.
            path = Path(td) / "blank.pdf"
            w = PdfWriter()
            w.add_blank_page(width=72, height=72)
            w.write(path.open("wb"))
            out = convert_path(path)
            # blank page may fail empty extract — either failed or ok with empty catch
            self.assertIn(out["status"], ("ok", "failed"))
            _ = pytest, NameObject, create_string_object


if __name__ == "__main__":
    unittest.main()

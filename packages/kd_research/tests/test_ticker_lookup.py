"""Mode A market-ticker abort (no network)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from packages.kd_research.scaffold import scaffold
from packages.kd_research.ticker_lookup import (
    FakeBackend,
    Quote,
    check_ticker,
    levenshtein,
    require_market_ticker,
)
from scripts.verify_ticker import main as verify_main


def _q(sym: str, *, qt: str = "EQUITY", name: str = "Co", n: int = 80, price: float = 1.0) -> Quote:
    return Quote(symbol=sym, quote_type=qt, name=name, n_fields=n, price=price)


class LevenshteinTests(unittest.TestCase):
    def test_distance(self) -> None:
        self.assertEqual(levenshtein("AAPL", "AAPL"), 0)
        self.assertEqual(levenshtein("APPL", "AAPL"), 1)
        self.assertEqual(levenshtein("META", "MSFT"), 3)


class TickerLookupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.be = FakeBackend(
            quotes={
                "META": _q("META", name="Meta Platforms, Inc."),
                "AAPL": _q("AAPL", name="Apple Inc."),
                "BRK-B": _q("BRK-B", name="Berkshire Hathaway Inc. New", n=172),
                "BRK.B": Quote(symbol="BRK.B", quote_type="EQUITY", name=None, n_fields=15, price=None),
                "APPL": Quote(symbol="APPL", quote_type="MUTUALFUND", name=None, n_fields=25, price=None),
                "0700.HK": _q("0700.HK", name="TENCENT", n=171),
            },
            search_hits={
                "APPL": [_q("AAPL", name="Apple Inc."), _q("AMAT", name="Applied Materials")],
                "ZZZNOPE": [],
            },
        )

    def test_real_ticker_ok(self) -> None:
        r = check_ticker("meta", backend=self.be)
        self.assertEqual(r.status, "ok")
        self.assertEqual(r.canonical, "META")

    def test_typo_obvious_match_aborts(self) -> None:
        r = check_ticker("APPL", backend=self.be)
        self.assertEqual(r.status, "abort_match")
        self.assertEqual(r.matches, ["AAPL"])
        self.assertIn("AAPL", r.reason)
        with self.assertRaises(ValueError) as ctx:
            require_market_ticker("APPL", backend=self.be)
        self.assertIn("AAPL", str(ctx.exception))

    def test_unknown_no_match_aborts(self) -> None:
        r = check_ticker("ZZZNOPE", backend=self.be)
        self.assertEqual(r.status, "abort_unknown")
        self.assertEqual(r.matches, [])
        self.assertIn("no obvious match", r.reason)

    def test_reserved_name_aborts(self) -> None:
        r = check_ticker("eng", backend=self.be)
        self.assertEqual(r.status, "abort_reserved")

    def test_syntax_aborts(self) -> None:
        r = check_ticker("not a ticker", backend=self.be)
        self.assertEqual(r.status, "abort_syntax")

    def test_brk_dot_b_is_alias_match(self) -> None:
        r = check_ticker("BRK.B", backend=self.be)
        self.assertEqual(r.status, "abort_match")
        self.assertEqual(r.matches, ["BRK-B"])

    def test_hk_padding_alias(self) -> None:
        r = check_ticker("700.HK", backend=self.be)
        self.assertEqual(r.status, "abort_match")
        self.assertIn("0700.HK", r.matches)

    def test_scaffold_python_api_skips_lookup(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = scaffold(
                "ZZFAKE",
                "2099-01-01",
                output_dir=td,
                orchestrator_model="grok-4.5",
                verify_ticker=False,
            )
            self.assertTrue((root / "meta" / "run_manifest.json").is_file())

    def test_scaffold_verify_aborts_without_folder(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError) as ctx:
                scaffold(
                    "ZZZNOPE",
                    "2099-01-01",
                    output_dir=td,
                    orchestrator_model="grok-4.5",
                    verify_ticker=True,
                    ticker_backend=self.be,
                )
            self.assertIn("ABORTED", str(ctx.exception))
            research = Path(td) / "archive" / "research" / "ZZZNOPE"
            self.assertFalse(research.exists())


class VerifyCliTests(unittest.TestCase):
    def test_cli_help_ok(self) -> None:
        with self.assertRaises(SystemExit):
            verify_main(["--help"])


if __name__ == "__main__":
    unittest.main()

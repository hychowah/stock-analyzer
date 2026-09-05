"""Mode A market-ticker existence + listing confirm (no network, no LLM)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from packages.kd_research.scaffold import scaffold
from packages.kd_research.ticker_lookup import (
    FakeBackend,
    Quote,
    check_ticker,
    confirm_listing,
    confirm_session_listing,
    quote_symbol_from_session,
)
from scripts.verify_listing import main as listing_main
from scripts.verify_ticker import main as verify_main


def _q(sym: str, *, qt: str = "EQUITY", name: str = "Co", n: int = 80, price: float = 1.0) -> Quote:
    return Quote(symbol=sym, quote_type=qt, name=name, n_fields=n, price=price)


class TickerLookupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.be = FakeBackend(
            quotes={
                "META": _q("META", name="Meta Platforms, Inc."),
                "AAPL": _q("AAPL", name="Apple Inc."),
                "ADYEN.AS": _q("ADYEN.AS", name="Adyen N.V."),
                "BRK.B": Quote(symbol="BRK.B", quote_type="EQUITY", name=None, n_fields=15, price=None),
                "APPL": Quote(symbol="APPL", quote_type="MUTUALFUND", name=None, n_fields=25, price=None),
            },
            search_hits={
                "APPL": [_q("AAPL", name="Apple Inc.")],
                "ADYEN": [_q("ADYEN.AS", name="Adyen N.V.")],
                "ZZZNOPE": [],
            },
        )

    def test_quoted(self) -> None:
        r = check_ticker("meta", backend=self.be)
        self.assertEqual(r.status, "quoted")
        self.assertTrue(r.ok)
        self.assertEqual(r.typed, "META")

    def test_search_evidence_does_not_remap_or_stamp(self) -> None:
        r = check_ticker("ADYEN", backend=self.be)
        self.assertEqual(r.status, "search_evidence")
        self.assertTrue(r.ok)
        self.assertEqual(r.typed, "ADYEN")
        self.assertNotIn("ADYEN.AS", r.reason)

    def test_unknown_no_listings_aborts(self) -> None:
        r = check_ticker("ZZZNOPE", backend=self.be)
        self.assertEqual(r.status, "abort_unknown")
        self.assertFalse(r.ok)

    def test_reserved_name_aborts(self) -> None:
        r = check_ticker("eng", backend=self.be)
        self.assertEqual(r.status, "abort_reserved")

    def test_syntax_aborts(self) -> None:
        r = check_ticker("not a ticker", backend=self.be)
        self.assertEqual(r.status, "abort_syntax")

    def test_typo_with_search_still_search_evidence(self) -> None:
        r = check_ticker("APPL", backend=self.be)
        self.assertEqual(r.status, "search_evidence")
        self.assertNotIn("AAPL", r.reason)

    def test_scaffold_leaves_quote_symbol_null(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = scaffold(
                "ZZFAKE",
                "2099-01-01",
                output_dir=td,
                orchestrator_model="grok-4.5",
            )
            man = json.loads((root / "meta" / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertIsNone(man.get("quote_symbol"))

    def test_unknown_does_not_scaffold(self) -> None:
        r = check_ticker("ZZZNOPE", backend=self.be)
        self.assertEqual(r.status, "abort_unknown")
        with tempfile.TemporaryDirectory() as td:
            self.assertFalse((Path(td) / "archive" / "research" / "ZZZNOPE").exists())

    def test_quote_symbol_from_session_reads_stamp(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = Path(td)
            (session / "meta").mkdir()
            (session / "meta" / "run_manifest.json").write_text(
                json.dumps({"ticker": "ADYEN", "quote_symbol": "ADYEN.AS"}),
                encoding="utf-8",
            )
            self.assertEqual(quote_symbol_from_session(session), "ADYEN.AS")

    def test_quote_symbol_from_session_missing_is_none(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = Path(td)
            (session / "meta").mkdir()
            (session / "meta" / "run_manifest.json").write_text(
                json.dumps({"ticker": "ADYEN"}),
                encoding="utf-8",
            )
            with patch(
                "packages.kd_research.ticker_lookup.check_ticker",
                side_effect=AssertionError("must not re-run lookup"),
            ):
                self.assertIsNone(quote_symbol_from_session(session))

    def test_confirm_listing_quotes(self) -> None:
        ok = confirm_listing("ADYEN.AS", backend=self.be)
        self.assertTrue(ok.ok)
        bad = confirm_listing("ADYEN", backend=self.be)
        self.assertFalse(bad.ok)

    def test_confirm_session_listing_requires_stamp(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = Path(td)
            (session / "meta").mkdir()
            (session / "meta" / "run_manifest.json").write_text(
                json.dumps({"ticker": "ADYEN", "quote_symbol": None}),
                encoding="utf-8",
            )
            r = confirm_session_listing(session, backend=self.be)
            self.assertFalse(r.ok)
            (session / "meta" / "run_manifest.json").write_text(
                json.dumps({"ticker": "ADYEN", "quote_symbol": "ADYEN.AS"}),
                encoding="utf-8",
            )
            r2 = confirm_session_listing(session, backend=self.be)
            self.assertTrue(r2.ok)


class VerifyCliTests(unittest.TestCase):
    def test_ticker_cli_help_ok(self) -> None:
        with self.assertRaises(SystemExit):
            verify_main(["--help"])

    def test_listing_cli_help_ok(self) -> None:
        with self.assertRaises(SystemExit):
            listing_main(["--help"])


class NoHardcodedYahooMapTests(unittest.TestCase):
    def test_outcome_marks_has_no_ticker_map(self) -> None:
        import scripts.fetch_outcome_marks as fom

        self.assertFalse(hasattr(fom, "YAHOO_SYMBOL_MAP"))
        self.assertFalse(hasattr(fom, "yahoo_symbol"))


if __name__ == "__main__":
    unittest.main()

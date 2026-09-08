"""Interactive Brokers activity CSV → typed statement.

Parses the sectioned Activity Statement export. Does not open sqlite, join
the research catalog, or map IB symbols to catalog tickers. Forex close
rates are copied onto the object; conversion is ``IbStatement.value_base``.

``IbStatement`` is one CSV report. ``IbBook`` is the stored book: latest
snapshot plus the account trade ledger.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


# Account Information / Statement keys that may be kept. Name and address
# are never stored on IbStatement.
_STATEMENT_KEYS = frozenset({"BrokerName", "Title", "Period", "WhenGenerated"})
_ACCOUNT_KEYS = frozenset({"Account", "Base Currency"})


@dataclass
class NavAsset:
    asset_class: str
    prior_total: float | None = None
    current_long: float | None = None
    current_short: float | None = None
    current_total: float | None = None
    change: float | None = None


@dataclass
class NavComponent:
    name: str
    value: float | None = None


@dataclass
class Cashflow:
    currency: str
    settle_date: str
    description: str
    amount: float | None = None


@dataclass
class Position:
    ib_symbol: str
    asset_category: str
    currency: str
    quantity: float | None = None
    multiplier: float | None = None
    cost_price: float | None = None
    cost_basis: float | None = None
    close_price: float | None = None
    value: float | None = None
    unrealized_pl: float | None = None
    listing_exch: str | None = None
    description: str = ""


@dataclass
class Instrument:
    asset_category: str
    ib_symbol: str
    description: str = ""
    listing_exch: str | None = None
    security_id: str | None = None


@dataclass
class MtmRow:
    asset_category: str
    ib_symbol: str
    pl_total: float | None = None
    current_qty: float | None = None
    current_price: float | None = None


@dataclass
class Trade:
    row_index: int
    discriminator: str
    asset_category: str
    currency: str
    ib_symbol: str
    traded_at: str
    quantity: float | None = None
    trade_price: float | None = None
    close_price: float | None = None
    proceeds: float | None = None
    commission: float | None = None
    basis: float | None = None
    realized_pl: float | None = None
    mtm_pl: float | None = None
    code: str = ""


def trade_fingerprint(account_id: str, trade: Trade) -> str:
    """Stable identity for one fill. MTM, basis, realized P/L, commission excluded."""
    return json.dumps(
        [
            (account_id or "").strip(),
            (trade.asset_category or "").strip(),
            (trade.currency or "").strip(),
            (trade.ib_symbol or "").strip(),
            (trade.traded_at or "").strip(),
            trade.quantity,
            trade.trade_price,
            (trade.discriminator or "").strip(),
        ],
        separators=(",", ":"),
        ensure_ascii=True,
    )


def dedupe_trades(account_id: str, trades: list[Trade]) -> list[Trade]:
    """Keep first occurrence of each fingerprint (in-file overlap / second Trades table)."""
    seen: set[str] = set()
    out: list[Trade] = []
    for t in trades:
        fp = trade_fingerprint(account_id, t)
        if fp in seen:
            continue
        seen.add(fp)
        out.append(t)
    return out


@dataclass
class IngestResult:
    statement_id: int
    account_id: str
    period_from: str
    period_to: str
    inserted: int
    skipped: int
    conflicts: int


@dataclass
class IbBook:
    """Latest snapshot plus the account trade ledger.

    ``snapshot.period_from`` / ``snapshot.period_to`` apply to snapshot fields
    only, never to ``trades``. ``snapshot.trades`` is unused; fills live here.
    """

    snapshot: IbStatement
    trades: list[Trade] = field(default_factory=list)


@dataclass
class IbStatement:
    """One activity statement CSV report. Identity of a holding is ``ib_symbol``.

    ``period_from`` / ``period_to`` apply to this file only.
    """

    account_id: str
    period_from: str
    period_to: str
    base_currency: str = "HKD"
    broker: str = ""
    title: str = ""
    source_csv: str = ""
    starting_nav: float | None = None
    ending_nav: float | None = None
    twr_pct: float | None = None
    deposits_total: float | None = None
    nav_assets: list[NavAsset] = field(default_factory=list)
    nav_components: list[NavComponent] = field(default_factory=list)
    cashflows: list[Cashflow] = field(default_factory=list)
    positions: list[Position] = field(default_factory=list)
    instruments: list[Instrument] = field(default_factory=list)
    mtm: list[MtmRow] = field(default_factory=list)
    trades: list[Trade] = field(default_factory=list)
    forex_closes: dict[str, float] = field(default_factory=dict)

    def forex_close(self, currency: str) -> float | None:
        cur = (currency or "").strip().upper()
        base = (self.base_currency or "").strip().upper()
        if cur and cur == base:
            return 1.0
        rate = self.forex_closes.get(cur)
        if rate is None and cur == "HKD":
            return 1.0
        return rate

    def value_base(self, native_value: float | None, currency: str) -> float | None:
        """Native amount × Forex Balances close (base currency = 1)."""
        if native_value is None:
            return None
        rate = self.forex_close(currency)
        if rate is None:
            return None
        return float(native_value) * float(rate)

    def nav_asset(self, asset_class: str) -> NavAsset | None:
        want = asset_class.strip().lower()
        for row in self.nav_assets:
            if row.asset_class.strip().lower() == want:
                return row
        return None


def parse_number(raw: Any) -> float | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s in {"--", "N/A", "n/a", "nan"}:
        return None
    neg = s.startswith("(") and s.endswith(")")
    if neg:
        s = s[1:-1]
    s = s.replace(",", "").replace("%", "").replace(" ", "")
    try:
        n = float(s)
    except ValueError:
        return None
    if n != n or n in (float("inf"), float("-inf")):
        return None
    return -n if neg else n


def parse_traded_at(raw: str) -> str:
    s = (raw or "").strip().strip('"')
    if not s:
        return ""
    if "," in s:
        day, rest = s.split(",", 1)
        return f"{day.strip()}T{rest.strip()}"
    return s


def parse_period(raw: str) -> tuple[str | None, str | None]:
    s = (raw or "").strip().strip('"')
    if " - " in s:
        left, right = s.split(" - ", 1)
        return _parse_long_date(left.strip()), _parse_long_date(right.strip())
    iso = _parse_long_date(s)
    return iso, iso


def _parse_long_date(raw: str) -> str | None:
    s = (raw or "").strip()
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    m = re.match(r"(\d{4}-\d{2}-\d{2})", s)
    return m.group(1) if m else None


def _zip_row(header: list[str], row: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for i, key in enumerate(header):
        name = (key or "").strip()
        if not name:
            continue
        out[name] = row[i] if i < len(row) else ""
    return out


def parse_activity_csv(path: Path | str) -> IbStatement:
    """Load one IB activity CSV. Raises ValueError if the file is not a statement."""
    p = Path(path)
    with p.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    if not rows:
        raise ValueError(f"empty CSV: {p}")

    headers: dict[str, list[str]] = {}
    kv: dict[str, dict[str, str]] = {}
    nav_assets: list[NavAsset] = []
    nav_components: list[NavComponent] = []
    cashflows: list[Cashflow] = []
    positions: list[Position] = []
    instruments: list[Instrument] = []
    mtm: list[MtmRow] = []
    trades: list[Trade] = []
    forex_closes: dict[str, float] = {}
    twr_pct: float | None = None
    trade_index = 0

    for row in rows:
        if len(row) < 2:
            continue
        section = row[0].strip()
        kind = row[1].strip()
        rest = row[2:]

        if kind == "Header":
            headers[section] = [c.strip() for c in rest]
            continue
        if kind in {"Total", "SubTotal"}:
            continue
        if kind != "Data":
            continue

        header = headers.get(section) or []
        rec = _zip_row(header, rest) if header else {}

        if section == "Statement":
            field = (rec.get("Field Name") or (rest[0] if rest else "")).strip()
            value = rec.get("Field Value") if "Field Value" in rec else (rest[1] if len(rest) > 1 else "")
            if field in _STATEMENT_KEYS:
                kv.setdefault("Statement", {})[field] = value
            continue

        if section == "Account Information":
            field = (rec.get("Field Name") or (rest[0] if rest else "")).strip()
            value = rec.get("Field Value") if "Field Value" in rec else (rest[1] if len(rest) > 1 else "")
            if field in _ACCOUNT_KEYS:
                kv.setdefault("Account", {})[field] = value
            continue

        if section == "Net Asset Value":
            if header == ["Time Weighted Rate of Return"] or (
                len(header) == 1 and "Time Weighted" in header[0]
            ):
                twr_pct = parse_number(rest[0] if rest else rec.get(header[0]))
                continue
            asset = (rec.get("Asset Class") or (rest[0] if rest else "")).strip()
            if not asset or asset.lower() == "time weighted rate of return":
                if rest:
                    twr_pct = parse_number(rest[0])
                continue
            nav_assets.append(
                NavAsset(
                    asset_class=asset,
                    prior_total=parse_number(rec.get("Prior Total")),
                    current_long=parse_number(rec.get("Current Long")),
                    current_short=parse_number(rec.get("Current Short")),
                    current_total=parse_number(rec.get("Current Total")),
                    change=parse_number(rec.get("Change")),
                )
            )
            continue

        if section == "Change in NAV":
            name = (rec.get("Field Name") or (rest[0] if rest else "")).strip()
            if not name:
                continue
            value = rec.get("Field Value") if "Field Value" in rec else (rest[1] if len(rest) > 1 else "")
            nav_components.append(NavComponent(name=name, value=parse_number(value)))
            continue

        if section == "Deposits & Withdrawals":
            currency = (rec.get("Currency") or "").strip()
            settle = (rec.get("Settle Date") or "").strip()[:10]
            if currency.lower() == "total" or not settle:
                continue
            cashflows.append(
                Cashflow(
                    currency=currency,
                    settle_date=settle,
                    description=(rec.get("Description") or "").strip(),
                    amount=parse_number(rec.get("Amount")),
                )
            )
            continue

        if section == "Open Positions":
            disc = (rec.get("DataDiscriminator") or "").strip()
            if disc and disc.lower() != "summary":
                continue
            symbol = (rec.get("Symbol") or "").strip()
            if not symbol:
                continue
            positions.append(
                Position(
                    ib_symbol=symbol,
                    asset_category=(rec.get("Asset Category") or "").strip(),
                    currency=(rec.get("Currency") or "").strip(),
                    quantity=parse_number(rec.get("Quantity")),
                    multiplier=parse_number(rec.get("Mult")),
                    cost_price=parse_number(rec.get("Cost Price")),
                    cost_basis=parse_number(rec.get("Cost Basis")),
                    close_price=parse_number(rec.get("Close Price")),
                    value=parse_number(rec.get("Value")),
                    unrealized_pl=parse_number(rec.get("Unrealized P/L")),
                )
            )
            continue

        if section == "Financial Instrument Information":
            symbol = (rec.get("Symbol") or "").strip()
            if not symbol:
                continue
            instruments.append(
                Instrument(
                    asset_category=(rec.get("Asset Category") or "").strip(),
                    ib_symbol=symbol,
                    description=(rec.get("Description") or "").strip(),
                    listing_exch=(rec.get("Listing Exch") or "").strip() or None,
                    security_id=(rec.get("Security ID") or "").strip() or None,
                )
            )
            continue

        if section == "Mark-to-Market Performance Summary":
            cat = (rec.get("Asset Category") or "").strip()
            symbol = (rec.get("Symbol") or "").strip()
            if not symbol or cat.lower().startswith("total"):
                continue
            mtm.append(
                MtmRow(
                    asset_category=cat,
                    ib_symbol=symbol,
                    pl_total=parse_number(rec.get("Mark-to-Market P/L Total")),
                    current_qty=parse_number(rec.get("Current Quantity")),
                    current_price=parse_number(rec.get("Current Price")),
                )
            )
            continue

        if section == "Trades":
            symbol = (rec.get("Symbol") or "").strip()
            if not symbol:
                continue
            trades.append(
                Trade(
                    row_index=trade_index,
                    discriminator=(rec.get("DataDiscriminator") or "").strip(),
                    asset_category=(rec.get("Asset Category") or "").strip(),
                    currency=(rec.get("Currency") or "").strip(),
                    ib_symbol=symbol,
                    traded_at=parse_traded_at(rec.get("Date/Time") or ""),
                    quantity=parse_number(rec.get("Quantity")),
                    trade_price=parse_number(rec.get("T. Price")),
                    close_price=parse_number(rec.get("C. Price")),
                    proceeds=parse_number(rec.get("Proceeds")),
                    commission=parse_number(rec.get("Comm/Fee")),
                    basis=parse_number(rec.get("Basis")),
                    realized_pl=parse_number(rec.get("Realized P/L")),
                    mtm_pl=parse_number(rec.get("MTM P/L")),
                    code=(rec.get("Code") or "").strip(),
                )
            )
            trade_index += 1
            continue

        if section == "Forex Balances":
            # Close Price is quoted currency (Description) per 1 unit, in base.
            quoted = (rec.get("Description") or "").strip().upper()
            rate = parse_number(rec.get("Close Price"))
            if quoted and rate is not None:
                forex_closes[quoted] = rate
            continue

    acct = kv.get("Account") or {}
    stmt_kv = kv.get("Statement") or {}
    account_id = (acct.get("Account") or "").strip()
    period_from, period_to = parse_period(stmt_kv.get("Period") or "")
    if not account_id:
        raise ValueError(f"no Account in statement: {p}")
    if not period_from or not period_to:
        raise ValueError(f"unparseable Period in statement: {p}")

    inst_by_symbol = {i.ib_symbol: i for i in instruments}
    for pos in positions:
        inst = inst_by_symbol.get(pos.ib_symbol)
        if inst:
            pos.listing_exch = inst.listing_exch
            pos.description = inst.description

    nav_by_name = {c.name: c.value for c in nav_components}
    deposit_sum = sum(c.amount or 0.0 for c in cashflows)
    deposits_total = nav_by_name.get("Deposits & Withdrawals")
    if deposits_total is None and cashflows:
        deposits_total = deposit_sum

    total_asset = next(
        (a for a in nav_assets if a.asset_class.strip().lower() == "total"),
        None,
    )
    ending = nav_by_name.get("Ending Value")
    if ending is None and total_asset is not None:
        ending = total_asset.current_total
    starting = nav_by_name.get("Starting Value")

    if "HKD" not in forex_closes:
        forex_closes["HKD"] = 1.0
    base = (acct.get("Base Currency") or "HKD").strip() or "HKD"
    if base not in forex_closes:
        forex_closes[base] = 1.0

    trades = dedupe_trades(account_id, trades)

    return IbStatement(
        account_id=account_id,
        period_from=period_from,
        period_to=period_to,
        base_currency=base,
        broker=(stmt_kv.get("BrokerName") or "").strip(),
        title=(stmt_kv.get("Title") or "").strip(),
        source_csv=str(p),
        starting_nav=starting,
        ending_nav=ending,
        twr_pct=twr_pct,
        deposits_total=deposits_total,
        nav_assets=nav_assets,
        nav_components=nav_components,
        cashflows=cashflows,
        positions=positions,
        instruments=instruments,
        mtm=mtm,
        trades=trades,
        forex_closes=forex_closes,
    )

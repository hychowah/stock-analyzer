"""App-local sqlite for one IB activity statement.

Callers use ``replace_statement`` / ``load``. Table names stay inside this
module. Catalog tickers are not stored.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from apps.analysis_web.services.ib_statement import (
    Cashflow,
    IbStatement,
    Instrument,
    MtmRow,
    NavAsset,
    NavComponent,
    Position,
    Trade,
)


SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS statements (
  id INTEGER PRIMARY KEY,
  account_id TEXT NOT NULL,
  broker TEXT,
  title TEXT,
  period_from TEXT NOT NULL,
  period_to TEXT NOT NULL,
  base_currency TEXT NOT NULL,
  source_csv TEXT,
  starting_nav REAL,
  ending_nav REAL,
  twr_pct REAL,
  deposits_total REAL,
  imported_at TEXT NOT NULL,
  UNIQUE(account_id, period_from, period_to)
);
CREATE TABLE IF NOT EXISTS nav_assets (
  statement_id INTEGER NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
  row_index INTEGER NOT NULL,
  asset_class TEXT NOT NULL,
  prior_total REAL,
  current_long REAL,
  current_short REAL,
  current_total REAL,
  change_amt REAL
);
CREATE TABLE IF NOT EXISTS nav_components (
  statement_id INTEGER NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
  row_index INTEGER NOT NULL,
  name TEXT NOT NULL,
  value REAL
);
CREATE TABLE IF NOT EXISTS cashflows (
  statement_id INTEGER NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
  row_index INTEGER NOT NULL,
  currency TEXT,
  settle_date TEXT,
  description TEXT,
  amount REAL
);
CREATE TABLE IF NOT EXISTS positions (
  statement_id INTEGER NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
  row_index INTEGER NOT NULL,
  ib_symbol TEXT NOT NULL,
  asset_category TEXT,
  currency TEXT,
  quantity REAL,
  multiplier REAL,
  cost_price REAL,
  cost_basis REAL,
  close_price REAL,
  value REAL,
  unrealized_pl REAL,
  listing_exch TEXT,
  description TEXT
);
CREATE TABLE IF NOT EXISTS instruments (
  statement_id INTEGER NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
  row_index INTEGER NOT NULL,
  asset_category TEXT,
  ib_symbol TEXT NOT NULL,
  description TEXT,
  listing_exch TEXT,
  security_id TEXT
);
CREATE TABLE IF NOT EXISTS mtm (
  statement_id INTEGER NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
  row_index INTEGER NOT NULL,
  asset_category TEXT,
  ib_symbol TEXT NOT NULL,
  pl_total REAL,
  current_qty REAL,
  current_price REAL
);
CREATE TABLE IF NOT EXISTS trades (
  statement_id INTEGER NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
  row_index INTEGER NOT NULL,
  discriminator TEXT,
  asset_category TEXT,
  currency TEXT,
  ib_symbol TEXT NOT NULL,
  traded_at TEXT,
  quantity REAL,
  trade_price REAL,
  close_price REAL,
  proceeds REAL,
  commission REAL,
  basis REAL,
  realized_pl REAL,
  mtm_pl REAL,
  code TEXT
);
CREATE TABLE IF NOT EXISTS forex_closes (
  statement_id INTEGER NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
  currency TEXT NOT NULL,
  close_price REAL NOT NULL
);
"""


class StoreError(Exception):
    """Sqlite file exists but cannot be read as a statement book."""


def db_path() -> Path:
    from apps.analysis_web.config import local_dir

    return local_dir() / "portfolio.sqlite"


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES ('schema_version', '1')"
    )


def replace_statement(stmt: IbStatement, *, path: Path | None = None) -> int:
    """Upsert one statement (account + period) and replace its child rows."""
    db = path or db_path()
    db.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn = _connect(db)
    try:
        _ensure_schema(conn)
        conn.execute(
            """
            DELETE FROM statements
            WHERE account_id = ? AND period_from = ? AND period_to = ?
            """,
            (stmt.account_id, stmt.period_from, stmt.period_to),
        )
        cur = conn.execute(
            """
            INSERT INTO statements (
              account_id, broker, title, period_from, period_to, base_currency,
              source_csv, starting_nav, ending_nav, twr_pct, deposits_total,
              imported_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stmt.account_id,
                stmt.broker,
                stmt.title,
                stmt.period_from,
                stmt.period_to,
                stmt.base_currency,
                stmt.source_csv,
                stmt.starting_nav,
                stmt.ending_nav,
                stmt.twr_pct,
                stmt.deposits_total,
                now,
            ),
        )
        sid = int(cur.lastrowid)
        conn.executemany(
            """
            INSERT INTO nav_assets (
              statement_id, row_index, asset_class, prior_total, current_long,
              current_short, current_total, change_amt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    sid,
                    i,
                    a.asset_class,
                    a.prior_total,
                    a.current_long,
                    a.current_short,
                    a.current_total,
                    a.change,
                )
                for i, a in enumerate(stmt.nav_assets)
            ],
        )
        conn.executemany(
            """
            INSERT INTO nav_components (statement_id, row_index, name, value)
            VALUES (?, ?, ?, ?)
            """,
            [
                (sid, i, c.name, c.value)
                for i, c in enumerate(stmt.nav_components)
            ],
        )
        conn.executemany(
            """
            INSERT INTO cashflows (
              statement_id, row_index, currency, settle_date, description, amount
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (sid, i, c.currency, c.settle_date, c.description, c.amount)
                for i, c in enumerate(stmt.cashflows)
            ],
        )
        conn.executemany(
            """
            INSERT INTO positions (
              statement_id, row_index, ib_symbol, asset_category, currency,
              quantity, multiplier, cost_price, cost_basis, close_price, value,
              unrealized_pl, listing_exch, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    sid,
                    i,
                    p.ib_symbol,
                    p.asset_category,
                    p.currency,
                    p.quantity,
                    p.multiplier,
                    p.cost_price,
                    p.cost_basis,
                    p.close_price,
                    p.value,
                    p.unrealized_pl,
                    p.listing_exch,
                    p.description,
                )
                for i, p in enumerate(stmt.positions)
            ],
        )
        conn.executemany(
            """
            INSERT INTO instruments (
              statement_id, row_index, asset_category, ib_symbol, description,
              listing_exch, security_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    sid,
                    i,
                    inst.asset_category,
                    inst.ib_symbol,
                    inst.description,
                    inst.listing_exch,
                    inst.security_id,
                )
                for i, inst in enumerate(stmt.instruments)
            ],
        )
        conn.executemany(
            """
            INSERT INTO mtm (
              statement_id, row_index, asset_category, ib_symbol, pl_total,
              current_qty, current_price
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    sid,
                    i,
                    m.asset_category,
                    m.ib_symbol,
                    m.pl_total,
                    m.current_qty,
                    m.current_price,
                )
                for i, m in enumerate(stmt.mtm)
            ],
        )
        conn.executemany(
            """
            INSERT INTO trades (
              statement_id, row_index, discriminator, asset_category, currency,
              ib_symbol, traded_at, quantity, trade_price, close_price, proceeds,
              commission, basis, realized_pl, mtm_pl, code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    sid,
                    t.row_index,
                    t.discriminator,
                    t.asset_category,
                    t.currency,
                    t.ib_symbol,
                    t.traded_at,
                    t.quantity,
                    t.trade_price,
                    t.close_price,
                    t.proceeds,
                    t.commission,
                    t.basis,
                    t.realized_pl,
                    t.mtm_pl,
                    t.code,
                )
                for t in stmt.trades
            ],
        )
        conn.executemany(
            """
            INSERT INTO forex_closes (statement_id, currency, close_price)
            VALUES (?, ?, ?)
            """,
            [(sid, cur, rate) for cur, rate in stmt.forex_closes.items()],
        )
        conn.commit()
        return sid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def load(*, path: Path | None = None) -> IbStatement | None:
    """Latest statement. ``None`` only when the sqlite file is missing."""
    db = path or db_path()
    if not db.is_file():
        return None
    try:
        conn = _connect(db)
    except sqlite3.Error as e:
        raise StoreError(f"cannot open IB book: {e}") from e
    try:
        try:
            row = conn.execute(
                """
                SELECT * FROM statements
                ORDER BY period_to DESC, imported_at DESC, id DESC
                LIMIT 1
                """
            ).fetchone()
        except sqlite3.Error as e:
            raise StoreError(f"IB book is unreadable: {e}") from e
        if row is None:
            raise StoreError("IB book has no statement")
        sid = int(row["id"])

        def rows(sql: str) -> list[sqlite3.Row]:
            return list(conn.execute(sql, (sid,)))

        nav_assets = [
            NavAsset(
                asset_class=r["asset_class"],
                prior_total=r["prior_total"],
                current_long=r["current_long"],
                current_short=r["current_short"],
                current_total=r["current_total"],
                change=r["change_amt"],
            )
            for r in rows(
                "SELECT * FROM nav_assets WHERE statement_id = ? ORDER BY row_index"
            )
        ]
        nav_components = [
            NavComponent(name=r["name"], value=r["value"])
            for r in rows(
                "SELECT * FROM nav_components WHERE statement_id = ? ORDER BY row_index"
            )
        ]
        cashflows = [
            Cashflow(
                currency=r["currency"] or "",
                settle_date=r["settle_date"] or "",
                description=r["description"] or "",
                amount=r["amount"],
            )
            for r in rows(
                "SELECT * FROM cashflows WHERE statement_id = ? ORDER BY row_index"
            )
        ]
        positions = [
            Position(
                ib_symbol=r["ib_symbol"],
                asset_category=r["asset_category"] or "",
                currency=r["currency"] or "",
                quantity=r["quantity"],
                multiplier=r["multiplier"],
                cost_price=r["cost_price"],
                cost_basis=r["cost_basis"],
                close_price=r["close_price"],
                value=r["value"],
                unrealized_pl=r["unrealized_pl"],
                listing_exch=r["listing_exch"],
                description=r["description"] or "",
            )
            for r in rows(
                "SELECT * FROM positions WHERE statement_id = ? ORDER BY row_index"
            )
        ]
        instruments = [
            Instrument(
                asset_category=r["asset_category"] or "",
                ib_symbol=r["ib_symbol"],
                description=r["description"] or "",
                listing_exch=r["listing_exch"],
                security_id=r["security_id"],
            )
            for r in rows(
                "SELECT * FROM instruments WHERE statement_id = ? ORDER BY row_index"
            )
        ]
        mtm = [
            MtmRow(
                asset_category=r["asset_category"] or "",
                ib_symbol=r["ib_symbol"],
                pl_total=r["pl_total"],
                current_qty=r["current_qty"],
                current_price=r["current_price"],
            )
            for r in rows(
                "SELECT * FROM mtm WHERE statement_id = ? ORDER BY row_index"
            )
        ]
        trades = [
            Trade(
                row_index=int(r["row_index"]),
                discriminator=r["discriminator"] or "",
                asset_category=r["asset_category"] or "",
                currency=r["currency"] or "",
                ib_symbol=r["ib_symbol"],
                traded_at=r["traded_at"] or "",
                quantity=r["quantity"],
                trade_price=r["trade_price"],
                close_price=r["close_price"],
                proceeds=r["proceeds"],
                commission=r["commission"],
                basis=r["basis"],
                realized_pl=r["realized_pl"],
                mtm_pl=r["mtm_pl"],
                code=r["code"] or "",
            )
            for r in rows(
                "SELECT * FROM trades WHERE statement_id = ? ORDER BY row_index"
            )
        ]
        forex_closes = {
            r["currency"]: float(r["close_price"])
            for r in rows("SELECT * FROM forex_closes WHERE statement_id = ?")
        }
        return IbStatement(
            account_id=row["account_id"],
            period_from=row["period_from"],
            period_to=row["period_to"],
            base_currency=row["base_currency"],
            broker=row["broker"] or "",
            title=row["title"] or "",
            source_csv=row["source_csv"] or "",
            starting_nav=row["starting_nav"],
            ending_nav=row["ending_nav"],
            twr_pct=row["twr_pct"],
            deposits_total=row["deposits_total"],
            nav_assets=nav_assets,
            nav_components=nav_components,
            cashflows=cashflows,
            positions=positions,
            instruments=instruments,
            mtm=mtm,
            trades=trades,
            forex_closes=forex_closes,
        )
    finally:
        conn.close()

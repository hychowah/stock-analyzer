"""App-local sqlite: IB trade ledger + latest statement snapshot.

Callers use ``ingest_statement`` / ``load``. ``load`` returns ``IbBook``.
Table names stay inside this module. Catalog tickers are not stored.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from apps.analysis_web.services.ib_statement import (
    Cashflow,
    IbBook,
    IbStatement,
    IngestResult,
    Instrument,
    MtmRow,
    NavAsset,
    NavComponent,
    Position,
    Trade,
    trade_fingerprint,
)


SCHEMA_VERSION = "2"

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
  id INTEGER PRIMARY KEY,
  account_id TEXT NOT NULL,
  fingerprint TEXT NOT NULL,
  first_statement_id INTEGER REFERENCES statements(id) ON DELETE SET NULL,
  source_csv TEXT,
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
  code TEXT,
  UNIQUE(account_id, fingerprint)
);
CREATE TABLE IF NOT EXISTS forex_closes (
  statement_id INTEGER NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
  currency TEXT NOT NULL,
  close_price REAL NOT NULL
);
"""

_SNAPSHOT_TABLES = (
    "nav_assets",
    "nav_components",
    "cashflows",
    "positions",
    "instruments",
    "mtm",
    "forex_closes",
)

_TRADES_V2 = """
CREATE TABLE trades (
  id INTEGER PRIMARY KEY,
  account_id TEXT NOT NULL,
  fingerprint TEXT NOT NULL,
  first_statement_id INTEGER REFERENCES statements(id) ON DELETE SET NULL,
  source_csv TEXT,
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
  code TEXT,
  UNIQUE(account_id, fingerprint)
);
"""


class StoreError(Exception):
    """Sqlite file exists but cannot be read as an IB book."""


def db_path() -> Path:
    from apps.analysis_web.config import local_dir

    return local_dir() / "portfolio.sqlite"


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _table_columns(conn: sqlite3.Connection, name: str) -> set[str]:
    return {str(r[1]) for r in conn.execute(f"PRAGMA table_info({name})")}


def _needs_v1_migrate(conn: sqlite3.Connection) -> bool:
    names = {
        str(r[0])
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    if "trades" not in names:
        return False
    return "fingerprint" not in _table_columns(conn, "trades")


def _trade_from_row(r: sqlite3.Row) -> Trade:
    return Trade(
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


def _migrate_v1_to_v2(conn: sqlite3.Connection) -> None:
    conn.execute("ALTER TABLE trades RENAME TO trades_v1")
    conn.executescript(_TRADES_V2)
    old = list(
        conn.execute(
            """
            SELECT t.*, s.account_id AS stmt_account, s.source_csv AS stmt_csv
            FROM trades_v1 t
            JOIN statements s ON s.id = t.statement_id
            ORDER BY t.statement_id, t.row_index
            """
        )
    )
    for r in old:
        trade = _trade_from_row(r)
        account_id = str(r["stmt_account"] or "")
        fp = trade_fingerprint(account_id, trade)
        conn.execute(
            """
            INSERT OR IGNORE INTO trades (
              account_id, fingerprint, first_statement_id, source_csv, row_index,
              discriminator, asset_category, currency, ib_symbol, traded_at,
              quantity, trade_price, close_price, proceeds, commission, basis,
              realized_pl, mtm_pl, code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account_id,
                fp,
                r["statement_id"],
                r["stmt_csv"],
                trade.row_index,
                trade.discriminator,
                trade.asset_category,
                trade.currency,
                trade.ib_symbol,
                trade.traded_at,
                trade.quantity,
                trade.trade_price,
                trade.close_price,
                trade.proceeds,
                trade.commission,
                trade.basis,
                trade.realized_pl,
                trade.mtm_pl,
                trade.code,
            ),
        )
    conn.execute("DROP TABLE trades_v1")


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    if _needs_v1_migrate(conn):
        _migrate_v1_to_v2(conn)
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES ('schema_version', ?)",
        (SCHEMA_VERSION,),
    )


def _num_close(a: float | None, b: float | None, *, eps: float = 1e-6) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    fa, fb = float(a), float(b)
    return abs(fa - fb) <= max(eps, 1e-6 * max(abs(fa), abs(fb), 1.0))


def _require_single_account(conn: sqlite3.Connection, account_id: str) -> None:
    rows = list(conn.execute("SELECT DISTINCT account_id FROM statements"))
    ids = {str(r["account_id"]) for r in rows}
    if ids and account_id not in ids:
        have = next(iter(sorted(ids)))
        raise StoreError(f"book is for {have}; refusing {account_id}")


def _upsert_statement(
    conn: sqlite3.Connection, stmt: IbStatement, now: str
) -> int:
    existing = conn.execute(
        """
        SELECT id FROM statements
        WHERE account_id = ? AND period_from = ? AND period_to = ?
        """,
        (stmt.account_id, stmt.period_from, stmt.period_to),
    ).fetchone()
    values = (
        stmt.broker,
        stmt.title,
        stmt.base_currency,
        stmt.source_csv,
        stmt.starting_nav,
        stmt.ending_nav,
        stmt.twr_pct,
        stmt.deposits_total,
        now,
    )
    if existing is not None:
        sid = int(existing["id"])
        conn.execute(
            """
            UPDATE statements SET
              broker=?, title=?, base_currency=?, source_csv=?,
              starting_nav=?, ending_nav=?, twr_pct=?, deposits_total=?,
              imported_at=?
            WHERE id=?
            """,
            (*values, sid),
        )
        for table in _SNAPSHOT_TABLES:
            conn.execute(f"DELETE FROM {table} WHERE statement_id = ?", (sid,))
        return sid
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
    return int(cur.lastrowid)


def _insert_snapshot_children(
    conn: sqlite3.Connection, sid: int, stmt: IbStatement
) -> None:
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
        [(sid, i, c.name, c.value) for i, c in enumerate(stmt.nav_components)],
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
        INSERT INTO forex_closes (statement_id, currency, close_price)
        VALUES (?, ?, ?)
        """,
        [(sid, cur, rate) for cur, rate in stmt.forex_closes.items()],
    )


def _merge_trades(
    conn: sqlite3.Connection, sid: int, stmt: IbStatement
) -> tuple[int, int, int]:
    inserted = skipped = conflicts = 0
    for t in stmt.trades:
        fp = trade_fingerprint(stmt.account_id, t)
        existing = conn.execute(
            """
            SELECT proceeds, commission FROM trades
            WHERE account_id = ? AND fingerprint = ?
            """,
            (stmt.account_id, fp),
        ).fetchone()
        if existing is not None:
            skipped += 1
            if not _num_close(existing["proceeds"], t.proceeds) or not _num_close(
                existing["commission"], t.commission
            ):
                conflicts += 1
            continue
        conn.execute(
            """
            INSERT INTO trades (
              account_id, fingerprint, first_statement_id, source_csv, row_index,
              discriminator, asset_category, currency, ib_symbol, traded_at,
              quantity, trade_price, close_price, proceeds, commission, basis,
              realized_pl, mtm_pl, code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stmt.account_id,
                fp,
                sid,
                stmt.source_csv,
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
            ),
        )
        inserted += 1
    return inserted, skipped, conflicts


def ingest_statement(stmt: IbStatement, *, path: Path | None = None) -> IngestResult:
    """Merge one CSV report: refresh that period's snapshot, append new fills."""
    db = path or db_path()
    db.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn = _connect(db)
    try:
        _ensure_schema(conn)
        _require_single_account(conn, stmt.account_id)
        sid = _upsert_statement(conn, stmt, now)
        _insert_snapshot_children(conn, sid, stmt)
        inserted, skipped, conflicts = _merge_trades(conn, sid, stmt)
        conn.commit()
        return IngestResult(
            statement_id=sid,
            account_id=stmt.account_id,
            period_from=stmt.period_from,
            period_to=stmt.period_to,
            inserted=inserted,
            skipped=skipped,
            conflicts=conflicts,
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _snapshot_from_row(conn: sqlite3.Connection, row: sqlite3.Row) -> IbStatement:
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
        for r in rows("SELECT * FROM mtm WHERE statement_id = ? ORDER BY row_index")
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
        trades=[],
        forex_closes=forex_closes,
    )


def _load_ledger(conn: sqlite3.Connection, account_id: str) -> list[Trade]:
    return [
        _trade_from_row(r)
        for r in conn.execute(
            """
            SELECT * FROM trades
            WHERE account_id = ?
            ORDER BY traded_at, row_index, id
            """,
            (account_id,),
        )
    ]


def load(*, path: Path | None = None) -> IbBook | None:
    """Latest snapshot plus account ledger. ``None`` only when the sqlite file is missing."""
    db = path or db_path()
    if not db.is_file():
        return None
    try:
        conn = _connect(db)
    except sqlite3.Error as e:
        raise StoreError(f"cannot open IB book: {e}") from e
    try:
        try:
            if _needs_v1_migrate(conn):
                _ensure_schema(conn)
                conn.commit()
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
        snapshot = _snapshot_from_row(conn, row)
        trades = _load_ledger(conn, snapshot.account_id)
        return IbBook(snapshot=snapshot, trades=trades)
    finally:
        conn.close()

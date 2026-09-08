"""App-local sqlite for alternative-history overlays.

Never writes the IB book. Computed NAV is not stored; replay on read.
Persist the whole History (frozen seed + fills) via ``save``.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from apps.analysis_web.services.alt_history import (
    History,
    NotFoundError,
    PricedFill,
    ReplayError,
    history_from_ib,
    trial_replay,
)
from apps.analysis_web.services.book_state import BookState
from apps.analysis_web.services.ib_statement import IbBook


SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS histories (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  notes TEXT NOT NULL DEFAULT '',
  fork_date TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  seed_json TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS decisions (
  id INTEGER PRIMARY KEY,
  history_id INTEGER NOT NULL REFERENCES histories(id) ON DELETE CASCADE,
  as_of TEXT NOT NULL,
  side TEXT NOT NULL,
  listing TEXT NOT NULL,
  quantity REAL NOT NULL,
  price_mode TEXT NOT NULL,
  fill_price REAL NOT NULL,
  currency TEXT NOT NULL,
  catalog_ticker TEXT,
  ib_symbol TEXT,
  notes TEXT NOT NULL DEFAULT '',
  stmt_fx REAL,
  created_at TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'hyp',
  cash_effect REAL
);
"""


def db_path() -> Path:
    from apps.analysis_web.config import local_dir

    return local_dir() / "alt_histories.sqlite"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(r[1]) for r in conn.execute(f"PRAGMA table_info({table})")}


def _ensure(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    cols = _columns(conn, "decisions")
    if "source" not in cols:
        conn.execute(
            "ALTER TABLE decisions ADD COLUMN source TEXT NOT NULL DEFAULT 'hyp'"
        )
    if "cash_effect" not in _columns(conn, "decisions"):
        conn.execute("ALTER TABLE decisions ADD COLUMN cash_effect REAL")
    hist_cols = _columns(conn, "histories")
    if "seed_json" not in hist_cols:
        conn.execute(
            "ALTER TABLE histories ADD COLUMN seed_json TEXT NOT NULL DEFAULT ''"
        )
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES ('schema_version', '3')"
    )


def _fill_from_row(r: sqlite3.Row) -> PricedFill:
    keys = r.keys()
    source = str(r["source"] or "hyp") if "source" in keys else "hyp"
    return PricedFill(
        id=int(r["id"]),
        as_of=str(r["as_of"]),
        side=str(r["side"]),
        listing=str(r["listing"]),
        quantity=float(r["quantity"]),
        fill_price=float(r["fill_price"]),
        currency=str(r["currency"] or ""),
        stmt_fx=r["stmt_fx"],
        catalog_ticker=r["catalog_ticker"],
        ib_symbol=r["ib_symbol"],
        price_mode=str(r["price_mode"] or "close"),
        notes=str(r["notes"] or ""),
        source=source,
        cash_effect=r["cash_effect"] if "cash_effect" in keys else None,
    )


def _seed_from_row(r: sqlite3.Row) -> BookState:
    keys = r.keys()
    raw = r["seed_json"] if "seed_json" in keys else ""
    if not raw:
        raise ReplayError(
            "missing_seed",
            "This history has no frozen seed. Copy trades again.",
        )
    try:
        payload = json.loads(str(raw))
    except json.JSONDecodeError as e:
        raise ReplayError("missing_seed", "Frozen seed is unreadable.") from e
    try:
        return BookState.from_json(payload)
    except ValueError as e:
        raise ReplayError("missing_seed", str(e) or "Frozen seed is unreadable.") from e


def _to_history(r: sqlite3.Row, fills: list[PricedFill]) -> History:
    return History(
        id=int(r["id"]),
        name=str(r["name"]),
        notes=str(r["notes"] or ""),
        fork_date=str(r["fork_date"]),
        fills=tuple(fills),
        seed=_seed_from_row(r),
    )


def _insert_fill(
    conn: sqlite3.Connection,
    history_id: int,
    fill: PricedFill,
    *,
    now: str,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO decisions (
          history_id, as_of, side, listing, quantity, price_mode,
          fill_price, currency, catalog_ticker, ib_symbol, notes, stmt_fx,
          created_at, source, cash_effect
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(history_id),
            fill.as_of,
            fill.side,
            fill.listing,
            fill.quantity,
            fill.price_mode,
            fill.fill_price,
            fill.currency,
            fill.catalog_ticker,
            fill.ib_symbol,
            fill.notes or "",
            fill.stmt_fx,
            now,
            fill.source or "hyp",
            fill.cash_effect,
        ),
    )
    return int(cur.lastrowid)


def save(hist: History, *, path: Path | None = None) -> History:
    """Persist the whole aggregate after a trial replay. Seed is frozen."""
    trial_replay(hist)
    label = (hist.name or "").strip() or "Untitled"
    day = (hist.fork_date or "").strip()[:10]
    if len(day) < 10 or day[4] != "-" or day[7] != "-":
        raise ReplayError("bad_date", "Fork date must be YYYY-MM-DD")
    now = _utc_now()
    p = path or db_path()
    seed_json = json.dumps(hist.seed.as_json())
    conn = _connect(p)
    try:
        _ensure(conn)
        hid = hist.id
        if hid is None:
            cur = conn.execute(
                """
                INSERT INTO histories(
                  name, notes, fork_date, created_at, updated_at, seed_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (label, hist.notes or "", day, now, now, seed_json),
            )
            hid = int(cur.lastrowid)
        else:
            r = conn.execute(
                "SELECT id FROM histories WHERE id = ?", (int(hid),)
            ).fetchone()
            if r is None:
                raise NotFoundError("History not found")
            conn.execute(
                """
                UPDATE histories
                SET name = ?, notes = ?, fork_date = ?, updated_at = ?,
                    seed_json = ?
                WHERE id = ?
                """,
                (label, hist.notes or "", day, now, seed_json, int(hid)),
            )
            conn.execute(
                "DELETE FROM decisions WHERE history_id = ?", (int(hid),)
            )
        for fill in hist.fills:
            _insert_fill(conn, int(hid), fill, now=now)
        conn.commit()
        return get_history(int(hid), path=p)
    finally:
        conn.close()


def create_from_ib(
    ib_book: IbBook,
    *,
    name: str,
    notes: str = "",
    path: Path | None = None,
) -> History:
    return save(history_from_ib(ib_book, name=name, notes=notes), path=path)


def create_history(
    *,
    name: str,
    fork_date: str,
    seed: BookState,
    notes: str = "",
    fills: tuple[PricedFill, ...] | list[PricedFill] = (),
    path: Path | None = None,
) -> History:
    """Low-level insert. Prefer ``create_from_ib`` for the product path."""
    return save(
        History(
            name=(name or "").strip() or "Untitled",
            fork_date=fork_date,
            fills=tuple(fills),
            seed=seed,
            notes=notes or "",
        ),
        path=path,
    )


def list_histories(*, path: Path | None = None) -> list[History]:
    p = path or db_path()
    if not p.is_file():
        return []
    conn = _connect(p)
    try:
        _ensure(conn)
        rows = list(
            conn.execute(
                "SELECT * FROM histories ORDER BY updated_at DESC, id DESC"
            )
        )
        out: list[History] = []
        for r in rows:
            fills = [
                _fill_from_row(d)
                for d in conn.execute(
                    """
                    SELECT * FROM decisions
                    WHERE history_id = ?
                    ORDER BY as_of, id
                    """,
                    (int(r["id"]),),
                )
            ]
            out.append(_to_history(r, fills))
        return out
    finally:
        conn.close()


def get_history(history_id: int, *, path: Path | None = None) -> History:
    p = path or db_path()
    conn = _connect(p)
    try:
        _ensure(conn)
        r = conn.execute(
            "SELECT * FROM histories WHERE id = ?", (int(history_id),)
        ).fetchone()
        if r is None:
            raise NotFoundError("History not found")
        fills = [
            _fill_from_row(d)
            for d in conn.execute(
                """
                SELECT * FROM decisions
                WHERE history_id = ?
                ORDER BY as_of, id
                """,
                (int(history_id),),
            )
        ]
        return _to_history(r, fills)
    finally:
        conn.close()


def update_history(
    history_id: int,
    *,
    name: str | None = None,
    notes: str | None = None,
    path: Path | None = None,
) -> History:
    p = path or db_path()
    conn = _connect(p)
    try:
        _ensure(conn)
        r = conn.execute(
            "SELECT * FROM histories WHERE id = ?", (int(history_id),)
        ).fetchone()
        if r is None:
            raise NotFoundError("History not found")
        new_name = (name if name is not None else r["name"]).strip() or r["name"]
        new_notes = notes if notes is not None else r["notes"]
        conn.execute(
            """
            UPDATE histories SET name = ?, notes = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_name, new_notes or "", _utc_now(), int(history_id)),
        )
        conn.commit()
        return get_history(history_id, path=p)
    finally:
        conn.close()


def copy_history(history_id: int, *, path: Path | None = None) -> History:
    src = get_history(history_id, path=path)
    return save(
        History(
            name=f"{src.name} copy",
            fork_date=src.fork_date,
            fills=src.fills,
            seed=src.seed,
            notes=src.notes,
        ),
        path=path,
    )


def delete_history(history_id: int, *, path: Path | None = None) -> None:
    p = path or db_path()
    conn = _connect(p)
    try:
        _ensure(conn)
        cur = conn.execute(
            "DELETE FROM histories WHERE id = ?", (int(history_id),)
        )
        if cur.rowcount < 1:
            raise NotFoundError("History not found")
        conn.commit()
    finally:
        conn.close()

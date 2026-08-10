"""SQLite comparison warehouse for finished research runs.

Disk sessions under archive/research/ remain the system of record.
This module manages archive/catalog/research_compare.sqlite as a rebuildable projection.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.kd_research.paths import PROJECT_ROOT, catalog_root, ensure_archive_tree

SCHEMA_VERSION = 2

DB_FILENAME = "research_compare.sqlite"

MIGRATIONS: dict[int, str] = {
    1: """
CREATE TABLE IF NOT EXISTS schema_migrations (
  version INTEGER PRIMARY KEY,
  applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS experiments (
  experiment_id TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  hypothesis TEXT,
  created_at TEXT,
  notes TEXT,
  config_json TEXT
);

CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  ticker TEXT NOT NULL,
  session_date TEXT NOT NULL,
  session_key TEXT NOT NULL,
  path TEXT NOT NULL,
  experiment_id TEXT,
  replicate INTEGER,
  exported_at TEXT NOT NULL,
  audit_verdict TEXT,
  data_quality TEXT,
  status TEXT,

  -- provenance (nullable until Phase B fills new runs)
  harness_spec TEXT,
  harness_git_sha TEXT,
  harness_dirty INTEGER,
  agents_md_sha256 TEXT,
  prompts_sha256 TEXT,
  orchestrator_model TEXT,
  default_subagent_model TEXT,
  model_map_json TEXT,
  temperature REAL,
  seed TEXT,
  research_depth TEXT,
  notes TEXT,

  -- market / classification
  asof_price REAL,
  currency TEXT,
  primary_sector TEXT,
  region TEXT,
  intensity TEXT,
  benchmark TEXT,
  peers_json TEXT,

  -- valuation summary
  fv_bear REAL,
  fv_base REAL,
  fv_bull REAL,
  fv_weighted REAL,
  p_bear REAL,
  p_base REAL,
  p_bull REAL,
  margin_of_safety_pct REAL,
  model_name TEXT,
  priced_for_perfection INTEGER,
  verdict_line TEXT,

  -- technical summary
  tech_signal TEXT,
  tech_regime TEXT,
  tech_summary_json TEXT,

  -- forward-compat + pointers
  extras_json TEXT,
  snapshot_path TEXT,
  manifest_path TEXT,

  FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
);

CREATE INDEX IF NOT EXISTS idx_runs_ticker_date ON runs(ticker, session_date);
CREATE INDEX IF NOT EXISTS idx_runs_experiment ON runs(experiment_id);
CREATE INDEX IF NOT EXISTS idx_runs_harness_sha ON runs(harness_git_sha);
CREATE INDEX IF NOT EXISTS idx_runs_model ON runs(orchestrator_model);
CREATE INDEX IF NOT EXISTS idx_runs_audit ON runs(audit_verdict);
CREATE INDEX IF NOT EXISTS idx_runs_sector_region ON runs(primary_sector, region);

CREATE TABLE IF NOT EXISTS run_metrics (
  run_id TEXT NOT NULL,
  metric_key TEXT NOT NULL,
  metric_value REAL,
  metric_text TEXT,
  PRIMARY KEY (run_id, metric_key),
  FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS outcomes (
  run_id TEXT NOT NULL,
  horizon TEXT NOT NULL,
  mark_date TEXT,
  realized_price REAL,
  total_return_pct REAL,
  benchmark_return_pct REAL,
  excess_return_pct REAL,
  direction_hit INTEGER,
  extras_json TEXT,
  PRIMARY KEY (run_id, horizon),
  FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);
""",
    2: """
ALTER TABLE runs ADD COLUMN harness_version TEXT;
CREATE INDEX IF NOT EXISTS idx_runs_harness_version ON runs(harness_version);
""",
}


def db_path(output_dir: Path | str | None = None) -> Path:
    ensure_archive_tree(output_dir)
    return catalog_root(output_dir) / DB_FILENAME


def connect(output_dir: Path | str | None = None, *, readonly: bool = False) -> sqlite3.Connection:
    """Open compare DB. Writers use WAL + busy_timeout; readers use immutable URI."""
    if readonly:
        # Do not mkdir via db_path/ensure_archive_tree on read path
        path = catalog_root(output_dir) / DB_FILENAME
        if not path.is_file():
            raise FileNotFoundError(f"Compare DB not found: {path}")
        uri = f"file:{path.resolve().as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    else:
        path = db_path(output_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path))
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=10000")
        except sqlite3.Error:
            pass
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _applied_versions(conn: sqlite3.Connection) -> set[int]:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
    )
    if cur.fetchone() is None:
        return set()
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return {int(r[0]) for r in rows}


def migrate(conn: sqlite3.Connection) -> int:
    """Apply pending migrations. Returns highest schema version after migrate."""
    applied = _applied_versions(conn)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for version in sorted(MIGRATIONS):
        if version in applied:
            continue
        conn.executescript(MIGRATIONS[version])
        # schema_migrations table is created in migration 1; insert version row
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
            (version, now),
        )
        conn.commit()
    applied = _applied_versions(conn)
    return max(applied) if applied else 0


def open_db(output_dir: Path | str | None = None, *, rebuild: bool = False) -> sqlite3.Connection:
    path = db_path(output_dir)
    if rebuild and path.is_file():
        path.unlink()
    conn = connect(output_dir, readonly=False)
    migrate(conn)
    return conn


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _json_dumps(obj: Any) -> str | None:
    if obj is None:
        return None
    return json.dumps(obj, ensure_ascii=False, default=str)


def _bool_int(v: Any) -> int | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, (int, float)):
        return 1 if v else 0
    if isinstance(v, str):
        low = v.strip().lower()
        if low in ("true", "yes", "1"):
            return 1
        if low in ("false", "no", "0"):
            return 0
    return None


RUN_COLUMNS = [
    "run_id",
    "ticker",
    "session_date",
    "session_key",
    "path",
    "experiment_id",
    "replicate",
    "exported_at",
    "audit_verdict",
    "data_quality",
    "status",
    "harness_version",
    "harness_spec",
    "harness_git_sha",
    "harness_dirty",
    "agents_md_sha256",
    "prompts_sha256",
    "orchestrator_model",
    "default_subagent_model",
    "model_map_json",
    "temperature",
    "seed",
    "research_depth",
    "notes",
    "asof_price",
    "currency",
    "primary_sector",
    "region",
    "intensity",
    "benchmark",
    "peers_json",
    "fv_bear",
    "fv_base",
    "fv_bull",
    "fv_weighted",
    "p_bear",
    "p_base",
    "p_bull",
    "margin_of_safety_pct",
    "model_name",
    "priced_for_perfection",
    "verdict_line",
    "tech_signal",
    "tech_regime",
    "tech_summary_json",
    "extras_json",
    "snapshot_path",
    "manifest_path",
]


def upsert_run(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    """Insert or replace a runs row. ``row`` keys should match RUN_COLUMNS."""
    data = {k: row.get(k) for k in RUN_COLUMNS}
    if not data.get("exported_at"):
        data["exported_at"] = utc_now()
    placeholders = ", ".join("?" for _ in RUN_COLUMNS)
    cols = ", ".join(RUN_COLUMNS)
    conn.execute(
        f"INSERT OR REPLACE INTO runs ({cols}) VALUES ({placeholders})",
        [data[k] for k in RUN_COLUMNS],
    )


def replace_run_metrics(conn: sqlite3.Connection, run_id: str, metrics: dict[str, Any]) -> None:
    conn.execute("DELETE FROM run_metrics WHERE run_id = ?", (run_id,))
    for key, val in metrics.items():
        if val is None:
            continue
        if isinstance(val, str):
            conn.execute(
                "INSERT INTO run_metrics(run_id, metric_key, metric_value, metric_text) VALUES (?,?,?,?)",
                (run_id, key, None, val),
            )
        else:
            try:
                num = float(val)
            except (TypeError, ValueError):
                conn.execute(
                    "INSERT INTO run_metrics(run_id, metric_key, metric_value, metric_text) VALUES (?,?,?,?)",
                    (run_id, key, None, str(val)),
                )
            else:
                conn.execute(
                    "INSERT INTO run_metrics(run_id, metric_key, metric_value, metric_text) VALUES (?,?,?,?)",
                    (run_id, key, num, None),
                )


def ensure_experiment(
    conn: sqlite3.Connection,
    experiment_id: str,
    *,
    label: str | None = None,
    hypothesis: str | None = None,
    notes: str | None = None,
    config: Any = None,
) -> None:
    if not experiment_id:
        return
    existing = conn.execute(
        "SELECT experiment_id FROM experiments WHERE experiment_id = ?", (experiment_id,)
    ).fetchone()
    if existing:
        return
    conn.execute(
        """
        INSERT INTO experiments(experiment_id, label, hypothesis, created_at, notes, config_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            experiment_id,
            label or experiment_id,
            hypothesis,
            utc_now(),
            notes,
            _json_dumps(config),
        ),
    )


def compute_run_metrics(row: dict[str, Any]) -> dict[str, Any]:
    """Derived metrics for UI / analysis."""
    metrics: dict[str, Any] = {}
    mos = row.get("margin_of_safety_pct")
    if isinstance(mos, (int, float)):
        metrics["mos_vs_base"] = float(mos)

    base = row.get("fv_base")
    bear = row.get("fv_bear")
    bull = row.get("fv_bull")
    if all(isinstance(x, (int, float)) and x for x in (base, bear, bull)):
        metrics["fv_range_pct"] = (float(bull) - float(bear)) / float(base) * 100.0

    for k_src, k_dst in (("p_bear", "bear_mass"), ("p_base", "base_mass"), ("p_bull", "bull_mass")):
        v = row.get(k_src)
        if isinstance(v, (int, float)):
            metrics[k_dst] = float(v)

    asof = row.get("asof_price")
    if isinstance(asof, (int, float)) and isinstance(base, (int, float)) and base:
        metrics["price_to_fv_base"] = float(asof) / float(base)
    weighted = row.get("fv_weighted")
    if isinstance(asof, (int, float)) and isinstance(weighted, (int, float)) and weighted:
        metrics["price_to_fv_weighted"] = float(asof) / float(weighted)

    audit = (row.get("audit_verdict") or "").upper()
    metrics["audit_pass"] = 1.0 if audit == "PASS" else 0.0

    # Cheap heuristic posture for chart coloring
    if isinstance(mos, (int, float)):
        if mos >= 15:
            metrics["posture"] = "cheap"
        elif mos <= -15:
            metrics["posture"] = "expensive"
        else:
            metrics["posture"] = "fair"

    return metrics


def row_from_export_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Map exporter payload into runs column dict (types coerced)."""
    peers = payload.get("peers")
    if isinstance(peers, list):
        peers_json = _json_dumps(peers)
    elif isinstance(peers, str):
        peers_json = peers
    else:
        peers_json = _json_dumps(peers) if peers is not None else None

    model_map = payload.get("model_map")
    tech_summary = payload.get("tech_summary")
    extras = payload.get("extras")

    return {
        "run_id": payload["run_id"],
        "ticker": payload["ticker"],
        "session_date": payload["session_date"],
        "session_key": payload.get("session_key") or payload["session_date"],
        "path": payload["path"],
        "experiment_id": payload.get("experiment_id"),
        "replicate": payload.get("replicate"),
        "exported_at": payload.get("exported_at") or utc_now(),
        "audit_verdict": payload.get("audit_verdict"),
        "data_quality": payload.get("data_quality"),
        "status": payload.get("status"),
        "harness_version": payload.get("harness_version"),
        "harness_spec": payload.get("harness_spec"),
        "harness_git_sha": payload.get("harness_git_sha"),
        "harness_dirty": _bool_int(payload.get("harness_dirty")),
        "agents_md_sha256": payload.get("agents_md_sha256"),
        "prompts_sha256": payload.get("prompts_sha256"),
        "orchestrator_model": payload.get("orchestrator_model"),
        "default_subagent_model": payload.get("default_subagent_model"),
        "model_map_json": _json_dumps(model_map) if model_map is not None else payload.get("model_map_json"),
        "temperature": payload.get("temperature"),
        "seed": str(payload["seed"]) if payload.get("seed") is not None else None,
        "research_depth": payload.get("research_depth"),
        "notes": payload.get("notes"),
        "asof_price": payload.get("asof_price"),
        "currency": payload.get("currency"),
        "primary_sector": payload.get("primary_sector"),
        "region": payload.get("region"),
        "intensity": payload.get("intensity"),
        "benchmark": payload.get("benchmark"),
        "peers_json": peers_json,
        "fv_bear": payload.get("fv_bear"),
        "fv_base": payload.get("fv_base"),
        "fv_bull": payload.get("fv_bull"),
        "fv_weighted": payload.get("fv_weighted"),
        "p_bear": payload.get("p_bear"),
        "p_base": payload.get("p_base"),
        "p_bull": payload.get("p_bull"),
        "margin_of_safety_pct": payload.get("margin_of_safety_pct"),
        "model_name": payload.get("model_name"),
        "priced_for_perfection": _bool_int(payload.get("priced_for_perfection")),
        "verdict_line": payload.get("verdict_line"),
        "tech_signal": payload.get("tech_signal"),
        "tech_regime": payload.get("tech_regime"),
        "tech_summary_json": _json_dumps(tech_summary)
        if tech_summary is not None
        else payload.get("tech_summary_json"),
        "extras_json": _json_dumps(extras) if extras is not None else payload.get("extras_json"),
        "snapshot_path": payload.get("snapshot_path"),
        "manifest_path": payload.get("manifest_path"),
    }


def count_runs(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) FROM runs").fetchone()
    return int(row[0]) if row else 0

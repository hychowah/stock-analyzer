"""CatalogApi — thin readonly facade over research_compare.sqlite + session files."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

# Project root: packages/catalog_api/client.py -> parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[2]

RUN_ID_RE = re.compile(
    r"^research:(?P<ticker>[^:]+):(?P<session_key>.+)$", re.IGNORECASE
)

# Safe deep-link prefixes (v1)
DEFAULT_ALLOW_PREFIXES = (
    "reports/",
    "meta/",
    "charts/",
    "registry/",
    "data/valuation_model.json",
    "data/price_snapshot.json",
)

DEFAULT_DENY_PREFIXES = (
    "data/raw_sec/",
    "data/transcripts/",
)

DEFAULT_MAX_BYTES = 2_000_000


class RunNotFound(KeyError):
    pass


class ArtifactDenied(PermissionError):
    pass


class DbMissing(FileNotFoundError):
    pass


def default_archive_root() -> Path:
    return PROJECT_ROOT / "archive"


def parse_run_id(run_id: str) -> tuple[str, str]:
    m = RUN_ID_RE.match(run_id.strip())
    if not m:
        raise ValueError(f"invalid run_id: {run_id!r}")
    return m.group("ticker").upper(), m.group("session_key")


# Allowlisted ORDER BY identifiers (never interpolate untrusted text).
RUN_SORT_COLUMNS: frozenset[str] = frozenset(
    {
        "ticker",
        "session_key",
        "session_date",
        "primary_sector",
        "region",
        "asof_price",
        "fv_base",
        "margin_of_safety_pct",
        "audit_verdict",
        "tech_signal",
        "harness_version",
    }
)

_DEFAULT_ORDER_SQL = "ORDER BY ticker, session_date DESC, session_key DESC"
_TIEBREAK = (("ticker", "ASC"), ("session_date", "DESC"), ("session_key", "DESC"))

_RUN_COLUMNS_V1 = """
            run_id, ticker, session_date, session_key, path,
            experiment_id, audit_verdict, data_quality, status,
            asof_price, currency, primary_sector, region, intensity,
            fv_bear, fv_base, fv_bull, fv_weighted,
            p_bear, p_base, p_bull, margin_of_safety_pct,
            model_name, tech_signal, tech_regime,
            exported_at, harness_git_sha, orchestrator_model
"""

_RUN_COLUMNS_V2 = """
            run_id, ticker, session_date, session_key, path,
            experiment_id, audit_verdict, data_quality, status,
            asof_price, currency, primary_sector, region, intensity,
            fv_bear, fv_base, fv_bull, fv_weighted,
            p_bear, p_base, p_bull, margin_of_safety_pct,
            model_name, tech_signal, tech_regime,
            exported_at, harness_version, harness_git_sha, orchestrator_model
"""


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Distinct-value columns for filter dropdowns (identifiers only; never user text).
_FACET_COLUMNS: tuple[tuple[str, str], ...] = (
    ("sector", "primary_sector"),
    ("region", "region"),
    ("tech_signal", "tech_signal"),
    ("harness_version", "harness_version"),
)


def _blank(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _semver_sort_key(value: str) -> tuple:
    """Tuple key so 2.17.0 sorts after 2.7.0 (lexicographic sqlite ORDER BY does not)."""
    parts: list[tuple[int, int | str]] = []
    for token in value.split("."):
        try:
            parts.append((0, int(token)))
        except ValueError:
            parts.append((1, token))
    return tuple(parts)


def _sql_semver_components(column: str) -> tuple[str, str, str]:
    """SQLite expressions for major, minor, patch. ``column`` must be allowlisted."""
    major = f"CAST({column} AS INTEGER)"
    after_major = f"substr({column}, instr({column} || '.', '.') + 1)"
    minor = f"CAST({after_major} AS INTEGER)"
    after_minor = f"substr({after_major}, instr({after_major} || '.', '.') + 1)"
    patch = f"CAST({after_minor} AS INTEGER)"
    return major, minor, patch


def _missing_optional_column(exc: BaseException, column: str) -> bool:
    return column.lower() in str(exc).lower()


def escape_like_prefix(prefix: str) -> str:
    """Uppercase prefix for LIKE, with %, _, and \\ as literals, plus trailing %."""
    out = prefix.upper().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return out + "%"


def _parse_float(name: str, value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"invalid {name}: {value!r}")
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError as e:
        raise ValueError(f"invalid {name}: {value!r}") from e


def _parse_date(name: str, value: Any) -> str | None:
    text = _blank(None if value is None else str(value))
    if text is None:
        return None
    if not _DATE_RE.match(text):
        raise ValueError(f"invalid {name}: {text!r} (want YYYY-MM-DD)")
    return text


def _append_numeric_range(
    clauses: list[str],
    params: list[Any],
    column: str,
    lo_name: str,
    hi_name: str,
    lo: Any,
    hi: Any,
) -> None:
    lo_v = _parse_float(lo_name, lo)
    hi_v = _parse_float(hi_name, hi)
    if lo_v is not None and hi_v is not None and lo_v > hi_v:
        raise ValueError(f"{lo_name} must be <= {hi_name}")
    if lo_v is not None:
        clauses.append(f"{column} >= ?")
        params.append(lo_v)
    if hi_v is not None:
        clauses.append(f"{column} <= ?")
        params.append(hi_v)


def _runs_filter_sql(
    *,
    ticker: str | None = None,
    ticker_prefix: str | None = None,
    sector: str | None = None,
    region: str | None = None,
    experiment_id: str | None = None,
    audit_verdict: str | None = None,
    tech_signal: str | None = None,
    harness_version: str | None = None,
    session_date_from: str | None = None,
    session_date_to: str | None = None,
    mos_min: Any = None,
    mos_max: Any = None,
    price_min: Any = None,
    price_max: Any = None,
    fv_base_min: Any = None,
    fv_base_max: Any = None,
    comparable_only: bool = True,
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    ticker = _blank(ticker)
    ticker_prefix = _blank(ticker_prefix)
    sector = _blank(sector)
    region = _blank(region)
    experiment_id = _blank(experiment_id)
    audit_verdict = _blank(audit_verdict)
    tech_signal = _blank(tech_signal)
    harness_version = _blank(harness_version)
    date_from = _parse_date("session_date_from", session_date_from)
    date_to = _parse_date("session_date_to", session_date_to)
    if ticker:
        clauses.append("ticker = ?")
        params.append(ticker.upper())
    if ticker_prefix:
        clauses.append("UPPER(ticker) LIKE ? ESCAPE '\\'")
        params.append(escape_like_prefix(ticker_prefix))
    if sector:
        clauses.append("primary_sector = ?")
        params.append(sector)
    if region:
        clauses.append("region = ?")
        params.append(region)
    if experiment_id:
        clauses.append("experiment_id = ?")
        params.append(experiment_id)
    if audit_verdict:
        clauses.append("audit_verdict = ?")
        params.append(audit_verdict)
    if tech_signal:
        clauses.append("tech_signal = ?")
        params.append(tech_signal)
    if harness_version:
        clauses.append("harness_version = ?")
        params.append(harness_version)
    if date_from is not None and date_to is not None and date_from > date_to:
        raise ValueError("session_date_from must be <= session_date_to")
    if date_from is not None:
        clauses.append("session_date >= ?")
        params.append(date_from)
    if date_to is not None:
        clauses.append("session_date <= ?")
        params.append(date_to)
    _append_numeric_range(
        clauses, params, "margin_of_safety_pct", "mos_min", "mos_max", mos_min, mos_max
    )
    _append_numeric_range(
        clauses, params, "asof_price", "price_min", "price_max", price_min, price_max
    )
    _append_numeric_range(
        clauses, params, "fv_base", "fv_base_min", "fv_base_max", fv_base_min, fv_base_max
    )
    if comparable_only:
        clauses.append("fv_base IS NOT NULL")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, params


def _runs_order_sql(sort: str | None, direction: str | None) -> str:
    sort = _blank(sort)
    direction = _blank(direction)
    if direction is not None and sort is None:
        raise ValueError("sort is required when dir is set")
    if direction is not None and direction.lower() not in ("asc", "desc"):
        raise ValueError("dir must be asc or desc")
    if sort is None:
        return _DEFAULT_ORDER_SQL
    if sort not in RUN_SORT_COLUMNS:
        raise ValueError(f"invalid sort: {sort!r}")
    dir_sql = "DESC" if (direction or "asc").lower() == "desc" else "ASC"
    if sort == "harness_version":
        major, minor, patch = _sql_semver_components("harness_version")
        parts = [
            "CASE WHEN harness_version IS NULL OR TRIM(harness_version) = '' THEN 1 ELSE 0 END ASC",
            f"{major} {dir_sql}",
            f"{minor} {dir_sql}",
            f"{patch} {dir_sql}",
        ]
    else:
        parts = [f"{sort} {dir_sql}"]
    for col, tie_dir in _TIEBREAK:
        if col != sort:
            parts.append(f"{col} {tie_dir}")
    return "ORDER BY " + ", ".join(parts)


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {k: row[k] for k in row.keys()}


@dataclass
class CatalogApi:
    """Readonly catalog client.

    Parameters
    ----------
    archive_root:
        Directory that **contains** research/, catalog/, outcomes/
        (i.e. project archive/ or eng/fixtures/archive).
    """

    archive_root: Path
    readonly: bool = True
    max_artifact_bytes: int = DEFAULT_MAX_BYTES

    def __post_init__(self) -> None:
        self.archive_root = Path(self.archive_root).expanduser().resolve()
        if not self.readonly:
            raise ValueError("CatalogApi is read-only; readonly must be True")

    # --- paths ----------------------------------------------------------------

    @property
    def catalog_dir(self) -> Path:
        return self.archive_root / "catalog"

    @property
    def research_dir(self) -> Path:
        return self.archive_root / "research"

    @property
    def outcomes_dir(self) -> Path:
        return self.archive_root / "outcomes"

    @property
    def db_path(self) -> Path:
        return self.catalog_dir / "research_compare.sqlite"

    def _connect(self) -> sqlite3.Connection:
        path = self.db_path
        if not path.is_file():
            raise DbMissing(f"Compare DB not found: {path}")
        # Readonly URI — never mkdir, never migrate
        uri = f"file:{path.resolve().as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    # --- health / list --------------------------------------------------------

    def health(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "archive_root": str(self.archive_root),
            "db_path": str(self.db_path),
            "db_exists": self.db_path.is_file(),
            "research_exists": self.research_dir.is_dir(),
            "schema_version": None,
            "run_count": None,
            "max_exported_at": None,
            "error": None,
        }
        if not out["db_exists"]:
            out["error"] = "db_missing"
            return out
        try:
            with self._connect() as conn:
                try:
                    ver = conn.execute(
                        "SELECT MAX(version) FROM schema_migrations"
                    ).fetchone()[0]
                    out["schema_version"] = int(ver) if ver is not None else None
                except sqlite3.Error:
                    out["schema_version"] = None
                out["run_count"] = int(
                    conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
                )
                mx = conn.execute("SELECT MAX(exported_at) FROM runs").fetchone()[0]
                out["max_exported_at"] = mx
        except Exception as e:  # noqa: BLE001
            out["error"] = str(e)
        return out

    def list_runs(
        self,
        *,
        ticker: str | None = None,
        ticker_prefix: str | None = None,
        sector: str | None = None,
        region: str | None = None,
        experiment_id: str | None = None,
        audit_verdict: str | None = None,
        tech_signal: str | None = None,
        harness_version: str | None = None,
        session_date_from: str | None = None,
        session_date_to: str | None = None,
        mos_min: Any = None,
        mos_max: Any = None,
        price_min: Any = None,
        price_max: Any = None,
        fv_base_min: Any = None,
        fv_base_max: Any = None,
        comparable_only: bool = True,
        sort: str | None = None,
        dir: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be 1..1000")
        if offset < 0:
            raise ValueError("offset must be >= 0")
        where, params = _runs_filter_sql(
            ticker=ticker,
            ticker_prefix=ticker_prefix,
            sector=sector,
            region=region,
            experiment_id=experiment_id,
            audit_verdict=audit_verdict,
            tech_signal=tech_signal,
            harness_version=harness_version,
            session_date_from=session_date_from,
            session_date_to=session_date_to,
            mos_min=mos_min,
            mos_max=mos_max,
            price_min=price_min,
            price_max=price_max,
            fv_base_min=fv_base_min,
            fv_base_max=fv_base_max,
            comparable_only=comparable_only,
        )
        order = _runs_order_sql(sort, dir)
        sql = f"""
            SELECT {_RUN_COLUMNS_V1}
            FROM runs
            {where}
            {order}
            LIMIT ? OFFSET ?
        """
        sql_v2 = f"""
            SELECT {_RUN_COLUMNS_V2}
            FROM runs
            {where}
            {order}
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        with self._connect() as conn:
            try:
                rows = conn.execute(sql_v2, params).fetchall()
            except sqlite3.OperationalError:
                try:
                    rows = conn.execute(sql, params).fetchall()
                except sqlite3.OperationalError as e:
                    if _missing_optional_column(e, "harness_version"):
                        if _blank(harness_version):
                            return []
                        if sort == "harness_version":
                            raise ValueError("invalid sort: 'harness_version'") from e
                    raise
        return [_row_to_dict(r) for r in rows]

    def count_runs(
        self,
        *,
        ticker: str | None = None,
        ticker_prefix: str | None = None,
        sector: str | None = None,
        region: str | None = None,
        experiment_id: str | None = None,
        audit_verdict: str | None = None,
        tech_signal: str | None = None,
        harness_version: str | None = None,
        session_date_from: str | None = None,
        session_date_to: str | None = None,
        mos_min: Any = None,
        mos_max: Any = None,
        price_min: Any = None,
        price_max: Any = None,
        fv_base_min: Any = None,
        fv_base_max: Any = None,
        comparable_only: bool = True,
    ) -> int:
        where, params = _runs_filter_sql(
            ticker=ticker,
            ticker_prefix=ticker_prefix,
            sector=sector,
            region=region,
            experiment_id=experiment_id,
            audit_verdict=audit_verdict,
            tech_signal=tech_signal,
            harness_version=harness_version,
            session_date_from=session_date_from,
            session_date_to=session_date_to,
            mos_min=mos_min,
            mos_max=mos_max,
            price_min=price_min,
            price_max=price_max,
            fv_base_min=fv_base_min,
            fv_base_max=fv_base_max,
            comparable_only=comparable_only,
        )
        sql = f"SELECT COUNT(*) FROM runs {where}"
        with self._connect() as conn:
            try:
                row = conn.execute(sql, params).fetchone()
            except sqlite3.OperationalError as e:
                if harness_version and _missing_optional_column(e, "harness_version"):
                    return 0
                raise
        return int(row[0] if row is not None else 0)

    def list_run_facets(self) -> dict[str, list[str]]:
        """Distinct non-empty values for filter dropdowns (sqlite projection)."""
        out: dict[str, list[str]] = {key: [] for key, _col in _FACET_COLUMNS}
        with self._connect() as conn:
            for key, col in _FACET_COLUMNS:
                try:
                    rows = conn.execute(
                        f"SELECT DISTINCT {col} FROM runs "
                        f"WHERE {col} IS NOT NULL AND TRIM({col}) != '' "
                        f"ORDER BY {col}"
                    ).fetchall()
                except sqlite3.OperationalError:
                    continue
                values = [str(r[0]) for r in rows]
                if key == "harness_version":
                    values.sort(key=_semver_sort_key)
                out[key] = values
        return out

    def get_run(self, run_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        if row is None:
            raise RunNotFound(run_id)
        return _row_to_dict(row)

    def get_session_root(self, run_id: str) -> Path:
        """Resolve session directory under this ARCHIVE_ROOT via run_id (not stored path)."""
        ticker, session_key = parse_run_id(run_id)
        # Prefer identity under current archive_root
        candidate = self.research_dir / ticker / session_key
        if candidate.is_dir():
            return candidate.resolve()
        # Fallback: stored path relative to project if present in DB
        try:
            row = self.get_run(run_id)
            rel = row.get("path")
            if rel:
                # path is typically archive/research/T/KEY relative to project
                # Map into this archive_root when prefix is archive/research
                p = Path(str(rel))
                parts = p.parts
                if "research" in parts:
                    idx = parts.index("research")
                    tail = Path(*parts[idx + 1 :])
                    alt = (self.research_dir / tail).resolve()
                    if alt.is_dir():
                        return alt
                proj = (PROJECT_ROOT / rel).resolve()
                if proj.is_dir():
                    return proj
        except (RunNotFound, DbMissing, ValueError):
            pass
        raise RunNotFound(f"{run_id} (session dir not found under {self.research_dir})")

    def get_report_paths(self, run_id: str) -> dict[str, str | None]:
        root = self.get_session_root(run_id)
        reports = root / "reports"
        out: dict[str, str | None] = {
            "session_root": str(root),
            "reports_dir": str(reports) if reports.is_dir() else None,
            "readme": None,
            "fundamental": None,
            "technical": None,
        }
        if not reports.is_dir():
            return out
        for p in sorted(reports.iterdir()):
            name = p.name.lower()
            if not p.is_file():
                continue
            if "readme" in name:
                out["readme"] = str(p)
            elif "fundamental" in name:
                out["fundamental"] = str(p)
            elif "technical" in name:
                out["technical"] = str(p)
        return out

    def _normalize_relpath(self, relpath: str) -> str:
        if not relpath or relpath.startswith("/") or relpath.startswith("~"):
            raise ArtifactDenied(f"absolute or empty relpath denied: {relpath!r}")
        if "\\" in relpath:
            raise ArtifactDenied("backslashes not allowed in relpath")
        norm = Path(relpath).as_posix()
        if norm.startswith("../") or "/../" in f"/{norm}/" or norm == "..":
            raise ArtifactDenied(f"path traversal denied: {relpath!r}")
        return norm

    def _assert_allowlisted(
        self,
        norm: str,
        *,
        allow_prefixes: Iterable[str] | None = None,
    ) -> None:
        allow = tuple(allow_prefixes or DEFAULT_ALLOW_PREFIXES)
        if not any(norm == a.rstrip("/") or norm.startswith(a) for a in allow):
            raise ArtifactDenied(f"prefix not allowlisted: {norm}")
        for d in DEFAULT_DENY_PREFIXES:
            if norm.startswith(d):
                raise ArtifactDenied(f"prefix denied: {norm}")

    def list_artifacts(
        self,
        run_id: str,
        *,
        prefix: str = "reports/",
        max_files: int = 200,
        allow_prefixes: Iterable[str] | None = None,
    ) -> list[dict[str, Any]]:
        """List allowlisted files under a session-relative prefix.

        Returns dicts with keys: relpath, name, size_bytes.
        Does not open file contents. Skips denied prefixes and escapes.
        """
        if max_files < 1 or max_files > 2000:
            raise ValueError("max_files must be 1..2000")
        prefix_norm = self._normalize_relpath(prefix if prefix.endswith("/") else prefix + "/")
        # prefix itself must be allowlisted (e.g. reports/)
        self._assert_allowlisted(prefix_norm, allow_prefixes=allow_prefixes)

        session_root = self.get_session_root(run_id).resolve()
        base = (session_root / prefix_norm).resolve()
        try:
            base.relative_to(session_root)
        except ValueError as e:
            raise ArtifactDenied(f"escapes session root: {prefix!r}") from e
        if not base.is_dir():
            return []

        out: list[dict[str, Any]] = []
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            try:
                rel = path.resolve().relative_to(session_root).as_posix()
            except ValueError:
                continue
            try:
                self._assert_allowlisted(rel, allow_prefixes=allow_prefixes)
            except ArtifactDenied:
                continue
            try:
                size = path.stat().st_size
            except OSError:
                size = None
            out.append({"relpath": rel, "name": path.name, "size_bytes": size})
            if len(out) >= max_files:
                break
        return out

    def get_snapshot(self, run_id: str) -> dict[str, Any]:
        root = self.get_session_root(run_id)
        snap = root / "meta" / "prediction_snapshot.json"
        if not snap.is_file():
            raise FileNotFoundError(snap)
        return json.loads(snap.read_text(encoding="utf-8"))

    def calibration(
        self,
        *,
        horizon: str = "1m",
        pass_only: bool = False,
    ) -> dict[str, Any]:
        """MoS buckets × realized outcomes (from sqlite outcomes table)."""
        sql = """
        SELECT r.run_id, r.ticker, r.session_date, r.margin_of_safety_pct,
               r.primary_sector, r.audit_verdict,
               o.horizon, o.total_return_pct, o.direction_hit, o.realized_price
        FROM runs r
        JOIN outcomes o ON o.run_id = r.run_id
        WHERE o.horizon = ?
          AND o.realized_price IS NOT NULL
        """
        params: list[Any] = [horizon]
        if pass_only:
            sql += " AND r.audit_verdict = 'PASS'"
        with self._connect() as conn:
            try:
                rows = [dict(x) for x in conn.execute(sql, params).fetchall()]
            except sqlite3.Error as e:
                return {
                    "horizon": horizon,
                    "pass_only": pass_only,
                    "n_joined": 0,
                    "error": str(e),
                    "overall": {},
                    "by_mos_bucket": {},
                }

        def bucket(mos: float | None) -> str:
            if mos is None:
                return "mos_unknown"
            if mos >= 15:
                return "cheap_mos>=15"
            if mos <= -15:
                return "expensive_mos<=-15"
            return "fair_|mos|<15"

        groups: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            mos = r.get("margin_of_safety_pct")
            if isinstance(mos, (int, float)):
                b = bucket(float(mos))
            else:
                b = bucket(None)
            groups.setdefault(b, []).append(r)

        def stats(items: list[dict[str, Any]]) -> dict[str, Any]:
            hits = [i["direction_hit"] for i in items if i.get("direction_hit") is not None]
            rets = [
                float(i["total_return_pct"])
                for i in items
                if isinstance(i.get("total_return_pct"), (int, float))
            ]
            return {
                "n": len(items),
                "n_scored": len(hits),
                "direction_hit_rate": (sum(hits) / len(hits)) if hits else None,
                "mean_return_pct": (sum(rets) / len(rets)) if rets else None,
            }

        return {
            "horizon": horizon,
            "pass_only": pass_only,
            "n_joined": len(rows),
            "overall": stats(rows),
            "by_mos_bucket": {k: stats(v) for k, v in sorted(groups.items())},
        }

    def open_artifact(
        self,
        run_id: str,
        relpath: str,
        *,
        allow_prefixes: Iterable[str] | None = None,
        max_bytes: int | None = None,
    ) -> bytes:
        """Read a file under the session root with containment + allowlist."""
        norm = self._normalize_relpath(relpath)
        self._assert_allowlisted(norm, allow_prefixes=allow_prefixes)

        session_root = self.get_session_root(run_id).resolve()
        target = (session_root / norm).resolve()
        try:
            target.relative_to(session_root)
        except ValueError as e:
            raise ArtifactDenied(f"escapes session root: {relpath!r}") from e
        if not target.is_file():
            raise FileNotFoundError(str(target))

        limit = max_bytes if max_bytes is not None else self.max_artifact_bytes
        data = target.read_bytes()
        if len(data) > limit:
            raise ArtifactDenied(
                f"artifact exceeds max_bytes={limit} (size={len(data)})"
            )
        return data

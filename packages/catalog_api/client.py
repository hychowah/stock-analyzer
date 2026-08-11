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
        sector: str | None = None,
        region: str | None = None,
        experiment_id: str | None = None,
        audit_verdict: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be 1..1000")
        if offset < 0:
            raise ValueError("offset must be >= 0")
        clauses: list[str] = []
        params: list[Any] = []
        if ticker:
            clauses.append("ticker = ?")
            params.append(ticker.upper())
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
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
            SELECT run_id, ticker, session_date, session_key, path,
                   experiment_id, audit_verdict, data_quality, status,
                   asof_price, currency, primary_sector, region, intensity,
                   fv_bear, fv_base, fv_bull, fv_weighted,
                   p_bear, p_base, p_bull, margin_of_safety_pct,
                   model_name, tech_signal, tech_regime,
                   exported_at, harness_git_sha, orchestrator_model
            FROM runs
            {where}
            ORDER BY ticker, session_date DESC, session_key DESC
            LIMIT ? OFFSET ?
        """
        # Prefer richer projection when harness_version column exists (schema v2+)
        sql_v2 = f"""
            SELECT run_id, ticker, session_date, session_key, path,
                   experiment_id, audit_verdict, data_quality, status,
                   asof_price, currency, primary_sector, region, intensity,
                   fv_bear, fv_base, fv_bull, fv_weighted,
                   p_bear, p_base, p_bull, margin_of_safety_pct,
                   model_name, tech_signal, tech_regime,
                   exported_at, harness_version, harness_git_sha, orchestrator_model
            FROM runs
            {where}
            ORDER BY ticker, session_date DESC, session_key DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        with self._connect() as conn:
            try:
                rows = conn.execute(sql_v2, params).fetchall()
            except sqlite3.OperationalError:
                rows = conn.execute(sql, params).fetchall()
        return [_row_to_dict(r) for r in rows]

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
        pass_only: bool = True,
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

"""Forbidden-citation scans: Agent 4 vs fundamentals, and cross-session paths.

Library path citations stay in library.py.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# Path-anchored tokens: avoid bare English false positives (e.g. "background").
AGENT4_FORBIDDEN_TOKENS = (
    "filing_deep_dive",
    "fdd_year",
    "valuation_model",
    "registry/background",
    "background.json",
    "latest_quarter",
    "market_context.json",
    "sec_filings",
    "sp_financials",
    "operating_path_brief",
    "oppath_",
    "revenue_growth.json",
    "industry_trend.json",
    "operating_leverage.json",
    "street_estimates",
    "street_bind",
    "archive/library",
    "library_bind",
    "tsr_validation",
)


def check_agent4_isolation(session: Path, *, full: bool = False) -> list[tuple[str, str, str]]:
    """Post-hoc: technical artifact/handoff must not cite fundamental session paths."""
    texts: list[tuple[str, str]] = []
    tech = session / "registry" / "technical.json"
    if tech.exists():
        try:
            texts.append(
                (str(tech.relative_to(session)), tech.read_text(encoding="utf-8", errors="replace"))
            )
        except OSError as e:
            return [("FAIL", "agent4_isolation", f"cannot read technical.json: {e}")]
    handoff_dir = session / "registry" / "handoffs"
    if handoff_dir.is_dir():
        for p in sorted(handoff_dir.glob("4*.md")):
            try:
                texts.append(
                    (str(p.relative_to(session)), p.read_text(encoding="utf-8", errors="replace"))
                )
            except OSError:
                continue
    if not texts:
        return [("SKIPPED", "agent4_isolation", "no technical.json or handoffs/4*.md")]

    hits: list[str] = []
    for rel, text in texts:
        lower = text.lower()
        for tok in AGENT4_FORBIDDEN_TOKENS:
            if tok.lower() in lower:
                hits.append(f"{rel}:{tok}")
    if not hits:
        return [("PASS", "agent4_isolation", f"scanned {len(texts)} file(s)")]
    detail = "; ".join(hits[:12])
    status = "FAIL" if full else "WARN"
    return [(status, "agent4_isolation", detail)]


def check_agent4_isolation_core(session: Path) -> list[tuple[str, str, str]]:
    return check_agent4_isolation(session, full=False)


def check_agent4_isolation_full(session: Path) -> list[tuple[str, str, str]]:
    return check_agent4_isolation(session, full=True)


_OTHER_SESSION_PATH_RE = re.compile(
    r"archive[/\\]research[/\\](?P<ticker>[A-Za-z0-9][A-Za-z0-9._-]*)[/\\]"
    r"(?P<sk>\d{4}-\d{2}-\d{2}(?:__[A-Za-z0-9][A-Za-z0-9._-]{0,80})?)",
    re.IGNORECASE,
)


def check_session_isolation(session: Path, *, full: bool = False) -> list[tuple[str, str, str]]:
    """Cross-session isolation: prior runs must not feed this session's valuation."""
    out: list[tuple[str, str, str]] = []
    iso = session / "registry" / "session_isolation.json"
    if iso.is_file():
        try:
            data = json.loads(iso.read_text(encoding="utf-8"))
            mode = data.get("mode") or "isolated"
            rules = data.get("rules") if isinstance(data.get("rules"), dict) else {}
            if rules.get("prior_valuation_as_input") is True:
                out.append(
                    (
                        "WARN",
                        "session_isolation policy",
                        "prior_valuation_as_input=true — unusual; risk of anchoring",
                    )
                )
            elif rules.get("intra_session_share") is False:
                out.append(
                    (
                        "WARN",
                        "session_isolation policy",
                        "intra_session_share=false — breaks normal phase handoffs",
                    )
                )
            else:
                out.append(("PASS", "session_isolation policy", f"mode={mode}"))
        except Exception as e:  # noqa: BLE001
            out.append(("FAIL", "session_isolation parse", str(e)))
    else:
        out.append(
            (
                "SKIPPED",
                "session_isolation",
                "registry/session_isolation.json absent (legacy OK; new scaffolds write it)",
            )
        )

    session_key = session.name
    ticker = session.parent.name.upper()
    allow: set[str] = set()
    if iso.is_file():
        try:
            data = json.loads(iso.read_text(encoding="utf-8"))
            for k in data.get("allow_prior_session_keys") or []:
                if isinstance(k, str) and k.strip():
                    allow.add(k.strip())
        except Exception:  # noqa: BLE001
            pass

    scan_rels = [
        "data/valuation_model.json",
        "registry/risk_bridge.json",
        "meta/prediction_snapshot.json",
        "registry/handoffs/5_valuation.md",
        "registry/handoffs/7_fundamental_report.md",
        "registry/handoffs/7_fundamental.md",
        "registry/handoffs/13_audit.md",
    ]
    for p in (session / "reports").glob("*.md") if (session / "reports").is_dir() else []:
        scan_rels.append(str(p.relative_to(session)).replace("\\", "/"))

    hits: list[str] = []
    for rel in scan_rels:
        path = session / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in _OTHER_SESSION_PATH_RE.finditer(text):
            other_t = m.group("ticker").upper()
            other_sk = m.group("sk")
            if other_t != ticker:
                continue
            if other_sk == session_key:
                continue
            if other_sk in allow:
                continue
            hits.append(f"{rel} → {other_t}/{other_sk}")

    if not hits:
        out.append(
            (
                "PASS",
                "cross-session valuation isolation",
                "no foreign session paths in valuation-facing artifacts",
            )
        )
        return out

    sample = "; ".join(hits[:5])
    more = f" (+{len(hits) - 5} more)" if len(hits) > 5 else ""
    detail = (
        f"prior session path(s) cited (risk of FV anchoring): {sample}{more}. "
        "Valuation must use this session only; compare-after is post-audit only."
    )
    out.append(
        (
            "FAIL" if full else "WARN",
            "cross-session valuation isolation",
            detail,
        )
    )
    return out


def check_session_isolation_core(session: Path) -> list[tuple[str, str, str]]:
    return check_session_isolation(session, full=False)


def check_session_isolation_full(session: Path) -> list[tuple[str, str, str]]:
    return check_session_isolation(session, full=True)

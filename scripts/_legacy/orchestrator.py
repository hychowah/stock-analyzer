#!/usr/bin/env python3
"""Research orchestration runbook.

Creates the per-ticker session folder structure, invokes research tools,
and writes registry files, data artifacts, charts, and stub reports.

Usage:
    /workspace-stock-research/yfinance-market-mcp/.venv/bin/python \
        scripts/orchestrator.py --ticker AAPL

Modes:
    direct (default): import tool functions from yfinance_mcp.server when
        available; otherwise fall back to scripts.orchestrator_tools.
    mcp             : call tools via a subprocess MCP server using JSON-RPC
        over stdio.  The server command is read from .mcp.json.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
YFINANCE_SRC = PROJECT_ROOT / "yfinance-market-mcp" / "src"
MCP_CONFIG = PROJECT_ROOT / ".mcp.json"
TEMPLATES_DIR = PROJECT_ROOT / "templates"

# Ensure the project root is on sys.path so `scripts` package imports work when
# this file is executed directly.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ── Tool resolution ─────────────────────────────────────────────────────────


class DirectToolClient:
    """Imports tool functions directly from the yfinance package or fallback."""

    def __init__(self):
        self._tools: dict[str, Callable] = {}
        self._load()

    def _load(self):
        # Prefer the real MCP server tools once they exist.
        sys.path.insert(0, str(YFINANCE_SRC))
        try:
            import yfinance_mcp.server as server

            for name in (
                "classify_sector",
                "get_latest_quarter_snapshot",
                "compute_valuation_model",
                "generate_charts",
                "get_peer_snapshot",
            ):
                if hasattr(server, name):
                    self._tools[name] = getattr(server, name)
                elif hasattr(server, "research") and hasattr(server.research, name):
                    self._tools[name] = getattr(server.research, name)
        except Exception:
            pass
        finally:
            sys.path.pop(0)

        # Fill any missing tools with local fallback implementations.
        # Always use the local chart implementation because the server-side
        # lazy import of matplotlib can leave the matplotlib module in a broken
        # state, causing chart generation to fail silently.
        from scripts import orchestrator_tools

        for name in (
            "classify_sector",
            "get_latest_quarter_snapshot",
            "compute_valuation_model",
            "generate_charts",
            "get_peer_snapshot",
        ):
            if name == "generate_charts":
                self._tools[name] = getattr(orchestrator_tools, name)
            elif name not in self._tools:
                self._tools[name] = getattr(orchestrator_tools, name)

    def call(self, name: str, **kwargs) -> Any:
        if name not in self._tools:
            raise RuntimeError(f"Tool '{name}' is not available.")
        return self._tools[name](**kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class McpStdioClient:
    """Minimal JSON-RPC stdio client for an MCP server.

    Performs the Model Context Protocol initialize handshake before making
    tool calls.  This is experimental; mode (a) direct imports are recommended
    for routine use.
    """

    def __init__(
        self,
        command: list[str],
        env: dict[str, str] | None = None,
        init_timeout: int = 30,
        call_timeout: int = 120,
    ):
        self.command = command
        self.env = env or {}
        self._proc: subprocess.Popen | None = None
        self._req_id = 0
        self._init_timeout = init_timeout
        self._call_timeout = call_timeout

    def __enter__(self):
        env = os.environ.copy()
        env.update(self.env)
        self._proc = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        self._initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._proc is not None:
            try:
                if self._proc.stdin:
                    self._proc.stdin.close()
                self._proc.wait(timeout=5)
            except Exception:
                self._proc.kill()

    def _send(self, msg: dict):
        self._proc.stdin.write(json.dumps(msg) + "\n")
        self._proc.stdin.flush()

    def _read_line(self, timeout: float | None = None) -> dict | None:
        if timeout is not None:
            import select

            ready, _, _ = select.select([self._proc.stdout], [], [], timeout)
            if not ready:
                raise TimeoutError("Timed out waiting for MCP server response")
        line = self._proc.stdout.readline()
        if not line:
            return None
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return None

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def _initialize(self):
        init_req = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "research-orchestrator", "version": "0.1.0"},
            },
        }
        self._send(init_req)
        while True:
            msg = self._read_line(timeout=self._init_timeout)
            if msg is None:
                raise RuntimeError("MCP server closed connection during initialize.")
            if msg.get("id") == init_req["id"]:
                if "error" in msg:
                    raise RuntimeError(f"MCP initialize error: {msg['error']}")
                break
        # Confirm initialization.
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def call(self, name: str, **kwargs) -> Any:
        if self._proc is None:
            raise RuntimeError("MCP client not started.")
        req_id = self._next_id()
        req = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": kwargs},
        }
        self._send(req)
        while True:
            msg = self._read_line(timeout=self._call_timeout)
            if msg is None:
                raise RuntimeError("MCP server closed connection unexpectedly.")
            if msg.get("id") == req_id:
                if "error" in msg:
                    raise RuntimeError(f"MCP error: {msg['error']}")
                result = msg.get("result", {})
                # FastMCP wraps tool output in content.
                if "content" in result:
                    for item in result["content"]:
                        if item.get("type") == "text":
                            try:
                                return json.loads(item["text"])
                            except json.JSONDecodeError:
                                return item["text"]
                return result


def _load_mcp_server_config(server_name: str) -> dict:
    if not MCP_CONFIG.exists():
        raise FileNotFoundError(f"{MCP_CONFIG} not found")
    cfg = json.loads(MCP_CONFIG.read_text())
    servers = cfg.get("mcpServers", {})
    if server_name not in servers:
        raise KeyError(f"No MCP server named '{server_name}' in {MCP_CONFIG}")
    return servers[server_name]


def _make_mcp_client(server_name: str = "yfinance") -> McpStdioClient:
    cfg = _load_mcp_server_config(server_name)
    command = cfg["command"]
    if isinstance(command, str):
        command = [command]
    env = cfg.get("env", {})
    return McpStdioClient(command=command, env=env)


# ── Folder / file writing ───────────────────────────────────────────────────


def _ensure_session_dirs(root: Path) -> dict[str, Path]:
    dirs = {
        "reports": root / "reports",
        "data": root / "data",
        "charts": root / "charts",
        "registry": root / "registry",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def _write_json(path: Path, data: Any):
    path.write_text(json.dumps(data, indent=2, default=str) + "\n")


def _records_to_csv(path: Path, records: list[dict], fieldnames: list[str] | None = None):
    if not records:
        path.write_text("")
        return
    if fieldnames is None:
        fieldnames = list(records[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in records:
            writer.writerow({k: row.get(k) for k in fieldnames})


def _normalize_sector_config(raw: dict, ticker: str, session_date: str) -> dict:
    """Ensure sector_config output conforms to sector_config.schema.json."""
    from scripts.orchestrator_tools import _build_substitutions

    primary = raw.get("primary_sector", "standard")
    is_also_growth = raw.get("is_also_growth", False)
    confidence = raw.get("confidence", 0.0)
    requires_manual_review = raw.get(
        "requires_manual_review",
        raw.get("manual_review_recommended", confidence < 0.70),
    )

    module_file = raw.get("module_file") or raw.get("suggested_module_file")
    if module_file is None and primary != "standard":
        module_file = f"/workspace-stock-research/sector_{primary}.md"
    # Standard framework uses no sector module (per AGENTS.md).

    substitutions = raw.get("substitutions")
    if not substitutions:
        substitutions = _build_substitutions(primary, is_also_growth)

    trigger_reasons = raw.get("trigger_reasons", [])
    if isinstance(trigger_reasons, dict):
        # research.py returns triggers grouped by sector; flatten to strings.
        flat: list[str] = []
        for sector, reasons in trigger_reasons.items():
            flat.extend(f"{sector}: {r}" for r in reasons)
        trigger_reasons = flat

    return {
        "ticker": ticker.upper(),
        "session_date": session_date,
        "primary_sector": primary,
        "confidence": confidence,
        "is_also_growth": is_also_growth,
        "module_file": module_file,
        "secondary_module_file": (
            "/workspace-stock-research/sector_growth.md" if is_also_growth else None
        ),
        "trigger_reasons": trigger_reasons,
        "all_scores": raw.get("all_scores", {}),
        "substitutions": substitutions,
        "agents_modified": raw.get("agents_modified", ["agent_0", "agent_2", "agent_5", "agent_12", "agent_13"]),
        "agents_unchanged": raw.get("agents_unchanged", ["agent_1", "agent_3", "agent_4", "agent_6", "agent_8", "agent_11"]),
        "requires_manual_review": bool(requires_manual_review),
        "review_notes": raw.get("review_notes") or (
            "Sector confidence below 0.70; fell back to standard framework. Human review recommended."
            if requires_manual_review else None
        ),
        "classification_timestamp": raw.get("classification_timestamp", _now()),
        "sources": raw.get("sources", ["yfinance Ticker.info"]),
    }


def _normalize_valuation(raw: dict, ticker: str) -> dict:
    """Ensure valuation output has a consistent scenarios structure."""
    price = raw.get("inputs", {}).get("price") or raw.get("current_price")
    model_name = raw.get("model_name") or raw.get("model", "DCF")
    sensitivities = raw.get("sensitivities", {})

    scenarios: dict[str, dict] = {}
    for key in ("bear", "base", "bull"):
        fv = sensitivities.get(key)
        if fv is None and key == raw.get("scenario_focus"):
            fv = raw.get("fair_value")
        scenarios[key] = {
            "fair_value_per_share": round(fv, 2) if isinstance(fv, (int, float)) else None,
            "upside_pct": round((fv - price) / price * 100, 2) if isinstance(fv, (int, float)) and price else None,
        }

    return {
        "ticker": ticker.upper(),
        "model": model_name,
        "current_price": price,
        "market_cap": raw.get("inputs", {}).get("market_cap") or raw.get("market_cap"),
        "scenarios": scenarios,
        "raw": raw,
    }


def _normalize_latest_quarter(raw: dict, ticker: str, session_date: str) -> dict:
    """Ensure latest_quarter output conforms to latest_quarter.schema.json."""
    rev = raw.get("revenue", {})
    margins = raw.get("margins", {})
    bs = raw.get("balance_sheet", {})
    cf = raw.get("cash_flow", {})
    cr = raw.get("capital_returns", {})
    price = raw.get("price", {})

    total_revenue = rev.get("total_revenue")
    net_income = rev.get("net_income")
    operating_margin = margins.get("operating_margin")
    net_margin = margins.get("net_margin")
    total_equity = bs.get("stockholders_equity")
    total_debt = bs.get("total_debt")
    cash = bs.get("cash")
    fcf = cf.get("free_cash_flow")

    net_debt = None
    if total_debt is not None and cash is not None:
        net_debt = total_debt - cash

    guidance = raw.get("guidance", {})

    return {
        "ticker": ticker.upper(),
        "session_date": session_date,
        "fiscal_period": raw.get("fiscal_period") or raw.get("period") or "latest_fiscal_quarter",
        "filing_date": raw.get("filing_date"),
        "sources": [
            {
                "name": "yfinance quarterly financials",
                "url": None,
                "accessed": _now(),
            }
        ],
        "revenue_earnings": {
            "total_revenue": total_revenue,
            "revenue_yoy_pct": None,
            "revenue_qoq_pct": None,
            "ebit": rev.get("ebit"),
            "ebitda": rev.get("ebitda"),
            "net_income": net_income,
            "eps_reported": None,
            "eps_consensus": None,
            "beat_miss_eps": None,
            "currency": None,
            "unit": "units",
        },
        "guidance": {
            "revenue_guidance": guidance.get("revenueGrowth"),
            "eps_guidance": None,
            "capex_guidance": None,
            "margin_guidance": None,
            "guidance_change": None,
            "guidance_notes": "Guidance from yfinance info/summary; populate from 10-Q/earnings release for full detail.",
        },
        "segment_performance": raw.get("segment_performance", []),
        "sector_kpis": raw.get("sector_kpis", {}),
        "margins_costs": {
            "gross_margin_pct": margins.get("gross_margin"),
            "operating_margin_pct": operating_margin,
            "net_margin_pct": net_margin,
            "cost_inflation_notes": None,
            "pricing_power_notes": None,
        },
        "balance_sheet": {
            "total_assets": bs.get("total_assets"),
            "total_equity": total_equity,
            "total_debt": total_debt,
            "net_debt": net_debt,
            "cash_and_equivalents": cash,
            "leverage_ratio": None,
            "capital_ratio": None,
            "reserves": None,
            "inventory": None,
            "working_capital": None,
        },
        "cash_flow": {
            "operating_cash_flow": cf.get("operating_cash_flow"),
            "free_cash_flow": fcf,
            "capex": cf.get("capex"),
            "sbc": cf.get("stock_based_compensation"),
            "sbc_pct_revenue": margins.get("sbc_over_revenue"),
        },
        "capital_returns": {
            "dividend_per_share": None,
            "dividend_yield_pct": None,
            "buyback_authorization": None,
            "buyback_executed": cr.get("buybacks"),
            "capital_raise": None,
        },
        "management_tone": {
            "demand_commentary": None,
            "pricing_environment": None,
            "supply_chain": None,
            "hiring_backlog": None,
            "overall_assessment": None,
        },
        "risks": raw.get("risks", []),
        "override_log": raw.get("override_log", []),
    }


def _write_stub_reports(
    reports_dir: Path,
    ticker: str,
    sector_config: dict,
    latest_quarter: dict,
    valuation: dict,
):
    ticker_uc = ticker.upper()

    readme = reports_dir / f"00_{ticker_uc}_README.md"
    fundamental = reports_dir / f"01_{ticker_uc}_fundamental.md"
    technical = reports_dir / f"02_{ticker_uc}_technical.md"

    primary = sector_config.get("primary_sector", "standard")
    confidence = sector_config.get("confidence", 0.0)
    review_flag = "**MANUAL REVIEW REQUIRED**" if sector_config.get("requires_manual_review") else ""

    readme.write_text(
        f"""# {ticker_uc} — Research Session Summary

**Ticker:** {ticker_uc}  
**Session Date:** {sector_config.get("session_date", _today())}  
**Classification:** {primary} (confidence {confidence:.2%}) {review_flag}  
**Module:** {sector_config.get("module_file") or "N/A (standard framework)"}  
**Also Growth:** {sector_config.get("is_also_growth", False)}

## Latest Quarter Headline

- Fiscal period: {latest_quarter.get("fiscal_period", "N/A")}
- Revenue: {latest_quarter.get("revenue_earnings", {}).get("total_revenue", "N/A")}
- Revenue YoY: {latest_quarter.get("revenue_earnings", {}).get("revenue_yoy_pct", "N/A")}
- FCF: {latest_quarter.get("cash_flow", {}).get("free_cash_flow", "N/A")}

## Valuation Snapshot

- Model: {valuation.get("model", "N/A")}
- Base-case fair value: {valuation.get("scenarios", {}).get("base", {}).get("fair_value_per_share", "N/A")}
- Current price: {valuation.get("current_price", "N/A")}

## Verdict

*To be completed by Agent 11 after fundamental and technical reports are finalized.*

## Required Inputs

- [ ] Company name
- [ ] Market region / exchange
- [ ] Reporting currency
- [ ] Regional benchmark index
- [ ] 3–5 closest competitors / peers
- [ ] Latest fiscal quarter / filing date

## Quality Gates

- [ ] Sector confidence ≥ 0.70 or manual-review flag present
- [ ] Correct sector module(s) loaded and substitutions applied
- [ ] Latest quarter read, extracted, and documented
- [ ] All five analytical perspectives addressed
- [ ] Valuation model uses sector-appropriate metrics
- [ ] Stress tests include 4 sector scenarios plus 1 macro scenario
- [ ] Reverse engineering flags any "priced for perfection" outcome
- [ ] SBC-adjusted returns calculated for growth / is_also_growth names
- [ ] Reports saved to correct folder
- [ ] No output fabricated; every number cites a source or assumption
"""
    )

    fundamental.write_text(
        f"""# {ticker_uc} — Fundamental, Valuation & Risk Report

## 1. Executive Summary

**Sector:** {primary}  
**Latest Quarter:** {latest_quarter.get("fiscal_period", "N/A")}  
**Primary Valuation Model:** {valuation.get("model", "N/A")}

*Agent 7 fills this section after Phase 2 modeling and Phase 2.5 stress testing.*

### Latest-Quarter Takeaway

{latest_quarter.get("guidance", {}).get("guidance_notes", "_Populate from earnings release / 10-Q._")}

## 2. Business & Moat Analysis

*Agent 0 output. Replace with sector-specific findings using the metric substitution table.*

Moat indicator for {primary}: `{sector_config.get("substitutions", {}).get("moat_indicator", "N/A")}`

## 3. Sector-Appropriate Financial Analysis

*Agent 2 output. Use substituted metrics:*

- ROIC equivalent: `{sector_config.get("substitutions", {}).get("roic_equivalent", "N/A")}`
- P/E equivalent: `{sector_config.get("substitutions", {}).get("pe_equivalent", "N/A")}`
- FCF yield equivalent: `{sector_config.get("substitutions", {}).get("fcf_yield_equivalent", "N/A")}`

## 4. Valuation Model

**Model used:** {valuation.get("model", "N/A")}

| Scenario | Fair Value | Upside vs Current |
|---|---|---|
| Bear | {valuation.get("scenarios", {}).get("bear", {}).get("fair_value_per_share", "N/A")} | {valuation.get("scenarios", {}).get("bear", {}).get("upside_pct", "N/A")}% |
| Base | {valuation.get("scenarios", {}).get("base", {}).get("fair_value_per_share", "N/A")} | {valuation.get("scenarios", {}).get("base", {}).get("upside_pct", "N/A")}% |
| Bull | {valuation.get("scenarios", {}).get("bull", {}).get("fair_value_per_share", "N/A")} | {valuation.get("scenarios", {}).get("bull", {}).get("upside_pct", "N/A")}% |

## 5. Reverse Engineering

*What is the current price implying? Target parameter:* `{sector_config.get("substitutions", {}).get("reverse_engineering_target", "N/A")}`

## 6. Stress Tests

*Agent 13 scenarios:*

{chr(10).join(f"- {s}" for s in sector_config.get("substitutions", {}).get("stress_test_scenarios", []))}

## 7. Risk Bridge

*See `registry/risk_bridge.json`. Map each risk to valuation parameters, probability, and time horizon.*

## 8. Five-Perspective Synthesis

### 8.1 Value Investor Lens
- Margin-of-safety threshold: **TBD**
- Normalized earnings/FCF check: **TBD**
- Capital allocation score: **TBD**
- Balance sheet floor: **TBD**

### 8.2 Growth Investor Lens
- TAM/SAM/SOM: **TBD**
- Organic vs M&A growth: **TBD**
- Customer/revenue concentration: **TBD**
- Reinvestment runway: **TBD**
- R&D / product pipeline: **TBD**

### 8.3 Contrarian / Catalyst Hunter Lens
- Catalyst calendar: **TBD**
- Sentiment / positioning: **TBD**
- Sum-of-the-parts or hidden assets: **TBD**
- Probability-weighted event paths: **TBD**

### 8.4 Risk Manager Lens
- Probability estimates for stress scenarios: **TBD**
- Liquidity and contingent liabilities: **TBD**
- ESG / regulatory materiality: **TBD**
- Concentration risk: **TBD**
- Covenant / refinancing wall: **TBD**
- Recommended position sizing: **TBD**

### 8.5 Technical / Entry-Timing Specialist Lens
- See `02_{ticker_uc}_technical.md`.

## 9. Perspective Conflicts

*Document any contradictions across the five lenses here.*
"""
    )

    technical.write_text(
        f"""# {ticker_uc} — Technical Analysis & Entry Timing

## Price Action

*Agent 4 / Agent 8 output. Pure price/volume analysis independent of fundamentals.*

## Key Levels

- Support: **TBD**
- Resistance: **TBD**
- Entry: **TBD**
- Stop-loss: **TBD**
- Target: **TBD**

## Indicators

- 50-day MA vs 200-day MA: **TBD**
- RSI / MACD: **TBD**
- ATR-based position sizing: **TBD**
- Relative strength vs sector/benchmark: **TBD**

## Latest-Quarter Price Reaction

*Note any gap or volume spike caused by the latest earnings release.*

{latest_quarter.get("fiscal_period", "N/A")}: **TBD**

## Technical–Fundamental Gap

- Current price: {valuation.get("current_price", "N/A")}
- Base-case fair value: {valuation.get("scenarios", {}).get("base", {}).get("fair_value_per_share", "N/A")}
- Gap assessment: **TBD**
"""
    )


# ── Main runbook ────────────────────────────────────────────────────────────


def _venv_python() -> Path:
    """Return the yfinance-market-mcp venv python interpreter."""
    return PROJECT_ROOT / "yfinance-market-mcp" / ".venv" / "bin" / "python"


def _run_agent_script(script_name: str, ticker: str, session_date: str, output_dir: Path) -> None:
    """Run an agent script in the project venv with consistent CLI args."""
    script_path = PROJECT_ROOT / "scripts" / script_name
    cmd = [
        str(_venv_python()),
        str(script_path),
        "--ticker", ticker,
        "--date", session_date,
        "--output-dir", str(output_dir),
    ]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def run_research(
    ticker: str,
    session_date: str,
    output_dir: Path,
    peers: list[str],
    mode: str = "direct",
):
    ticker = ticker.upper()
    session_root = output_dir / ticker / session_date
    if session_root.exists():
        raise FileExistsError(
            f"Session folder already exists: {session_root}. "
            "Use a different --date or remove the folder manually."
        )
    dirs = _ensure_session_dirs(session_root)

    # Initialize tool client
    if mode == "mcp":
        client_cm = _make_mcp_client("yfinance")
    else:
        client_cm = DirectToolClient()

    with client_cm as client:
        # Phase 0: Sector detection
        sector_config_raw = client.call("classify_sector", ticker=ticker)
        sector_config = _normalize_sector_config(sector_config_raw, ticker, session_date)
        _write_json(dirs["registry"] / "sector_config.json", sector_config)

        # Phase 1: API data + latest quarter snapshot
        _run_agent_script("agent2_api_data.py", ticker, session_date, output_dir)
        latest_quarter_raw = client.call("get_latest_quarter_snapshot", ticker=ticker)
        latest_quarter = _normalize_latest_quarter(latest_quarter_raw, ticker, session_date)
        _write_json(dirs["registry"] / "latest_quarter.json", latest_quarter)

        # Peer snapshot
        peer_data = client.call("get_peer_snapshot", ticker=ticker, peers=peers)
        _write_json(dirs["data"] / "peer_comparison.json", peer_data)
        peer_rows = peer_data.get("data", [])
        if isinstance(peer_rows, dict):
            peer_rows = list(peer_rows.values())
        if peer_rows:
            _records_to_csv(dirs["data"] / "peer_comparison.csv", peer_rows)

        # Financials CSV (latest annual + quarterly income statement)
        import yfinance as yf

        t = yf.Ticker(ticker)
        fin_records = []
        for freq, stmt in (
            ("annual", t.income_stmt),
            ("quarterly", t.quarterly_income_stmt),
        ):
            if stmt is not None and not stmt.empty:
                df = stmt.T.reset_index()
                df["freq"] = freq
                df = df.rename(columns={df.columns[0]: "period"})
                fin_records.extend(df.to_dict("records"))
        if fin_records:
            _records_to_csv(
                dirs["data"] / "financials.csv",
                fin_records,
                fieldnames=list(fin_records[0].keys()),
            )

        # Phase 2: Valuation model and risk bridge
        primary_sector = sector_config.get("primary_sector", "standard")
        _run_agent_script("agent5_valuation.py", ticker, session_date, output_dir)
        valuation = json.loads((dirs["data"] / "valuation_model.json").read_text())

        # Phase 2.5 / 4: Technical analysis
        _run_agent_script("agent4_technical.py", ticker, session_date, output_dir)

        # Phase 5: TSR validation
        _run_agent_script("agent12_tsr.py", ticker, session_date, output_dir)

        # Phase 3: Charts (uses the agent5 valuation model if available)
        chart_result = client.call("generate_charts", ticker=ticker, output_dir=str(dirs["charts"]))
        if "error" in chart_result:
            print(f"WARNING chart generation failed: {chart_result['error']}", file=sys.stderr)

        # Phase 6: Stub reports (to be expanded by Agent 7/8/11)
        _write_stub_reports(
            dirs["reports"], ticker, sector_config, latest_quarter, valuation
        )

    return session_root


def main():
    parser = argparse.ArgumentParser(description="Research orchestration runbook")
    parser.add_argument("--ticker", required=True, help="Ticker symbol to research")
    parser.add_argument(
        "--date",
        default=_today(),
        help="Session date in YYYY-MM-DD format (default: today UTC)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT),
        help="Root directory under which <TICKER>/<DATE>/ will be created",
    )
    parser.add_argument(
        "--peers",
        default="",
        help="Comma-separated list of peer tickers",
    )
    parser.add_argument(
        "--mode",
        choices=["direct", "mcp"],
        default="direct",
        help="Tool invocation mode (default: direct imports)",
    )
    args = parser.parse_args()

    peers = [p.strip().upper() for p in args.peers.split(",") if p.strip()]
    output_dir = Path(args.output_dir).expanduser().resolve()

    session_root = run_research(
        ticker=args.ticker,
        session_date=args.date,
        output_dir=output_dir,
        peers=peers,
        mode=args.mode,
    )

    print(f"Research scaffolding created at: {session_root}")
    print("Next steps:")
    print("  1. Review registry/sector_config.json")
    print("  2. Populate registry/latest_quarter.json from the 10-Q/earnings release")
    print("  3. Fill in agent content in reports/")
    print("  4. Run scripts/validate_registry.py to check registry JSON files")


if __name__ == "__main__":
    main()

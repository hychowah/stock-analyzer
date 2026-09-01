"""UI-scheduled map prompt: coordinates only. Methodology lives in the pin."""

from __future__ import annotations

from typing import Any

from packages.research_jobs.paths import UI_SCHEDULED_HEADING

ALREADY_SCAFFOLDED = "Session is ALREADY scaffolded"
NO_RE_SCAFFOLD = "Do not run scripts/scaffold_session.py"
NO_LIST_SIBLINGS = "Do not list archive/research/"
R2_WARNING = "WILL allocate __r2"
LISTING_JUDGE = "Confirm the Yahoo listing with tools"
LISTING_VERIFY = "scripts/verify_listing.py"
ABANDON_IF_UNREAL = "If TICKER is not a real market issuer, write registry/abandon.json and STOP"
OPEN_PIN_LAW = "Read Mode A law under ROOT/ only"
NO_CHECKOUT_HARNESS = "Do not open the interactive checkout harness/"


def _root(job: dict[str, Any]) -> str:
    pin = job.get("pin")
    if isinstance(pin, dict) and pin.get("root"):
        return str(pin["root"])
    return str(job.get("harness_root") or job.get("project_root") or "")


def build_prompt(job: dict[str, Any], *, resume: bool = False) -> str:
    ticker = job["ticker"]
    stamp = job.get("quote_symbol")
    stamp_s = str(stamp).strip().upper() if stamp else ""
    session_key = job["session_key"]
    session_root = job["session_root"]
    root = _root(job)
    orch = job.get("orchestrator_model") or "grok-4.5"
    sub = job.get("subagent_model") or orch
    session_date = job.get("session_date") or session_key.split("__", 1)[0]
    pin_ver = ""
    pin = job.get("pin")
    if isinstance(pin, dict):
        pin_ver = str(pin.get("label") or pin.get("version") or "")
    listing_block = (
        f"BEFORE classification: {LISTING_JUDGE} (yfinance / Yahoo MCP / web). "
        "Write the live listing into S/meta/run_manifest.json quote_symbol "
        "(JSON string; do not use TICKER as a guess if it does not quote). "
        "Do not rename the archive folder. Then run "
        f"python3 {root}/scripts/verify_listing.py --ticker {ticker} --date {session_key} . "
        "Non-zero exit → "
        f"{ABANDON_IF_UNREAL} before Phase 0 — do not invent a company.\n"
    )
    if resume:
        if stamp_s:
            stop = (
                "RESUME the named folder S only. Read registry/phase_status.json and resume_hint.\n"
                f"quote_symbol is already stamped as {stamp_s}. Do not re-run listing unless it is wrong.\n"
                "Do not re-run agents already complete.\n"
                "Do not browse other session_keys. Do not scaffold. Do not verify_ticker.\n"
            )
        else:
            stop = (
                "RESUME the named folder S only. Read registry/phase_status.json and resume_hint.\n"
                "quote_symbol is NOT stamped yet. "
                + listing_block
                + "Then continue incomplete phases. Do not browse other session_keys. "
                "Do not scaffold. Do not verify_ticker.\n"
            )
    else:
        stop = (
            listing_block
            + "Then start orchestrator classification (sector_config + market_context + research_brief).\n"
            "phase_status.json is pending. Stop when finalize_session succeeds, or when you\n"
            "write registry/abandon.json.\n"
        )
    listing_line = (
        f"YAHOO_QUOTE_SYMBOL: {stamp_s} (stamped; inject this into specialists)\n"
        if stamp_s
        else (
            "YAHOO_QUOTE_SYMBOL: unset until you stamp run_manifest.quote_symbol and "
            f"{LISTING_VERIFY} succeeds.\n"
        )
    )
    pin_line = f"PIN: {pin_ver or 'live'}\n" if pin_ver else "PIN: live\n"
    return (
        "You are the Mode A research orchestrator for a UI-scheduled run.\n\n"
        f"{OPEN_PIN_LAW}. Open and follow, in this order, before Phase 0:\n"
        f"1. {root}/harness/orchestrator_runbook.md — read \"{UI_SCHEDULED_HEADING}\" FIRST\n"
        f"2. {root}/harness/RESEARCH_AGENTS.md (full law) — do NOT re-scaffold; Python already did existence check\n"
        f"3. {root}/harness/HARNESS_MAP.md\n"
        f"4. {root}/harness/agent_prompts.md (when spawning; slice per subagent — do not dump into children)\n\n"
        "This prompt is coordinates, not a substitute for those files.\n\n"
        "HARD RULES\n"
        f"- {ALREADY_SCAFFOLDED}. Do not run scripts/verify_ticker.py.\n"
        f"  {NO_RE_SCAFFOLD} (a same-day call {R2_WARNING}\n"
        "  and desync this job). "
        f"{NO_LIST_SIBLINGS}<TICKER>/ except S.\n"
        f"- {NO_CHECKOUT_HARNESS} to update this pin. Law and scripts are under ROOT.\n"
        "- Work only under S (absolute path below). Intra-session sharing is required.\n"
        "- Isolation: read S/registry/session_isolation.json and meta/run_manifest.json notes.\n"
        "  Do not open other session_keys for FV, MoS, thesis, handoffs, or\n"
        '  "is yesterday usable?"\n'
        "- Do not git commit.\n"
        "- Run pin scripts as python3 ROOT/scripts/<name>.py (ROOT below).\n"
        "- English only for registry keys, schemas, reports.\n"
        "- Do not write archive/outcomes or archive/research_jobs (ignore them).\n"
        "  Job control is Mode B's file.\n\n"
        f"{pin_line}"
        f"TICKER: {ticker}\n"
        f"{listing_line}"
        "The session folder and catalog ticker stay TICKER "
        "(do not rename the archive folder).\n"
        f"session_date: {session_date}\n"
        f"session_key: {session_key}\n"
        f"S: {session_root}\n"
        f"ROOT: {root}\n"
        f"orchestrator_model: {orch}   (already stamped in meta/run_manifest.json)\n"
        f"default_subagent_model: {sub}\n\n"
        f"{stop}"
    )

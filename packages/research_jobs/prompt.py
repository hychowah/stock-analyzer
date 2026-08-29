"""Short Mode A orchestrator map prompt (not a paste of RESEARCH_AGENTS.md)."""

from __future__ import annotations

from typing import Any

from packages.research_jobs.paths import UI_SCHEDULED_HEADING

# Frozen-string tokens tests assert these appear in the prompt.
ALREADY_SCAFFOLDED = "Session is ALREADY scaffolded"
NO_RE_SCAFFOLD = "Do not run scripts/scaffold_session.py"
NO_LIST_SIBLINGS = "Do not list archive/research/"
R2_WARNING = "WILL allocate __r2"
LISTING_JUDGE = "Confirm the Yahoo listing with tools"
LISTING_VERIFY = "scripts/verify_listing.py"
ABANDON_IF_UNREAL = "If TICKER is not a real market issuer, write registry/abandon.json and STOP"


def build_prompt(job: dict[str, Any], *, resume: bool = False) -> str:
    ticker = job["ticker"]
    stamp = job.get("quote_symbol")
    stamp_s = str(stamp).strip().upper() if stamp else ""
    session_key = job["session_key"]
    session_root = job["session_root"]
    project_root = job["project_root"]
    orch = job.get("orchestrator_model") or "grok-4.5"
    sub = job.get("subagent_model") or orch
    session_date = job.get("session_date") or session_key.split("__", 1)[0]
    listing_block = (
        f"BEFORE classification: {LISTING_JUDGE} (yfinance / Yahoo MCP / web). "
        "Write the live listing into S/meta/run_manifest.json quote_symbol "
        "(JSON string; do not use TICKER as a guess if it does not quote). "
        "Do not rename the archive folder. Then run "
        f"python3 {LISTING_VERIFY} --ticker {ticker} --date {session_key} . "
        "Non-zero exit → "
        f"{ABANDON_IF_UNREAL} before Phase 0 — do not invent a company.\n"
    )
    if resume:
        if stamp_s:
            stop = (
                "RESUME the named folder S only. Read registry/phase_status.json and resume_hint.\n"
                f"quote_symbol is already stamped as {stamp_s}. Do not re-run listing unless it is wrong.\n"
                "Do not re-run agents already complete (5b carve-out after 2.5 still applies).\n"
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
    return (
        "You are the Mode A research orchestrator for a UI-scheduled run.\n\n"
        "Open and follow, in this order, before Phase 0:\n"
        f"1. harness/orchestrator_runbook.md — read \"{UI_SCHEDULED_HEADING}\" FIRST\n"
        "2. harness/RESEARCH_AGENTS.md (full law) — do NOT re-scaffold; Python already did existence check\n"
        "3. harness/HARNESS_MAP.md\n"
        "4. harness/agent_prompts.md (when spawning; slice per subagent — do not dump into children)\n\n"
        "This prompt is a map, not a substitute for those files.\n\n"
        "HARD RULES\n"
        f"- {ALREADY_SCAFFOLDED}. Do not run scripts/verify_ticker.py.\n"
        f"  {NO_RE_SCAFFOLD} (a same-day call {R2_WARNING}\n"
        "  and desync this job). "
        f"{NO_LIST_SIBLINGS}<TICKER>/ except S.\n"
        "- Work only under S (absolute path below). Intra-session sharing is required.\n"
        "- Isolation: read S/registry/session_isolation.json and meta/run_manifest.json notes.\n"
        "  Do not open other session_keys for FV, MoS, thesis, handoffs, or\n"
        '  "is yesterday usable?"\n'
        "- Do not git commit.\n"
        "- Agent 5 is the single writer of valuation / decision.json (including 5b reopen\n"
        "  after Phase 2.5 — lead, do not spawn subagent 5 in 2_5).\n"
        "- Specialists MUST be spawn_subagent + scripts/record_spawn.py. Spawn failure →\n"
        "  scripts/abandon_session.py then STOP. Never write specialist artifacts as the lead.\n"
        "- After research_brief, run scripts/bind_library.py before Agent 2b.\n"
        "  Read harness/library.md (you and 2b only).\n"
        "- Preflight before phases 1_parallel / 2_parallel / 2_5 / 4_parallel / 5.\n"
        "- Before Phase 2: freeze data/price_snapshot.json (price-only; no FV).\n"
        "- After audit PASS or explicit README waivers: python3 scripts/check_session.py\n"
        "  --ticker T --date <session_key> --full then\n"
        "  python3 scripts/finalize_session.py --ticker T --date <session_key>\n"
        "  (session_key, including __r2 / slug — not bare date if they differ).\n"
        "- MCP/tools may fail. RESEARCH_AGENTS.md §4: log, fallback, widen range.\n"
        "  Do not invent a company or numbers.\n"
        "- English only for registry keys, schemas, reports.\n"
        "- Do not write archive/outcomes or archive/research_jobs (ignore them).\n"
        "  Job control is Mode B's file.\n\n"
        f"TICKER: {ticker}\n"
        f"{listing_line}"
        "The session folder and catalog ticker stay TICKER "
        "(do not rename the archive folder).\n"
        f"session_date: {session_date}\n"
        f"session_key: {session_key}\n"
        f"S: {session_root}\n"
        f"ROOT: {project_root}\n"
        f"orchestrator_model: {orch}   (already stamped in meta/run_manifest.json)\n"
        f"default_subagent_model: {sub}\n\n"
        f"{stop}"
    )

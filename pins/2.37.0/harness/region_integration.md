# Region / market-context integration — decision record

**Status:** accepted and implemented in the harness (v2 addendum)  
**Date:** 2026-08-03  
**Scope:** how region-specific analysis (local rates / cost of capital, accounting regimes, ownership & control such as family / SOE / VIE) enters the research graph.

## Multi-perspective inputs

Four independent design perspectives were run (plan agents). Verbatim summaries live with the implementing session evidence; abstracts:

| ID | Perspective | Core advice |
|---|---|---|
| P1 | Minimal hooks-only | Optional intensity overlay on existing agents; no new files/agents; soft checks only |
| P2 | Module-plus-hooks (sector analog) | `market_context.json` + advisory `region_*.md` + valuation `market_context_hooks`; **no Agent 2f** |
| P3 | Extra-agent heavy | Gated Agent **2f** as dedicated CoC/ownership producer for non-US |
| P4 | Keep-harness-thin critic | Reject always-on agents, region module matrix, hardcoded Rf/ERP/family discounts; force justified dials + use-or-reject hooks |

## Decision (chosen shape)

**Ship P2 as the primary shape, constrained by P4 and intensity gating from P1.**

1. **Orchestrator** (same phase as sector classification) writes `registry/market_context.json` once per new session.
2. **Advisory modules** `region_us.md`, `region_hk_china.md`, `region_generic.md` — methodology checklists only; **numbers are reference ranges, never mandates** (same rule as sector modules).
3. **Valuation** must read market context + named region module and log `market_context_hooks[]` (use / reject / noted_only), mirroring `filing_deep_dive_hooks`.
4. **Intensity gate** `low | medium | high`:
   - **low** (typical US widely-held, US GAAP, USD model): one `noted_only` hook is enough; no invented country haircuts; no mandatory regional stress.
   - **medium / high**: deeper 2e ownership/accounting work; CoC build-up must address local Rf / ERP framing / FX; ≥1 region-relevant stress when high (and expected when medium).
5. **No new always-on agent.** No Phase 0 region swarm. **No Agent 2f in this cut.**
6. **No hardcoded** regional WACC, country ERP tables, or family-control discounts in code or schemas. Decided dials live only as `{value, rationale, basis}` in valuation assumptions.

## Accept / reject by recommendation

| Recommendation | Verdict | Why |
|---|---|---|
| Separate `market_context.json` + light schema | **Accept** | Auditable, sector-analog, cleaner than stuffing free-form into README only |
| Advisory `region_*.md` (us + hk_china + generic) | **Accept (thin set)** | High-value HK/China depth without a full country matrix; generic covers `other` |
| Valuation `market_context_hooks` | **Accept** | Same proven pattern as deep-dive hooks; silence becomes visible |
| Intensity no-op for simple US names | **Accept** | Keeps US mega-caps cheap; satisfies P1/P4 load goals |
| Prompt hooks on 2b / 2e / 5 / 2.5 / 7 / 11 / 13 | **Accept** | Region must be consumed, not only declared |
| Always-on region agent / Phase 0 region swarm | **Reject** | Latency + audit surface; violates thin-harness principle |
| Ship Agent 2f now | **Reject (defer)** | 2e already owns related-party/dual-class; valuation owns CoC judgment. Revisit **only if** Phase 5 audits show systematic VIE/SOE/local-Rf misses on `intensity=high` sessions |
| Hardcoded Rf / CRP / family % tables | **Reject** | Violates AGENTS.md §1 (no hardcoded formulas/multiples/probabilities) |
| Make `market_context.json` required in `check_session` for all sessions | **Reject** | Would false-FAIL legacy US sessions; absent → **SKIPPED** |
| Closed ontology of every country as `primary_region` enum growth forever | **Reject for now** | Start with `us \| hk_china \| korea \| japan \| eu_uk \| other`; extend when needed |

## Integration map (writers → consumers)

```text
Orchestrator
  ├─ registry/sector_config.json          (existing)
  └─ registry/market_context.json         (NEW)
        module_file → region_*.md         (advisory)

Phase 0  ← read market_context (macro / ownership / local rates emphasis when intensity ≠ low)
2b       ← filing source regime (EDGAR vs local)
2e       ← ownership.complexity med/high → deeper related_party / control / accounting notes
Agent 5  ← MUST log market_context_hooks; CoC dials justified; no module-default discounts without use/reject
Phase 2.5 ← ≥1 regional/governance/FX scenario when intensity = high (expected when medium)
Agent 7  ← Market & institutional context subsection (one paragraph no-op OK when intensity = low)
Agent 11 ← region + intensity one-liner
Agent 13 ← hooks present when market_context exists; no silent regional haircuts
```

## Machine check policy

- `registry/market_context.json` is **not** in the always-required CORE/FULL file lists.
- When the file is **absent**: `check_session` records **SKIPPED** (legacy / pre-cutover sessions).
- When the file is **present**: schema + required keys + non-empty rationale; if `data/valuation_model.json` also exists, require non-empty `market_context_hooks`.
- Never validate Rf magnitudes or enforce family-discount enums in machine checks (audit owns substance).

## Non-goals (this change)

- Full live ticker research as proof.
- Exhaustive country modules.
- Hardcoded valuation constants.
- Rewriting the Phase 0–5 dependency graph beyond the hooks above.

## Future optional Agent 2f (not shipped)

If audits document repeated gaps on high-intensity non-US names, add **gated** `2f_market_institutional` parallel to 2d/2e that *deepens* (does not replace) `market_context.json` with snapshotted local CoC series. Gate must remain off for simple US widely-held names.

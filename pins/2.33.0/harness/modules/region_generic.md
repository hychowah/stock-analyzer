# Region module: Generic / other markets (advisory)

**Module file:** `region_generic.md`  
**Use when:** `primary_region=other`, or when a specialized module (e.g. `region_hk_china.md`) does not yet exist for the listing (Korea, Japan, EU/UK may use this until dedicated modules ship — or a future `region_korea.md` etc.).

**No mandated numbers.** Same justification contract as sector modules.

## Required judgments (orchestrator + valuation)

1. **Listing & filings** — exchange, primary filing source, forms expected; never force EDGAR language if the annual is local.
2. **Reporting currency vs model currency** — state match or conversion policy.
3. **Accounting basis** — IFRS / local GAAP / mixed; one sentence on peer-comp traps.
4. **Cost of capital stack** — local Rf instrument name, ERP framing, whether a country overlay is on; script intermediates.
5. **Ownership** — widely held vs family / state / dual-class / pyramid; set `ownership.complexity` so 2e knows depth.
6. **Intensity** — if control is concentrated or filings are non-English/thin, prefer `medium` or `high` and **widen** range when data quality is degraded.

## Stress seeds

At least consider: local policy/rate shock, FX, and one governance/liquidity scenario when intensity ≥ medium.

## Explicit forbid

- Inventing a "standard EM discount"
- Copying US 10Y + US ERP onto non-USD cash flows without rationale
- Skipping `market_context_hooks` because the region felt "standard"

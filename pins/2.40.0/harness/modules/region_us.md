# Region module: United States (advisory)

**Module file:** `region_us.md`  
**Typical intensity:** `low` for widely held US-listed, US GAAP, USD cash-flow models. Raise intensity when dual-class control, material non-US ops with convertibility risk, or ADR of a non-US parent dominates economics.

This file is **advisory methodology** (same contract as sector modules). It contains **no mandated WACC, ERP, multiples, or control discounts**. Every decided dial must appear in `valuation_model.json` as `{value, rationale, basis}`.

## Detection signals

- Primary listing NYSE/Nasdaq; filings 10-K / 10-Q / 8-K on EDGAR
- Reporting currency USD; accounting US GAAP
- Regional benchmark often SPY/S&P 500 (orchestrator declares the actual series)

## Cost of capital (checklist, not formulas)

- Default path: USD risk-free + equity risk premium framing appropriate to the **cash-flow currency** (usually USD)
- Script realized beta / other intermediates in `data/compute/` when used
- Country-risk overlay is usually **off** for pure domestic large-caps; if set, justify why (not "because module said so")
- Dual-class / founder control is a **governance** dial, not an automatic country premium

## Accounting

- US GAAP is the peer baseline for most US comps
- Watch non-GAAP adjustments, SBC, leases (ASC 842), and segment vs consolidated definitions — still via 2e footnotes

## Ownership & control

- `widely_held` is common; still extract dual-class / related-party when present (`related_party_dual_class`)
- Intensity stays **low** unless control structure is material to claim on cash or dilution

## Stress seeds (optional when intensity low)

- Macro rate shock is usually enough; do **not** invent "US institutional" scenarios for theater

## No-op path for valuation

When `intensity=low`, Agent 5 may log a single `market_context_hooks` entry with `action: noted_only` stating standard US liquid listing, US GAAP, no country-risk or control overlay — then proceed with sector module as usual.

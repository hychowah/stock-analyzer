# Rationale quality exemplars

Purpose: teach substantive `{value, rationale, basis}` — not empty schema compliance.  
Used by: Agents 4, 5, 2e, 12, 13.  
**ILLUSTRATIVE — not real filing numbers.**

---

## Pair 1 — Discount rate / WACC assumption

### Context (shared)

Valuation agent sets WACC for a large-cap US tech name. Beta was scripted at 1.15 from weekly 5y returns vs SPY; 10y Treasury snapshot 4.2%; ERP judgment 4.5%.

### BAD

```json
{
  "wacc": {
    "value": 0.095,
    "rationale": "Industry standard WACC for tech.",
    "basis": "common practice"
  }
}
```

**Why bad:** Restates a label (“industry standard”) without linking to scripted intermediates, capital structure, or currency. Auditor cannot verify or challenge the number. Schema-valid, judgment-empty.

### GOOD

```json
{
  "wacc": {
    "value": 0.095,
    "rationale": "Blended CoE 10.4% (Rf 4.2% + 1.15 beta × 4.5% ERP + 0% size) with after-tax cost of debt 3.8% at 12% debt weight yields ~9.5% WACC. No country add-on: market_context intensity low / US GAAP USD model. Slightly above peer median ~9.0% to reflect higher capex/execution risk in the explicit forecast.",
    "basis": "data/compute/valuation.py beta_blend; price_snapshot Rf; assumptions.erp; capital structure from sp_financials FY last; market_context.intensity=low"
  }
}
```

**Why good:** States build-up, cites scripted intermediate, explains deviations, ties to market_context. A reader can recompute or disagree with a specific step.

---

## Pair 2 — Technical entry level

### Context (shared)

Technical agent (price-only) sets entry after a pullback scenario. ATR14 = 8.2; last close 180; support cluster 168–172.

### BAD

```json
{
  "entry": {
    "value": 170,
    "rationale": "Looks like a good buy zone.",
    "basis": "chart"
  }
}
```

**Why bad:** No link to computed levels, ATR, or the scenario the entry is meant to express. “Good buy zone” is not auditable.

### GOOD

```json
{
  "entry": {
    "value": 170.0,
    "rationale": "Highest-probability near-term path is a retest of the 20d swing support band (168–172) after RSI recovered from 32. Entry at 170 sits mid-band, ~1.2× ATR below last close, consistent with the pullback scenario rather than chasing the 180 close. Stop goes below band (see stop).",
    "basis": "data/compute/technical_indicators.py support_levels; ATR14=8.2; scenario pullback_to_support in technical.json"
  }
}
```

**Why good:** Coherent with stated scenario, cites compute outputs, explains placement inside the band.

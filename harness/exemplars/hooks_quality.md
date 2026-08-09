# Hooks quality exemplars

Purpose: teach real consumption of `filing_deep_dive` and `market_context` via hooks — not checkbox theater.  
Used by: Agent 5 (write), Agent 13 (grade).  
**ILLUSTRATIVE — not real filings.**

---

## Pair 1 — Filing deep dive → assumption

### Context (shared)

Deep dive extracted unrecognized SBC ~$2.1B and diluted share path; scorecard hit-rate on opex guide was mixed. Valuation must log `filing_deep_dive_hooks`.

### BAD

```json
{
  "filing_deep_dive_hooks": [
    {
      "from": "footnotes.sbc_unrecognized",
      "action": "noted_only",
      "reason": "Noted SBC."
    },
    {
      "from": "management_scorecard.credibility_summary",
      "action": "noted_only",
      "reason": "Acknowledged."
    }
  ]
}
```

**Why bad:** Material dilution and credibility findings got `noted_only` with empty analysis. Hook array is non-empty for schema, but nothing moved assumptions or explained rejection. Documentation theater.

### GOOD

```json
{
  "filing_deep_dive_hooks": [
    {
      "from": "footnotes.sbc_unrecognized",
      "action": "used_as:sbc_pct_path",
      "old": "SBC 8% of revenue flat",
      "new": "SBC 10.5% Y1 declining to 7% Y5; share count path uses diluted SO + 60% of unrecognized RSUs",
      "reason": "Unrecognized SBC ~$2.1B and elevated SBC% in latest year make flat 8% understate dilution; aligns with growth-module critical intensity."
    },
    {
      "from": "management_scorecard.credibility_summary",
      "action": "used_as:scenario_probabilities",
      "old": "bear/base/bull 0.25/0.50/0.25",
      "new": "0.30/0.45/0.25",
      "reason": "Quantitative opex/margin promises graded mixed (miss on FY opex ceiling); slightly higher bear weight. Does not auto-set WACC."
    },
    {
      "from": "footnotes.contingencies_legal",
      "action": "noted_only",
      "reason": "Contingency note has no quantifiable reserve change; stress scenario S3 carries legal/reg narrative without inventing a dollar haircut."
    }
  ]
}
```

**Why good:** Material items either change a named assumption (old→new) or explicitly reject with a reason that points to how risk is handled. Silent skips avoided.

---

## Pair 2 — Market context intensity

### Context (shared)

`market_context.intensity` is `high` (HK list, PRC ops, parent control). Region module is advisory only.

### BAD

```json
{
  "market_context_hooks": [
    {
      "from": "intensity",
      "action": "noted_only",
      "reason": "Noted high intensity."
    }
  ]
}
```

**Why bad:** Intensity high requires real CoC/governance treatment (or explicit reject). A single empty `noted_only` is only valid for intensity **low**. Pastes no dials and invents no posture — fails the intensity gate.

### GOOD

```json
{
  "market_context_hooks": [
    {
      "from": "cost_of_capital_flags.use_local_rf",
      "action": "used_as:risk_free_rate",
      "old": "US 10Y 4.2%",
      "new": "Local sovereign proxy 2.1% in HKD model; cash flows CNY translated at explicit FX policy",
      "reason": "Listing/price in HKD; avoid USD Rf on non-USD discounting. Region module range used as reference only; value chosen from local curve snapshot in compute script."
    },
    {
      "from": "ownership.control_type",
      "action": "used_as:ownership_governance_adjustment",
      "old": "0",
      "new": "+100bp CoE governance add-on (not a fixed module family discount)",
      "reason": "Parent control + RPT footnotes material; add-on sized from peer dispersion and stress seeds, disclosed to avoid double-count with country ERP."
    },
    {
      "from": "module_file",
      "action": "rejected",
      "reason": "Rejected pasting region_hk_china.md default country premium table as mandated ERP; built ERP from judgment + hooks above instead."
    }
  ]
}
```

**Why good:** Addresses local CoC and ownership with use/reject; refuses silent module hardcoding; consistent with intensity high.

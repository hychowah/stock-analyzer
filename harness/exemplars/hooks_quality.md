# Hooks quality exemplars

Purpose: teach real consumption of `filing_deep_dive` and `market_context` via hooks — not checkbox theater.  
Used by: Agent 5 (write), Agent 13 (grade).  
**ILLUSTRATIVE — not real filings.**

---

## Pair 0 — Operating-path brief (1d)

### BAD

```json
{
  "operating_path_hooks": [
    {"from": "operating_path_brief", "action": "noted_only", "reason": "Noted growth and leverage."}
  ]
}
```

**Why bad:** The brief exists so Agent 5 cannot invent a fade or OM path. A single `noted_only` is checkbox theater. Machine FAIL if all hooks are `noted_only`.

### BAD — destock-in-base while Street FY+1 is usable (harness ≥ 2.18 FAIL)

```json
{
  "operating_path_hooks": [
    {
      "from": "registry/operating_path_brief.json#conflicts.fade_vs_flatten",
      "action": "used_as:base",
      "applies_in": "base",
      "old": "Y1 Street duration; destock analog lives in bear only",
      "new": "Y1 destock/quality-reset on the base path (run-rate ex destock); duration only in bull",
      "reason": "Y1 destock while Street FY+1 is usable."
    }
  ]
}
```

**Why bad:** Street FY+1 is the required Y1 start. Putting a destock analog in **base** while Street is usable is the Session B failure. Wave 3/4 on ≥ 2.18 FAIL destock-in-base. (On 2.12–2.17 this pairing was the GOOD example: destock default was base until cash/channel proved demand. That wording belongs in this caption, not in a live `reason` field.)

### GOOD

```json
{
  "operating_path_hooks": [
    {
      "from": "registry/operating_path_brief.json#conflicts.fade_vs_flatten",
      "action": "used_as:bear_only",
      "applies_in": "bear_only",
      "old": "Y1 destock/quality-reset on the base path",
      "new": "Y1 Street duration; destock analog lives in bear only",
      "reason": "Street FY+1 is the Y1 baseline; destock analog is a bear seed. Conflict not averaged."
    },
    {
      "from": "registry/operating_path_brief.json#rejected_shapes.om_28_35",
      "action": "rejected",
      "reason": "GM-minus-opex identity and incremental OM on session actuals do not support a 28–35% OM path."
    }
  ],
  "street_hooks": [
    {
      "from": "street_estimates.years[+1y].revenue",
      "action": "used_as:fy1_baseline",
      "reason": "Street FY+1 revenue is base Y1; destock analog is bear-only."
    }
  ]
}
```

**Why good:** Street is Y1 (`used_as:fy1_baseline`). Destock analog is `applies_in: bear_only`. Material OM recommendation is `rejected`. Illustrative numbers are style only. Destock-in-base remains legal only when Street is `street_unusable` **and** analog matches this print.

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
      "reason": "Quantitative opex/margin promises graded mixed (miss on FY opex ceiling); +5pp bear vs neutral 25/50/25. Counterfactual: if opex hit-rate were clean, keep 0.25/0.50/0.25. Does not auto-set WACC. (Template-shaped masses OK only with this kind of company-specific shift + counterfactual.)"
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

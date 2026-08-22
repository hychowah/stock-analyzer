# Valuation decision-quality exemplars

Purpose: teach **decision-grade** MoS units, reverse-engineering / `priced_for_perfection`, scenario weights, and ERP selection — not schema theater.  
Used by: Agent 5 (write), Agent 13 (grade).  
**ILLUSTRATIVE — do not copy numbers into a live session.**

Also read: `rationale_quality.md`, `hooks_quality.md`.

---

## Pair 1 — Margin of safety units

### Context (shared)

Price 100; base FV 140 → MoS fraction = `1 - 100/140 = 0.2857…` ≈ **0.286**; percent points = **28.6**.

### BAD

```json
{
  "fair_value": {
    "base": 140,
    "bear": 90,
    "bull": 200,
    "margin_of_safety_pct": 0.286
  }
}
```

**Why bad:** Field name says `*_pct` but value is a 0–1 fraction. Cross-session catalogs mis-rank vs names that store `28.6`.

### GOOD

```json
{
  "fair_value": {
    "base": 140,
    "bear": 90,
    "bull": 200,
    "margin_of_safety": 0.286,
    "margin_of_safety_pct": 28.6
  }
}
```

**Why good:** Both fields; pct = 100 × fraction; denominator is **base** FV; price vintage stated elsewhere (price_snapshot).

---

## Pair 2 — `priced_for_perfection` surface vs mechanical

### Context (shared)

Base FV 80; bull 120; price 110. Reverse-eng must name dials.

### BAD

```json
{
  "reverse_engineering": {
    "priced_for_perfection": false,
    "rationale": "probability_weighted 85 < price*1.02 so not perfection."
  }
}
```

**Why bad:** Boolean from a mechanical PW-threshold. No implied growth/margin/WACC/multiple. Decision-useless.

### GOOD

```json
{
  "reverse_engineering": {
    "implied": {
      "terminal_om": "matches ~bull Y10 OM 22% on base WACC",
      "or_wacc": "base path needs WACC ~7.1% vs model 9.0%"
    },
    "priced_for_perfection": true,
    "rationale": "At 110 vs base 80, matching price on the base volume path requires terminal OM at/above the bull terminal (22%) or WACC ~200bp below base — perfection-class on at least one primary dial vs management mid-cycle. Not a price>base automatic flag."
  }
}
```

**Why good:** Names dials and levels; TRUE only because price needs bull-class or multi-dial stretch; forbidden threshold-only logic.

---

## Pair 3 — Scenario weights: template without vs with counterfactual

### Context (shared)

Scorecard mixed; binary pipeline AdCom risk elevated.

### BAD

```json
{
  "fair_value": {
    "scenario_probabilities": { "bear": 0.30, "base": 0.45, "bull": 0.25 }
  },
  "assumptions": {
    "scenario_probabilities": {
      "value": { "bear": 0.30, "base": 0.45, "bull": 0.25 },
      "rationale": "Standard bear/base/bull weights.",
      "basis": "house default"
    }
  }
}
```

**Why bad:** Exact template mass with no company-specific sizing or counterfactual. Audit theater.

### GOOD

```json
{
  "fair_value": {
    "probability_method": "Binary AdCom fail ~35% historical for class + mixed scorecard → bear 0.34; residual split base/bull.",
    "scenario_probabilities": {
      "bear": {
        "value": 0.34,
        "rationale": "AdCom 3–9 against prior similar asset; binary fail path dominates left tail.",
        "basis": "registry/latest_quarter.json + filing_deep_dive scorecard"
      },
      "base": {
        "value": 0.41,
        "rationale": "Partial approval / delayed label still allows royalty path at reduced peak.",
        "basis": "strategy_arc dual-engine"
      },
      "bull": {
        "value": 0.25,
        "rationale": "Full clean label + uptake above base; counterfactual if AdCom were 8–4 for, bull would be ~0.35 and bear ~0.22.",
        "basis": "pipeline analog base rates"
      }
    }
  }
}
```

**Why good:** Masses can still be near a common triple **if** numeric argument + counterfactual exist. `probability_method` one-liner. risk_bridge mirror later uses bare floats only.

---

## Pair 4 — ERP selection (anti-folklore)

### BAD

```json
{
  "erp": {
    "value": 0.05,
    "rationale": "Mid of the standard 4.5–5.5% band.",
    "basis": "industry standard"
  }
}
```

**Why bad:** No method choice; no rejected alternative; soft hardcode of 5%.

### GOOD

```json
{
  "erp": {
    "value": 0.05,
    "rationale": "Use long-run historical US ERP ~5.0% for USD FCFF. Rejected implied ERP from current market (~4.0%) because the name is mid-cap with idiosyncratic binary risk not captured in the market-wide implied premium; rejected country-table paste as primary because cash flows are USD-reported.",
    "basis": "data/market_inputs_snapshot.json; rejected Damodaran country ERP as primary for USD model"
  }
}
```

**Why good:** Chosen method + rejected competitor + why unfit for **this** currency/risk profile. Value still free judgment.

---

## Pair 5 — Rationale ↔ path congruence

### BAD

```json
{
  "op_margin_path": {
    "value": [0.152, 0.155, 0.160],
    "rationale": "Anchored to company guide of ~16.5% operating margin.",
    "basis": "EX-99.1"
  }
}
```

**Why bad:** Prose cites 16.5%; path starts 15.2%. Reader cannot rehydrate.

### GOOD

```json
{
  "op_margin_path": {
    "value": [0.152, 0.155, 0.160],
    "rationale": "Guide implies ~16.5% exit; model starts 15.2% (130bp haircut for brand reinvestment and channel mix) then fades toward 16.0% by Y3.",
    "basis": "EX-99.1 guide; haircut logged in overrides_applied"
  }
}
```

**Why good:** Explicit old→new haircut; first path value matches the modeled level. This pair is **congruence** (prose matches the number). It is **not** permission to exile a printed **revenue** guide from **base** without putting the haircut in bear/range — see Pair 6.

---

## Pair 6 — Independent FY+1 vs Street calibration (do not copy consensus)

Next-year Street revenue is a **reference** (usually reasonably accurate). The agent must **predict** it from company evidence, not paste it.

### BAD — copy Street

```json
{
  "assumptions": {
    "fy_plus_1_revenue": {
      "value": 173.6,
      "rationale": "Yahoo consensus FY+1 revenue.",
      "basis": "registry/street_estimates.json"
    }
  }
}
```

**Why bad:** Consensus is not a model. Skill is building the stack (guide + segments + run-rate) so you *land near* Street.

### BAD — silent haircut of company guide into base

```json
{
  "street_bind": {
    "guide": 100,
    "street": 174,
    "base": 123.5,
    "delta_pct": -0.29,
    "independent_construction": { "rationale": "Transcripts degraded; use $72B AI in base." }
  }
}
```

**Why bad:** Printed company AI/revenue outlook was dropped from **base** because a call transcript was HTML. That is a skill miss. Haircut belongs in **bear**, or the independent stack is rebuilt.

### GOOD — independent stack, then calibrate

```json
{
  "street_bind": {
    "guide": 154.0,
    "street": 173.6,
    "base": 158.0,
    "delta_pct": -0.09,
    "independent_construction": {
      "rationale": "FY+1 base = AI company floor 100 + software run-rate 36 + non-AI 18 from 8-K segments and Q3 sequential; not Street mean."
    },
    "response": "keep_independent_vs_street"
  },
  "street_hooks": [
    {
      "from": "street_estimates.years[+1y].revenue",
      "action": "used_as:calibration_check",
      "reason": "Independent stack 158 vs Street 173.6 (delta -9%) — inside 20%; no path copy."
    }
  ]
}
```

**Why good:** Path from company evidence; Street used only after; no paste. If |delta| were >20%, GOOD is `response: reopen_path` and a rebuilt stack, not `base = street`.

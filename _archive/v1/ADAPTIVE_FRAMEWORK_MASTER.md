# Adaptive Multi-Sector Stock Analysis Framework
## Master Synthesis Document

> **Purpose**: Automatically detect company type and apply the correct valuation methodology, metrics, risk factors, and stress tests.
> **Base Framework**: FCF-based DCF, ROIC, P/E, Operating Leverage, SBC Analysis
> **Sectors Covered**: Banking, Insurance, Growth/Negative FCF, REITs, Utilities, Cyclicals
> **Coverage**: 6 sector modules | 300+ metrics | 24 stress scenarios | 60+ quality indicators

---

## PART 1: SECTOR DETECTION & ROUTING ENGINE

### 1.1 Primary Classification Decision Tree

```
COMPANY INPUT (Ticker / Financial Data)
│
├─> Step 1: Industry Code Check
│   ├─ GICS 4010xx / SIC 60xx / NAICS 5221 → BANKING MODULE
│   ├─ GICS 4030xx / SIC 63xx / NAICS 5241 → INSURANCE MODULE
│   ├─ GICS 6010xx / SIC 6798 → REIT MODULE
│   ├─ GICS 5510xx / SIC 49xx / NAICS 2211 → UTILITY MODULE
│   └─ Continue to Step 2 if no match
│
├─> Step 2: Financial Signature Check
│   ├─ Total Loans / Total Assets > 30% AND Deposits / Liabilities > 20%
│   │   → BANKING MODULE (even if code mismatch)
│   ├─ FCF Margin < 0% AND Revenue Growth > 20% AND SBC/Revenue > 5%
│   │   → GROWTH MODULE (even if in "mature" sector)
│   ├─ Depreciation > 30% of Revenue AND Dividend Yield > 3%
│   │   → REIT MODULE
│   ├─ PP&E > 60% of Assets AND Debt/Capital > 50% AND "rate base" in filings
│   │   → UTILITY MODULE
│   ├─ EBIT Margin Range (10yr) > 15pp OR Revenue Volatility > 2x market
│   │   → CYCLICAL MODULE
│   ├─ "Premiums earned" on IS AND "Loss reserves" on BS
│   │   → INSURANCE MODULE
│   └─ Continue to Step 3 if no match
│
├─> Step 3: Standard Framework (Default)
│   └─ Apply base framework with minor sector adjustments
│
└─> Step 4: Confidence Scoring
    └─ If detection confidence < 70%, flag for manual review
```

### 1.2 Detection Confidence Matrix

| Sector | Primary Signal | Confidence | Secondary Confirmation |
|--------|---------------|------------|----------------------|
| Banking | GICS 4010xx | 99% | Loans/Assets > 30% |
| Insurance | SIC 63xx | 95% | Premiums earned line item |
| Growth/Neg FCF | FCF < 0 + Growth > 20% | 90% | SBC/Revenue > 5% |
| REIT | SIC 6798 or "REIT" in name | 99% | Depreciation > 30% rev |
| Utility | GICS 5510xx | 98% | PP&E > 60%, debt/cap > 50% |
| Cyclical | EBIT margin range > 15pp | 85% | Commodity price linkage |

### 1.3 Edge Cases & Hybrid Classification

| Edge Case | Primary Module | Secondary Adjustments |
|-----------|---------------|----------------------|
| Fintech lender | Banking | Add growth module SBC analysis |
| Berkshire Hathaway | Insurance (P&C) | Add conglomerate SOTP |
| mREIT | REIT (but separate) | Use mREIT sub-module, not equity REIT |
| Renewable developer | Utility | Add growth module path-to-profitability |
| Biotech pre-revenue | Growth | Add binary outcome modeling |
| Shipping company | Cyclical | Add asset-based NAV backup |
| Broker-dealer (non-bank) | Banking (sub-module) | Use asset manager model |
| REOC (non-REIT real estate) | REIT (blended) | Add corporate DCF overlay |

---

## PART 2: UNIFIED METRIC SUBSTITUTION MATRIX

### 2.1 Core Valuation Model Substitutions

| Standard Component | Banking | Insurance | Growth/Neg FCF | REITs | Utilities | Cyclicals |
|---|---|---|---|---|---|---|
| **Primary Valuation Model** | Excess Return Model | EV / Float / MCEV | Extended DCF (path to profitability) | NAV (cap rate) | Rate-Base DCF | TTC Earnings / NAV |
| **Secondary Model** | P/B-ROE Regression | DDM / P/B-ROE | EV/Revenue Comps | FFO/AFFO Multiple | DDM | Replacement Cost |
| **Tertiary Model** | DDM | Reserve-adjusted BV | Unit Economics (LTV/CAC) | DDM | Replacement Cost | Commodity x Reserves |
| **Terminal Value Basis** | Excess returns in perpetuity | Float growth / Reserve runoff | Steady-state FCF (post-profitability) | Cap rate on terminal NOI | Rate base x allowed ROE | Zero-growth (g=0) |

### 2.2 Key Metric Substitutions

| Standard Metric | Banking | Insurance | Growth/Neg FCF | REITs | Utilities | Cyclicals |
|---|---|---|---|---|---|---|
| **ROIC** | ROE / ROA / RAROC | ROE / ROEV | Burn Multiple / Unit Economics | FFO/AFFO yield | Earned ROE vs Allowed ROE | Cost curve position |
| **P/E** | P/B (primary) | P/B (P&C) / P/EV (Life) | EV/Revenue | P/FFO or P/AFFO | Dividend Yield | TTC EV/EBITDA |
| **FCF Yield** | Div Yield + Buyback Yield | Investment yield on float | Burn Multiple / Rule of 40 | FFO Yield | Dividend Yield | FCF breakeven price |
| **Revenue Growth** | NII growth + Fee growth | Premium growth / Float growth | ARR growth / NRR | Same-store NOI growth | Rate base CAGR | Volume growth (ex-price) |
| **Operating Leverage** | Financial leverage x NIM sensitivity | Float leverage / Expense ratio | Operating leverage (near breakeven) | Fixed cost / Lease spreads | Regulatory lag | Operating leverage (amplifies cycles) |
| **Gross Margin** | NIM | Combined ratio (inverse) | Gross margin (SaaS: >70%) | NOI margin | Allowed ROE spread | Cash cost margin |
| **SBC Analysis** | Comp/Revenue (low) | SBC/BV dilution | SBC/Revenue (CRITICAL: 10-30%) | SBC/FFO (low) | SBC/Dividend impact | SBC/Earnings (low) |
| **Moat Indicator** | Deposit franchise / Low-cost funding | Float duration / Pricing discipline | NRR / Switching costs | Location / Lease terms | Regulatory compact | Cost curve position |
| **Capital Structure** | CET1 / Tier 1 | Solvency II / RBC | Cash runway / Burn rate | LTV / Debt maturity | Debt/Total capital | Net debt/EBITDA |
| **Quality Score** | ROE consistency + Asset quality | CR stability + Reserve adequacy | NRR + Unit economics + Rule of 40 | Occupancy + WALT + Lease spreads | Regulatory lag + Reliability | Cost position + Balance sheet |

### 2.3 Risk Factor Substitution Matrix

| Standard Risk | Banking | Insurance | Growth/Neg FCF | REITs | Utilities | Cyclicals |
|---|---|---|---|---|---|---|
| Credit risk | Loan portfolio quality | Reserve adequacy | Funding runway | Tenant credit | Wildfire liability | Counterparty risk |
| Interest rate risk | NIM sensitivity / ALM | Duration mismatch / ALM | Not material (low debt) | Cap rate expansion | Financing cost + Bond-proxy | Not primary |
| Regulatory risk | Capital requirements / CCAR | Solvency II / IFRS 17 | Data privacy / Antitrust | Rent control / Zoning | Rate case denial | Environmental / Carbon |
| Liquidity risk | Deposit flight (SVB) | Catastrophe claims | Cash burn / Funding winter | Refinancing wall | N/A (regulated) | Inventory / Working capital |
| Competition risk | Fintech disruption | Pricing cycle (P&C) | Feature parity / Price war | New supply / Sublease | N/A (franchise) | Overcapacity |
| Operational risk | Cybersecurity | Cat modeling error | Execution / Churn | Property management | Grid reliability | Mine safety / Shutdowns |

### 2.4 Stress Test Scenario Selection Matrix

| Scenario | Banking | Insurance | Growth/Neg FCF | REITs | Utilities | Cyclicals |
|---|---|---|---|---|---|---|
| **Scenario 1** | Credit downturn (NPL +500bp) | Reserve deficiency (+8% adverse dev) | Funding winter (can't raise) | Cap rate expansion (+200bp) | Regulatory shock (ROE -200bp) | Commodity crash (-40%) |
| **Scenario 2** | Rate shock (parallel +300bp) | Cat super-year ($250B losses) | Growth deceleration (growth halves) | Occupancy shock (-10%) | Rate spike (+300bp) | Recession demand collapse |
| **Scenario 3** | Liquidity crisis (deposit flight) | Interest rate shock (+300bp) | Churn shock (NRR < 100%) | Refinancing crisis | $5B wildfire liability | China demand shock (-10%) |
| **Scenario 4** | Regulatory shock (CET1 +300bp) | Pandemic / Mass mortality | SBC cliff (cut 50%, talent leaves) | Rent decline (-10%) | Demand destruction | Overcapacity (new supply) |

---

## PART 3: SECTOR-SPECIFIC MODULE INDEX

| Module | File | Lines | Key Innovation | Primary Metric |
|--------|------|-------|---------------|----------------|
| **Banking** | `sector_banking.md` | 1,192 | Excess Return Model replaces DCF | ROE, CET1, NIM |
| **Insurance** | `sector_insurance.md` | 1,463 | EV/Float/MCEV replaces DCF | Combined Ratio, ROE, Float |
| **Growth/Neg FCF** | `sector_growth.md` | 1,396 | Extended DCF + EV/Revenue replaces FCF-DCF | ARR, NRR, Rule of 40, Burn Multiple |
| **REITs** | `sector_reit.md` | 1,207 | NAV + FFO/AFFO replaces DCF | Cap Rate, FFO/share, WALT |
| **Utilities** | `sector_utility.md` | 1,368 | Rate-Base DCF replaces FCF-DCF | Allowed ROE, Rate Base CAGR, Div Yield |
| **Cyclicals** | `sector_cyclical.md` | 1,800 | TTC Earnings + NAV replaces DCF | Cost curve position, FCF breakeven, Utilization |

**Total**: 8,426 lines of sector-specific analysis framework

---

## PART 4: UNIFIED REPORT STRUCTURE (SECTOR-ADAPTIVE)

The final report for any company follows this structure, with **sector-conditional sections**:

### Section 1: Executive Summary
- Sector classification and detection confidence
- Which modules were activated
- Key findings (2-3 bullets)

### Section 2: "Why Is It Cheap?" — Structural Discount Analysis
- Apply structural discount framework from base model
- ADD sector-specific discount factors (e.g., regulatory discount for utilities, cycle position for cyclicals)

### Section 3: Valuation Model (SECTOR-SPECIFIC)
- **[Banking]**: Excess Return Model output + P/B-ROE regression
- **[Insurance]**: EV/MCEV (Life) or Float valuation (P&C) or Combined Ratio analysis
- **[Growth]**: Extended DCF scenarios + EV/Revenue sanity check + Unit economics
- **[REIT]**: NAV + Premium/Discount + FFO/AFFO multiple
- **[Utility]**: Rate-Base DCF + DDM + Regulatory lag analysis
- **[Cyclical]**: TTC earnings + NAV at long-run commodity price + Cycle position

### Section 4: Operating Metrics Dashboard (SECTOR-SPECIFIC)
- Display the 10 most relevant metrics for the detected sector
- Benchmark against sector median
- Trend analysis (3-5 year history)

### Section 5: ROIC Analysis → SECTOR EQUIVALENT
- **[Banking]**: ROE trajectory + ROE vs Cost of Equity spread
- **[Insurance]**: ROE + Combined Ratio trend + Investment yield
- **[Growth]**: Unit economics (LTV/CAC) + Burn Multiple + Path to profitability
- **[REIT]**: FFO/AFFO yield + Cap rate + Same-store NOI growth
- **[Utility]**: Earned ROE vs Allowed ROE + Regulatory lag
- **[Cyclical]**: Cost curve position + FCF breakeven + Operating leverage

### Section 6: SBC / Dilution Analysis (SECTOR-SPECIFIC INTENSITY)
- **[Banking/Utility/Cyclical]**: Low intensity — flag if >3% of revenue
- **[Insurance]**: Low-medium — track BV dilution
- **[REIT]**: Low intensity — flag if meaningful
- **[Growth]**: **CRITICAL** — SBC often 15-30% of revenue, major valuation impact

### Section 7: Risk Factors (SECTOR-SPECIFIC)
- Top 5 risks for the detected sector
- Quantified impact on key valuation driver
- Probability assessment

### Section 8: Stress Testing
- Run 4 sector-appropriate stress scenarios
- Report: Implied price, survival probability, key vulnerabilities

### Section 9: Reverse Engineering
- Extract market-implied assumptions from current price
- Compare to historical capability and sector benchmarks
- Flag "priced for perfection" if implied > achievable

### Section 10: Peer Comparison
- Compare using sector-appropriate metrics
- Same-market primary, cross-market secondary (with adjustments)
- Highlight outliers and positioning

### Section 11: Honest Conclusion
- Q1: Why is it cheap? (sector-specific reasons)
- Q2: How much discount is permanent vs temporary?
- Q3: What is the adjusted fair value? (sector model output)
- Q4: What type of investment is this? (sector-specific classification)
- Q5: Final recommendation with sector-appropriate position sizing

---

## PART 5: SECTOR-SPECIFIC INVESTMENT CLASSIFICATION

The base framework's investment type classification is replaced with sector-aware versions:

### Banking Classification
| Type | Criteria | Example |
|------|----------|---------|
| High-quality bank | ROE > 12%, CET1 > 12%, NIM stable, Low NPL | JPMorgan |
| Value bank | P/B < 1.0x, ROE > 8%, fixable problems | Post-crisis recovery banks |
| Yield bank | High div yield (>5%), stable earnings, slow growth | Regional banks |
| Turnaround bank | ROE < 8%, management change, restructuring | Post-crisis European banks |
| Value trap bank | ROE < COE, rising NPLs, capital concerns | Zombie banks |

### Insurance Classification
| Type | Criteria | Example |
|------|----------|---------|
| Underwriting excellence | Combined Ratio < 95%, pricing discipline | Progressive, Berkshire |
| Float compounder | Low CR + High investment yield | Berkshire Hathaway |
| Life value | High VNB margin + Low lapse rate | AIA Group |
| Turnaround | Reserve strengthening + New management | AIG (post-crisis) |
| Value trap | Adverse reserve development + Low yields | Zombie life insurers |

### Growth Classification
| Type | Criteria | Example |
|------|----------|---------|
| Rule of 40 champion | >40 score + NRR > 120% | Snowflake, Datadog |
| Path to profitability | Gross margin > 70% + Operating leverage visible | CrowdStrike |
| Unit economics gem | LTV/CAC > 5 + Payback < 6 months | Best-in-class SaaS |
| Cash burn concern | Burn Multiple > 2 + Runway < 18 months | Many late-stage startups |
| SBC trap | SBC/Revenue > 20% + Declining NRR | Overvalued growth |

### REIT Classification
| Type | Criteria | Example |
|------|----------|---------|
| Premium REIT | Trading > NAV + Superior NOI growth | Industrial REITs (pre-2023) |
| Discount opportunity | Trading < NAV + Temporary issues | Office REITs (if recovery thesis) |
| Yield REIT | High div yield + Stable FFO | Net lease REITs (O, WPC) |
| Development REIT | High yield-on-cost pipeline + Strong sponsor | REITs with embedded development |
| Value trap | Structural decline + High leverage | Malls, some office |

### Utility Classification
| Type | Criteria | Example |
|------|----------|---------|
| Regulatory compounder | Rate base CAGR > 6% + Friendly jurisdiction | Southern Company |
| Yield play | Div yield > 4% + Stable regulatory environment | Utilities in friendly states |
| ESG transition | Coal retirement + Renewable buildout | NextEra Energy |
| Wildfire risk | California / High fire-risk state exposure | PG&E (bankruptcy risk) |
| Regulatory challenged | Difficult PUC + ROE compression risk | NY/CA utilities |

### Cyclical Classification
| Type | Criteria | Example |
|------|----------|---------|
| First quartile cost | AISC in bottom 25% of cost curve | BHP, Rio Tinto |
| Cycle trough | Trading below replacement cost + Strong BS | Any cyclical at bottom |
| Structural growth | Supply deficit + Long demand runway | Copper (electrification) |
| Balance sheet strength | Net cash or low leverage entering downturn | Best cyclicals |
| Value trap | High cost curve + Weak BS + Peak earnings | High-cost producers at peak |

---

## PART 6: IMPLEMENTATION CHECKLIST

### For Each New Analysis:

- [ ] Run sector detection algorithm (3-step classification)
- [ ] Confirm detection confidence > 70% (else flag for manual review)
- [ ] Load appropriate sector module
- [ ] Substitute standard metrics with sector-specific metrics
- [ ] Run sector-specific valuation model (primary + secondary)
- [ ] Calculate sector quality score
- [ ] Run 4 sector-appropriate stress tests
- [ ] Perform reverse engineering with sector metrics
- [ ] Compare to sector-appropriate peer group
- [ ] Generate sector-adapted report using unified structure

### Quality Gates:

- [ ] Valuation model output is sensible (no negative values for going concerns)
- [ ] Key metrics are within sector-normal ranges (flag outliers >2 std dev)
- [ ] Stress test results show survival probability > 50% for investment-grade ideas
- [ ] Reverse engineering flags any "priced for perfection" concerns
- [ ] Peer comparison uses correct metrics (not comparing banks on P/E!)

---

## APPENDIX: QUICK REFERENCE — WHAT TO USE WHEN

| If the company is... | Use this valuation model | Key metric | Ignore this |
|---|---|---|---|
| A bank | Excess Return Model | ROE, P/B, CET1 | FCF, P/E (alone) |
| An insurer | EV / Float / MCEV | Combined Ratio, ROE | FCF Yield |
| A pre-profitability SaaS | Extended DCF + EV/Revenue | ARR, NRR, Rule of 40 | P/E, FCF Yield |
| A REIT | NAV + FFO Multiple | Cap Rate, FFO/share | P/E, FCF |
| A utility | Rate-Base DCF + DDM | Allowed ROE, Div Yield | FCF, Revenue growth |
| A miner/oil company | TTC Earnings + NAV | AISC, Reserve life, FCF breakeven | P/E (point-in-time) |
| A mature tech company | Standard DCF (with SBC adj) | ROIC, FCF, SBC/Revenue | Revenue growth alone |
| A consumer staples co. | Standard DCF | ROIC, FCF, Volume growth | Nothing major |

---

*This master framework synthesizes 6 sector-specific modules into a unified adaptive analysis engine. Each sector module contains full details, formulas, worked examples, and implementation guidance. Refer to the individual sector files for deep-dive analysis on any specific sector.*

**Generated Files**:
1. `/workspace-stock-research/ADAPTIVE_FRAMEWORK_MASTER.md` (this file)
2. `/workspace-stock-research/sector_banking.md` — Banking & Financial Services
3. `/workspace-stock-research/sector_insurance.md` — Insurance Companies
4. `/workspace-stock-research/sector_growth.md` — Growth / Negative FCF Companies
5. `/workspace-stock-research/sector_reit.md` — REITs & Real Estate
6. `/workspace-stock-research/sector_utility.md` — Utilities & Infrastructure
7. `/workspace-stock-research/sector_cyclical.md` — Cyclical Industries

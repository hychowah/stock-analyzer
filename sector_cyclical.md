# Sector Module: Cyclical Industries — Adaptive Framework Design

## Executive Summary

Cyclical industries represent a unique analytical challenge: standard valuation frameworks fail because earnings are mean-reverting, peak valuations signal danger, and trough valuations signal opportunity. This module provides a comprehensive replacement framework for analyzing commodity producers, manufacturing cyclicals, shipping, and semiconductors. Every component is designed with cycle-awareness at its core.

**Core Principle:** For cyclicals, the cycle IS the investment thesis. A steel company at 3x P/E is expensive; at 30x P/E it may be cheap. The framework must invert standard intuition.

---

## 1. SECTOR DETECTION RULES

### 1.1 Cyclical Sub-Types and Identification Criteria

| Sub-Type | Cycle Length | Primary Drivers | Detection Rules |
|---|---|---|---|
| **Metals & Mining** (Cu, Fe, Al, Au, Li) | 5-10 years | Chinese fixed-asset investment, supply disruptions, ESG constraints | GICS 151040 (Metals & Mining), revenue correlated with commodity spot prices, COGS dominated by mining/processing costs |
| **Oil & Gas (E&P)** | 5-7 years | OPEC+ policy, shale supply, global demand, energy transition | GICS 101020 (Oil & Gas E&P), reserves reported in annual filings, revenue = production x commodity price |
| **Steel** | 3-5 years | Chinese construction, auto production, scrap prices, tariffs | GICS 15104055 (Steel), capacity utilization 60-90% range, heavy operating leverage |
| **Chemicals** | 3-7 years | Oil/feedstock costs, agricultural demand (fertilizers), industrial demand | GICS 151010 (Commodity Chemicals), naphtha/ethane cost pass-through dynamics |
| **Fertilizers** (N, P, K) | 3-5 years | Grain prices, natural gas (nitrogen input), mining economics | GICS 15101050 (Fertilizers), potash/urea price linkage to crop economics |
| **Shipping (Dry Bulk, Container, Tankers)** | 8-15 years (asset cycle) | Trade volumes, fleet growth, shipyard capacity, regulations | GICS 203050 (Marine), charter rate volatility, vessel values as key asset |
| **Semiconductors** | 2-4 years | Memory pricing, PC/smartphone cycles, AI capex, inventory | GICS 453010 (Semiconductors), book-to-bill ratio > 1 = expansion, memory spot pricing |
| **Construction Equipment** | 5-8 years | Infrastructure spend, mining capex, replacement cycle | GICS 201060 (Construction Machinery), order book as % of sales |
| **Automotive (OEMs)** | 4-7 years | Consumer credit, interest rates, model cycle, incentives | GICS 251010 (Automobiles), SAAR (Seasonally Adjusted Annual Rate) as demand proxy |
| **Airlines** | 5-8 years | GDP, jet fuel, labor costs, capacity discipline | GICS 203020 (Airlines), RASK (Revenue per Available Seat-Km), load factor |

### 1.2 Automatic Detection Logic

A stock is classified as **cyclical** if ANY of the following are true:

```
1. Revenue volatility > 2x S&P 500 median over 10 years
2. EBIT margin range (max - min) > 15 percentage points over 10 years
3. Commodity price exposure: >30% of revenue linked to commodity spot/contract prices
4. GICS code match in cyclical sectors list
5. Capacity utilization mentioned in filings as key metric
6. Order book / backlog reported as material metric
7. Book-to-bill ratio tracked by management
```

### 1.3 Sub-Type Classification Flow

```
IF commodity_producer:
    IF reserves_reported AND (oil OR gas): -> Oil & Gas E&P
    IF reserves_reported AND (metals OR minerals): -> Mining
    IF feedstock_driven AND chemicals: -> Chemicals
    IF grain_price_linked AND (N OR P OR K): -> Fertilizers
ELIF manufacturing_cyclical:
    IF steel_production: -> Steel
    IF semiconductor: -> Semiconductors
    IF vehicles: -> Automotive
    IF construction_equipment: -> Construction Equipment
ELIF service_cyclical:
    IF shipping: -> Shipping
    IF airline: -> Airlines
```

---

## 2. VALUATION MODELS

### 2.1 Through-the-Cycle (TTC) Earnings Approach

**Concept:** Cyclical earnings oscillate around a mean. The TTC approach calculates the "mid-cycle" earnings power and applies a normalized multiple.

**Step 1: Calculate Mid-Cycle Earnings**

```
Method A: Simple 10-Year Average
    Mid-Cycle EBIT = Average annual EBIT over last 10 years
    -> Best for: Mature commodities with stable long-run prices

Method B: Volume-Weighted Average
    Mid-Cycle EBIT = SUM(Annual EBIT) / 10, weighted toward recent volumes
    -> Best for: Growing production profiles (new mines, expanding E&P)

Method C: Commodity Price-Neutral Normalization
    Mid-Cycle EBIT = Current Volume x (Long-Run Price - Normalized Unit Cost)
    -> Best for: Commodity producers where volumes are stable but prices volatile

Method D: Capacity-Normalized
    Mid-Cycle EBIT = Nameplate Capacity x Mid-Cycle Utilization x Mid-Cycle Margin
    -> Best for: Manufacturing cyclicals (steel, chemicals, autos)
```

**How to Determine "Mid-Cycle":**

| Approach | Formula | When to Use |
|---|---|---|
| Historical average | 10-year mean real commodity price (inflation-adjusted) | Long history, no structural demand shift |
| 90th/10th percentile midpoint | (P90 + P10) / 2 | Captures extremes, good for volatile commodities |
| Incentive price | Price required to justify greenfield investment | Forward-looking, accounts for cost inflation |
| Marginal cost | 75th percentile of global cost curve | Price gravitates to cost of marginal producer |

**The Incentive Price Concept:**

The long-run commodity price must incentivize new supply. For copper:
```
Incentive Price = Greenfield AISC + Return on Capital + Development Risk Premium
                ~= $7,500-$9,000/tonne (2024 real terms)
```

If spot price ($9,000) > incentive price -> supply will eventually grow -> price reverts
If spot price ($6,000) < incentive price -> supply growth stalls -> price recovers

**Step 2: Apply Normalized Multiple**

```
TTC EV/EBIT Multiple:
    - Use median through-cycle EV/EBIT (not point-in-time)
    - Reference: Historical 10-year average for the sub-sector
    - Adjust for: Balance sheet strength, cost position, growth profile

Typical Ranges:
    Mining (copper): 6-8x mid-cycle EV/EBITDA
    Oil & Gas E&P: 4-6x mid-cycle EV/EBITDAX
    Steel: 4-5x mid-cycle EV/EBITDA
    Chemicals: 6-8x mid-cycle EV/EBITDA
    Shipping: 5-7x mid-cycle EV/EBITDA
    Semiconductors: 8-12x mid-cycle EV/EBITDA (higher due to growth)
```

### 2.2 Replacement Cost / NAV Valuation (Mining / Oil & Gas)

**Concept:** What would it cost to recreate this asset base? Book value is meaningless for resource companies (assets written down at trough, revalued at peak).

**For Mining:**

```
NAV = SUM[ PV(Reserves x Recovery Rate x Long-Run Price - Operating Costs - Royalties - Taxes) ]
      - Net Debt
      - PV(Reclamation/Closure Costs)
      + PV(Exploration/Resource Upside)

NAV per share = NAV / Shares Outstanding
```

**For Oil & Gas:**

```
NAV = SUM[ PV(2P Reserves x NRI x Long-Run Oil Price - Lifting Costs - Production Taxes) ]
      - Net Debt
      - PV(Asset Retirement Obligations)
      + PV(Unrisked Resources x Chance of Development)

Where:
    2P = Proved + Probable reserves
    NRI = Net Revenue Interest (working interest x (1 - royalty))
```

**Key Decisions:**

| Parameter | Conservative | Base Case | Optimistic |
|---|---|---|---|
| Commodity price | 10th percentile of 10-year range | Long-run incentive price | Current spot |
| Reserve conversion | 1P only | 2P | 2P + 50% of resources |
| Discount rate | 10% real | 8% real | 6% real |
| Cost inflation | +3% p.a. | +2% p.a. | +1% p.a. |

**Replacement Cost Check:**

```
Replacement Cost Multiple = Market Cap / Replacement Cost of Assets

Interpretation:
    < 0.5x: Assets cheaper to buy than build -> potential buy signal at trough
    0.5-1.0x: Fair value range through cycle
    > 1.5x: Market pricing in premium to replacement -> sell signal at peak

Example: If building a new copper mine costs $10,000/tonne of capacity,
         and the market prices existing mines at $5,000/tonne,
         replacement cost multiple = 0.5x -> trough signal
```

### 2.3 Commodity Price x Resource Base (Quick Valuation)

**For Miners (Back-of-Envelope):**

```
Quick Value = (Reserves x Long-Run Price x Recovery Rate - Total LOM Costs - Net Debt) / Shares

Simplified:
Quick EV = Annual Production x Reserve Life x (Spot Price - AISC) x Multiple
         ~= Annual Production x Reserve Life x Margin x 4-6x
```

**For Oil & Gas (Quick Valuation):**

```
Quick EV = Daily Production x Reserve Life x (Oil Price - Lifting Cost) x 365 x Multiple
         ~= BOE/day x Reserve Life (years) x Netback x 365 x 4-6x

Rules of thumb:
    EV per flowing barrel: $30,000-$80,000/bbl/day (varies by asset quality)
    EV per 2P reserve: $5-$15/BOE
```

### 2.4 Sum-of-the-Parts (Conglomerate Cyclicals)

Applies to: Diversified miners (BHP, Glencore), integrated oil companies, conglomerates with cyclical divisions.

```
SOTP EV = Division 1 EV + Division 2 EV + ... + Division N EV

Where each division:
    - Is valued using the appropriate cycle position
    - Commodity division: NAV or TTC multiple at mid-cycle
    - Stable division: Standard DCF or trading comparables

Example: BHP
    - Copper: NAV at $8,000/t long-run copper price
    - Iron Ore: NAV at $80/t long-run price
    - Coal: NAV at lower long-run price (transition risk)
    - Nickel: Write down (structurally challenged)
    - Sum and subtract corporate costs, net debt
```

**Critical:** Apply different cycle assumptions to different divisions. Do NOT apply the same multiple to copper (early-cycle) and coal (late-cycle/declining).

### 2.5 FCF-DCF with Cycle Overlay

**Standard DCF fails for cyclicals because:** It assumes steady-state growth, but cyclicals have explicit up/down phases.

**Modified Approach:**

```
Phase 1: Explicit Cycle Modeling (Years 1-5)
    Model each year separately with commodity price assumptions
    Year 1-2: Current spot / near-term futures curve
    Year 3-5: Gradual reversion to long-run price

    Revenue(t) = Volume(t) x Price(t) x Realization Rate
    EBITDA(t) = Revenue(t) - Cash Operating Costs(t) - Royalties(t)
    FCF(t) = EBITDA(t) - Sustaining Capex(t) - Growth Capex(t) - Taxes(t) +/- WC

Phase 2: Mid-Cycle Steady State (Years 6-10)
    Use mid-cycle commodity price
    Constant volume (no growth unless justified)
    Sustaining capex only

Phase 3: Terminal Value
    Terminal Value = Mid-Cycle FCF / (WACC - g)
    Where g = 0% for commodities (no real growth in long run)
    -> Terminal Value = Mid-Cycle FCF / WACC
```

**WACC for Cyclicals:**

```
Cyclical companies typically require HIGHER WACC due to:
    - Commodity price risk (unhedgable)
    - Political/jurisdiction risk (mining)
    - Capital intensity and execution risk

Typical WACC ranges:
    Developed market mining: 8-10%
    Emerging market mining: 10-14%
    Oil & Gas (onshore): 8-10%
    Oil & Gas (deepwater): 10-12%
    Steel/Chemicals: 8-10%
    Semiconductors: 10-12%
```

### 2.6 Asset-Based Valuation (Trough / Distress)

**When to use:** At or near cycle trough, when earnings are negative and DCF is meaningless.

```
Liquidation Value = Current Assets - Total Liabilities
                    = Working Capital + PP&E (fire-sale value) - All Debt

Scrap Value (for shipping, mining equipment):
    = Fleet / Equipment book value x Scrap discount (30-50%)

Property Value (for mining): 
    = Mineral rights + Surface rights - Reclamation obligations

Going-Concern Floor = Maintenance Capex / (WACC - 0%)
    -> What is the value of a business that only maintains itself?
```

**The "Would You Buy vs. Build?" Test:**

```
If Market Cap + Net Debt < 0.7 x Replacement Cost:
    -> Assets are cheaper to buy than build
    -> Strong buy signal at trough (if balance sheet survives)

If Market Cap + Net Debt > 1.3 x Replacement Cost:
    -> Cheaper to build than buy
    -> Sell signal (peak valuation)
```

---

## 3. KEY OPERATING METRICS

### 3.1 Commodity Producers (Mining / Oil & Gas)

#### AISC (All-In Sustaining Cost) vs. Spot Price

```
AISC = Cash Cost + Sustaining Capex + G&A + Exploration + Royalties

Margin = Spot Price - AISC
Margin % = (Spot Price - AISC) / Spot Price

BREAKEVEN PRICE = AISC (for sustaining operations)
FCF BREAKEVEN = AISC + Growth Capex/Production + Interest/Production

Example: Copper miner
    Spot Cu: $9,000/t
    AISC: $6,000/t
    Margin: $3,000/t (33% margin)
    FCF Breakeven: $6,000 + $500 + $300 = $6,800/t
    -> At $9,000/t, FCF margin = $2,200/t = 24%
```

**Cash Cost Curve Position (Critical):**

```
Quartile Ranking = Percentile of company's AISC on global cost curve

Q1 (bottom 25%): Superior cost position -- survives any downturn
Q2 (25-50%): Good position -- survives most downturns
Q3 (50-75%): Marginal -- vulnerable in severe downturns
Q4 (top 25%): High cost -- first to close in downturns

WHY IT MATTERS: Price is set by marginal producer. Q1-Q2 producers
earn profits through the cycle. Q3-Q4 producers lose money at trough.

Example: Global copper cost curve (2024)
    Q1 threshold: <$4,500/t
    Median: $6,000/t
    Q3 threshold: $7,500/t
    Top decile: >$9,000/t
    -> At $7,000/t copper, top 30% of producers lose money
```

#### Reserve Life Index

```
Reserve Life = Proven + Probable Reserves / Annual Production

Interpretation:
    < 5 years: Short reserve life -- high reinvestment risk
    5-10 years: Medium -- needs replacement discovery/buying
    10-20 years: Good -- sustainable production
    > 20 years: Excellent -- long-duration cash flows

REPLACEMENT RATIO = Reserves Added / Reserves Mined
    > 100%: Growing resource base
    < 100%: Depleting -- value destruction if not replaced
```

#### FCF Breakeven Price

```
FCF Breakeven = (Operating Costs + Sustaining Capex + Interest + Dividends) / Production Volume

This is the commodity price at which the company generates ZERO free cash flow.
It is the TRUE survival threshold.

Example:
    Operating costs: $3.0B
    Sustaining capex: $1.2B
    Interest: $0.3B
    Dividends: $0.5B
    Production: 1M tonnes
    FCF Breakeven = ($3.0B + $1.2B + $0.3B + $0.5B) / 1M = $5,000/tonne
    -> If copper drops below $5,000/t, company burns cash
```

#### Capital Intensity Metrics

```
Sustaining Capex Intensity = Sustaining Capex / Revenue
    -> How much of revenue must be reinvested to maintain production?
    Mining: 10-20%
    Oil & Gas: 15-25%

Growth Capex Efficiency = Incremental Production / Growth Capex ($/tonne or $/bbl)
    -> How efficiently does the company grow?
    Low = efficient growth (good)
    High = expensive growth (bad)

All-In Cash Cost = (Operating Cost + Sustaining Capex) / Production Unit
    -> True cost of production including maintenance
```

### 3.2 Manufacturing Cyclicals (Auto / Steel / Chemicals)

#### Capacity Utilization Rate

```
Capacity Utilization = Actual Output / Nameplate Capacity

Break-even utilization = Fixed Costs / (Price per Unit - Variable Cost per Unit)

Operating leverage effect:
    Above break-even: each additional unit drops mostly to bottom line
    Below break-even: company burns cash

Typical break-even levels:
    Steel: 70-75% utilization
    Chemicals: 65-70%
    Autos: 60-65% (highly automated)
```

#### Inventory Days

```
Inventory Days = Average Inventory / COGS x 365

WARNING SIGNS:
    Rising inventory days + flat/falling sales = demand slowdown
    Rising inventory + rising sales = production ramping (normal in upturn)
    Sharp spike (>30% above normal) = imminent price collapse

Steel inventory rule: When Chinese steel inventories exceed 15M tonnes
for >2 months, price correction typically follows within 1 quarter.
```

#### Order Book / Backlog

```
Backlog Coverage = Order Backlog / Quarterly Revenue

Interpretation:
    Rising backlog = visibility into future revenue (bullish)
    Falling backlog = demand weakening (bearish)
    Backlog / capacity > 1.0x = supply constrained -> pricing power
```

#### Pricing Power (Spot vs. Contract)

```
Contract Premium = Contract Price / Spot Price - 1

In tight markets: contract > spot (buyers lock supply)
In weak markets: contract < spot (sellers desperate for volume)

Spot-Contract Spread = Spot - Contract
    Positive and widening = tight market, strong near-term pricing
    Negative and widening = oversupply, contract roll-offs will hurt
```

### 3.3 Shipping

| Metric | Formula | Interpretation |
|---|---|---|
| **Spot Charter Rate** | Daily hire rate for immediate charter | Leading indicator of market tightness |
| **Time Charter Equivalent (TCE)** | Avg realized rate across spot + contract | True revenue metric |
| **Fleet Utilization** | Active vessels / Total fleet | >95% = very tight; <85% = oversupply |
| **Orderbook as % of Fleet** | Orderbook (dwt) / Existing fleet (dwt) | <10% bullish; >20% bearish (supply wave coming) |
| **Demolition Price** | Scrap steel value of vessel | Floor for vessel values |
| **Net Fleet Growth** | Deliveries - Demolitions +/- Conversions | Supply growth metric |
| **Baltic Dry Index (BDI)** | Composite dry bulk freight index | Sentiment and rate proxy |

**Vessel Valuation Rules:**

```
Newbuild Price vs. 5-Year Average:
    >1.3x average = peak signal (ordering frenzy)
    <0.7x average = trough signal

Secondhand Value / Newbuild Value:
    >0.9x = tight market (used vessels command premium)
    <0.5x = weak market (newbuilds much more expensive)
```

### 3.4 Semiconductors

| Metric | Formula | Bullish / Bearish Thresholds |
|---|---|---|
| **Book-to-Bill** | Orders Received / Billings | >1.1 bullish; <0.9 bearish; <0.8 severe downturn |
| **Inventory DOI** | Days of Inventory | Rising DOI + falling orders = BEARISH |
| **Memory Spot Price** | DRAM/NAND $/GB | Rising = tight supply; falling 3+ months = glut |
| **Wafer Fab Utilization** | Output / Capacity | >90% pricing power; <70% price wars |
| **Capex / Revenue** | Capex / Sales | >35% bearish (overspending); 15-25% healthy |

**Semiconductor Cycle Phases:**

```
Phase 1: Recovery (Book-to-Bill rising from <1 to >1)
    -> Inventory lean, restocking begins
    -> Memory prices bottom, start rising
    -> BUY signal

Phase 2: Expansion (Book-to-Bill > 1.1, utilization >90%)
    -> Revenue and margins expanding
    -> Capex plans announced
    -> HOLD / ADD

Phase 3: Peak (Book-to-Bill declining from high, inventories building)
    -> Everyone ordering, double-ordering begins
    -> Memory prices plateau
    -> REDUCE (sell into strength)

Phase 4: Downturn (Book-to-Bill < 1, utilization falling)
    -> Inventory glut, price wars
    -> Capex cuts announced
    -> ACCUMULATE (but only quality names with balance sheets)
```

### 3.5 Universal Cyclical Metrics

#### Operating Leverage

```
Operating Leverage = % Change in EBIT / % Change in Revenue

Or from regression:
    EBIT = alpha + beta x Revenue + epsilon
    beta = operating leverage coefficient

Interpretation:
    beta = 2.0x: 10% revenue drop -> 20% EBIT drop
    beta = 3.0x: 10% revenue drop -> 30% EBIT drop (very high risk)

Typical ranges:
    Mining: 1.5-2.5x
    Steel: 2.0-4.0x (very high fixed costs)
    Semiconductors: 1.5-3.0x (high fixed cost fabs)
    Shipping: 2.0-5.0x (operating costs fixed, revenue volatile)
```

#### FCF Conversion Rate

```
FCF Conversion = FCF / EBITDA

Healthy cyclical: >40% conversion (after sustaining capex)
Poor cyclical: <20% conversion (capital intensive, high maintenance)

At cycle peak: conversion should be >60% for miners
At mid-cycle: 40-50% is normal
At trough: negative conversion is expected
```

#### Net Debt / EBITDA Through Cycle

```
Point-in-time: Current Net Debt / LTM EBITDA
TTC-adjusted: Net Debt / Mid-Cycle EBITDA

Survival thresholds:
    Net Debt / Mid-Cycle EBITDA < 1.5x: Strong (survives deep trough)
    Net Debt / Mid-Cycle EBITDA 1.5-3.0x: Moderate (vulnerable)
    Net Debt / Mid-Cycle EBITDA > 3.0x: Dangerous (refinancing risk at trough)

Downturn survival rule: If Net Debt > 3x mid-cycle EBITDA,
company will likely need equity raise in a severe downturn.
```

#### Capital Allocation Discipline Score

```
Score components:
    - Buybacks at peak (-2 points): Destroying value
    - Buybacks at trough (+2 points): Accretive
    - Growth capex at peak (-1 point): Likely overpaying
    - Dividend cut avoided at trough (+1 point): Well prepared
    - Acquisition at peak (-2 points): Peak-of-cycle M&A destroys value
    - Acquisition at trough (+2 points): Counter-cyclical buying

Score > +2: Excellent allocator (rare)
Score 0 to +2: Good
Score -2 to 0: Poor
Score < -2: Value destroyer
```

**Red Flag:** Buybacks at peak earnings = management doesn't understand their own cycle. This is remarkably common among cyclical management teams.

---

## 4. KEY RISK FACTORS

### 4.1 Risk Matrix with Quantitative Indicators

| Risk | Probability | Impact | Early Warning Indicators | Quantitative Trigger |
|---|---|---|---|---|
| **Commodity price collapse** | Medium | Very High | Spot price falls 3-month moving avg; futures curve inverts | Spot < 75th pctile of cost curve for >6 months |
| **Extended downturn** | Medium | High | Inventory builds for 2+ quarters; credit spreads widen | >3 consecutive quarters of declining EBITDA |
| **Overcapacity / new supply** | Medium | High | Orderbook spiking; new projects announced globally | Industry capex > 25% of revenue for 2+ years |
| **Chinese demand shock** | Medium | Very High | China PMI < 50; property starts declining | China imports down >10% YoY for 2+ months |
| **Currency risk** | Low-Med | Medium | USD strengthening vs. local cost currency | 20%+ currency move in 12 months |
| **ESG transition** | High (long-term) | High | Carbon pricing expanding; EV adoption accelerating | Oil demand growth < 0.5% for 3+ years |
| **Operating leverage blow-up** | High at trough | Very High | Revenue declining; fixed costs sticky | EBIT declines > 2x revenue decline rate |
| **Balance sheet stress** | High for levered cos | Very High | Net debt/EBITDA > 5x; interest coverage < 2x | Covenant breach or refinancing needed |

### 4.2 Detailed Risk Analysis

#### Risk 1: Commodity Price Collapse

```
Scenario: Spot price drops 40% from current level
Impact Model:
    New Price = Current Price x 0.6
    New Revenue = Volume x New Price
    New EBITDA = New Revenue - Cash Costs (sticky downward)
    -> EBITDA typically drops 50-70% (operating leverage)

Example: Copper at $9,000 -> $5,400/t
    AISC $6,000/t producer:
        At $9,000: EBITDA margin = 33%
        At $5,400: EBITDA margin = -10% (loses money!)
    AISC $4,000/t producer (Q1 cost curve):
        At $9,000: EBITDA margin = 56%
        At $5,400: EBITDA margin = 26% (still profitable)
-> Cost curve position determines survival
```

#### Risk 2: Chinese Demand Shock

```
China consumes:
    ~50% of global copper
    ~60% of global iron ore
    ~35% of global oil demand growth
    ~50% of global steel
    ~40% of global chemicals

Shock Model:
    China demand down 10% -> Global demand down 5-6%
    -> Price impact: -15% to -30% depending on supply elasticity

Indicator: China Credit Impulse (YoY change in social financing)
    Leading indicator: 6-month lead on commodity prices
    Credit impulse turning negative -> commodity prices follow within 6 months
```

#### Risk 3: ESG Transition Risk

```
Phase-out commodities:
    Thermal coal: Demand peak likely passed (2023)
    Oil: Demand peak projected 2028-2032
    ICE autos: Phase-out by 2035 in most markets

Transition winners:
    Copper: Electrification demand (+50% by 2035)
    Lithium: EV battery demand (10x by 2035)
    Nickel: Battery chemistry dependent
    Uranium: Nuclear renaissance

Carbon cost impact:
    Carbon price $100/tCO2 adds:
        ~$10/tonne to steel costs (10% of margin)
        ~$5/bbl to oil sands production
        ~$30/tonne to aluminum costs
```

#### Risk 4: Balance Sheet Stress at Trough

```
Stress Test Model:
    Trough EBITDA = Mid-Cycle EBITDA x 0.3 (70% decline)
    Net Debt / Trough EBITDA = ?

If ratio > 5x:
    -> High probability of equity raise
    -> Dividend suspension likely
    -> Asset sales at fire-sale prices
    -> Potential covenant breach

Survival Checklist:
    [ ] Unrestricted cash > 12 months of operating losses
    [ ] Revolver undrawn
    [ ] Debt maturity wall > 3 years out
    [ ] Maintenance capex can be deferred if needed
    [ ] No material off-balance-sheet liabilities
```


---

## 5. QUALITY INDICATORS: GOOD CYCLICAL vs. BAD CYCLICAL

### Top 10 Quality Indicators (Ranked by Importance)

| Rank | Indicator | Why It Matters | How to Measure | Good / Bad Threshold |
|---|---|---|---|---|
| **1** | **Cost curve position** | Determines who survives the downturn; price is set at the margin | AISC percentile on global cost curve | Q1-Q2 = good; Q3-Q4 = bad |
| **2** | **Balance sheet strength entering downturn** | Determines survival duration and strategic optionality | Net Debt / Mid-Cycle EBITDA | <1.5x = good; >3x = bad |
| **3** | **Capital allocation discipline** | Peak-of-cycle spending destroys decades of value | Buyback timing, M&A timing, growth capex discipline | Counter-cyclical = good; pro-cyclical = bad |
| **4** | **Reserve/resource quality** | Long-life, high-grade assets compound value; short-life assets need constant reinvestment | Reserve life, grade, metallurgical recovery | >15 years = good; <5 years = bad |
| **5** | **Management track record** | Cyclical industries are full of "this time is different" thinking | Returns through cycle, NAV per share growth | Positive TSR through cycle = good |
| **6** | **Asset diversity (geography/commodity)** | Single-asset, single-commodity = binary risk | Number of producing assets, commodity mix | 3+ assets, 2+ commodities = good |
| **7** | **FCF conversion efficiency** | Revenue is meaningless if it doesn't convert to cash | FCF/EBITDA through cycle | >45% = good; <25% = bad |
| **8** | **ESG positioning** | Carbon costs, license to operate, access to capital | Carbon intensity, water usage, community relations | Industry-leading = good; laggard = bad |
| **9** | **Operational track record** | Cost guidance met? Production targets hit? | Guidance accuracy over 3+ years | >80% accuracy = good; frequent misses = bad |
| **10** | **Optionality / embedded upside** | Exploration, expansion projects, resource conversion | Resources vs. Reserves ratio, growth projects pipeline | Resources > 3x Reserves = good optionality |

### Quality Scoring Framework

```
Score each indicator 1-5, weighted sum:

Weighted Score = (Rank 1 x 5) + (Rank 2 x 4) + (Rank 3 x 4) + (Rank 4 x 3) 
               + (Rank 5 x 3) + (Rank 6 x 2) + (Rank 7 x 2) + (Rank 8 x 2)
               + (Rank 9 x 1) + (Rank 10 x 1)

Maximum score: 270
    > 200: Excellent quality cyclical (buy at first sign of trough)
    150-200: Good quality (buy at confirmed trough)
    100-150: Average (only buy at deep trough with margin of safety)
    < 100: Poor quality (avoid even at trough -- value trap)
```

### Real-World Examples

| Company | Cost Position | Balance Sheet | Allocation | Quality Verdict |
|---|---|---|---|---|
| **BHP** (copper/iron ore) | Q1-Q2 | Net debt/EBITDA ~1.0x | Disciplined post-2015 | **Excellent** |
| **Glencore** (diversified) | Q1-Q2 (coal), Q2 (copper) | Net debt manageable | Contrarian acquisitions | **Good** |
| **Freeport-McMoRan** (copper) | Q1-Q2 | De-leveraging | Learning from mistakes | **Good** |
| **US Steel** (steel) | Q3 | Levered | Pro-cyclical capex | **Poor** |
| **Teck Resources** (copper/coal) | Q2 | Solid | Focused copper pivot | **Good** |

---

## 6. STRESS TEST SCENARIOS

### 6.1 Scenario Framework

For each scenario, model:
1. Revenue impact (volume x price change)
2. Cost behavior (which costs are fixed vs. variable)
3. EBITDA impact (operating leverage amplification)
4. FCF impact (capex cuts partially offset)
5. Balance sheet impact (net debt/EBITDA spike)
6. Equity value impact

### 6.2 Scenario 1: Commodity Price Crash (-40%)

```
Assumptions:
    Commodity price: -40% from current spot
    Volume: Unchanged (production maintained)
    Variable costs: -10% (some input cost relief)
    Fixed costs: Unchanged
    Capex: Growth capex cut -50%; sustaining capex maintained

Impact Model:
    Revenue impact = -40%
    Cost impact = -10% x variable_cost_ratio
    EBITDA impact ~= -50% to -65% (operating leverage)
    FCF impact ~= -60% to -80%

Example - Copper miner (1M tpa, $9,000/t -> $5,400/t):
    Revenue: $9,000M -> $5,400M (-40%)
    Cash costs: $4,500M -> $4,050M (-10%)
    Sustaining capex: $1,200M (unchanged)
    EBITDA: $4,500M -> $1,350M (-70%)
    FCF: $2,300M -> -$150M (negative!)
    Net Debt/EBITDA: 1.3x -> 4.4x (stressful)

-> Outcome: Dividends suspended, potential equity raise if sustained >12 months
-> Key variable: How long does the crash last?
    If 6 months: Manageable (cash burn = $900M, covered by cash)
    If 24 months: Equity raise likely required
```

### 6.3 Scenario 2: Demand Collapse (Recession)

```
Assumptions (2008-09 style recession):
    Global GDP: -2% to -3%
    Industrial production: -8% to -12%
    Commodity demand: -5% to -10%
    Commodity price: -30% to -50%
    Volume for individual company: -10% to -20%

Impact Model:
    Revenue = Volume(-15%) x Price(-35%) = -45% total revenue decline
    EBITDA decline: -60% to -80%
    FCF: Negative for most producers

Duration analysis:
    2008-09 recession: 12 months from peak to trough
    2015-16 commodity downturn: 18 months
    2020 COVID: 3 months (V-shaped, unusual)

Recovery playbook:
    Month 1-3: Cut all discretionary capex, freeze hiring
    Month 3-6: Reduce sustaining capex, renegotiate contracts
    Month 6-12: Equity raise if Net Debt/EBITDA > 5x
    Month 12+: Acquisitions at trough (if balance sheet allows)
```

### 6.4 Scenario 3: Chinese Demand Shock (-10% Import Volume)

```
Assumptions:
    China imports down 10% across commodities
    Domestic China production maintained (protecting local jobs)
    Global price impact varies by commodity:
        Iron ore: -25% to -35% (China = 75% of seaborne)
        Copper: -15% to -20% (China = 50% of consumption)
        Oil: -10% to -15%
        Coal: -20% to -30%

Probability Assessment:
    Base case (next 5 years): 25-30% probability
    Trigger conditions: Property sector crisis, infrastructure slowdown

Mitigation: Companies with <30% revenue exposure to China
    (e.g., North American focused, European markets)
```

### 6.5 Scenario 4: Overcapacity (New Supply Floods Market)

```
Assumptions:
    New projects commissioned during boom come online simultaneously
    Supply growth: +8-12% in 2 years
    Demand growth: +2-3%
    Price impact: -25% to -40%

Historical examples:
    Lithium 2023: Supply +35%, prices -80%
    Iron ore 2014: Brazil/Australia expansion, prices -50%
    LNG 2024-25: Qatar expansion, US projects, price collapse

Warning signs:
    - Industry orderbook > 20% of fleet (shipping)
    - New project announcements > 2x current pipeline
    - Capital raising for new projects at rate > $10B/year

Impact timeline:
    Year 1: Prices soften -10-15% (market anticipating supply)
    Year 2: Prices crash -30-40% as new supply hits
    Year 3-4: Marginal producers shut in; prices recover to 75th cost pctile
```

### 6.6 Stress Test Summary Matrix

| Scenario | Probability | EBITDA Impact | FCF Impact | Balance Sheet Risk | Required Mitigation |
|---|---|---|---|---|---|
| Price crash -40% | 20% | -60% to -75% | Negative | High for Q3-Q4 producers | Pre-positioned liquidity |
| Recession | 25% | -50% to -80% | Negative | Very high | Balance sheet strength entering |
| China -10% | 25% | -30% to -50% | Reduced | Moderate | Geographic diversification |
| Overcapacity | 15% | -40% to -60% | Reduced | Moderate-High | Avoid late-cycle expansion |

---

## 7. PEER COMPARISON FRAMEWORK

### 7.1 Principles for Cyclical Peer Comparison

**WRONG:** Compare P/E ratios at the same point in time.
**RIGHT:** Compare through-cycle metrics.

### 7.2 Comparison Metrics by Sub-Type

#### Mining Peer Comparison

| Metric | Formula | Why It Matters |
|---|---|---|
| **Cost curve position** | AISC percentile | #1 determinant of survival |
| **Reserve life** | Reserves / Production | Duration of cash flows |
| **FCF yield on EV** | FCF / EV (TTC basis) | Normalized return |
| **NAV discount/premium** | Market Cap / NAV | What you're paying vs. asset value |
| **Net debt / TTC EBITDA** | Survival metric | Balance sheet strength |
| **Copper equivalent production growth** | Volume growth 3-yr CAGR | Value creation potential |

#### Oil & Gas Peer Comparison

| Metric | Formula | Why It Matters |
|---|---|---|
| **F&D cost** | Finding & Development cost ($/boe) | Capital efficiency of reserve replacement |
| **Recycle ratio** | Operating netback / F&D cost | Value creation: >2x is good, <1x destroys value |
| **Reserve life** | 2P Reserves / Production | Asset duration |
| **Breakeven oil price** | Price for FCF breakeven | Risk threshold |
| **Net debt / TTC EBITDAX** | Leverage | Survival capacity |

#### Steel Peer Comparison

| Metric | Formula | Why It Matters |
|---|---|---|
| **Cost per tonne** | Cash cost / Shipped tonnes | Global competitiveness |
| **Blast furnace vs. EAF mix** | % EAF production | EAF uses scrap = lower carbon, more variable cost |
| **Tonne-miles to market** | Average shipping distance | Proximity to customers = lower freight |
| **Net debt / TTC EBITDA** | Leverage | Survival at trough |
| **Product mix premium** | % specialty / value-added | Pricing power vs. commodity steel |

#### Shipping Peer Comparison

| Metric | Formula | Why It Matters |
|---|---|---|
| **Vessel age** | Average age of fleet | Younger = more fuel efficient, longer life |
| **Eco-vessel %** | % fleet with eco-engines | Fuel cost advantage: eco vessels save $2,000+/day |
| **Break-even TCE** | Daily break-even rate | Lower = survives downturns |
| **Net debt / fleet value** | Loan-to-value | Balance sheet leverage on real asset value |
| **Orderbook %** | Contracted newbuilds / fleet | Low = less cash drain, more strategic flexibility |

### 7.3 Through-Cycle Comparison Template

```
Peer: [Company A] vs [Company B] vs [Company C]

Metric                          | A       | B       | C       | Winner
--------------------------------|---------|---------|---------|--------
AISC ($/tonne)                  | 5,000   | 6,500   | 7,000   | A
Cost curve quartile             | Q1      | Q2      | Q3      | A
Reserve life (years)            | 22      | 12      | 8       | A
FCF yield (TTC basis)           | 8%      | 6%      | 4%      | A
NAV discount/premium            | -10%    | +5%     | +20%    | A
Net Debt / TTC EBITDA           | 1.0x    | 1.8x    | 3.2x    | A
Prod. growth (3yr CAGR)         | 5%      | 3%      | -2%     | A
Capital allocation score        | +2      | 0       | -2      | A
                                |         |         |         |
OVERALL QUALITY RANKING         | #1      | #2      | #3      |
```

**Key Rule:** Never rank cyclicals on current P/E. Rank on cost position, balance sheet, and through-cycle returns.

---

## 8. REPLACEMENT TABLE: STANDARD vs. CYCLICAL FRAMEWORK

| Standard Component | Cyclical Replacement | Rationale |
|---|---|---|
| **DCF (steady-state)** | **FCF-DCF with explicit cycle phases** | Cyclicals do NOT have steady-state earnings. Model the cycle explicitly: boom/bust phases with reversion to long-run price. Terminal value must use mid-cycle FCF, not peak FCF. |
| **ROIC (point-in-time)** | **Through-Cycle ROIC** | Point-in-time ROIC at peak can be 20%+; at trough, negative. Calculate ROIC using mid-cycle EBIT and average capital employed through the cycle. Quality threshold: TTC ROIC > WACC. |
| **P/E multiple** | **TTC EV/EBITDA or NAV discount** | P/E is inverted for cyclicals: low P/E at peak = expensive (sell signal); high P/E at trough = cheap (buy signal). Replace with TTC EV/EBITDA or price-to-NAV. |
| **FCF Yield (current)** | **FCF Yield on TTC basis** | Current FCF yield at peak can be 15%+ (unsustainable). Calculate FCF yield using mid-cycle FCF. Target: TTC FCF yield > 8% for miners. |
| **Revenue growth focus** | **Volume growth + cost control** | Revenue growth in cyclicals often reflects price inflation, not value creation. Focus on volume growth (production increases), cost reductions, and reserve replacement. |
| **Value trap detection** | **Balance sheet stress test + cost position** | For cyclicals, a "value trap" is a company that looks cheap (low P/E, low P/B) but is about to burn cash and dilute shareholders. Test: Net Debt / Trough EBITDA > 5x = likely trap regardless of valuation multiple. |
| **Gordon Growth Terminal Value** | **No-growth terminal value (g=0)** | Commodities have no real long-run growth (limited by finite resources). Terminal value = Mid-Cycle FCF / WACC (not FCF / (WACC - g)). |
| **DCF WACC (standard)** | **Cyclical-adjusted WACC (+1-2%)** | Add cyclical risk premium: commodity price volatility, political risk, capital intensity. Mining WACC = 9-11%, not 7-8%. |
| **Earnings quality score** | **Cost guidance accuracy + FCF conversion** | For cyclicals, earnings quality = meeting cost guidance, converting EBITDA to FCF, not manipulating depreciation. |
| **Competitive moat assessment** | **Cost curve position + reserve quality** | Cyclical moats are NOT brand or switching costs. They are: lowest cost position, longest reserve life, best assets. These are the only durable advantages. |

### Decision Flow: Which Valuation Method to Use?

```
IF company is commodity_producer (mining / O&G):
    PRIMARY: NAV at long-run commodity price
    SECONDARY: TTC EV/EBITDA
    TROUGH CHECK: Replacement cost / liquidation value

IF company is manufacturing_cyclical (steel / chemicals / auto):
    PRIMARY: TTC EV/EBIT (mid-cycle earnings)
    SECONDARY: Replacement cost (would you buy vs. build?)
    TROUGH CHECK: Break-even volume vs. current volume

IF company is shipping:
    PRIMARY: NAV (vessel values) + TTC earnings
    SECONDARY: Asset play (buy vs. build)
    CYCLE CHECK: Orderbook as % of fleet

IF company is semiconductor:
    PRIMARY: TTC EV/EBITDA (book-to-bill normalized)
    SECONDARY: P/B (asset value of fabs)
    CYCLE CHECK: Inventory levels, memory pricing

IF at or near cycle trough (all types):
    PRIMARY: Asset-based (liquidation, replacement cost)
    SECONDARY: NAV
    DO NOT USE: DCF (earnings negative), P/E (meaningless)
```

---

## 9. REVERSE ENGINEERING: IMPLIED COMMODITY PRICES

### 9.1 What Does a Low P/E Imply for a Cyclical?

**Standard (non-cyclical) interpretation:** Low P/E = cheap, buy.
**Cyclical interpretation:** Low P/E = peak earnings, SELL.

```
Why? P/E = Price / Earnings

At peak:
    Earnings are temporarily inflated by high commodity prices
    P/E appears low (denominator is large)
    But earnings will mean-revert downward
    -> "Value trap" -- appears cheap but is expensive

At trough:
    Earnings are depressed or negative
    P/E appears high or negative
    But earnings will recover
    -> "Optical expensive" -- appears expensive but is cheap

EARNINGS YIELD RULE for Cyclicals:
    Current Earnings Yield (E/P) > 15% -> likely at peak, REDUCE
    Current Earnings Yield (E/P) < 5% or negative -> likely at trough, ACCUMULATE

This is the OPPOSITE of standard value investing.
```

### 9.2 Extracting Implied Commodity Price from Stock Price

**Method: Reverse NAV Calculation**

```
Given: Market Cap, Net Debt, Reserves, Recovery Rate, Costs, Discount Rate
Solve for: Implied Commodity Price

Formula:
    Market Cap + Net Debt = PV(Reserves x Recovery x Price - Costs - Royalties - Taxes)
    
    Rearrange to solve for Price:
    Implied Price = f(Market Cap, Net Debt, Reserves, Recovery, Costs, Discount Rate)

Example - Simplified:
    Market Cap = $10B
    Net Debt = $3B
    EV = $13B
    Reserves = 500M tonnes
    Recovery = 85%
    Mine life = 20 years
    Real discount rate = 8%
    Annuity factor (8%, 20yr) = 9.82
    
    Annual payable metal = 500M x 85% / 20 = 21.25M tonnes/year
    
    Implied margin = EV / (Annual payable x Annuity factor)
                    = $13B / (21.25M x 9.82)
                    = $13B / 208.7M
                    = $62.3/tonne margin
    
    If operating cost = $50/tonne:
    Implied Price = $50 + $62.3 = $112.3/tonne
    
    If current spot = $150/tonne:
    -> Market is pricing in $112.3 vs. $150 spot
    -> Stock is discounting a 25% price decline
    -> If you believe price stays at $150, stock is undervalued
    -> If you believe price falls to $100, stock is overvalued
```

**Method: Reverse Multiple**

```
Given: Market Cap, Net Debt, Production, Industry EV/EBITDA multiple
Solve for: Implied EBITDA -> Implied Commodity Price

Formula:
    Target EV = Market Cap + Net Debt
    Implied EBITDA = Target EV / Target EV/EBITDA Multiple
    Implied Revenue = Implied EBITDA + Cash Costs
    Implied Price = Implied Revenue / Production Volume

Example:
    Market Cap = $15B, Net Debt = $5B -> EV = $20B
    Production = 1M tonnes
    Target TTC EV/EBITDA = 6x
    Cash costs = $5,000M
    
    Implied EBITDA = $20B / 6 = $3,333M
    Implied Revenue = $3,333M + $5,000M = $8,333M
    Implied Price = $8,333M / 1M tonnes = $8,333/tonne
    
    If current spot = $9,000/t:
    -> Market implies $8,333/t vs. $9,000/t spot
    -> Market is pricing in ~7.5% price decline from spot
```

### 9.3 The "Consensus Trap"

```
When spot price > implied price:
    -> Market is skeptical of current spot (expects reversion)
    -> If you believe spot is sustainable, stock is cheap
    -> This is the classic bull case for cyclicals

When spot price < implied price:
    -> Market is pricing in recovery above current spot
    -> If you believe spot stays low, stock is expensive
    -> This is the "value trap" zone

TRAP: Consensus earnings estimates for cyclicals are almost always wrong
at turning points. Analysts extrapolate current conditions. At peak,
estimates are too high; at trough, too low. Use TTC estimates, not
consensus.
```

---

## 10. ACCOUNTING RED FLAGS

### 10.1 Top 10 Accounting Risks in Cyclical Industries

| Rank | Red Flag | Detection Method | Impact on Valuation |
|---|---|---|---|
| 1 | **Aggressive depreciation lives** | PP&E / D&A expense = implied life. Compare to industry norm. Extending from 15 to 20 years can boost EPS 10-15% | Overstates earnings by 10-20% at mid-cycle |
| 2 | **Inventory build before downturn** | Inventory Days rising >20% above trend while sales flat. LIFO liquidation in down markets inflates margins temporarily | Falsely signals strong demand; write-downs follow |
| 3 | **Capitalization of exploration** | CapEx/Exploration ratio vs. peers. IFRS allows more capitalization than US GAAP. | Inflates assets and understates expenses |
| 4 | **Impairment timing games** | Write-downs clustered at CEO/CFO changes. Delaying impairment until new management arrives. | NAV overstates true asset value by 10-30% |
| 5 | **Off-balance-sheet JVs** | Operating companies with significant JVs not consolidated. Check "investments in associates" vs. total activity. | Hides debt and liabilities |
| 6 | **Asset retirement obligation underestimation** | ARO / total reserves ratio vs. peers. Check discount rate used (higher rate = lower liability). | Understates true liability by 20-50% |
| 7 | **Revenue recognition (take-or-pay)** | Long-term contracts with minimum payments. Revenue recognized before delivery. | Front-loads revenue; creates obligation risk |
| 8 | **Hedging disclosure gaps** | Gains/losses on hedges buried in "other income." Hedging can smooth earnings artificially. | Masks true commodity price exposure |
| 9 | **Related-party transactions** | Trading companies (e.g., Glencore model) buying from mines at non-arm's-length prices. | Profit shifting between entities |
| 10 | **Depletion rate manipulation** | Depletion rate changes that don't match reserve changes. Lower depletion = higher earnings. | Overstates earnings by 5-15% |

### 10.2 Detailed Detection Methods

#### Red Flag 1: Aggressive Depreciation Lives

```
Calculation:
    Implied Asset Life = Gross PP&E / Annual Depreciation
    
    Copper mine: If implied life = 30 years but reserve life = 15 years
    -> Depreciation understated by 50%
    -> Earnings overstated by $X (D&A difference)
    
Industry norms:
    Open-pit mines: 10-20 years
    Underground mines: 8-15 years
    Oil & gas fields: 10-20 years (by unit-of-production)
    Steel mills: 20-30 years
    Semiconductor fabs: 5-10 years

Test: Compare implied life to reserve life. If depreciation life > reserve life,
      the company is overstating earnings.
```

#### Red Flag 2: Inventory Build-Up

```
Warning Pattern:
    Quarter 1: Inventory +15%, Sales +5% -> "stocking for growth"
    Quarter 2: Inventory +25%, Sales +3% -> "supply chain management"
    Quarter 3: Inventory +35%, Sales -2% -> write-down announcement

LIFO vs. FIFO Impact in Downturn:
    LIFO company in rising prices: Matches current costs, conservative
    LIFO company in falling prices: Liquidates old inventory = margin boost
    -> This margin boost is one-time and misleading
    
Detection:
    Track "LIFO liquidation gains" in footnotes
    If >5% of operating income: flag as non-recurring
```

#### Red Flag 3: Exploration Cost Capitalization

```
GAAP (US) vs. IFRS:
    US GAAP: Exploration costs generally EXPENSED (conservative)
    IFRS: Exploration costs can be CAPITALIZED if technical feasibility demonstrated

Test:
    Capitalized Exploration / Total Exploration Spend
    IFRS companies with ratio > 50%: aggressive capitalization
    -> Compare to peers using same accounting standard
    
Impact: A company capitalizing 80% of exploration vs. a peer expensing 80%
    will report earnings ~10-20% higher (depending on exploration intensity)
```

#### Red Flag 4: Impairment Timing

```
Pattern to watch:
    - Commodity price peaked 12+ months ago
    - Stock price down 40%+
    - No impairment taken
    - "Management believes recovery is imminent"
    
Likely outcome: Massive impairment when management changes

Test:
    PP&E carrying value vs. replacement cost
    If carrying value > 1.5x replacement cost: impairment likely needed
    
For miners:
    NAV using spot prices vs. book value of mining assets
    If NAV < 0.7 x book value: impairment needed
```

#### Red Flag 5: Off-Balance-Sheet Structures

```
Common structures:
    - JVs where company has 50% ownership (not consolidated)
    - JVs with disproportionate debt (company guarantees)
    - Related-party offtake agreements
    
Detection:
    Read footnotes for "commitments and contingencies"
    Search for "guarantees," "letters of credit," "take-or-pay"
    Compare total disclosed debt to book debt
    
Example: A mining company with $5B book debt but $8B in JV guarantees
    has true leverage of $13B, not $5B.
```


---

## APPENDIX A: WORKED EXAMPLE -- COPPER MINER VALUATION

### Company Profile

| Parameter | Value |
|---|---|
| **Annual Production** | 1,000,000 tonnes copper |
| **AISC** | $6,000/tonne |
| **Total Reserves (2P)** | 20,000,000 tonnes |
| **Current Copper Spot Price** | $9,000/tonne |
| **Long-Run Copper Price (incentive)** | $8,000/tonne |
| **Net Debt** | $3,000M |
| **Shares Outstanding** | 500M |
| **Current Share Price** | $30.00 |
| **Market Cap** | $15,000M |
| **Sustaining Capex** | $1,200M/year |
| **Growth Capex** | $800M/year |
| **Tax Rate** | 30% |
| **Royalty Rate** | 5% of revenue |
| **Recovery Rate** | 88% |
| **Discount Rate (WACC)** | 9% |

### Valuation Method 1: NAV (Net Asset Value)

**Step 1: Calculate Life-of-Mine Revenue**

```
Reserve Life = 20M tonnes / 1M tonnes per year = 20 years

Payable Metal (after recovery) = 1M tonnes x 88% = 880,000 tonnes/year

Annual Revenue (at long-run $8,000/t):
    = 880,000 x $8,000 = $7,040M

Annual Revenue (at spot $9,000/t):
    = 880,000 x $9,000 = $7,920M
```

**Step 2: Calculate Life-of-Mine Costs**

```
Annual Operating Costs (AISC basis):
    Mining + Processing + Refining = $6,000/tonne x 1M tonnes = $6,000M

Royalties:
    = 5% x $7,040M = $352M (at $8,000/t)

Sustaining Capex:
    = $1,200M/year

Total Annual Cash Costs:
    = $6,000M + $352M + $1,200M = $7,552M
```

**Step 3: Calculate Annual Cash Flow**

```
At long-run $8,000/t:
    Revenue:         $7,040M
    Operating costs: ($6,000M)
    Royalties:         ($352M)
    EBITDA:          $688M
    Sustaining capex:  ($1,200M)
    EBIT:            ($512M) <- Negative at long-run price!
    -> This is a MARGINAL asset at $8,000/t

Wait -- let me recalculate. AISC already includes sustaining capex.
```

**Correction: AISC Definition**

```
AISC = All-In Sustaining Cost = operating cost + sustaining capex + G&A + royalties

So if AISC = $6,000/tonne, this INCLUDES sustaining capex.

Revenue:              $7,040M
AISC (1M tonnes):     ($6,000M)
Royalty (already in AISC? Need to check)

Let's assume AISC includes all cash costs except taxes:
    Revenue:          $7,040M
    AISC:             ($6,000M)
    EBITDA (AISC basis): $1,040M
    Taxes (30%):        ($312M)
    Annual Cash Flow:   $728M

At spot $9,000/t:
    Revenue:          $7,920M
    AISC:             ($6,000M)
    EBITDA:           $1,920M
    Taxes:              ($576M)
    Annual Cash Flow:   $1,344M
```

**Step 4: Calculate NAV**

```
NAV = PV(Annual Cash Flow, 20 years, 9% discount) - Net Debt

At long-run $8,000/t:
    Annual CF = $728M
    Annuity factor (9%, 20yr) = 9.1285
    PV of CF = $728M x 9.1285 = $6,646M
    NAV = $6,646M - $3,000M = $3,646M
    NAV per share = $3,646M / 500M = $7.29/share

At spot $9,000/t:
    Annual CF = $1,344M
    PV of CF = $1,344M x 9.1285 = $12,269M
    NAV = $12,269M - $3,000M = $9,269M
    NAV per share = $9,269M / 500M = $18.54/share
```

**Step 5: NAV Conclusion**

```
Current share price: $30.00

NAV at long-run price ($8,000/t): $7.29/share
    -> Premium to NAV: ($30.00 / $7.29) - 1 = +312%
    -> MASSIVELY OVERVALUED on long-run NAV basis

NAV at spot price ($9,000/t): $18.54/share
    -> Premium to NAV: ($30.00 / $18.54) - 1 = +62%
    -> Still overvalued even at spot prices

INTERPRETATION: The market is pricing in:
    - Higher copper prices than $9,000/t, OR
    - Significant growth beyond 1M tpa, OR
    - Premium for this being a high-quality asset

Implied copper price to justify $30/share:
    Target NAV = $30 x 500M = $15,000M + $3,000M debt = $18,000M
    Required annual CF = $18,000M / 9.1285 = $1,972M
    Required EBITDA = $1,972M / (1 - 0.30) = $2,817M
    Required Revenue = $2,817M + $6,000M = $8,817M
    Implied Copper Price = $8,817M / 880,000 = $10,019/tonne

-> Stock at $30 implies copper price of ~$10,000/t
-> Current spot is $9,000/t
-> Stock is pricing in $10,000/t sustained for 20 years
-> If you believe copper goes to $12,000+, stock could work
-> If you believe copper reverts to $8,000, stock is worth ~$7 (75% downside)
```

### Valuation Method 2: Through-the-Cycle EV/EBITDA

**Step 1: Calculate Mid-Cycle EBITDA**

```
Approach: Use long-run price ($8,000/t) as mid-cycle

Revenue = 880,000 payable tonnes x $8,000 = $7,040M
Cash operating costs (ex-sustaining capex) = $4,800M
    (assuming AISC $6,000M includes $1,200M sustaining capex)
Royalties = $352M

Mid-Cycle EBITDA = $7,040M - $4,800M - $352M = $1,888M
```

**Step 2: Apply TTC Multiple**

```
Copper mining sector median TTC EV/EBITDA: 6.0x (range: 5-8x)
    - Premium for Q1 cost position: +0.5x
    - Premium for long reserve life: +0.5x
    - Discount for moderate leverage: -0.5x
    -> Adjusted multiple: 6.5x

EV = $1,888M x 6.5 = $12,272M
Equity Value = $12,272M - $3,000M = $9,272M
Value per share = $9,272M / 500M = $18.54/share
```

**Step 3: TTC Conclusion**

```
TTC value: $18.54/share
Current price: $30.00/share
Premium to TTC: +62%

The market is pricing in significantly better than mid-cycle conditions.
```

### Valuation Method 3: Replacement Cost

**Step 1: Estimate Replacement Cost**

```
Greenfield copper mine development cost (2024):
    $8,000 - $12,000 per tonne of annual capacity
    (includes exploration, permitting, construction, infrastructure)

Replacement cost for 1M tpa capacity:
    Low: $8,000M
    Base: $10,000M
    High: $12,000M

Adjustments:
    - Brownfield expansion (lower risk): -20% = $8,000M
    - Existing infrastructure: -10% = $7,200M
    - Reserve quality (20-year life is good): no adjustment
    - Jurisdiction risk (assume stable): no adjustment

Adjusted replacement cost: ~$8,000M - $10,000M
```

**Step 2: Compare to Market Value**

```
Market EV = $15,000M + $3,000M = $18,000M

Replacement cost multiple = $18,000M / $9,000M (midpoint) = 2.0x

Interpretation:
    Replacement cost multiple > 1.5x = expensive (peak signal)
    -> Market is paying 2x what it would cost to build equivalent capacity
    -> Only justified if copper prices sustain above $10,000/t

At trough (hypothetical):
    Market EV = $5,000M + $3,000M = $8,000M
    Replacement multiple = $8,000M / $9,000M = 0.9x
    -> Approaching "buy vs. build" threshold
```

### Valuation Method 4: FCF-DCF with Cycle Overlay

**Step 1: Model Explicit Cycle Phases**

```
Year 1-2 (Current boom):
    Copper price: $9,000/t
    Revenue: $7,920M
    AISC: ($6,000M)
    EBITDA: $1,920M
    Growth capex: ($800M)
    Sustaining capex: included in AISC
    Taxes: ($576M)
    FCF: $544M

Year 3-4 (Gradual reversion):
    Copper price: $8,500/t -> $8,000/t
    Revenue: $7,480M -> $7,040M
    FCF: $361M -> $208M

Year 5 (Mid-cycle):
    Copper price: $8,000/t
    FCF: $208M (as calculated above)

Year 6-10 (Mid-cycle steady state):
    Copper price: $8,000/t (long-run)
    Volume: 1M tonnes (flat)
    FCF: $208M/year

Terminal Value (Year 10):
    TV = Mid-Cycle FCF / WACC = $208M / 9% = $2,311M
    (No growth -- commodities are finite resources)
```

**Step 2: Calculate DCF Value**

```
Year  FCF ($M)  Discount Factor  PV ($M)
----  --------  ---------------  -------
1     $544M     0.917            $499M
2     $544M     0.842            $458M
3     $361M     0.772            $279M
4     $208M     0.708            $147M
5     $208M     0.650            $135M
6     $208M     0.596            $124M
7     $208M     0.547            $114M
8     $208M     0.502            $104M
9     $208M     0.460            $96M
10    $208M     0.422            $88M + $2,311M TV = $2,399M

Sum of PVs = $3,443M
NAV = $3,443M - $3,000M (net debt) = $443M
Value per share = $443M / 500M = $0.89/share

Wait -- this seems too low. Let me recalculate with EBITDA approach.
```

**Recalculation with EBITDA-based FCF:**

```
Annual FCF (mid-cycle, $8,000/t):
    EBITDA: $1,888M (from TTC method)
    Sustaining capex: ($1,200M)
    Growth capex: $0 (mid-cycle, no growth)
    Taxes: ($206M) [30% of ($1,888M - $1,200M)]
    Working capital: $0 (stable)
    FCF: $482M

Year 1-2 (boom, $9,000/t):
    EBITDA: $2,720M
    Sustaining capex: ($1,200M)
    Growth capex: ($800M)
    Taxes: ($216M)
    FCF: $504M

Year 3-4 (reversion, $8,500/t):
    EBITDA: $2,304M
    Sustaining capex: ($1,200M)
    Growth capex: ($400M)
    Taxes: ($331M)
    FCF: $373M

Year 5-10 (mid-cycle, $8,000/t):
    FCF: $482M

DCF Calculation:
Year  FCF ($M)  DF (9%)    PV ($M)
1     $504M     0.917      $462M
2     $504M     0.842      $424M
3     $373M     0.772      $288M
4     $373M     0.708      $264M
5     $482M     0.650      $313M
6     $482M     0.596      $287M
7     $482M     0.547      $264M
8     $482M     0.502      $242M
9     $482M     0.460      $222M
10    $482M     0.422      $203M + TV

TV = $482M / 9% = $5,356M
PV of TV = $5,356M x 0.422 = $2,260M

Total PV = $2,269M + $2,260M = $4,529M
Equity Value = $4,529M - $3,000M = $1,529M
Value per share = $1,529M / 500M = $3.06/share

Hmm -- still low. The issue is taxes. Let me recalculate with proper tax shield.
```

**Final Corrected DCF:**

```
Year 1-2 (boom):
    Revenue: $7,920M
    Cash operating costs: ($4,800M)
    Royalties: ($396M) [5% of revenue]
    EBITDA: $2,724M
    D&A: ($1,200M) [sustaining capex proxy]
    EBIT: $1,524M
    Taxes: ($457M) [30%]
    NOPAT: $1,067M
    Add back D&A: $1,200M
    Less sustaining capex: ($1,200M)
    Less growth capex: ($800M)
    FCF: $267M

Wait -- this approach double-counts. Let me use cleaner method:

FCF = (Revenue - Cash Costs - Royalties) x (1 - Tax Rate) - Capex
    = EBITDA x (1 - Tax Rate) + (D&A x Tax Rate) - Capex

Year 1-2:
    EBITDA: $2,724M
    Tax rate: 30%
    Sustaining capex: $1,200M
    Growth capex: $800M
    FCF = $2,724M x 0.70 - $2,000M = $1,907M - $2,000M = -$93M
    
Actually the company is FCF negative during growth! This is common.

Let's simplify with the most standard approach:

Mid-Cycle FCF ($8,000/t):
    Revenue: $7,040M
    Cash costs: ($4,800M)
    Royalties: ($352M)
    EBITDA: $1,888M
    Sustaining capex: ($1,200M)
    Pre-tax FCF: $688M
    Taxes (30%): ($206M)
    Post-tax FCF: $482M

Boom FCF ($9,000/t):
    EBITDA: $2,720M
    Sustaining capex: ($1,200M)
    Pre-tax FCF: $1,520M
    Taxes: ($456M)
    Post-tax FCF: $1,064M
    Less growth capex: ($800M)
    Net FCF: $264M

DCF:
    Years 1-2: FCF = $264M/year
    Years 3-4: FCF = $482M/year (reversion, growth capex stops)
    Years 5-10: FCF = $482M/year
    TV = $482M / 9% = $5,356M

PV calculation:
    Year 1: $264M x 0.917 = $242M
    Year 2: $264M x 0.842 = $222M
    Year 3: $482M x 0.772 = $372M
    Year 4: $482M x 0.708 = $341M
    Year 5: $482M x 0.650 = $313M
    Year 6: $482M x 0.596 = $287M
    Year 7: $482M x 0.547 = $264M
    Year 8: $482M x 0.502 = $242M
    Year 9: $482M x 0.460 = $222M
    Year 10: $482M + $5,356M = $5,838M x 0.422 = $2,464M
    
    Total PV = $4,969M
    Equity Value = $4,969M - $3,000M = $1,969M
    Per share = $1,969M / 500M = $3.94/share
```

**Important Realization:** At $8,000/t long-run copper, this is a marginal asset with limited equity value. The current $30/share price ONLY works if copper sustains well above $9,000/t.

### Valuation Method 5: Quick Commodity-Price-Implied Check

```
Current market cap: $15,000M
Plus net debt: $3,000M
EV: $18,000M

Implied annual FCF to justify EV at 6x FCF:
    Required FCF = $18,000M / 6 = $3,000M

Work backwards to implied copper price:
    Required EBITDA = $3,000M / 0.70 = $4,286M (before tax)
    Required Revenue = $4,286M + $4,800M + $352M = $9,438M
    Implied Copper Price = $9,438M / 880,000 = $10,725/tonne

-> Market at $30/share implies $10,725/t copper sustained
-> Current spot: $9,000/t
-> Upside to implied: 19%
-> If copper goes to $12,000/t, stock has upside to ~$50+
```

### Summary of Valuations

| Method | Assumed Cu Price | Value/Share | vs. $30 Price |
|---|---|---|---|
| NAV (long-run) | $8,000/t | $7.29 | -76% |
| NAV (spot) | $9,000/t | $18.54 | -38% |
| TTC EV/EBITDA | $8,000/t mid-cycle | $18.54 | -38% |
| Replacement Cost | N/A | $8,000M vs. $18,000M EV | 2.0x replacement |
| FCF-DCF (cycle overlay) | $8,000/t long-run | $3.94 | -87% |
| Implied from stock price | Solve backward | $10,725/t required | -- |

### Investment Conclusion

```
BEAR CASE ($7,000/t copper - global recession):
    EBITDA: $1,040M
    FCF: Negative
    NAV: ~$0 (marginal asset)
    Stock value: $5-10/share (balance sheet support)
    DOWNSIDE from $30: -70% to -85%

BASE CASE ($8,000/t copper - mid-cycle):
    EBITDA: $1,888M
    NAV: $7.29/share
    TTC value: $18.54/share
    DOWNSIDE from $30: -38%

BULL CASE ($10,000/t copper - structural deficit):
    EBITDA: $3,520M
    NAV: $28/share
    Upside case: $40-50/share
    UPSIDE from $30: +35% to +65%

STRUCTURAL CASE ($12,000/t - electrification boom):
    EBITDA: $5,280M
    NAV: $48/share
    UPSIDE: $60-80/share
    UPSIDE from $30: +100% to +165%

KEY INSIGHT: 
    At $30, the stock is a bet on copper >$10,000/t sustained.
    This is NOT a value investment -- it's a commodity price speculation.
    A true value investor would only buy below $15/share (assuming
    $8,000/t is the right long-run price), providing 50% margin of safety.
```

---

## APPENDIX B: KEY FORMULAS SUMMARY

### Valuation Formulas

```
NAV = SUM[PV(Reserves x Recovery x Price - Costs - Royalties - Taxes)] - Net Debt

TTC EV/EBITDA Value = Mid-Cycle EBITDA x Sector Multiple - Net Debt

Replacement Cost Multiple = (Market Cap + Net Debt) / Replacement Cost

Implied Commodity Price = f(Market Cap, Net Debt, Reserves, Costs, WACC)

Mid-Cycle EBIT = 10-Year Average EBIT (inflation-adjusted)

FCF Breakeven Price = (Operating Costs + Sustaining Capex + Interest + Dividends) / Volume
```

### Operating Metrics

```
AISC = Cash Cost + Sustaining Capex + G&A + Royalties + Exploration

Reserve Life = 2P Reserves / Annual Production

FCF Conversion = FCF / EBITDA

Operating Leverage = % Change EBIT / % Change Revenue

Net Debt / TTC EBITDA = Net Debt / 10-Year Average EBITDA

Cost Curve Quartile = Percentile rank on global AISC curve
```

### Cycle Indicators

```
P/E Inversion Signal:
    E/P > 15% -> Peak earnings -> SELL
    E/P < 5% or negative -> Trough earnings -> ACCUMULATE

Inventory Warning:
    Inventory Days > 130% of 3-year average + Flat sales = Price crash coming

China Credit Impulse:
    6-month change in social financing < 0 = Commodity prices follow down in 6 months

Orderbook Signal (shipping):
    Orderbook > 20% of fleet = Supply wave coming -> AVOID
```

---

## APPENDIX C: SECTOR-SPECIFIC CYCLE LENGTHS

| Sector | Typical Cycle | Current Position (2024) | Key Driver |
|---|---|---|---|
| Copper | 8-10 years | Mid-cycle, early deficit | Supply underinvestment, electrification |
| Iron Ore | 5-7 years | Late-cycle, Chinese property | China steel demand, Brazilian supply |
| Gold | 10-15 years | Unclear, real rates key | US real yields, central bank buying |
| Lithium | 3-5 years | Deep downturn post-2023 | EV demand, Australian/S. American supply |
| Oil | 5-7 years | Late-cycle, demand peak debate | OPEC+ discipline, shale maturity |
| Natural Gas | 5-8 years | Regional divergence | LNG exports, European supply restructuring |
| Steel | 3-5 years | Late-cycle, China property | China stimulus, protectionism |
| Fertilizers | 3-5 years | Post-peak normalization | Grain prices, natural gas costs |
| Dry Bulk Shipping | 8-12 years | Early-cycle recovery | Fleet aging, orderbook lows |
| Container Shipping | 5-8 years | Post-peak normalization | Trade growth, fleet expansion |
| Semiconductors | 2-4 years | AI-driven boom | AI capex, memory pricing |
| Construction Equipment | 5-8 years | Late-cycle | Mining capex, infrastructure |
| Automotive | 4-7 years | Transition disruption | EV adoption, interest rates |

---

## APPENDIX D: CHECKLIST -- BEFORE INVESTING IN ANY CYCLICAL

### Balance Sheet Check
- [ ] Net Debt / Mid-Cycle EBITDA < 2.0x
- [ ] Interest coverage > 4x at mid-cycle
- [ ] No debt maturities within 24 months
- [ ] Revolver undrawn or < 50% drawn
- [ ] Unrestricted cash > 6 months of operating costs

### Cost Position Check
- [ ] AISC in Q1 or Q2 of global cost curve
- [ ] FCF breakeven < 80th percentile of historical price range
- [ ] Unit costs declining or stable (not rising)

### Capital Allocation Check
- [ ] No large growth projects sanctioned at peak prices
- [ ] Buyback history: did they buy back at trough or peak?
- [ ] Dividend policy sustainable at mid-cycle earnings
- [ ] No value-destroying M&A in past 3 years

### Cycle Timing Check
- [ ] P/E is HIGH or negative (not low) -- confirming trough
- [ ] Inventory levels normalizing or declining
- [ ] Order book improving or stable
- [ ] Commodity price above 90th percentile of cost curve
- [ ] Competitor capex cuts announced (supply response)

### Quality Check
- [ ] Reserve life > 10 years (mining/O&G)
- [ ] Management met guidance for 3+ years
- [ ] Geographic/political risk is manageable
- [ ] ESG score not in bottom quartile

### Valuation Check
- [ ] Price < 1.0x replacement cost (trough) OR
- [ ] Price < 0.8x NAV at long-run price (trough) OR
- [ ] TTC FCF yield > 8%
- [ ] Implied commodity price < my forecast

**If ALL boxes checked -> Strong buy candidate**
**If 4-5 boxes checked -> Buy with caution**
**If < 4 boxes checked -> Avoid (value trap risk)**

---

*Document generated for adaptive stock analysis framework -- Cyclical Industries Module*
*Version: 1.0 | Last updated: 2024*

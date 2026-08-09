# REITs & Real Estate — Adaptive Framework Design

> **Module Purpose**: Replace standard equity analysis (FCF-based DCF, ROIC, P/E) with REIT-specific methodologies that account for appreciating real assets, pass-through tax structures, and sector-specific operating metrics.

---

## 1. SECTOR DETECTION RULES

### 1.1 Auto-Detection Criteria

| Criterion | Threshold | Notes |
|-----------|-----------|-------|
| SIC/NAICS codes | 6798 (REITs), 5311 (real estate), 6792 (mREITs) | Primary identifier |
| GICS sub-industry | Real Estate Investment Trusts (60101010), Real Estate Management & Development (601020) | Industry classification |
| "REIT" in company name | Binary flag | ~90% of REITs include "REIT" or "Realty" |
| Depreciation > 30% of revenue | Screen | REITs have massive depreciation charges |
| Dividend yield > 3% | Screen | REITs must distribute ≥90% of taxable income |
| Property/equipment on BS > 60% of assets | Screen | Equity REITs hold hard real estate |
| Mortgage-backed securities > 50% of assets | Screen | Indicates mREIT |

### 1.2 Three-Way Classification

#### **Equity REITs** (Own and operate properties)
> Core business: Acquire, develop, manage, and lease physical real estate. Revenue = rental income. Subject to standard REIT distribution requirements.

| Sub-Type | Key Revenue Driver | Critical Metric | Structural Tailwind/Risk |
|----------|-------------------|-----------------|-------------------------|
| **Industrial/Warehouse** | E-commerce logistics demand | In-place rent vs. market rent | Amazon, supply chain reshoring |
| **Data Center** | Cloud/AI computing demand | MW (megawatts) leased, utilization | AI explosion, power constraints |
| **Residential (Multifamily)** | Demographics, household formation | Same-store NOI growth, rent/occupancy | Housing affordability crisis |
| **Single-Family Rental (SFR)** | Home ownership affordability | Occupancy, rent growth, maintenance costs | Institutional capital inflow |
| **Office** | Employment, return-to-office | WALT, tenant retention, sublease rate | **Structural decline** (remote work) |
| **Retail (Shopping Centers)** | Consumer spending, tenant sales | Sales per sq ft, occupancy cost % | E-commerce, tenant health |
| **Net Lease** | Credit quality of tenants | WALT, % investment-grade tenants | Bond-proxy characteristics |
| **Healthcare** | Aging demographics, Medicare | Operator coverage ratios, NOI yield | Regulatory, operator credit |
| **Self-Storage** | Population mobility, life events | Same-store occupancy, street rates | Highly cyclical, local competition |
| **Timber** | Housing starts, lumber prices | Harvest volume, acreage value | Lumber futures correlation |
| **Lodging/Resorts** | RevPAR (Revenue per Available Room) | Occupancy × ADR (Average Daily Rate) | Highly cyclical, travel trends |
| **Cell Tower** | Wireless carrier lease demand | Tower cash flow, lease escalators | 5G deployment, carrier M&A |

#### **Mortgage REITs (mREITs)** (Own mortgages and MBS, not properties)
> **TREAT AS A COMPLETELY DIFFERENT SECTOR.** mREITs are levered bond portfolios, not real estate operators.

| Feature | Equity REIT | Mortgage REIT |
|---------|-------------|---------------|
| Assets | Physical properties | Mortgage loans, MBS |
| Revenue | Rental income | Interest income |
| Key metric | NOI, FFO | Net interest margin, book value |
| Leverage | 4-8x debt/EBITDA | 5-10x (sometimes higher) |
| Sensitivity | Cap rates, occupancy | Interest rates, prepayment speeds, spreads |
| Dividend yield | 3-5% | 8-15% (higher risk) |
| Appropriate model | NAV, FFO multiple | Book value, dividend sustainability |

#### **Real Estate Operating Companies (REOCs)**
> Non-REIT real estate companies (e.g., Brookfield Corp, Howard Hughes Holdings). Not subject to 90% distribution rule, more flexible capital allocation. Can retain earnings for development. Standard corporate tax applies. Analysis blends REIT and corporate approaches.

### 1.3 Detection Logic Flow

```
IF (SIC in [6798, 6792, 5311] OR "REIT" in name OR property assets > 60%):
    IF mortgage securities > 50% of assets:
        CLASSIFY → Mortgage REIT (mREIT)
        USE MODEL → Book Value + NIM approach
    ELSE:
        CLASSIFY → Equity REIT
        IDENTIFY sub-type from property mix / NAICS
        USE MODEL → NAV + FFO/AFFO approach
    IF NOT meeting 90% income distribution test:
        FLAG as REOC (blended approach)
```

---

## 2. VALUATION MODELS

### 2.1 Primary: NAV (Net Asset Value) Model

> **Why NAV first?** NAV represents the liquidation value of the REIT — what you would get if all properties were sold at fair value and debt repaid. Trading price vs. NAV is the single most important valuation metric for equity REITs.

#### Formula

```
Gross Asset Value (GAV) = Σ Property Values
                        = NOI / Cap Rate (portfolio level)
                        OR = Σ (Property_i NOI_i / Cap Rate_i) (property-by-property)

Net Asset Value (NAV) = GAV - Total Debt - Preferred Equity - Minority Interests
                        + Cash & Equivalents - Other Liabilities

NAV per Share = NAV / Shares Outstanding

Premium/(Discount) to NAV = (Stock Price - NAV per Share) / NAV per Share
```

#### Cap Rate Determination (Critical!)

The cap rate is the **most sensitive input** in NAV valuation. A 25bp change in cap rate can swing NAV by 5-10%.

| Method | Description | Best Used For |
|--------|-------------|---------------|
| **Market transaction comps** | Recent comparable property sales cap rates | All types — most objective |
| **Broker estimates** (CBRE, JLL, Eastdil) | Quarterly market cap rate surveys | Lacking transaction data |
| **Stabilized NOI yield** | NOI / current market value of properties | When appraisals available |
| **10-year Treasury + spread** | 10Y UST + property-type risk spread | Quick estimate, sensitivity analysis |
| **Implied cap rate** | NOI / (Market Cap + Net Debt) | Reverse-engineering market expectations |

**Typical Cap Rate Ranges by Property Type (2024):**

| Property Type | Cap Rate Range | Spread to 10Y UST |
|---------------|---------------|-------------------|
| Data Center | 5.0% - 7.0% | +150-350bps |
| Industrial | 4.5% - 6.0% | +100-250bps |
| Multifamily | 4.25% - 5.5% | +75-200bps |
| Net Lease | 5.5% - 7.5% | +200-400bps |
| Grocery-anchored Retail | 6.0% - 7.5% | +250-400bps |
| Office (Class A) | 6.5% - 9.0% | +300-600bps |
| Self-Storage | 4.75% - 6.0% | +125-250bps |
| Healthcare/Senior Housing | 7.5% - 9.5% | +400-650bps |
| Lodging | 7.0% - 9.0% | +350-600bps |
| Cell Tower | 3.5% - 5.5% | +25-200bps |

> **Cap rate rule of thumb**: Cap rates move inversely and proportionally with interest rates. If the 10Y UST rises 100bps, expect cap rates to expand 75-100bps (with lag).

#### When is Premium/Discount to NAV Justified?

| Scenario | Premium/Discount | Rationale |
|----------|-----------------|-----------|
| Superior management, development pipeline | 10-25% premium | Value creation above liquidation |
| Below-market lease portfolio (embedded growth) | 5-15% premium | Rollover upside not in NAV |
| Premium locations, irreplaceable assets | 10-20% premium | Scarcity value |
| Poor management, value destruction | 10-30% discount | NAV likely overstated |
| High leverage, refinancing risk | 15-30% discount | NAV overstates equity value |
| Lease rollover into weak market | 10-20% discount | Forward NOI will decline |
| Poor corporate governance, related-party issues | 15-25% discount | Control discount |

---

### 2.2 Secondary: FFO/AFFO Multiple

> **Why FFO?** Standard net income is meaningless for REITs because depreciation — a massive non-cash charge — artificially suppresses earnings while properties typically APPRECIATE in value.

#### FFO Formula (NAREIT Definition)

```
FFO = Net Income (GAAP)
      + Depreciation and Amortization of real estate
      - Gains on sales of properties
      + Losses on sales of properties

FFO per Share = FFO / Weighted Average Shares Outstanding
```

#### AFFO Formula (Adjusted FFO — closer to true cash flow)

```
AFFO = FFO
       - Recurring Capital Expenditures
       - Leasing Commissions
       - Tenant Improvements
       - Straight-line Rent Adjustments
       + Non-cash stock compensation (optional)
       - Non-recurring items

AFFO per Share = AFFO / Weighted Average Shares Outstanding
```

> **FFO vs AFFO**: FFO is more widely reported and comparable. AFFO is closer to sustainable cash flow available for dividends. The FFO-to-AFFO gap varies by property type (older buildings need more CapEx).

#### P/FFO and P/AFFO Multiples

| Property Type | P/FFO Range (2024) | P/AFFO Range | FFO Growth Target |
|---------------|-------------------|--------------|-------------------|
| Data Center | 18x - 25x | 22x - 30x | 8-15% |
| Industrial | 20x - 28x | 24x - 32x | 8-12% |
| Multifamily | 18x - 24x | 22x - 28x | 5-8% |
| Net Lease | 14x - 18x | 16x - 20x | 3-5% |
| Self-Storage | 20x - 26x | 24x - 30x | 5-8% |
| Office | 8x - 14x | 10x - 16x | -5% to +2% |
| Healthcare | 12x - 16x | 14x - 18x | 3-6% |
| Cell Tower | 18x - 24x | 22x - 28x | 6-10% |

> **High multiple = market pricing in above-average growth.** Data centers trade at 25x FFO because of AI-driven demand growth. Office trades at 10x because of structural decline. Always compare multiples WITHIN property types, not across.

---

### 2.3 Tertiary: Dividend Discount Model

> REITs are income vehicles. For many investors, the dividend IS the thesis. DDM provides a floor value based on dividend sustainability.

```
Value = D₁ / (r - g)

Where:
D₁ = Expected dividend next year
r  = Required rate of return (cost of equity)
g  = Sustainable dividend growth rate
```

#### AFFO Payout Ratio — The Dividend Sustainability Test

```
FFO Payout Ratio  = Annual Dividends / FFO
AFFO Payout Ratio = Annual Dividends / AFFO

Target AFFO Payout: 70-85% for most equity REITs
> 90% = UNSUSTAINABLE (no margin for safety, limited growth CapEx)
< 60% = CONSERVATIVE (room to raise dividend or reinvest)
```

| Payout Level | Interpretation |
|-------------|----------------|
| < 65% | Conservative, likely dividend raise coming |
| 65-80% | Healthy, sustainable with growth |
| 80-90% | Stretched, limited growth capacity |
| > 90% | **RED FLAG** — dividend at risk if NOI declines |
| > 100% | **CRISIS** — paying out more than earning (liquidating) |

#### Dividend Yield Context

| Yield Level | Interpretation |
|-------------|----------------|
| < 3% | Growth REIT (data center, industrial), or overpriced |
| 3-4.5% | Standard equity REIT range |
| 4.5-6% | Higher risk or mature, slow-growth REIT |
| 6-8% | Distressed, or mREIT |
| > 8% | **RED FLAG** — market pricing dividend cut |

---

### 2.4 mREIT Valuation (Completely Different Model)

> **Do NOT use NAV or FFO for mREITs.** mREITs are levered fixed-income portfolios, not real estate operators.

#### Book Value Approach

```
Book Value per Share = Shareholders' Equity / Shares Outstanding
Price-to-Book (P/B) = Stock Price / Book Value per Share

Economic Return = (Change in Book Value + Dividends) / Beginning Book Value
```

| P/B Level | Interpretation |
|-----------|----------------|
| > 1.0x | Market expects spread/earnings to improve |
| 0.9-1.0x | Fair value range |
| 0.8-0.9x | Discount — market expects spread compression or losses |
| < 0.8x | **Deep discount** — significant balance sheet concern |

#### Net Interest Income Model

```
Net Interest Income = Interest Income - Interest Expense
Net Interest Margin (NIM) = Net Interest Income / Average Earning Assets

Leverage = Total Assets / Shareholders' Equity (typically 5-10x)
ROE = NIM × Leverage (approximate)

Earnings = (Asset Yield - Cost of Funds) × Leverage × Equity
```

#### CPR (Constant Prepayment Rate) Sensitivity

```
CPR = % of mortgage principal prepaid annually (refinancing, home sales)

Impact: Higher CPR → mortgages pay off faster → reinvestment risk
        Lower CPR → mortgages extend → duration risk

Effective Duration = Sensitivity of portfolio value to 100bp rate change
```

| mREIT Type | Assets | Key Risk |
|------------|--------|----------|
| Agency RMBS | Fannie/Freddie MBS | Prepayment risk, duration extension |
| Credit RMBS | Non-agency MBS | Credit risk, liquidity risk |
| Commercial MBS | CMBS loans | Property-level credit risk |
| Residential Whole Loans | Direct mortgage ownership | Servicing risk, credit risk |

---

## 3. KEY OPERATING METRICS

### 3.1 Property Metrics

#### NOI (Net Operating Income)
```
NOI = Rental Revenue + Other Property Income - Operating Expenses
      (excluding depreciation, interest, corporate G&A)

NOI Margin = NOI / Rental Revenue
```
> NOI is the real estate equivalent of gross profit. It measures property-level profitability before financing and corporate overhead.

**NOI Margin Benchmarks:**
- Industrial: 65-72%
- Multifamily: 60-68%
- Data Center: 75-82%
- Office: 55-65% (declining)
- Self-Storage: 55-65%
- Net Lease: 90%+ (tenant pays most expenses)

#### Cap Rate
```
Cap Rate = NOI / Property Value
Implied Cap Rate = NOI / (Market Cap + Net Debt)
```

#### Same-Store NOI Growth (Organic Growth)
```
Same-Store NOI Growth = (Current Period NOI - Prior Period NOI) / Prior Period NOI
                        (for properties owned in both periods)
```
> **This is the purest measure of organic growth.** Excludes acquisitions, dispositions, and developments. Compare to inflation + GDP growth.

| Property Type | Healthy Same-Store Growth | Concerning |
|---------------|--------------------------|------------|
| Industrial | 5-10% | < 3% |
| Data Center | 6-12% | < 4% |
| Multifamily | 3-6% | < 1% |
| Self-Storage | 3-7% | < 0% |
| Office | -2% to +2% | <-5% |
| Net Lease | 1-3% | < 0% |

#### Occupancy Rate
```
Occupancy Rate = Occupied Square Feet / Total Square Feet
Economic Occupancy = Actual Rental Income / Potential Rental Income
                     (accounts for free rent, concessions)
```

| Property Type | Healthy Occupancy | Warning |
|---------------|------------------|---------|
| Industrial | 95-98% | < 90% |
| Data Center | 85-95% | < 80% |
| Multifamily | 94-97% | < 90% |
| Office | 85-92% | < 80% |
| Self-Storage | 88-93% | < 82% |
| Net Lease | 98-100% | < 95% |

#### WALT (Weighted Average Lease Term)
```
WALT = Σ (Lease Rent_i × Remaining Term_i) / Total Rent
       (years)
```
> Long WALT = stability, short WALT = growth/rollover risk. Net leases often have 10-20 year WALTs. Office/industrial typically 5-8 years.

| WALT Range | Interpretation |
|-----------|----------------|
| > 10 years | Very stable, bond-like (net lease, data center) |
| 5-10 years | Moderate stability (industrial, office) |
| 3-5 years | Higher rollover risk (multifamily, self-storage) |
| < 3 years | High turnover, market-rate exposure |

#### Lease Spreads (New Rents vs. Expiring Rents)
```
Cash Lease Spread = (New Rent - Expiring Rent) / Expiring Rent

Positive spread = rising rents (bullish)
Negative spread = falling rents (bearish)
```

| Spread Level | Signal |
|-------------|--------|
| > 15% | Very strong market |
| 5-15% | Healthy market |
| 0-5% | Flat market |
| < 0% | Declining rents — **warning** |

#### Tenant Retention Rate
```
Retention Rate = (Square Feet Renewed / Square Feet Expiring) × 100%
```

---

### 3.2 Debt & Capital Metrics

#### LTV (Loan-to-Value)
```
LTV = Total Debt / Gross Asset Value (GAV)
Net LTV = (Total Debt - Cash) / GAV
```

| LTV Range | Risk Level |
|-----------|-----------|
| < 25% | Conservative (AAA balance sheet) |
| 25-35% | Moderate (investment grade) |
| 35-45% | Average for REITs |
| 45-55% | Elevated risk |
| > 55% | High risk (refinancing vulnerability) |

#### Debt/EBITDA
```
Net Debt / EBITDA (typically using annualized NOI as proxy)
```

| Ratio | Rating Implication |
|-------|-------------------|
| < 4.0x | Investment grade territory |
| 4.0-5.5x | Typical for REITs |
| 5.5-7.0x | Elevated |
| > 7.0x | **High risk**, limited flexibility |

#### Interest Coverage
```
Interest Coverage = NOI / Interest Expense
                  (or EBITDA / Interest Expense)
```

| Ratio | Interpretation |
|-------|----------------|
| > 5.0x | Strong |
| 3.5-5.0x | Adequate |
| 2.5-3.5x | Stretched |
| < 2.5x | **Danger zone** |

#### Fixed Charge Coverage
```
Fixed Charge Coverage = EBITDA / (Interest Expense + Preferred Dividends + Scheduled Debt Amortization)
```

#### Weighted Average Cost of Debt (WACD)
```
WACD = Σ (Debt_i × Interest Rate_i) / Total Debt
```

#### Debt Maturity Schedule (Critical!)
```
Refinancing Risk = % of Debt Maturing Within 3 Years

Safe: < 20% maturing in next 3 years
Watch: 20-35% maturing
Danger: > 35% maturing (especially if rates elevated)
```

---

### 3.3 FFO/AFFO Metrics

#### FFO per Share
```
FFO per Share = FFO / Weighted Average Diluted Shares
```

#### AFFO per Share
```
AFFO per Share = AFFO / Weighted Average Diluted Shares
```

#### Payout Ratios
```
FFO Payout Ratio  = Annual Dividends per Share / FFO per Share
AFFO Payout Ratio = Annual Dividends per Share / AFFO per Share  ← MORE ACCURATE
```

#### FFO Growth Rate
```
FFO Growth = (Current FFO - Prior FFO) / Prior FFO

Sources of FFO Growth:
1. Same-store NOI growth (organic)
2. Acquisitions (external)
3. Development completions (external)
4. Share buybacks (EPS accretion)
```

---

### 3.4 Development Metrics

#### Yield on Cost
```
Yield on Cost = Stabilized NOI / Total Development Cost

Spread vs. Cap Rate = Yield on Cost - Market Cap Rate
```
> **Spread > 150bps = value-creating development.** Spread < 100bps = marginal, may not be worth the risk.

#### Development Pipeline as % of NAV
```
Development Pipeline % = Under-Development Cost / NAV

Safe: < 10% of NAV
Active: 10-20%
Aggressive: > 20% (higher risk)
```

#### Stabilized Yield Analysis
```
Value Creation = (Stabilized Value - Development Cost) / Development Cost
               = (Stabilized NOI / Cap Rate - Development Cost) / Development Cost
```

---

## 4. KEY RISK FACTORS (REIT-Specific)

### 4.1 Interest Rate Risk
> **THE dominant risk for all REITs.** Rising rates hit REITs through two channels: (1) higher cap rates reduce NAV, (2) higher interest expense reduces FFO.

**Quantitative Indicators:**
- Duration of rate sensitivity: Every 100bps rise in 10Y UST → cap rates expand 75-100bps → NAV declines 10-15%
- % of debt at fixed vs. floating rate (floating = more exposed)
- Weighted average debt maturity (shorter = more refinancing risk)
- Debt/EBITDA trending higher

**Formula:**
```
NAV Sensitivity = -Property Value × (ΔCap Rate / Cap Rate)
Example: $1B portfolio, 5% cap rate → 100bp increase → $1B × (0.01/0.05) = $200M NAV loss (-20%)
```

### 4.2 Tenant Concentration / Credit Risk
> A single tenant bankruptcy can devastate a REIT's NOI. JCPenney's bankruptcy killed multiple mall REITs.

**Quantitative Indicators:**
- Top 10 tenant concentration (% of ABR — Annual Base Rent)
- % of tenants rated investment grade
- Anchor tenant exposure (retail)
- Single-tenant exposure (net lease)

**Red Flags:**
```
Top tenant > 10% of ABR → HIGH RISK
Top 3 tenants > 25% of ABR → CONCENTRATED
Top 10 tenants > 50% of ABR → VERY CONCENTRATED
```

### 4.3 Lease Rollover Schedule
> Large lease expirations in a weak market = rent resets at lower rates.

**Quantitative Indicators:**
```
% of ABR expiring each year (next 5 years)
Rent roll-down risk = Σ (Expiring Rent_i - Market Rent_i) × SF_i / Total NOI
```

| Rollover Profile | Risk Level |
|-----------------|-----------|
| < 15% expiring annually | Low |
| 15-25% expiring annually | Moderate |
| > 25% in single year | **HIGH** |
| > 25% in single year AND market rents declining | **CRITICAL** |

### 4.4 Development Risk
> Development is high-risk, high-reward. Cost overruns and lease-up failures can destroy value.

**Quantitative Indicators:**
- Development pipeline as % of total assets
- Pre-leasing % for developments under construction
- Historical yield-on-cost vs. projection accuracy
- Construction cost inflation trends

### 4.5 Regulatory / Zoning Risk
> Government intervention can cap rents or restrict operations.

**Key Risks:**
- Rent control (multifamily — NYC, CA, OR)
- Eviction moratoriums (COVID-era demonstrated massive risk)
- Zoning restrictions (data center power, industrial locations)
- Environmental regulations (asbestos, PFAS, climate)
- Property tax increases (Illinois, New Jersey, Texas)

### 4.6 Property Type Structural Decline
> Some property types face secular (not cyclical) demand decline.

| Property Type | Structural Threat | Quantitative Signal |
|---------------|------------------|---------------------|
| Office | Remote/hybrid work | Occupancy stuck <70% nationally, sublease rate >3% |
| Mall/Retail | E-commerce | Tenant sales declining, store closures accelerating |
| Strip centers | Retail evolution | Big-box tenant bankruptcies |

### 4.7 Refinancing Risk
> The "debt maturity wall" — if debt matures when rates are high and credit is tight, REITs face distress.

**Quantitative Indicators:**
```
Years of Runway = Weighted Average Debt Maturity
Near-term Maturity % = Debt maturing in next 3 years / Total Debt

Danger: > 35% maturing in next 3 years
Severe: > 50% maturing in next 3 years AND LTV > 50%
```

---

## 5. QUALITY INDICATORS — What Makes a "Good REIT"?

### Top 10 Quality Indicators (Ranked)

| Rank | Indicator | Formula/Target | Why It Matters |
|------|-----------|---------------|----------------|
| 1 | **Balance sheet strength** | Net Debt/EBITDA < 5.0x, Fixed charge coverage > 3.0x | Survives downturns, flexible capital allocation |
| 2 | **Same-store NOI growth** | Consistent 3%+ (property-type dependent) | Organic value creation, pricing power |
| 3 | **Occupancy premium to market** | Occupancy > market average by 200+bps | Best-in-class operations, sticky tenants |
| 4 | **WALT stability** | WALT > 5 years, staggered expirations | Predictable cash flows, no cliff risk |
| 5 | **AFFO payout ratio discipline** | 65-85%, never > 90% | Dividend is safe, retains capital for growth |
| 6 | **Development yield spread** | Yield on cost > cap rate + 150bps | Accretive growth, not dilutive empire-building |
| 7 | **Low tenant concentration** | Top 10 tenants < 30% of ABR | Diversified income, single-tenant bankruptcy won't crush |
| 8 | **Investment-grade credit rating** | BBB- or higher | Access to capital markets, lower cost of debt |
| 9 | **Management track record** | 5+ year FFO/share CAGR, NAV creation history | REITs are actively managed — management MATTERS |
| 10 | **Property quality/location** | Infill/suburban growth markets, irreplaceable locations | Real estate is LOCATION — can't fix bad location |

### Composite Quality Score
```
Quality Score = Σ (Indicator_i × Weight_i)

Weights: Balance sheet (25%), Growth (20%), Operations (20%), 
         Dividend safety (15%), Management (10%), Location (10%)
```

---

## 6. STRESS TEST SCENARIOS

### Scenario 1: Cap Rate Expansion (Interest Rate Shock)

**Assumption:** 200bp rise in cap rates across the portfolio

```
Pre-Stress:  NOI = $500M, Cap Rate = 5.0%, Property Value = $10.0B
Post-Stress: NOI = $500M, Cap Rate = 7.0%, Property Value = $7.14B

NAV Decline = $10.0B - $7.14B = $2.86B (-28.6%)

If Debt = $5.0B:
Pre-Stress:  Equity = $5.0B, LTV = 50%
Post-Stress: Equity = $2.14B, LTV = 70% ← near distress
```

**Impact Channels:**
- NAV destruction: -28.6%
- Stock price typically falls 20-30% (market anticipates)
- Refinancing becomes more expensive
- Acquisition pipeline likely halted

---

### Scenario 2: Occupancy Shock (Major Tenant Bankruptcy)

**Assumption:** Anchor tenant (10% of NOI) bankrupts, property re-leases at 20% below prior rent after 12 months vacancy

```
Pre-Shock:   NOI = $500M
Immediate:   NOI drops 10% = $450M (-$50M)
Re-leased:   NOI = $450M - ($50M × 20%) = $440M (-12% total)

If cap rate = 5%:
Property Value pre:  $500M / 5% = $10.0B
Property Value post: $440M / 5% = $8.8B (-$1.2B, -12%)

Impact amplified if:
- Co-tenancy clauses trigger (other tenants can leave)
- Property is levered (equity takes full hit)
```

---

### Scenario 3: Refinancing Crisis

**Assumption:** $2B debt matures. Market rates risen from 3.5% to 7.5%. Original terms: 3.5% fixed, 10-year. New terms: 7.5% fixed.

```
Pre-Refinancing:  Interest = $2B × 3.5% = $70M/year
Post-Refinancing: Interest = $2B × 7.5% = $150M/year
Additional Interest = $80M/year

If NOI = $500M:
Pre:  FFO = $500M - $70M - G&A = ~$380M
Post: FFO = $500M - $150M - G&A = ~$300M (-21%)

FFO per share: $3.80 → $3.00 (-21%)
Stock impact:  -20% to -25% (P/FFO multiple may compress too)
```

**If the REIT cannot refinance (credit freeze):**
- Forced asset sales at distressed prices
- Potential equity issuance (dilutive)
- Worst case: bankruptcy/restructuring

---

### Scenario 4: Market Rent Decline (10% Decline, Lease Rollover)

**Assumption:** Market rents decline 10%. 25% of leases roll over in Year 1 into the weaker market.

```
Pre-Decline:     NOI = $500M
Year 1 Impact:   25% of leases × -10% rent = -2.5% NOI decline
                 NOI = $500M × 0.975 = $487.5M (-$12.5M)

If rollover continues in Years 2-3:
Year 2: Additional 20% at -10% → cumulative -4.5%
Year 3: Additional 15% at -10% → cumulative -6.0%

Steady-state NOI = $470M (-6% from peak)
Property value at 5% cap rate: $10.0B → $9.4B (-$600M)

With operating leverage (fixed costs):
NOI decline = -6% but FFO decline = -8% to -12%
```

---

## 7. PEER COMPARISON FRAMEWORK

### 7.1 Comparison Rules

| Rule | Rationale |
|------|-----------|
| **Same property type ONLY** | Office and data center have totally different economics |
| **Same geography** | US, European, Asian cap rates differ significantly |
| **Similar quality grade** | Class A office vs. Class B are different products |
| **Similar size/market cap** | Small-cap REITs trade at discounts for liquidity |
| **Same lifecycle stage** | Development-heavy vs. stabilized portfolios |

### 7.2 Comparison Metrics Table

| Metric | Why Compare | What to Look For |
|--------|------------|------------------|
| Cap Rate | Valuation level | Lower = higher quality/premium market |
| LTV | Balance sheet risk | Lower = safer, but may be inefficient |
| WALT | Cash flow visibility | Longer = more stable |
| Lease Spreads | Growth trajectory | Higher = pricing power |
| Same-Store NOI Growth | Organic growth | Consistent outperformance = good management |
| AFFO Payout Ratio | Dividend safety | 65-85% = sustainable sweet spot |
| P/FFO Multiple | Market pricing | Premium = market expects outperformance |
| Premium/Discount to NAV | Valuation vs. assets | Context-dependent (see Section 2.1) |
| Debt/EBITDA | Leverage | < 5.0x = conservative |
| Interest Coverage | Debt service ability | > 3.5x = comfortable |

### 7.3 Example Peer Comparison: Industrial REITs

| Metric | Prologis (PLD) | Realty Income (O) | Sector Avg |
|--------|---------------|-------------------|------------|
| Cap Rate (implied) | 4.5% | 6.0% | 5.0% |
| LTV | 28% | 35% | 35% |
| WALT | 4.5 years | 9.5 years | 5.5 years |
| Same-Store NOI Growth | 6.5% | 2.0% | 4.0% |
| AFFO Payout | 65% | 75% | 72% |
| P/FFO | 24x | 15x | 20x |
| Debt/EBITDA | 4.2x | 5.0x | 5.0x |
| Premium to NAV | +15% | +5% | +5% |

> **Key insight:** Prologis trades at a premium (24x FFO, +15% NAV) because of superior growth (6.5% same-store NOI) and global scale. Realty Income trades at lower multiple but offers bond-like stability with net leases and monthly dividends.

---

## 8. REPLACEMENT TABLE: Standard Framework → REIT Framework

| Standard Component | REIT Replacement | Rationale |
|--------------------|-----------------|-----------|
| **DCF (FCF-based)** | **NAV Model + FFO/AFFO Multiple** | FCF understates REIT cash flow (adds back depreciation). Real estate appreciates while depreciation reduces book value. NAV captures liquidation value; FFO multiple captures operating performance. |
| **ROIC** | **FFO Return on NAV (or Cash-on-Cash Yield)** | ROIC uses GAAP invested capital which is depreciated and understated. FFO/NAV measures cash return on real market value. |
| **Operating Leverage** | **Same-Store NOI Growth + Lease Spread Analysis** | REIT operating leverage comes from fixed property costs vs. variable rents. Same-store growth shows revenue-to-cost leverage. Lease spreads show pricing power. |
| **P/E** | **P/FFO or P/AFFO** | GAAP earnings include massive depreciation charges that don't represent economic reality. FFO adds back real estate depreciation. |
| **FCF Yield** | **AFFO Yield (AFFO / Market Cap)** | AFFO is the REIT equivalent of FCF — funds available after maintenance CapEx, leasing costs, and working capital. |
| **SBC (Stock-Based Compensation)** | **REIT SBC is minimal** | REITs rarely use significant stock compensation (unlike tech). If present, it represents dilution. Add back to AFFO if non-cash, but monitor share count growth. |
| **Revenue growth** | **Same-Store NOI Growth + Development Pipeline Yield** | Revenue growth from acquisitions is external, not organic. Same-store NOI growth is the pure organic metric. Development yield shows accretive growth potential. |
| **EBITDA** | **NOI (Net Operating Income)** | NOI is property-level EBITDA. Use NOI for REITs, not corporate EBITDA. |
| **Book Value** | **NAV (Net Asset Value)** | GAAP book value is meaningless — properties carried at depreciated historical cost, often 50%+ below market value. NAV uses market-based cap rates. |
| **Debt/Equity** | **LTV + Debt/EBITDA + Interest Coverage** | Debt/Equity uses GAAP equity which is understated. LTV uses market-value assets. Multiple debt metrics needed for full picture. |
| **Working Capital** | **Minimal importance** | REITs don't have traditional working capital cycles (no inventory, no receivables in the traditional sense). Focus on leasing pipeline, not working capital. |
| **Capex** | **Recurring CapEx + Development Capex** | Separate maintenance CapEx (deduct from FFO → AFFO) from development CapEx (growth investment). Both matter but are treated differently. |

---

## 9. REVERSE ENGINEERING: What Does the Price Imply?

### 9.1 Trading at 1.2x NAV (20% Premium)

**What the market is saying:**
- The REIT's properties are worth 20% more than their individual appraised values (portfolio premium)
- Management will create additional value through development, leasing, or operations
- The portfolio has below-market rents with positive lease spreads (embedded growth)
- Properties are irreplaceable or in supply-constrained markets

**Implied required return:**
```
If NAV per share = $100, Price = $120 (1.2x)
Implied return = (NOI / NAV) + Growth Rate = Cap Rate + Growth
Example: 5% cap rate + 3% growth = 8% return
vs. trading at NAV: 5% cap rate + 3% growth = 8% return, but $20 less capital

Premium implies market expects:
- FFO growth > 5% annually, OR
- NAV accretion from development > 2% annually, OR
- Cap rate compression in the portfolio's market
```

**When premium is NOT justified:**
- LTV > 50% (equity is riskier than NAV suggests)
- Lease rollover in next 2 years into weak market
- Development pipeline > 20% of NAV (execution risk)
- AFFO payout > 90% (no retained earnings for growth)

---

### 9.2 Dividend Yield of 3% vs. Sector Average of 4%

**What the market is saying:**
```
Yield = Annual Dividend / Stock Price

3% yield vs. 4% average → Stock price is 33% higher relative to dividend
= Market expects above-average dividend growth, OR
= Market expects above-average capital appreciation, OR
= The REIT has superior asset quality warranting a premium
```

**Implied growth rate (Gordon Growth Model):**
```
Required Return (r) = Risk-free rate + Equity risk premium
                   = 4.5% + 4.0% = 8.5%

If Yield = 3%:  Implied growth = r - Yield = 8.5% - 3% = 5.5%
If Yield = 4%:  Implied growth = r - Yield = 8.5% - 4% = 4.5%

The 3% yield REIT needs to grow dividends 100bps faster to justify valuation.
```

**Reality check:**
- Can this REIT grow FFO 5.5%+? (vs. sector average 4%)
- Does it have lease spreads, development pipeline, or acquisition capacity to support this?
- If not, the 3% yield may be overvalued — the dividend is "too low" for the growth profile.

**When 3% yield is justified:**
- Same-store NOI growth > 5% (vs. 3% sector)
- Development pipeline yielding 150bps+ spread to cap rate
- Investment-grade balance sheet with low LTV
- WALT > 7 years (stable cash flow base)

**When 3% yield is a SELL signal:**
- FFO growth is actually 2-3% (market overestimating)
- Lease rollover headwinds in next 2 years
- AFFO payout > 85% (no room to grow dividend)

---

### 9.3 Reverse Engineering Checklist

| Observation | Likely Interpretation | Verify By |
|-------------|----------------------|-----------|
| P/FFO > 25x | Market expects 8%+ FFO growth | Check development pipeline, lease spreads |
| P/FFO < 12x | Market expects stagnation/decline, or structural issue | Check occupancy, sublease rate, debt maturity |
| Premium to NAV > 15% | Market values management/platform | Check historical NAV creation, track record |
| Discount to NAV > 15% | Market fears NAV overstatement or balance sheet risk | Check debt maturity, occupancy, lease rollovers |
| Yield > 6% | Market pricing dividend cut | Check AFFO payout ratio, FFO trend |
| Yield < 2.5% | Growth REIT or overpriced | Check if growth justifies the yield compression |

---

## 10. ACCOUNTING RED FLAGS

### 10.1 Straight-Line Rent Smoothing

**The Issue:** GAAP requires REITs to recognize rent evenly over lease term, even if actual cash rent escalates. This creates a gap between reported revenue and actual cash received.

```
Straight-Line Rent Adjustment = Average Rent over Lease Term - Cash Rent Received

If rents are back-loaded (typical): Reported revenue > Cash received
If rents are front-loaded: Reported revenue < Cash received
```

**Red Flag:** Large and growing straight-line rent receivable on balance sheet. This is essentially an accounting asset with no cash backing it.

**Detection:**
```
Straight-Line Rent Receivable / Total Assets > 5% → FLAG
Compare reported FFO to actual cash from operations — large divergence = concern
```

---

### 10.2 CapEx Under-Reporting (FFO vs. AFFO Gap)

**The Issue:** Some REITs report "FFO" but understate recurring CapEx, making FFO appear higher than sustainable cash flow.

```
FFO to AFFO Gap = FFO - AFFO
                 = Recurring CapEx + Leasing Commissions + Tenant Improvements

Typical Gap by Property Type:
- Net Lease: 5-10% of FFO
- Industrial: 10-15% of FFO
- Office: 15-20% of FFO
- Multifamily: 15-20% of FFO
- Self-Storage: 10-15% of FFO
- Data Center: 8-12% of FFO
```

**Red Flag:**
```
If (FFO - AFFO) / FFO < 5% → Likely UNDER-REPORTING CapEx
Compare to peers — if this REIT's gap is much smaller, dig deeper
Check if "recurring CapEx" excludes major categories
```

---

### 10.3 Related-Party Transactions (Sponsored REITs)

**The Issue:** External management structures create conflicts of interest. Management may prioritize fees over shareholder returns.

**Red Flags:**
- External management structure (vs. internalized)
- Transactions with affiliated entities (acquisitions, development services, property management)
- Management fees based on assets (not performance)
- Above-market compensation relative to peers
- Complex organizational structures with multiple related entities

**Detection:**
```
Related-Party Revenue / Total Revenue > 10% → FLAG
G&A / Revenue > 15% → FLAG (vs. 5-8% for well-run REITs)
Management fee as % of assets > 0.5% annually → High
```

> **Note:** Many REITs have moved to internalized management. External management is more common in smaller/non-US REITs and is generally viewed negatively by institutional investors.

---

### 10.4 Valuation Methodology Changes for Level 3 Assets

**The Issue:** REITs must fair-value certain assets (development projects, unconsolidated JVs) using Level 3 inputs (unobservable, management-estimated). Changing valuation assumptions can inflate NAV.

**Red Flags:**
- Change in cap rate assumptions used for Level 3 valuations
- Change in discount rates for development projects
- Change in estimated completion costs or timelines
- Valuations consistently higher than third-party appraisals

**Detection:**
```
Compare disclosed cap rates to market transaction cap rates
If Level 3 cap rate is 50bps+ below market → OVERVALUATION
Track changes in assumptions quarter-over-quarter
```

---

### 10.5 Debt Classification Games

**The Issue:** REITs may reclassify debt to make leverage ratios appear lower.

**Tricks to watch for:**
- JV debt not consolidated (off-balance sheet)
- Preferred stock classified as equity (it's really debt)
- Convertible debt with favorable terms
- Debt guarantees to JVs not fully disclosed

**Detection:**
```
Look-Brough Leverage = (Reported Debt + JV Debt + Preferred) / (GAV + JV Assets)

If Look-Through Debt/EBITDA > Reported by 1.0x+ → Material off-BS debt
Preferred / Total Capital > 10% → Treat as debt
```

---

### 10.6 Other Red Flags

| Red Flag | Detection Method | Severity |
|----------|-----------------|---------|
| Frequent asset impairments | Write-downs > 5% of assets annually | High |
| Declining occupancy with rising rents | Cross-check — are they giving concessions? | Medium |
| Acquisitions at cap rates below borrowing cost | Spread negative = value destructive | High |
| Increasing reliance on equity issuance for growth | Shares outstanding growing > 5%/year | Medium |
| Changing same-store pool definition | Pool changes that boost reported growth | Medium |
| High tenant improvement allowances | TI > 1 year of rent for renewals | Medium |
| G&A growing faster than NOI | G&A growth > NOI growth for 2+ years | Medium |

---

## WORKED EXAMPLE: Industrial REIT Valuation

### Given Parameters

| Parameter | Value |
|-----------|-------|
| NOI | $500M |
| Cap Rate | 5.0% |
| Total Debt | $2,000M |
| Preferred Equity | $0 |
| Shares Outstanding | 100M |
| Annual Recurring CapEx | $100M |
| Leasing Commissions + TI | $30M |
| Annual Dividend | $2.50/share |
| Occupancy | 90% |
| WALT | 5 years |
| Same-Store NOI Growth | 4.0% |
| Development Pipeline | $300M (yield on cost: 7.0%) |
| Weighted Avg Debt Maturity | 6 years |
| Avg Interest Rate on Debt | 4.0% |
| Straight-Line Rent Adjustment | $15M |

---

### Step 1: NAV Valuation

```
Property Value = NOI / Cap Rate
               = $500M / 5.0%
               = $10,000M ($10.0B)

NAV = Property Value - Debt - Preferred + Cash
    = $10,000M - $2,000M - $0 + $0
    = $8,000M ($8.0B)

NAV per Share = $8,000M / 100M shares = $80.00/share
```

---

### Step 2: FFO Calculation

```
Net Income proxy: We use NOI-based approach
FFO = NOI - Interest Expense - G&A + Non-cash items
    = $500M - ($2,000M × 4.0%) - $40M (est. G&A) + $0
    = $500M - $80M - $40M
    = $380M

FFO per Share = $380M / 100M = $3.80/share

P/FFO at various prices:
- At $80 (NAV):  80 / 3.80 = 21.1x
- At $90:        90 / 3.80 = 23.7x
- At $70:        70 / 3.80 = 18.4x
```

---

### Step 3: AFFO Calculation

```
AFFO = FFO - Recurring CapEx - Leasing Commissions - Straight-Line Rent
     = $380M - $100M - $30M - $15M
     = $235M

AFFO per Share = $235M / 100M = $2.35/share

P/AFFO at various prices:
- At $80:  80 / 2.35 = 34.0x
- At $90:  90 / 2.35 = 38.3x
- At $70:  70 / 2.35 = 29.8x
```

---

### Step 4: Dividend Analysis

```
Dividend per Share = $2.50
Total Dividends = $2.50 × 100M = $250M

FFO Payout Ratio  = $250M / $380M = 65.8% ✓ (Healthy)
AFFO Payout Ratio = $250M / $235M = 106.4% ⚠️ (OVER 100%!)

Dividend Yield:
- At $80: 2.50 / 80 = 3.13%
- At $90: 2.50 / 90 = 2.78%
- At $70: 2.50 / 70 = 3.57%
```

> **⚠️ CRITICAL FINDING:** The AFFO payout ratio is 106.4%. This REIT is paying out MORE in dividends than it generates in sustainable cash flow. The $2.50 dividend is NOT sustainable without either: (a) NOI growth, (b) reduced CapEx, or (c) using debt/cash reserves.

---

### Step 5: Debt Metrics

```
LTV = Debt / Property Value = $2,000M / $10,000M = 20.0% ✓ (Conservative)

Debt/EBITDA (using NOI as proxy):
EBITDA = NOI - G&A = $500M - $40M = $460M
Net Debt/EBITDA = $2,000M / $460M = 4.3x ✓ (Reasonable)

Interest Coverage = NOI / Interest Expense = $500M / $80M = 6.25x ✓ (Strong)

WACD = 4.0% ✓ (Low cost of debt)
Debt Maturity = 6 years ✓ (Comfortable runway)
```

---

### Step 6: Development Analysis

```
Development Pipeline = $300M
Yield on Cost = 7.0%
Stabilized NOI from Development = $300M × 7.0% = $21M

Spread to Cap Rate = 7.0% - 5.0% = 200bps ✓✓ (Excellent, >150bps)

Value Created at Stabilization:
Stabilized Value = $21M / 5.0% = $420M
Value Creation = $420M - $300M = $120M (+40%)
Development as % of NAV = $300M / $8,000M = 3.75% ✓ (Conservative)
```

---

### Step 7: Premium/Discount Assessment

| Price | Premium to NAV | P/FFO | Dividend Yield | Assessment |
|-------|---------------|-------|----------------|------------|
| $80 | 0% (at NAV) | 21.1x | 3.13% | Fair for quality industrial |
| $90 | +12.5% | 23.7x | 2.78% | Premium — needs growth justification |
| $70 | -12.5% | 18.4x | 3.57% | Discount — IFF dividend sustainable |

---

### Step 8: Stress Test Summary

| Scenario | Impact on NAV | Impact on FFO | Dividend Safety |
|----------|--------------|---------------|-----------------|
| Cap rate +200bp | NAV: $80 → $57 (-29%) | Minimal direct | AFFO payout worsens |
| 10% occupancy drop | NAV: $80 → $72 (-10%) | FFO: $3.80 → $3.40 (-11%) | **Dividend at risk** |
| Refinancing at +300bp | NAV: minimal | FFO: $3.80 → $3.20 (-16%) | **Dividend at risk** |
| 10% rent decline | NAV: $80 → $75 (-6%) | FFO: $3.80 → $3.50 (-8%) | **Dividend at risk** |

---

### Step 9: Final Valuation Conclusion

```
BASE CASE VALUE: $75 - $82 per share
- NAV: $80
- P/FFO = 20x × $3.80 = $76
- P/AFFO = 30x × $2.35 = $70.50
- DDM: $2.50 / (8.5% - 3%) = $45.45 (dividend too high for AFFO!)

BULL CASE: $90 - $100
- Requires: Cap rate compression, NOI grows 6%+, development delivers

BEAR CASE: $55 - $65
- Requires: Cap rate expansion, occupancy drops, dividend cut
```

**⚠️ KEY RISK:** The $2.50 dividend ($250M) exceeds AFFO ($235M). This is a **red flag for dividend sustainability.** Either:
1. The REIT will cut the dividend to ~$2.20 (88% AFFO payout)
2. NOI must grow >6% to make the math work
3. The REIT is funding dividends with debt (unsustainable)

**Fair Value Estimate: $75-80/share** with a **DIVIDEND CUT WARNING** on the $2.50 payout.

---

## APPENDIX: Quick Reference Formulas

### Core Valuation
```
Property Value = NOI / Cap Rate
NAV = Property Value - Net Debt
FFO = Net Income + Depreciation - Gains on Sales
AFFO = FFO - Recurring CapEx - Leasing Costs - Straight-Line Rent
```

### Key Ratios
```
Cap Rate = NOI / Property Value
LTV = Debt / Property Value
Interest Coverage = NOI / Interest Expense
Debt/EBITDA = Net Debt / EBITDA
FFO Payout = Dividends / FFO
AFFO Payout = Dividends / AFFO
```

### Growth
```
Same-Store NOI Growth = ΔNOI (same properties) / Prior NOI
Lease Spread = (New Rent - Old Rent) / Old Rent
Yield on Cost = Stabilized NOI / Development Cost
```

### mREIT Specific
```
Net Interest Margin = Interest Income - Interest Expense / Assets
Book Value per Share = Equity / Shares
Economic Return = ΔBook Value + Dividends / Beginning BV
Leverage = Total Assets / Equity
```

---

## APPENDIX: Property Type Quick Reference

| Type | Cap Rate | WALT | Same-Store Growth | P/FFO | Yield | Key Metric |
|------|----------|------|-------------------|-------|-------|------------|
| Industrial | 4.5-6% | 4-7 yr | 5-10% | 20-28x | 2.5-3.5% | Rent/sq ft vs. market |
| Data Center | 5-7% | 7-12 yr | 6-12% | 18-25x | 2.5-3.5% | MW leased |
| Multifamily | 4.25-5.5% | 1-2 yr | 3-6% | 18-24x | 3.0-4.0% | Rent/occupancy |
| Office | 6.5-9% | 5-8 yr | -2 to +2% | 8-14x | 4.5-7% | Tenant retention |
| Net Lease | 5.5-7.5% | 8-15 yr | 1-3% | 14-18x | 4.5-5.5% | % IG tenants |
| Self-Storage | 4.75-6% | N/A | 3-7% | 20-26x | 2.5-3.5% | Street rates |
| Healthcare | 7.5-9.5% | 8-12 yr | 3-6% | 12-16x | 5.5-7% | Operator coverage |
| Cell Tower | 3.5-5.5% | 8-10 yr | 5-8% | 18-24x | 3.0-3.5% | Tower cash flow |
| Timber | 5-6% | N/A | 2-4% | 18-22x | 3.0-4.0% | Acreage value |
| mREIT | N/A | N/A | N/A | N/A | 8-15% | Price/Book |

---

*Document Version: 1.0 | Framework: Adaptive REIT Analysis Module | Last Updated: 2024*

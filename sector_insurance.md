# Sector Analysis Module: Insurance Companies

## Adaptive Framework Design — Insurance Sector Overrides

**Version:** 1.0  
**Date:** July 2025  
**Scope:** Life Insurance, Property & Casualty (P&C), Reinsurance, Insurance Brokers  
**Classification:** Sector-Specific Override Module for Adaptive Equity Analysis Framework

---

## Executive Summary

Standard equity analysis frameworks fail for insurers because:
- **No meaningful "free cash flow"**: Premiums received today fund claims paid years later ("float"). DCF on free cash flow is conceptually flawed.
- **Long-duration liabilities**: Life insurance policies generate cash flows over 20-40 years. Book value is a poor proxy for economic value.
- **Reserves are estimates, not facts**: P&C loss reserves are actuarial projections. Under-reserving creates phantom earnings.
- **Regulatory capital is binding**: Insurers are constrained by Solvency II, RBC, or local capital requirements — not just economic logic.

**This module replaces the base framework's DCF/FCF/ROIC methodology with insurance-appropriate tools:** Embedded Value for Life, Combined Ratio + Float for P&C, and specialized metrics for Reinsurance and Brokers.

---

## 1. SECTOR DETECTION RULES

### 1.1 Auto-Detection Logic

| Detection Signal | Weight | Threshold | Notes |
|-----------------|--------|-----------|-------|
| SIC/NAICS codes | 90% | SIC 63xx, NAICS 524xx | Primary detection |
| "Insurance" in company name | 70% | Case-insensitive match | Confirmatory only |
| "Premiums earned" on income statement | 95% | Presence of line item | Strong signal |
| "Policyholder reserves" on balance sheet | 95% | Presence of line item | Strong signal |
| "Loss reserves" or "Claim reserves" | 90% | Presence of line item | Strong signal |
| "Combined ratio" in disclosures | 90% | Any mention | P&C/Reinsurance signal |
| "Embedded value" in disclosures | 90% | Any mention | Life Insurance signal |
| "Value of new business" / "VNB" | 90% | Any mention | Life Insurance signal |
| "Float" discussed explicitly | 85% | Berkshire-style disclosure | P&C signal |
| "Catastrophe" / "Cat load" | 80% | In risk disclosures | P&C/Reinsurance signal |
| "Beneft reserve" / "Policy reserve" | 85% | Life-specific reserves | Life Insurance signal |
| "Acquisition cost" / "DAC" | 75% | Deferred Acquisition Costs | Insurance signal |

### 1.2 Sub-Sector Classification

Once detected as an insurer, classify into sub-sector using this decision tree:

```
INSURER DETECTED
├── Does company SELL insurance policies? (YES = Underwriter, NO = Broker)
│   ├── BROKER: Revenue from commissions/fees, no underwriting risk
│   │   ├── Retail brokers (e.g., Aon, Marsh McLennan, Willis Towers Watson)
│   │   ├── Wholesale/MGA brokers
│   │   └── Specialty brokers
│   │
│   └── UNDERWRITER: Bears insurance risk
│       ├── Does company assume risk from OTHER insurers? (YES = Reinsurer)
│       │   ├── Global reinsurers (e.g., Munich Re, Swiss Re, Hannover Re, SCOR)
│       │   ├── Bermuda reinsurers (e.g., Renaissance Re, Arch Capital)
│       │   └── Retrocession specialists
│       │
│       └── Does company underwrite DIRECT policies? (YES = Primary Insurer)
│           ├── LIFE INSURER: Long-duration contracts, mortality/longevity risk
│           │   ├── Traditional life (whole life, term life)
│           │   ├── Variable/Universal life
│           │   ├── Annuities (fixed, variable, indexed)
│           │   └── Health insurance (long-duration)
│           │   Examples: Aflac, Prudential (US), MetLife, AIA Group, Dai-ichi Life
│           │
│           └── P&C INSURER: Short-duration contracts, property/casualty risk
│               ├── Personal lines (auto, homeowners)
│               │   Examples: GEICO, Progressive, Allstate, State Farm
│               ├── Commercial lines (general liability, workers comp)
│               │   Examples: Chubb, Travelers, Hartford
│               └── Specialty lines (marine, aviation, cyber, D&O)
│                   Examples: Beazley, Hiscox, W. R. Berkley
```

### 1.3 Classification by Balance Sheet and Revenue Structure

| Feature | Life Insurance | P&C Insurance | Reinsurance | Brokers |
|---------|--------------|-------------|-------------|---------|
| **Avg policy duration** | 10-40 years | 6-12 months | 1-3 years | N/A (no policies) |
| **Key liability** | Policy reserves, benefit reserves | Loss reserves, UPR | Technical reserves, UPR | None (payables) |
| **Investment assets** | Very large (70-85% of assets) | Large (60-75% of assets) | Very large (80%+ of assets) | Minimal |
| **Revenue source** | Premiums + investment income | Net earned premiums | Net earned premiums | Commission/fees |
| **Profit driver** | Spread (investment - crediting), mortality | Underwriting margin + float | Underwriting + investment | Volume × commission rate |
| **Key ratio** | VNB margin, EV growth | Combined ratio | Combined ratio, ROE | EBITDA margin, organic growth |
| **Reserve duration** | Long (decades) | Short (1-5 years) | Medium (2-7 years) | N/A |

### 1.4 Data Source Verification

Confirm classification using:
- **SEC 10-K Item 1**: Business description — "We underwrite life insurance" vs. "We provide insurance brokerage"
- **10-K Revenue breakdown**: Look for "premiums earned" (underwriter) vs. "commissions" (broker)
- **Balance sheet**: Underwriters carry "unpaid loss reserves" and "unearned premium reserve"; brokers do not
- **NAIC Annual Statement** (for US insurers): Schedule P (loss development), Schedule D (investments)

---

## 2. VALUATION MODEL — WHAT REPLACES/ADAPTS DCF?

### 2.1 Why Standard DCF Fails for Insurers

| Standard Framework Element | Why It Fails for Insurers | What to Use Instead |
|---------------------------|--------------------------|---------------------|
| **FCF-based DCF** | Float means cash inflows today fund future claims. "Free cash flow" is not free — it's owed to policyholders. A growing insurer shows negative FCF (collecting premiums that become reserves). | Embedded Value (Life), Float-based valuation (P&C), Book Value + ROE (P&C) |
| **ROIC = NOPAT / Invested Capital** | Invested capital excludes policyholder liabilities (float), which are the primary funding source. ROIC massively overstates insurer returns. | ROE (measures return on equity capital only), ROEV (Return on Embedded Value for Life) |
| **Operating Leverage** | Revenue recognition is delayed (earned over policy term). Premiums written ≠ premiums earned. Fixed vs. variable cost distinction is blurred (claim costs are "variable" but reserved in advance). | Financial leverage (float/equity), Combined Ratio decomposition |
| **P/E multiple** | Earnings are smoothed by reserve changes. A P/E of 8x could mean cheap OR heavily under-reserved. P/E varies wildly with investment income (not core underwriting). | P/EV (Life), P/B with ROE adjustment (P&C), P/VNB (Life growth) |
| **SBC analysis** | Stock-based compensation is less common in insurers (asset-heavy, not tech). When present, dilutes tangible book value which is the primary valuation anchor. | Monitor dilution of book value per share, not just share count |
| **FCF Yield** | Meaningless for growing insurers (negative FCF is normal). Mature insurers may show positive FCF from reserve releases, but this is non-recurring. | Dividend yield + reserve growth yield, Float growth yield |

### 2.2 Life Insurance Valuation: Embedded Value (EV) Methodology

#### 2.2.1 Core Formula

```
Embedded Value (EV) = Adjusted Net Asset Value (ANAV) + Value of In-Force (VIF)

Appraisal Value (AV) = EV + Value of New Business (VNB) × Franchise Multiple
                     = ANAV + VIF + (VNB × Franchise Multiple)
```

**Adjusted Net Asset Value (ANAV):**
```
ANAV = Market Value of Shareholders' Assets - Market Value of Liabilities
     = Statutory Surplus 
       + Unrealized Gains on Investments
       - Intangible Assets (goodwill, DAC)
       +/- Other Adjustments (surplus notes, subordinated debt)
```

**Value of In-Force (VIF):**
```
VIF = PVFP - CoC

Where:
  PVFP = Present Value of Future Profits from existing policies
       = Σ [ (Projected Premiums + Investment Income - Claims - Expenses - Taxes) / (1 + r)^t ]
  
  CoC = Cost of Capital (frictional cost of holding required capital)
      = Required Capital × (Hurdle Rate - After-Tax Investment Return on Required Capital)
```

#### 2.2.2 European Embedded Value (EEV) Enhancement

EEV adds explicit recognition of financial options and guarantees:

```
EEV = ANAV + PVFP - CoC - TVFOG

Where TVFOG = Time Value of Financial Options and Guarantees
  (e.g., guaranteed minimum crediting rates on universal life, 
   guaranteed annuity options, minimum death benefits)
```

**Example — AIA Group (2024):**
| Component | USD Billions |
|-----------|-------------|
| Adjusted Net Asset Value | ~$28.0 |
| Value of In-Force (VIF) | ~$43.6 |
| **Embedded Value** | **~$71.6** |
| Value of New Business (VNB) | $4.71 |
| VNB Margin | 54.5% |

#### 2.2.3 Market Consistent Embedded Value (MCEV) — Best Practice

MCEV eliminates subjective discount rate choices by using market-observable inputs:

```
MCEV = ANAV + PVFP(market-consistent) - TVFOG - FC - CRNHR

Where:
  PVFP(market-consistent) = Discounted at swap curve (risk-free), not risk-adjusted rate
  TVFOG = Time Value of Financial Options and Guarantees (stochastic valuation)
  FC = Frictional Costs of holding required capital
  CRNHR = Cost of Residual Non-Hedgeable Risk (99.5% VaR for mortality, lapse, expense risks)
```

**Why MCEV matters:**
- Eliminates company-specific assumption gaming (under TEV, companies choose their own risk discount rate)
- All financial risk valued consistently with capital markets (swap rates, implied volatilities)
- Enables cross-company comparison
- Required by CFO Forum for European insurers; increasingly adopted in Asia

**Example — SOMPO Himawari Life (March 2025):**
| Component | JPY Billions |
|-----------|-------------|
| MCEV | 1,211.9 |
| Adjusted Net Worth | (225.3) |
| Value of In-Force | 1,437.2 |
| New Business Value | 28.9 |

> Note: Negative ANW due to rising interest rates reducing bond unrealized gains, offset by higher VIF from higher discount rates. This illustrates why ANAV + VIF must be viewed together.

#### 2.2.4 Appraisal Value: Adding Franchise Value

```
Appraisal Value = EV + Franchise Value
                = EV + (VNB × Franchise Multiple)

Franchise Multiple = 1 / (Discount Rate - VNB Growth Rate)
                   = 1 / (r - g)
```

Typical franchise multiples range from 8x to 15x depending on:
- VNB growth trajectory
- Competitive moat (distribution, brand)
- Margin sustainability
- Market penetration potential

**Example — AIA Group (2024):**
- VNB = $4.71B, growing at ~15% annually
- At 12x franchise multiple: Franchise Value = $56.5B
- EV = $71.6B
- Appraisal Value = ~$128B
- Market cap ~$100B → trading at ~0.78x Appraisal Value (reasonable given growth execution risk)

#### 2.2.5 Dividend Discount Model (DDM) — Secondary Approach

For stable, mature life insurers with predictable dividend policies:

```
Value = D₁ / (r - g)

Where:
  D₁ = Expected dividend next year (often based on dividend payout ratio × EV earnings)
  r = Cost of equity (CAPM or implied)
  g = Long-term dividend growth rate (typically 3-5% for mature markets)
```

DDM is most appropriate for:
- Mature life insurers in slow-growth markets (Japan, Western Europe)
- Mutual insurers converting to stock form
- Dividend-focused investors assessing yield-attractiveness

### 2.3 P&C Insurance Valuation

#### 2.3.1 Combined Ratio as the Primary Profitability Metric

```
Combined Ratio = Loss Ratio + Expense Ratio
               = (Incurred Losses / Earned Premiums) + (Underwriting Expenses / Written Premiums)
```

| Combined Ratio Zone | Interpretation |
|-------------------|----------------|
| **Below 95%** | Excellent underwriting discipline. Negative cost of float (being PAID to hold float). |
| **95-100%** | Good underwriting. Free or nearly-free float. |
| **100%** | Break-even underwriting. Float is costless. Investment income on float = pure profit. |
| **100-105%** | Marginal underwriting. Modest cost of float. May still be profitable if investment income exceeds underwriting loss. |
| **Above 105%** | Poor underwriting discipline. Float is expensive. |
| **Above 110%** | Crisis territory. Significant capital destruction likely. |

**Example — Progressive (2023):**
- Loss Ratio: ~68%
- Expense Ratio: ~22%
- Combined Ratio: ~90% → underwriting profit of 10% of premiums
- With $50B+ of float, this generates enormous value

**Example — Berkshire Hathaway (historical):**
- 53 of 57 years generated underwriting profit (Combined Ratio < 100%)
- In 2013: underwriting profit = ~4% of $77B float = negative 4% cost of float
- "We are being paid to hold other people's money" — Warren Buffett

#### 2.3.2 Float-Based Valuation: The Berkshire Method

```
Float = Loss Reserves + Unearned Premium Reserve (UPR) + Loss Adjustment Expense Reserves
        - Agents' Balances Receivable - Premiums Receivable - Deferred Acquisition Costs

Simplified: Float ≈ Total Reserves - Receivables
```

**Float Valuation Framework:**

```
Intrinsic Value = (Float × Value per Dollar of Float) + Investments + Excess Capital

Value per Dollar of Float:
  - Negative cost float (CR < 95%): $1.00 - $1.50 per dollar of float
  - Free float (CR = 100%): ~$0.50 per dollar of float
  - Expensive float (CR > 105%): Negative value (liability, not asset)
```

**Berkshire Hathaway Float Analysis (1967-2023):**
| Year | Float ($B) | Avg Cost of Float | Cumulative Float Growth |
|------|-----------|-------------------|------------------------|
| 1967 | 0.017 | N/A | — |
| 1990 | 2.6 | Negative | 15.3% CAGR |
| 2000 | 27.6 | Negative | 26.3% CAGR |
| 2010 | 65.8 | Negative | 9.1% CAGR |
| 2020 | 138.0 | Negative | 7.7% CAGR |
| 2023 | ~168 | Negative | ~4% CAGR |

> "Float is wonderful — if it doesn't come at too high a price. Its cost is determined by our underwriting results." — Warren Buffett, 2014 Letter

#### 2.3.3 Book Value + Underwriting Profit DCF

For most P&C insurers, a practical two-stage model:

```
Value = Tangible Book Value + PV(Underwriting Profits) + PV(Investment Income on Float)

Stage 1 (Years 1-5): Project using explicit combined ratio, premium growth, investment yield
Stage 2 (Terminal): Gordon growth on normalized underwriting profit + investment income

Terminal Value = [Normalized Underwriting Profit + (Float × Investment Yield)] × (1 + g) / (r - g)
```

**Example — A P&C insurer with:**
- Tangible Book Value: $10B
- Combined Ratio: 96% (4% underwriting margin)
- Net Earned Premiums: $20B
- Float: $25B
- Investment yield: 4%
- Cost of equity: 10%
- Long-term growth: 3%

```
Annual underwriting profit = $20B × (1 - 0.96) = $0.8B
Annual investment income on float = $25B × 4% = $1.0B
Total annual value creation = $1.8B

Terminal Value = $1.8B × 1.03 / (0.10 - 0.03) = $26.5B
PV (5-year explicit) ≈ $6.0B
Total Value = $10B + $6.0B + $20.5B (terminal PV) ≈ $36.5B
```

#### 2.3.4 P/B-ROE Approach for P&C

For stable P&C insurers, a simpler relative valuation:

```
Justified P/B = (ROE - g) / (r - g)

Where:
  ROE = Return on Equity (sustainable, through cycle)
  g   = Long-term growth rate (typically 3-4%)
  r   = Cost of equity

Implied ROE from P/B = g + (P/B) × (r - g)
```

**Example:**
- A P&C insurer trades at 1.5x book value
- Cost of equity = 10%, growth = 3%
- Implied sustainable ROE = 3% + 1.5 × (10% - 3%) = 3% + 10.5% = 13.5%

### 2.4 Reinsurance Valuation

Reinsurers share P&C valuation DNA but with critical differences:

#### 2.4.1 Special Considerations

| Factor | Impact on Valuation |
|--------|-------------------|
| **Counterparty risk** | Reinsurers are exposed to cedent default. Monitor cedent credit quality. |
| **Retrocession dependency** | Reinsurers buy reinsurance too (retrocession). Concentration in retrocessionnaires creates systemic risk. |
| **Pricing cycles** | Reinsurance pricing is MORE cyclical than primary insurance. January 1 renewals drive annual repricing. |
| **Natural catastrophe exposure** | Cat risk is disproportionately concentrated in reinsurance. 1-in-100 year events can wipe out 1-2 years of earnings. |
| **Long-tail lines** | Asbestos, environmental, workers comp reserves can develop for decades. Reserve uncertainty is higher. |
| **Collateral requirements** | Increasing collateral demands from cedents reduce capital efficiency. |

#### 2.4.2 Reinsurance-Specific Valuation Adjustments

```
Adjusted Book Value = Reported Book Value
                      - Reserve Uncertainty Buffer (5-15% of long-tail reserves)
                      - Potential CAT Loss Buffer (1-in-100 year exposure)
                      + Excess Capital (above target solvency ratio)
```

**Reserve Uncertainty Buffer:**
```
Buffer = Σ (Reserve by Line × Uncertainty Factor)

Uncertainty Factors:
  - Short-tail lines (auto, property): 2-5%
  - Medium-tail lines (general liability): 10-20%
  - Long-tail lines (asbestos, workers comp): 20-40%
```

**Example — Munich Re:**
- Reported Book Value: ~EUR 35B
- Long-tail reserves: ~EUR 20B × 15% uncertainty = EUR 3B buffer
- 1-in-100 CAT exposure: EUR 2.5B buffer
- Adjusted Book Value: ~EUR 29.5B (16% discount)

#### 2.4.3 Cycle-Aware Valuation

Reinsurance pricing follows a clear cycle. Valuation must account for where we are in the cycle:

| Cycle Phase | Price Level | Combined Ratio (Forward) | Valuation Approach |
|-------------|------------|------------------------|-------------------|
| Hard market (post-cat) | Rising (+20-50%) | 85-95% | Premium to book; value growth |
| Hardening | Rising (+10-20%) | 90-98% | Premium to book |
| Soft market | Flat/declining | 98-105% | Discount to book |
| Deep soft market | Declining (-10-20%) | 105-115% | Deep discount to book |

**Current cycle indicators:** Monitor Guy Carpenter Global Property Catastrophe Rate on Line Index and January 1 renewal pricing data from major reinsurers.

### 2.5 Insurance Broker Valuation

Brokers are the exception — standard DCF and multiples WORK here because:
- No underwriting risk (no float, no reserves)
- Fee/commission-based revenue (earned when policy is placed)
- Standard working capital dynamics
- Traditional operating leverage applies

#### 2.5.1 Standard DCF with Broker Adjustments

```
Revenue = Total Insured Value × Commission Rate (typically 5-15%)
EBITDA Margin = 30-50% (large brokers)
FCF Conversion = 80-95% of EBITDA (low capex, minimal working capital)
```

**Key broker multiples:**
| Multiple | Typical Range | Notes |
|----------|--------------|-------|
| EV/Revenue | 3.5x - 6.0x | Revenue quality matters (recurring vs. one-time) |
| EV/EBITDA | 12x - 20x | Industry standard for large brokers |
| P/E | 20x - 30x | Reflects high margins, low capital intensity |
| FCF Yield | 3-5% | Lower than market due to growth premium |

**Example — Aon (2024):**
- Revenue: $13.4B
- Organic growth: 7% (strong pricing environment)
- EBITDA margin: ~34%
- EV/EBITDA: ~16x
- Key metric: Organic revenue growth (exposes true growth vs. M&A-driven)

#### 2.5.2 Broker-Specific Metrics

```
Organic Revenue Growth = Total Revenue Growth - M&A Growth - FX Impact

Revenue per Employee = Total Revenue / Employee Count
                       (Benchmark: $200K-$350K for large brokers)

Retention Rate = (Prior Year Clients Still Active) / (Total Prior Year Clients)
                 (Target: >90% for large commercial accounts)

Revenue/Client = Total Revenue / Number of Clients
```

---

## 3. KEY OPERATING METRICS (WITH FORMULAS)

### 3.1 Life Insurance Metrics

#### 3.1.1 Value of New Business (VNB) and Margin

```
VNB = Present Value of Future Profits from policies written THIS YEAR
    = PVFP(New Business) - CoC(New Business)

VNB Margin = VNB / APE

Or alternatively:
VNB Margin = VNB / PVNBP (Present Value of New Business Premiums)
```

| VNB Margin Range | Interpretation |
|-----------------|----------------|
| >50% | Excellent value creation (protection-focused, low distribution cost) |
| 35-50% | Good value creation (typical for Asian protection business) |
| 20-35% | Moderate (savings-linked products, higher acquisition costs) |
| 10-20% | Weak (low-margin savings products, high commission structures) |
| <10% | Poor (commoditized products, likely destroying value at scale) |

**Example — AIA Group (2024):**
- VNB: $4.71B
- VNB Margin: 54.5% (among the highest globally — reflects protection-focused strategy)

#### 3.1.2 Annual Premium Equivalent (APE)

```
APE = Single Premiums × 10% + Annualized Regular Premiums

Where:
  Single Premiums: Lump-sum payments (e.g., single-pay annuity)
  Regular Premiums: Monthly/annual recurring payments, annualized
```

APE standardizes measurement by treating 10% of a single premium as equivalent to one year of regular premiums. This reflects that single premium business requires less ongoing servicing but is less sustainable.

#### 3.1.3 New Business Value (NBV)

NBV is interchangeable with VNB in most contexts — both measure the value of new policies written. Some companies use NBV to refer to the post-tax measure while VNB may be pre-tax. Always check the company's definition.

#### 3.1.4 Embedded Value and Multiples

```
EV/Equity = Market Cap / Embedded Value
          = Premium or discount to appraisal value

Typical ranges:
  - Asian growth insurers: 1.5x - 2.5x EV
  - Mature US/European insurers: 0.8x - 1.5x EV
  - Japanese insurers: 0.4x - 0.8x EV (demographic headwinds)

P/EV = Price per Share / EV per Share
```

```
VNB Multiple = Market Cap / VNB
             = How market values new business generation

Typical ranges: 15x - 30x for high-growth insurers; 8x - 15x for mature
```

#### 3.1.5 Policy Lapse/Surrender Rates

```
Lapse Rate = Lapsed Policies / Policies In Force (beginning of period)

Persistency Rate = 1 - Lapse Rate
                = Policies Retained / Policies In Force

Surrender Rate = Surrender Benefits Paid / Account Balances (UL/VL)
```

| Lapse Rate Range | Interpretation |
|-----------------|----------------|
| <5% annually | Excellent persistency (sticky products, strong relationships) |
| 5-10% | Good persistency |
| 10-15% | Moderate (watch for adverse selection) |
| >15% | Poor (product issues, aggressive pricing, bad distribution) |

**Why it matters:** Lapse rates directly impact VIF. Higher-than-expected lapses = lower future profits. Early lapses are especially damaging (acquisition costs not yet recovered).

#### 3.1.6 Investment Yield vs. Assumed Rates

```
Actual Investment Yield = Net Investment Income / Average Invested Assets

Assumed Rate (Booked) = Guaranteed crediting rates + Assumed spread

Spread = Actual Investment Yield - Assumed Crediting Rate
```

**Spread compression risk:** When interest rates fall, investment yields decline but guaranteed crediting rates (on older policies) cannot be reduced. This compresses spreads and threatens profitability.

**Example:**
- Assumed investment yield: 5.0%
- Actual investment yield: 4.2%
- Guaranteed crediting rate: 3.5%
- Expected spread: 1.5%; Actual spread: 0.7%
- **Result:** Earnings miss, potential reserve strengthening needed

### 3.2 P&C Insurance Metrics

#### 3.2.1 Combined Ratio = Loss Ratio + Expense Ratio

```
Loss Ratio = (Incurred Losses + Loss Adjustment Expenses) / Net Earned Premiums

Expense Ratio = (Underwriting Expenses) / Net Written Premiums

Combined Ratio = Loss Ratio + Expense Ratio
```

**Decomposition:**
```
Loss Ratio = Paid Loss Ratio + Change in Reserves / Earned Premiums

Expense Ratio = Acquisition Cost Ratio + General & Administrative Expense Ratio
```

**Example — Industry Benchmarks (2023-2024):**
| Company | Loss Ratio | Expense Ratio | Combined Ratio |
|---------|-----------|--------------|----------------|
| Progressive (PGR) | ~68% | ~22% | ~90% |
| Travelers (TRV) | ~62% | ~29% | ~91% |
| Chubb (CB) | ~55% | ~32% | ~87% |
| Allstate (ALL) | ~75% | ~25% | ~100% (struggling) |

#### 3.2.2 Float Calculation

```
Float = Loss Reserves
      + Loss Adjustment Expense Reserves
      + Unearned Premium Reserve (UPR)
      + Reinsurance Balances Payable
      - Premiums Receivable
      - Reinsurance Recoverable
      - Deferred Acquisition Costs

Float-to-Equity Ratio = Float / Shareholders' Equity
```

**Example — Berkshire Hathaway (2023):**
| Component | $B |
|-----------|-----|
| Loss reserves | ~85 |
| UPR | ~25 |
| Other | ~15 |
| Less: Receivables/DAC | ~(17) |
| **Total Float** | **~$168B** |
| Float/Equity | ~0.65x |

#### 3.2.3 Investment Yield on Float

```
Investment Yield on Float = Net Investment Income / Average Float

Pre-tax Yield = (Investment Income + Realized Gains) / Average Invested Assets
After-tax Yield = Pre-tax Yield × (1 - Tax Rate)
```

**Example:**
- Float: $50B
- Investment income: $2.5B
- Investment yield: 5.0%
- Combined ratio: 96%
- Cost of float: -4% (negative — being paid to hold)
- Net benefit: 5% investment yield + 4% underwriting profit = 9% total return on float

#### 3.2.4 Reserve Development

```
Reserve Development = Initial Reserve Estimate - Ultimate Actual Payout

Favorable Development = Initial estimate was too high (reserve release)
                      → Increases current earnings (but quality is questionable)

Unfavorable Development = Initial estimate was too low (reserve strengthening)
                        → Decreases current earnings (red flag for under-reserving)

Calendar Year Combined Ratio = Accident Year Combined Ratio + Reserve Development Ratio
```

**Loss Reserve Development Analysis (Schedule P for US insurers):**
```
Development Factor = (Reserves at Evaluation Year X + Cumulative Paid) / Original Reserve

Example: 10-year development factor of 1.15 means reserves were 15% inadequate
```

| Reserve Development Pattern | Interpretation |
|---------------------------|----------------|
| Consistent favorable (releases) | Conservative reserving OR aging book shedding claims |
| Consistent unfavorable (strengthening) | Aggressive reserving (understated initial reserves to boost earnings) |
| Switching pattern | Most concerning — changed reserving philosophy or new management gaming |

**Red flag:** If an insurer consistently shows calendar-year combined ratios lower than accident-year ratios, they may be using reserve releases to mask deteriorating current underwriting.

#### 3.2.5 Catastrophe (Cat) Load and Exposure

```
Cat Load = Expected Cat Losses / Earned Premiums

Cat Budget (Industry typical): 3-7% of earned premiums

Cat Load by Region:
  - Florida homeowners: 15-25%
  - California earthquake: 10-20%
  - Global diversified: 3-5%

1-in-100 Year PML (Probable Maximum Loss) = Stress test metric
1-in-250 Year PML = Solvency II / rating agency stress metric
```

**Cat Exposure Concentration Metrics:**
```
PML / Shareholders' Equity = Cat leverage ratio
  - <20%: Low concentration
  - 20-50%: Moderate
  - >50%: High concentration (dangerous in multi-cat years)
```

#### 3.2.6 Premium Growth Rate

```
Net Written Premium Growth = (NWP(t) - NWP(t-1)) / NWP(t-1)

Organic Growth = Total Growth - Growth from Acquisitions - FX Impact

Price Change (Rate) = Change in average premium per exposure unit
Exposure Change = Change in number of policies/risk units
```

| Growth Source | Quality Assessment |
|--------------|-------------------|
| Rate increase > loss cost trend | Excellent (expanding margins) |
| Rate increase = loss cost trend | Good (maintaining margins) |
| Rate increase < loss cost trend | Poor (margin compression) |
| Volume growth only | Concerning (buying market share) |

**Example — Progressive:**
- Premium growth: 20%+ in 2023
- Rate increases: 10-14%
- Loss cost trend: 8-10% (inflation in auto repair/replacement)
- Net: Margin expansion from rate adequacy

#### 3.2.7 Retention Rate

```
Retention Rate = Policies Renewed / Policies Eligible for Renewal

Net Retention = Net Written Premium / Gross Written Premium
              (After reinsurance ceded)
```

High retention (>85%) indicates pricing adequacy and customer satisfaction. Low retention suggests price-sensitive customers or service issues.

### 3.3 Universal Metrics

#### 3.3.1 Return on Equity (ROE)

```
ROE = Net Income / Average Shareholders' Equity

Decomposed (DuPont-style for insurers):
ROE = (Net Income / Earned Premiums) × (Earned Premiums / Invested Assets) × (Invested Assets / Equity)
    = Profit Margin × Asset Turnover × Leverage
```

| ROE Range | Assessment |
|-----------|-----------|
| >15% | Excellent (Berkshire, Progressive in good years) |
| 10-15% | Good (industry average) |
| 8-10% | Adequate |
| 5-8% | Below average (cost of equity concern) |
| <5% | Poor (value destruction) |

#### 3.3.2 Solvency Ratio / Risk-Based Capital (RBC)

**US — NAIC RBC Ratio:**
```
RBC Ratio = Total Adjusted Capital / Authorized Control Level RBC

Where:
  Total Adjusted Capital = Statutory Surplus + AVR + 50% of Dividend Liabilities
  Authorized Control Level = 2 × (R0 + R1 + R2 + √(R3² + R4² + R5²))

R0 = Asset risk — affiliates
R1 = Asset risk — fixed income
R2 = Asset risk — equity
R3 = Credit risk
R4 = Underwriting risk — pricing
R5 = Catastrophe risk / interest rate risk

Regulatory Action Levels:
  - RBC > 200%: No action
  - 150-200%: Company action level
  - 100-150%: Regulatory action level
  - 70-100%: Authorized control level (regulators can take control)
  < 70%: Mandatory control level
```

**Europe — Solvency II Ratio:**
```
Solvency II Ratio = Eligible Own Funds / Solvency Capital Requirement (SCR)
                  = Own Funds / SCR

Minimum: 100% (regulatory minimum)
Target: 150-200% (management target, rating agency comfort)
Stress: Below 100% = regulatory intervention

SCR calculated using:
  - Standard formula (prescribed by EIOPA)
  - Internal model (company-specific, approved by regulator)
```

**Bermuda — BSCR (Bermuda Solvency Capital Requirement):**
```
BSCR Ratio = ECR / BSCR
           (Economic Capital Ratio / Bermuda Solvency Capital Requirement)

Target: Above 120%
```

#### 3.3.3 Investment Portfolio Yield and Duration

```
Portfolio Yield = (Interest Income + Dividend Income) / Average Invested Assets

Current Yield = Annualized Income / Market Value of Portfolio

Yield to Maturity (for fixed income) = IRR of bond cash flows

Modified Duration = - (ΔPrice / Price) / ΔYield
                  = Sensitivity to 100bp interest rate change

Effective Duration = Duration incorporating embedded options
```

**ALM (Asset-Liability Management) Metrics:**
```
Duration Gap = Asset Duration - Liability Duration

Positive gap (DA > DL): Net beneficiary of rising rates (assets reprice faster)
Negative gap (DA < DL): Net beneficiary of falling rates (liabilities are longer)

Example: If asset duration = 7 years, liability duration = 12 years
  Duration gap = -5 years
  → 100bp rate rise → equity value declines (liabilities fall less than assets)
```

**Example — Life Insurer ALM:**
| Metric | Value | Interpretation |
|--------|-------|----------------|
| Asset duration | 8.2 years | Intermediate fixed income |
| Liability duration | 11.5 years | Long-dated life policies |
| Duration gap | -3.3 years | Exposed to rising rates |
| Interest rate hedge ratio | 65% | Partially hedged |

#### 3.3.4 Expense Ratio (Universal)

```
Expense Ratio = Operating Expenses / Earned Premiums (P&C)
              = Operating Expenses / APE (Life)

Acquisition Cost Ratio = Commission + Underwriting Expenses / Written Premiums
```

Low expense ratio = operational efficiency. But beware: very low expense ratios may indicate under-investment in claims handling or technology.

---

## 4. KEY RISK FACTORS (INSURANCE-SPECIFIC)

### 4.1 Reserve Adequacy Risk

**What it is:** Insurers set aside reserves for future claims. If reserves are insufficient, future earnings will be hit when claims exceed reserves.

**Quantitative Indicators:**

| Indicator | Formula | Red Flag Threshold |
|-----------|---------|-------------------|
| Reserve development ratio | Reserve development / Earned premiums | >2% unfavorable for 2+ years |
| Reserve duration vs. industry | Avg reserve age | Significantly younger than peers |
| IBNR / Case reserves ratio | IBNR / Total reserves | <20% (may be under-reserving) |
| Reserve discount rate sensitivity | Change in PV for -100bp | Large impact suggests aggressive discounting |
| Schedule P development triangles | 10-year development factor | >1.10 (10% deficiency) |

**Real-world example — GE Insurance (2000s):**
- GE's Employers Re subsidiary consistently under-reserved long-tail workers comp
- 10-year development factors exceeded 1.30 (30% deficiency)
- Result: billions in reserve strengthening, business ultimately sold

### 4.2 Catastrophe Risk

**What it is:** Natural disasters (hurricanes, earthquakes, floods) cause concentrated losses. A single event can wipe out a year of earnings.

**Quantitative Indicators:**

| Metric | Formula | Red Flag Threshold |
|--------|---------|-------------------|
| PML / Equity (1-in-100) | Probable Maximum Loss / Equity | >50% |
| PML / Equity (1-in-250) | Stress PML / Equity | >100% |
| Cat budget / earned premium | Expected cat losses / EP | >10% for non-cat specialists |
| Gross vs. net PML | Before/after reinsurance | Small difference = insufficient reinsurance |
| Cat bond coverage | % of PML covered by ILS | <30% for peak zones |

**Modeling approach:**
```
Expected Annual Cat Loss = Σ [Probability(Event_i) × Severity(Event_i)]

Across peril regions:
  - US Atlantic Hurricane
  - US Earthquake (California, New Madrid)
  - European Windstorm
  - Japanese Typhoon / Earthquake
  - Flood (increasingly modeled separately)
```

**Example — 2017 Hurricane Year (Harvey, Irma, Maria):**
- Combined industry insured losses: ~$120B+
- Individual reinsurer losses: 50-150% of annual earnings
- Companies with PML/Equity >60% suffered material capital events

### 4.3 Interest Rate Risk (ALM Risk)

**What it is:** Life insurers hold long-duration liabilities matched against fixed-income assets. Rising rates cause unrealized losses on bonds while reducing liability PV. The net effect depends on duration gap.

**Quantitative Indicators:**

| Metric | Formula | Red Flag Threshold |
|--------|---------|-------------------|
| Duration gap | Asset duration - Liability duration | >±3 years |
| Unrealized losses / Equity | AOCI losses / Equity | >20% |
| Crediting rate spread | Portfolio yield - Guaranteed rate | <50bp (spread compression) |
| VA guarantee exposure | GMDB/GMIB notional / Equity | >5x (for VA writers) |
| DAC unlock sensitivity | Earnings impact of rate change | Large relative to earnings |

**Example — Japanese Life Insurers (1990s):**
- Sold policies with 5-6% guaranteed returns in 1980s
- JGB yields collapsed to <1% by 2000s
- Spread turned deeply negative: "negative spread" problem
- Result: Massive insolvencies, industry consolidation, government bailouts

### 4.4 Longevity Risk

**What it is:** Life insurers assumed mortality rates for annuity pricing. If people live longer than assumed, annuity payments exceed reserves.

**Quantitative Indicators:**

| Metric | Formula | Red Flag Threshold |
|--------|---------|-------------------|
| Annuity exposure / Total reserves | Annuity reserves / Total | >40% |
| Mortality assumption vs. CMI | Company assumption - industry | Significantly lighter than CMI/SOA tables |
| Longevity hedge ratio | Hedged exposure / Total exposure | <50% for large exposures |
| Pension buyout growth | New business growth rate | Rapid growth without hedging |

### 4.5 Pricing Cycle Risk (P&C)

**What it is:** P&C insurance pricing is cyclical. Soft markets (excess capital → low prices → poor underwriting) alternate with hard markets (cat events → capital shortage → high prices).

**Quantitative Indicators:**

| Metric | Formula | Red Flag Threshold |
|--------|---------|-------------------|
| Rate change | Year-over-year pricing change | Negative for 2+ years |
| Combined ratio (accident year) | Current accident year CR | >100% for 2+ years |
| Industry capital growth | Industry surplus growth | >10% (fuels soft market) |
| Premium growth vs. GDP | Industry premium growth / GDP growth | <0.5x (pricing below economic growth) |

### 4.6 Investment Portfolio Risk

**What it is:** Insurers hold large investment portfolios. Credit losses, equity volatility, and illiquidity can impair capital.

**Quantitative Indicators:**

| Metric | Formula | Red Flag Threshold |
|--------|---------|-------------------|
| Equity allocation | Equity assets / Total invested assets | >15% for life insurers; >25% for P&C |
| Below-investment-grade bonds | HY bonds / Total fixed income | >10% |
| Level 3 assets / Total | Illiquid assets / Total investments | >10% |
| Concentration in single issuer | Top 10 issuer exposure | >50% of equity |
| CRE/CMBS exposure | Commercial real estate / Total | >15% |

### 4.7 Regulatory/Supervisory Risk

**What it is:** Changes in accounting standards (IFRS 17, LDTI) and capital requirements (Solvency II reform, Basel III) can force reserve changes, capital raises, or business model changes.

**Quantitative Indicators:**

| Risk | Current Status | Impact |
|------|---------------|--------|
| IFRS 17 transition | Effective 2023 (international) | Changes profit recognition timing, CSM volatility |
| LDTI (US Long-Duration Targeted Improvements) | Effective 2023 | Eliminates shadow accounting, increases earnings volatility |
| Solvency II review | Ongoing (2023-2026) | Potential capital requirement changes |
| NAIC RBC formula changes | Periodic updates | May increase capital for certain risks |

**IFRS 17 Impact Example:**
```
IFRS 17 introduces:
- Contractual Service Margin (CSM) = unearned profit, recognized over coverage period
- Risk Adjustment = explicit compensation for uncertainty in future cash flows
- OCI option = allows separating insurance finance income between P&L and OCI

Impact on metrics:
- Revenue: Lower (premiums no longer gross of claims)
- Profit timing: Smoothed (CSM release pattern)
- ROE: May change due to different equity base
- Key new metric: CSM Balance = future profit embedded in book
```

---

## 5. QUALITY INDICATORS

### 5.1 Life Insurance — 10 Quality Indicators (Ranked)

| Rank | Indicator | Formula/Measure | What "Good" Looks Like |
|------|-----------|----------------|----------------------|
| 1 | **VNB Margin** | VNB / APE | >40% (AIA: 54.5%) |
| 2 | **ROEV** | Operating Profit / EV | >12% consistently |
| 3 | **New Business Growth** | VNB YoY Growth | >10% in local currency |
| 4 | **Persistency Rate** | 1 - Lapse Rate | >90% (13-month persistency) |
| 5 | **Solvency Ratio** | Own Funds / SCR | 150-250% (strong but not inefficient) |
| 6 | **Expense Ratio** | Expenses / APE | Improving trend, below 30% |
| 7 | **Investment Yield Spread** | Actual yield - Assumed rate | >0 (positive, not compressing) |
| 8 | **CSM Growth (IFRS 17)** | CSM Balance Growth | Growing = profitable new business |
| 9 | **Capital Generation** | Own Funds Growth - Dividends | Self-sustaining (no capital raises) |
| 10 | **Distribution Quality** | Agency productivity, bank partnerships | Exclusive, productive channels |

**What separates good from bad:**
- **Good:** High VNB margin (>40%), growing VNB, sticky customers (low lapses), strong capital generation, protection-focused product mix
- **Bad:** Low VNB margin (<15%), declining persistency, spread compression, reliance on single-premium savings products, weak capital position

### 5.2 P&C Insurance — 10 Quality Indicators (Ranked)

| Rank | Indicator | Formula/Measure | What "Good" Looks Like |
|------|-----------|----------------|----------------------|
| 1 | **Combined Ratio (3-year avg)** | (Loss + Expense) / Premium | <95% through cycle |
| 2 | **Reserve Adequacy** | 10-year development factor | <1.05 (consistently adequate) |
| 3 | **Float Growth** | Float YoY Growth | Growing faster than GDP |
| 4 | **Cost of Float** | (CR - 100%) × Earned Premium / Float | Negative (underwriting profit) |
| 5 | **ROE (5-year avg)** | Net Income / Equity | >12% |
| 6 | **Investment Yield** | Investment Income / Invested Assets | >3.5% (in current rate environment) |
| 7 | **Expense Ratio** | Expenses / Written Premium | <28% (direct); <32% (agency) |
| 8 | **Premium Rate Adequacy** | Rate change - Loss cost trend | Positive (expanding margins) |
| 9 | **Cat Exposure Management** | Net PML / Equity (1-in-250) | <50% |
| 10 | **Retention Rate** | Renewed Policies / Eligible | >85% |

**What separates good from bad:**
- **Good:** Consistent underwriting profit (CR <95%), growing float at negative cost, adequate reserves, disciplined pricing through soft markets
- **Bad:** Combined ratio >100% for multiple years, consistent unfavorable reserve development, float shrinking, buying market share with price cuts

**Real-world exemplars:**
- **Progressive (PGR):** CR ~90%, data-driven pricing (telemetrics), low expense ratio, consistent growth
- **Berkshire Hathaway:** Negative cost of float for 53 of 57 years, massive float base, investment income on float
- **Travelers (TRV):** CR ~91%, excellent reserve management, disciplined commercial lines

---

## 6. STRESS TEST SCENARIOS

### 6.1 Scenario 1: Reserve Deficiency (Adverse Development)

**Trigger:** Economic inflation drives loss costs higher than originally reserved. Social inflation (litigation trends) amplifies liability lines.

| Parameter | Base Case | Stress Case | Rationale |
|-----------|-----------|-------------|-----------|
| Reserve development ratio | +1% favorable | +8% unfavorable | Inflation 3 years at 6%+ vs. 2% assumed |
| Loss cost trend | +4% annually | +10% annually | Social inflation in liability lines |
| Combined ratio impact | 95% | 103% | 8 points from reserve development |
| Reserve strengthening | None | 10% of reserves | Mid-tail lines affected |
| Capital impact | None | -15% RBC ratio | Reserve charge hits surplus |

**Affected lines (severity):**
1. Commercial auto (severe — social inflation, nuclear verdicts)
2. General liability (severe — asbestos, PFAS, opioid litigation)
3. Workers compensation (moderate — medical inflation)
4. Personal auto (moderate — repair cost inflation)

**Example test:** Progressive with $35B reserves
- 8% adverse development = $2.8B charge
- Pre-stress equity: $25B → Post-stress: $22.2B (-11%)
- RBC ratio: 180% → 155% (still adequate, but close to action level)

### 6.2 Scenario 2: Catastrophe Super-Year

**Trigger:** Multiple major hurricanes (Category 4-5), major earthquake, and European windstorm in same calendar year.

| Parameter | Base Case | Stress Case | Rationale |
|-----------|-----------|-------------|-----------|
| Hurricane landfalls | 1-2 moderate | 3 major (Cat 4+) | Climate change intensity |
| Industry cat losses | $50B annually | $250B+ annually | Multiple major events |
| Company gross cat losses | 3% of premium | 15% of premium | Concentrated exposure |
| Net cat losses (after reinsurance) | 2% of premium | 8% of premium | Reinstatement premiums, exhausted covers |
| Combined ratio | 95% | 115% | 20 points from cat load |
| Investment impact | None | -5% equity portfolio | Risk-off market reaction |

**Example test:** A global reinsurer with $20B equity
- 1-in-250 PML = $6B gross, $2.5B net
- Super-year: 2x 1-in-250 events = $5B net cat losses
- Equity: $20B → $15B (-25%)
- Solvency ratio: 220% → 165% (survives but capital constrained)

### 6.3 Scenario 3: Interest Rate Shock

**Trigger:** Federal Reserve raises rates 300bp in 12 months to combat inflation (2022-style).

| Parameter | Base Case | Stress Case | Rationale |
|-----------|-----------|-------------|-----------|
| 10-year Treasury yield | 4.0% | 7.0% | Aggressive tightening |
| Investment portfolio value | Par | -8% (unrealized losses) | Duration = 5 years |
| Liability discount rate | 4.0% | 7.0% | GAAP/SAP discounting |
| Net equity impact | Flat | -5% to +5% | Depends on duration gap |
| DAC unlocking | None | -$500M | Accelerated amortization |
| VA guarantee reserves | $1B | $2B | Higher hedging costs |

**Life insurer ALM test:**
```
Insurer with:
  Invested assets: $100B, duration = 7 years
  Liabilities: $90B, duration = 10 years
  Duration gap: -3 years

+300bp rate shock:
  Asset value change: $100B × (-3% × 7) = -$21B
  Liability value change: $90B × (-3% × 10) = -$27B
  Net impact: +$6B (liabilities fall more than assets)
  Equity: Increases (positive gap in rising rate environment)
```

**Warning:** Under LDTI/IFRS 17, discount rate changes flow through earnings more quickly. A rate DROP (deflation scenario) is often more dangerous for life insurers than a rate rise.

### 6.4 Scenario 4: Pandemic / Longevity Shock

**Trigger:** Novel pandemic causes mass mortality (life insurers) OR extended lockdowns cause business interruption claims (P&C).

**For Life Insurers:**

| Parameter | Base Case | Stress Case |
|-----------|-----------|-------------|
| Mortality rate | 1.0% annually | 1.5% annually (50% excess mortality) |
| Life insurance claims | $5B | $8B (+60%) |
| Annuity persistency | 95% | 90% (lapse spike from financial distress) |
| Equity market | +8% annually | -30% (crash) |
| VA guarantees | In-the-money 10% | In-the-money 40% |
| Net income impact | Base | -50% to -100% |

**Example — COVID-19 actual impact on life insurers (2020-2021):**
- US life insurance claims: +15-20% in 2020
- Some insurers (Genworth, LTC writers) saw massive claims
- Others with younger books were less affected
- Reinsurance protections partially absorbed

**For P&C Insurers (Business Interruption):**

| Parameter | Base Case | Stress Case |
|-----------|-----------|-------------|
| BI claims | $1B industry | $50B+ industry |
| Pandemic exclusion | Clear | Ambiguous (litigation risk) |
| Court rulings | For insurers | Against insurers (UK, some US states) |
| Capital impact | Minimal | -10% to -30% equity for affected lines |

---

## 7. PEER COMPARISON METHODOLOGY

### 7.1 Life Insurance Peer Comparison

| Metric | Comparison Method | Normalization |
|--------|------------------|---------------|
| **EV multiples** | P/EV, Market Cap/EV | Adjust for accounting methodology (MCEV vs. TEV) |
| **VNB margins** | Cross-company VNB/APE | Must use same premium measure (APE vs. PVNBP) |
| **ROEV** | Operating return on EV | Use operating EV (exclude market value adjustments) |
| **New business growth** | VNB CAGR | Local currency, constant exchange rates |
| **Expense ratios** | Operating expenses / APE | Adjust for distribution model (agency vs. bancassurance) |
| **Persistency** | 13-month persistency rate | Same measurement window |
| **Solvency ratios** | Own Funds / SCR | Adjust for different SCR calculation methods |
| **Investment yields** | Net investment income / Assets | Adjust for asset mix (equity %, HY %) |

**Cross-market adjustment factors:**
```
MCEV premium over TEV: +5-15% (MCEV is more conservative)
IFRS 17 CSM vs. EV: CSM is "locked-in" at inception; EV is dynamic
Growth market premium: Asian insurers trade at 1.5-2.5x EV vs. 0.5-0.8x for Japanese
```

### 7.2 P&C Insurance Peer Comparison

| Metric | Comparison Method | Normalization |
|--------|------------------|---------------|
| **Combined ratio** | CR or CR ex-cats | Adjust for cat load differences |
| **Expense ratio** | UW expenses / Written premium | Separate acquisition vs. admin |
| **ROE** | Net income / Average equity | 5-year average through cycle |
| **Reserve development** | 5-year avg development ratio | As % of earned premium |
| **Float growth** | Float CAGR | Per share, inflation-adjusted |
| **Investment yield** | Investment income / Invested assets | Pre-tax, by asset class |
| **Book value growth** | TBVPS CAGR | Excluding dividends (total return) |

**Example — P&C Peer Group (2023-2024):**
| Company | Combined Ratio | Expense Ratio | ROE | P/B |
|---------|---------------|--------------|-----|-----|
| Progressive (PGR) | 90% | 22% | 18% | 5.0x |
| Travelers (TRV) | 91% | 29% | 13% | 1.8x |
| Chubb (CB) | 87% | 32% | 14% | 1.7x |
| Allstate (ALL) | 100% | 25% | 5% | 1.3x |
| Berkshire (BRK) | 92%* | N/A | 10% | 1.5x |

*BRK combined ratio includes all insurance operations; float value justifies premium

### 7.3 Cross-Market Issues: US GAAP vs. IFRS

| Issue | US GAAP (ASC 944) | IFRS 17 | Impact on Comparison |
|-------|------------------|---------|---------------------|
| Reserve discounting | Generally undiscounted (except long-tail) | Risk-adjusted present value | IFRS reserves are lower for long-duration liabilities |
| DAC amortization | Capitalize and amortize | Expensed as incurred (or CSM) | IFRS shows lower early profits |
| Unearned premium reserve | Pro-rata over policy term | CSM release pattern | Different profit recognition timing |
| Shadow accounting | Allowed (smoothes investment income) | Eliminated | IFRS shows more volatile investment results |
| Reserve strengthening | Flows through earnings immediately | Affects CSM first, then earnings | IFRS may defer recognition |
| Catastrophe reserves | Not permitted (prohibited) | Risk adjustment component | IFRS may show higher reserves for cat risk |

**Adjustment methodology for cross-border comparison:**
1. For US GAAP companies: Add back DAC to get economic capital
2. For IFRS 17 companies: Use CSM as proxy for VIF
3. For all: Normalize combined ratios to exclude investment income
4. Use "operating" metrics that exclude accounting differences

---

## 8. REPLACEMENT TABLE: BASE FRAMEWORK → INSURANCE FRAMEWORK

| Standard Component | Insurance Replacement | Rationale |
|-------------------|----------------------|-----------|
| **DCF on FCF** | **Life:** Embedded Value + Appraisal Value (ANAV + VIF + VNB multiple) | Float/reserves are liabilities, not free cash. EV captures economic value of in-force business. |
| | **P&C:** Book Value + PV of Underwriting Profits + Investment Income on Float | Float is the primary value driver. Underwriting profit + investment yield on float = total return. |
| | **Brokers:** Standard DCF (works with minor adjustments) | Brokers have normal working capital; FCF is meaningful. |
| **ROIC (NOPAT/Invested Capital)** | **ROE** (Net Income / Equity) | Float is not "invested capital" — it's a policyholder liability. ROE measures return on shareholder capital only. |
| | **ROEV** (Return on Embedded Value) for Life | Measures return on total economic value (ANAV + VIF). |
| | **Return on Float** for P&C | Underwriting profit / Float + Investment yield = total float return. |
| **Operating Leverage Regression** | **Financial Leverage: Float/Equity** | Insurers are funded by float (policyholder money), not debt. Float/Equity = true leverage. |
| | **Combined Ratio decomposition** | Fixed costs (G&A) vs. variable costs (claims) separated via loss and expense ratios. |
| | **Revenue recognition lag** | Premiums written ≠ earned. Growth in written premium creates reserve buildup (negative FCF). |
| **P/E Multiple** | **Life:** P/EV (Price to Embedded Value) | Earnings are smoothed by reserve changes and investment income. EV is more stable. |
| | **P&C:** P/B with ROE adjustment (Justified P/B = (ROE-g)/(r-g)) | P/E is distorted by investment income volatility. P/B anchors to tangible capital. |
| | **Life:** P/VNB (Price to Value of New Business) | Values growth trajectory of new business generation. |
| | **Brokers:** EV/EBITDA or P/E (standard works) | Brokers have standard earnings quality. |
| **SBC (Stock-Based Compensation) Analysis** | **Dilution of Book Value per Share** | SBC is less common in insurers. When present, dilutes tangible book value (primary valuation anchor). |
| | **Expense ratio impact** | Include SBC in expense ratio analysis if material. |
| **FCF Yield** | **Dividend Yield + Reserve Growth Yield** | Mature insurers return capital via dividends. Reserve growth (float growth) is the retained value. |
| | **Float Yield** (Investment income on float / Float) | Measures return on the "free float" even when FCF is negative. |
| | **Book Value Growth Rate** | For insurers not paying dividends, BVPS growth is the shareholder return. |

---

## 9. REVERSE ENGINEERING FOR INSURERS

### 9.1 What Combined Ratio Implies About Pricing Discipline

| Combined Ratio (3-yr avg) | Implied Pricing Discipline | Float Cost | Valuation Impact |
|---------------------------|---------------------------|------------|-----------------|
| <90% | Exceptional (Progressive, Berkshire) | Strongly negative | Premium P/B warranted |
| 90-95% | Excellent | Negative | Premium P/B (1.5-2.5x) |
| 95-100% | Good | Zero to slightly positive | Moderate P/B (1.0-1.5x) |
| 100-105% | Marginal (soft market participant) | Positive (paying for float) | Discount P/B (0.8-1.0x) |
| 105-110% | Poor | Expensive | Deep discount P/B (<0.8x) |
| >110% | Crisis | Destroying capital | Avoid unless turnaround is credible |

**Example — Reverse engineering Progressive at P/B = 5.0x:**
```
P/B = 5.0x, Cost of equity = 10%, Growth = 4%
Implied ROE = g + (P/B) × (r - g) = 4% + 5.0 × (10% - 4%) = 4% + 30% = 34%

Progressive actual ROE: ~18% in 2023
Interpretation: Market is pricing in sustained superior underwriting +
                above-average investment returns +
                continued market share gains
                = High expectations, limited margin of safety
```

### 9.2 What P/B Implies About ROE Expectations

```
Implied Sustainable ROE = g + (P/B) × (r - g)

Example tables:
```

| P/B | r=10%, g=3% | r=10%, g=4% | r=12%, g=3% |
|-----|-------------|-------------|-------------|
| 0.5x | 6.5% | 7.0% | 7.5% |
| 0.8x | 8.6% | 8.8% | 10.2% |
| 1.0x | 10.0% | 10.0% | 12.0% |
| 1.2x | 11.4% | 11.2% | 13.8% |
| 1.5x | 13.5% | 13.0% | 16.5% |
| 2.0x | 17.0% | 16.0% | 21.0% |
| 3.0x | 24.0% | 22.0% | 30.0% |

**Interpretation:**
- P/B of 1.0x implies ROE = cost of equity (fair value, no excess returns)
- P/B < 1.0x implies ROE < cost of equity (value destruction expected)
- P/B > 1.5x implies sustained above-cost ROE (competitive advantage required)

### 9.3 What VNB Multiple Implies About Growth Expectations

```
VNB Multiple = Market Cap / VNB = Franchise Multiple

Implied VNB Growth = r - (1 / Franchise Multiple)

Example: VNB Multiple = 20x, r = 10%
Implied perpetual VNB growth = 10% - (1/20) = 10% - 5% = 5%
```

| VNB Multiple | Implied Perpetual Growth (r=10%) | Implied Perpetual Growth (r=12%) |
|-------------|--------------------------------|--------------------------------|
| 10x | 0% | 2% |
| 15x | 3.3% | 5.3% |
| 20x | 5.0% | 7.0% |
| 25x | 6.0% | 8.0% |
| 30x | 6.7% | 8.7% |

**Example — AIA Group at VNB multiple of ~21x:**
```
VNB = $4.71B, Market Cap = ~$100B
VNB Multiple = 100 / 4.71 = 21.2x
Implied growth at 10% cost of equity = 10% - (1/21.2) = 10% - 4.7% = 5.3%

AIA's actual VNB growth: 15-20% in recent years
Interpretation: Market expects VNB growth to slow significantly from current rates
                to a 5% perpetual rate. If growth sustains above 10%, multiple could expand.
```

---

## 10. ACCOUNTING RED FLAGS

### 10.1 IFRS 17 / LDTI Transition Impacts

| Red Flag | What to Watch | Why It Matters |
|----------|--------------|----------------|
| **Large CSM write-offs at transition** | CSM reduced by >20% at transition date | Indicates prior earnings were overstated; future profit recognition reduced |
| **Switching between PAA and GMM** | Change in measurement model mid-stream | May be gaming to show better results |
| **OCI election changes** | Moving insurance finance from P&L to OCI | Could be hiding investment volatility |
| **LDTI transition impacts (US)** | Large day-one adjustments to retained earnings | Long-duration target improvements may reveal reserve inadequacy |
| **VFA eligibility claims** | Claiming Variable Fee Approach for non-participating contracts | Inflates CSM, defers loss recognition |

**Example — IFRS 17 CSM as quality indicator:**
```
CSM / Total Reserves Ratio:
  - >15%: Strong future profit visibility (Prudential UK: ~20%)
  - 5-15%: Moderate
  - <5%: Weak future profits, may be writing onerous contracts
```

### 10.2 Reserve Strengthening vs. Release Patterns

| Red Flag | Pattern | Investigation Required |
|----------|---------|----------------------|
| **Consistent releases with deteriorating accident year CR** | Using prior-year reserves to offset current-year underwriting losses | Is core underwriting deteriorating? |
| **Step-function reserve changes** | Years of small releases, then one massive strengthening | Was management smoothing? |
| **Reserve releases after management change** | New CEO takes large reserve hit | "Kitchen sinking" — clearing prior management's under-reserving |
| **Reserve adequacy ratio declining** | IBNR / Total reserves falling | Less conservative reserving, potentially to boost earnings |
| **Schedule P triangles showing acceleration** | Paid losses developing faster than prior years | Inflation or social inflation accelerating |

**Diagnostic — Reserve Quality Scorecard:**
```
1. 5-year average reserve development ratio: _______% (<2% favorable = good)
2. Change in IBNR % of total reserves: _______% (declining = concern)
3. Accident year CR vs. Calendar year CR spread: _______% (>5% = using reserves)
4. Reserve to surplus ratio vs. peers: _______ (much lower = aggressive)
5. A.M. Best reserve adequacy opinion: _______ (marginal = red flag)
```

### 10.3 Level 3 Investments / Illiquid Assets

| Red Flag | Threshold | Concern |
|----------|-----------|---------|
| Level 3 assets / Total invested assets | >10% | Hard to value, potential for mark-to-model gaming |
| Private equity / hedge fund allocation | >5% of total | Illiquid, volatile, hard to stress test |
| Commercial real estate concentration | >15% of fixed income | Cyclical, correlated with economic downturns |
| Affiliate investments / related-party | >5% of assets | Conflict of interest, potential for sweetheart pricing |
| Structured products (CDO, CLO) | Material | Complexity risk, liquidity risk |

**Example — AIG (pre-crisis):**
- Credit default swap portfolio (super-senior): Marked at model, not market
- Level 3 assets: >20% of investment portfolio
- When models broke, AIG required $182B government bailout

### 10.4 Shadow Accounting Assumptions

**What it is:** Under US GAAP (pre-LDTI), insurers could adjust DAC amortization based on actual vs. expected investment returns — effectively smoothing earnings.

| Red Flag | What to Watch |
|----------|--------------|
| DAC balance growing faster than premium growth | May be capitalizing costs that should be expensed |
| DAC unlocking events | Frequent unlocks suggest assumptions were too aggressive |
| DAC / PVFP ratio > 50% | High capitalization ratio, may reverse |
| Shadow accounting eliminating investment volatility | Earnings appear too smooth relative to markets |

**LDTI Impact (effective 2023):** Shadow accounting is eliminated. Companies must amortize DAC on a constant basis. This will increase earnings volatility for life insurers with large DAC balances.

### 10.5 Aggressive Mortality / Morbidity Assumption Changes

| Red Flag | Pattern |
|----------|---------|
| Mortality improvement assumptions changed frequently | Each change releases reserves or increases VIF |
| Assumptions lighter than industry tables (CMI, SOA) | Company outlier = potential future reserve hit |
| Lapse assumptions changed to increase VNB | Lower assumed lapses = higher VNB, but may not be realistic |
| Expense assumption changes reducing VNB margin denominator | Lower unit costs assumed = higher VNB, but hard to achieve |
| Morbidity improvement for LTC/health | Similar to mortality — small changes have large reserve impacts |

**Example — Long-Term Care (LTC) insurers:**
- Assumed 5% lapse rates (policyholders would drop policies)
- Actual lapse rates: <1% (policyholders kept policies and claimed)
- Result: Massive reserve deficiencies — Genworth nearly insolvent
- Lesson: Lapse assumptions are critical; overly aggressive assumptions destroy value

---

## APPENDIX A: QUICK REFERENCE FORMULA SHEET

### Life Insurance
```
EV = ANAV + VIF
VIF = PVFP - CoC
Appraisal Value = EV + (VNB × Franchise Multiple)
VNB Margin = VNB / APE
ROEV = Operating Profit / EV
APE = Single Premiums × 10% + Annualized Regular Premiums
Persistency = 1 - Lapse Rate
```

### P&C Insurance
```
Combined Ratio = Loss Ratio + Expense Ratio
Loss Ratio = Incurred Losses / Earned Premiums
Expense Ratio = Underwriting Expenses / Written Premiums
Float = Loss Reserves + UPR + LAE - Receivables - DAC
Cost of Float = (Combined Ratio - 100%) × Earned Premiums / Float
Investment Yield on Float = Net Investment Income / Average Float
Reserve Development = Initial Reserve - Ultimate Actual Payout
Cat Load = Expected Cat Losses / Earned Premiums
Justified P/B = (ROE - g) / (r - g)
```

### Reinsurance
```
Adjusted Book Value = Reported BV - Reserve Buffer - CAT Buffer + Excess Capital
Reserve Buffer = Long-tail Reserves × 15% (typical)
CAT Buffer = 1-in-100 PML × 50%
Net Retention = Net Written / Gross Written Premiums
```

### Brokers
```
Organic Growth = Total Growth - M&A Growth - FX
Revenue/Employee = Revenue / Headcount
Retention Rate = Renewed Clients / Total Prior Year Clients
EV/EBITDA = Enterprise Value / EBITDA
```

### Universal
```
ROE = Net Income / Average Equity
RBC Ratio = Total Adjusted Capital / Authorized Control Level RBC
Solvency II Ratio = Own Funds / SCR
Duration Gap = Asset Duration - Liability Duration
Spread = Investment Yield - Guaranteed Crediting Rate
```

---

## APPENDIX B: COMPANY EXAMPLES SUMMARY

| Company | Type | Key Metric | Value | Why It Matters |
|---------|------|-----------|-------|----------------|
| **AIA Group** | Life (Asia) | VNB Margin | 54.5% | Best-in-class protection business |
| **AIA Group** | Life (Asia) | EV | $71.6B (2024) | Largest Asian life insurer by EV |
| **Berkshire Hathaway** | P&C Conglomerate | Float | ~$168B (2023) | Largest insurance float globally |
| **Berkshire Hathaway** | P&C Conglomerate | Cost of Float | Negative 53/57 years | Paid to hold other people's money |
| **Progressive** | P&C (Personal Auto) | Combined Ratio | ~90% | Data-driven pricing advantage |
| **Progressive** | P&C (Personal Auto) | P/B | ~5.0x | Market prices in sustained outperformance |
| **Prudential plc** | Life (UK/Asia) | EEV | $44.2B | Transitioning to TEV methodology |
| **Aflac** | Life (Japan/US) | ROE | ~12-15% | Dominant cancer insurance in Japan |
| **Munich Re** | Reinsurance | Solvency II | ~250%+ | Gold standard of reinsurance capital |
| **Aon** | Broker | EV/EBITDA | ~16x | Premium for organic growth + margin |
| **Aon** | Broker | Organic Growth | 7% (2024) | True growth excluding M&A |
| **SOMPO Himawari** | Life (Japan) | MCEV | ¥1,211.9B | Negative ANW + large VIF = rate sensitivity |

---

## APPENDIX C: DATA SOURCES FOR IMPLEMENTATION

| Data Item | Source | Frequency |
|-----------|--------|-----------|
| **Embedded Value** | Company annual reports (supplementary disclosure) | Annual |
| **VNB** | Company earnings releases | Quarterly/Annual |
| **Combined Ratio** | Company earnings, NAIC filings | Quarterly |
| **Reserve Development** | Schedule P (NAIC), Annual Report | Annual |
| **Float** | Derived from balance sheet | Quarterly |
| **Solvency II Ratio** | Company disclosure, EIOPA | Quarterly/Annual |
| **RBC Ratio** | NAIC Annual Statement | Annual |
| **Investment Portfolio** | Schedule D (NAIC), Annual Report notes | Annual |
| **Cat Exposure** | Company risk disclosures, RMS/Moody's | Annual |
| **IFRS 17 CSM** | Company financial statements (post-2023) | Quarterly |
| **A.M. Best Ratings** | aambest.com | Continuous |
| **Reinsurance Pricing** | Guy Carpenter, Lane Financial | Quarterly (January 1 renewals) |

---

*Document Version 1.0 — Insurance Sector Override Module for Adaptive Equity Analysis Framework*

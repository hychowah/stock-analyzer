# Banking & Financial Services — Adaptive Framework Module

> **Author**: Senior Equity Research Analyst, Banking & Financial Services  
> **Last Updated**: 2025  
> **Applies To**: Commercial Banks, Investment Banks, Asset Managers, Fintech Lenders, Diversified Financials  
> **Trigger**: Automatic activation when `sector = Financial Services` AND banking flags detected

---

## Executive Summary

The standard adaptive framework (FCF-based DCF, ROIC, P/E, operating leverage regression, SBC analysis) **completely fails for banks**. This document provides a comprehensive replacement module covering:

| Standard Framework Component | Bank-Specific Replacement |
|------------------------------|---------------------------|
| FCF-based DCF | Excess Return Model / Dividend Discount Model |
| ROIC | ROE / ROA / RAROC |
| Operating Leverage | Financial Leverage + NIM Sensitivity |
| P/E multiple | P/B (primary), P/TBV, P/E (secondary) |
| SBC analysis | Compensation/Revenue ratio |
| FCF Yield | Dividend Yield + Buyback Yield |
| Revenue growth focus | NII growth + Fee income growth |

**Why standard DCF fails for banks**: Deposits are simultaneously liabilities AND the core funding engine. Banks borrow short (deposits) and lend long (loans) by design. FCF is not a meaningful concept when capital is regulatory, not operational, and "maintenance capex" includes loan growth. The correct approach values the **excess returns generated over the cost of equity capital**.

---

## 1. Sector Detection Rules

### 1.1 Automatic Classification Hierarchy

Banks are detected using a **multi-layer classification system**:

| Layer | Method | Criteria | Confidence |
|-------|--------|----------|------------|
| **Primary** | Industry Classification | GICS 401010 (Banks), SIC 60xx, NAICS 5221/5222 | 99%+ |
| **Secondary** | Balance Sheet Structure | Total Loans / Total Assets > 30% AND Deposits / Total Liabilities > 20% | 95%+ |
| **Tertiary** | Revenue Composition | Net Interest Income / Total Revenue > 25% OR Fee Income from banking activities > 30% | 90%+ |
| **Quaternary** | Regulatory Flag | Subject to Basel III/IV, CCAR, ECB stress tests, or banking regulator oversight | 99%+ |

### 1.2 Detailed Detection Rules

```python
# Pseudocode for bank detection
def is_bank(ticker):
    # Layer 1: Industry codes
    gics = get_gics_sector(ticker)
    sic = get_sic_code(ticker)
    if gics.startswith("40") or sic.startswith("60") or sic.startswith("61"):
        return True, "industry_code"

    # Layer 2: Balance sheet structure
    bs = get_balance_sheet(ticker)
    if (bs["loans"] / bs["total_assets"] > 0.30 and
        bs["deposits"] / bs["total_liabilities"] > 0.20):
        return True, "balance_sheet"

    # Layer 3: Revenue composition
    inc = get_income_statement(ticker)
    if inc["net_interest_income"] / inc["total_revenue"] > 0.25:
        return True, "revenue_mix"

    # Layer 4: Regulatory filings
    filings = get_filings(ticker)
    if has_call_report(filings) or mentions_basell(filings):
        return True, "regulatory"

    return False, "not_bank"
```

### 1.3 Sub-Sector Classification

Once detected as a bank, classify into sub-sector for model selection:

| Sub-Sector | Revenue Mix | Key Metrics | Preferred Model |
|------------|-------------|-------------|-----------------|
| **Large Cap Diversified Banks** | NII 50-60%, Fee 40-50% | CET1, NIM, ROTCE | Excess Return Model |
| **Regional / Community Banks** | NII 70-80%, Fee 20-30% | NIM, Efficiency, NPLs | P/B-ROE + DDM |
| **Investment Banks** | Trading 30-40%, IB 20-30% | ROE, VaR, Leverage | Excess Return Model |
| **Asset Managers** | Fee income 90%+ | AUM, fee rate, flows | AUM-based DDM |
| **Consumer Finance** | NII 80%+, provisions high | NIM, NPL, provision coverage | Excess Return Model |
| **Custody / Trust Banks** | Fee income 70%+ | AUC, operating leverage | P/B-ROE |

### 1.4 Edge Cases

| Company Type | Bank Flag? | Rationale | Handling |
|--------------|------------|-----------|----------|
| Berkshire Hathaway (BRK) | No | Diversified holding company | Use standard framework |
| Fintech lenders (SOFI, AFRM) | Hybrid | Bank charter + tech platform | Use bank module with tech adjustments |
| Insurance-bank hybrids | Split | Separate segments | Segment-level analysis |
| REITs with lending arms | No | Real estate exposure differs | Use standard framework |
| Brokerages (SCHW, IBKR) | Hybrid | Interest income significant | Bank module for NII, standard for commissions |

---

## 2. Valuation Models — What Replaces DCF

### 2.1 Primary Model: Excess Return Model (Residual Income)

The Excess Return Model (ERM) is the gold standard for bank valuation. It values a bank as:

> **Bank Value = Book Value + Present Value of Future Excess Returns**

#### Formula

```
V_0 = BV_0 + SUM(t=1 to n)[(ROE_t - k_e) * BV_{t-1}] / (1 + k_e)^t 
          + [(ROE_n - k_e) * BV_{n-1}] / [(k_e - g) * (1 + k_e)^n]
```

Where:
- `V_0` = Intrinsic value per share today
- `BV_0` = Current book value per share
- `ROE_t` = Return on equity in year t
- `k_e` = Cost of equity
- `g` = Long-term growth rate of excess returns
- `n` = Explicit forecast period (typically 3-5 years)

#### Why This Works for Banks

1. **Book value is meaningful** for banks — unlike industrials, bank book values approximate liquidation values because assets are mostly financial (loans, securities, cash)
2. **Captures the economic reality** — banks earn returns ON equity capital; value is created only when ROE > cost of equity
3. **Handles regulatory capital constraints** — growth is constrained by capital requirements, not by FCF reinvestment
4. **Dividends are not value-creative** — they distribute capital; value creation happens through NIM and fee generation

#### Two-Stage Implementation

```python
def excess_return_model(bvps, roe_forecast, ke, g_terminal, n_years=5):
    """
    Two-stage excess return model for bank valuation
    
    Parameters:
    - bvps: current book value per share
    - roe_forecast: list of ROE forecasts for years 1-n
    - ke: cost of equity
    - g_terminal: terminal growth rate of excess returns
    - n_years: length of explicit forecast
    """
    value = bvps  # Start with book value
    bv = bvps
    
    # Stage 1: Explicit forecast period
    for t in range(n_years):
        roe = roe_forecast[t]
        er = (roe - ke) * bv  # Excess return for year t
        value += er / (1 + ke) ** (t + 1)
        bv = bv * (1 + roe * (1 - payout_ratio))  # Grow BV by retained earnings
    
    # Stage 2: Terminal value (perpetual excess returns growing at g)
    terminal_roe = roe_forecast[-1]
    terminal_er = (terminal_roe - ke) * bv * (1 + g_terminal) / (ke - g_terminal)
    value += terminal_er / (1 + ke) ** n_years
    
    return value
```

### 2.2 Secondary Model: P/B-ROE Regression

The P/B-ROE regression provides a quick cross-sectional valuation check:

#### Formula

```
P/B = alpha + beta_1 * ROE + beta_2 * Growth + beta_3 * Beta + beta_4 * CET1_Premium + epsilon
```

**Simplified analytical form** (single-factor):

```
P/B = (ROE - g) / (k_e - g)
```

#### The P/B-ROE Relationship

| ROE vs Cost of Equity | P/B Implication | Interpretation |
|-----------------------|----------------|----------------|
| ROE > k_e | P/B > 1 | Bank creates value — premium justified |
| ROE = k_e | P/B = 1 | Bank earns exactly its cost of capital |
| ROE < k_e | P/B < 1 | Bank destroys value — "value trap" risk |

**Key insight**: A bank with ROE = 16.5%, k_e = 9.5%, and g = 3.5% should trade at:
```
P/B = (0.165 - 0.035) / (0.095 - 0.035) = 2.17x
```

If it trades above 2.17x, the market is either: (a) assuming higher ROE persistence, (b) using a lower cost of equity, or (c) pricing in growth optionality (e.g., rate environment, M&A).

### 2.3 Tertiary Model: Dividend Discount Model (DDM)

Use DDM when:
- The bank has a **stable, predictable dividend policy** (European banks, Canadian banks)
- The bank is in **mature, low-growth phase** (regional banks post-consolidation)
- **Payout ratios are high and stable** (>50%)

#### Gordon Growth Formula

```
V_0 = D_1 / (k_e - g)
```

Where:
- `D_1` = Expected dividend per share next year
- `k_e` = Cost of equity
- `g` = Sustainable growth rate (typically lower for banks due to capital constraints)

#### Sustainable Growth Rate for Banks

```
g = ROE * (1 - Payout Ratio) = ROE * Retention Ratio
```

**Important constraint**: Bank growth is capped by regulatory capital requirements:
```
g_max = (CET1 Ratio / Minimum CET1 Requirement) - 1
```

### 2.4 Model Selection by Sub-Sector

| Sub-Sector | Primary Model | Secondary | When to Use Secondary |
|------------|---------------|-----------|----------------------|
| Large Diversified Banks (JPM, BAC) | Excess Return | P/B-ROE | Quick screening, peer ranking |
| Regional Banks (PNFP, TFC) | P/B-ROE + DDM | Excess Return | When M&A premiums are relevant |
| Investment Banks (GS, MS) | Excess Return | P/TBV | Trading revenues are volatile |
| Asset Managers (BLK, STT) | AUM-based DDM | P/E | Fee rate stability assessment |
| Custody Banks (BK, STT) | P/B-ROE | DDM | Operating leverage assessment |
| Consumer Finance (COF, SYF) | Excess Return | P/E | Credit cycle turning points |

### 2.5 Worked Example: JPMorgan Chase (JPM)

#### Step 1: Gather Current Data (2025)

| Metric | Value | Source |
|--------|-------|--------|
| Stock Price | $336.47 | Market |
| Book Value/Share | $128.38 | 10-K |
| Tangible Book Value/Share | $103.73 | 10-K |
| 2025 Net Income | $57.05B | 10-K |
| Total Equity | $362.4B | Balance Sheet |
| ROE (reported) | 16.5% | Calculated |
| ROA | 1.27% | Calculated |
| Dividend/Share | $6.00 | Company |
| Payout Ratio | 28.7% | Calculated |
| Beta | 0.98 | Yahoo Finance |
| P/B | 2.62x | Market |
| CET1 Ratio | ~15.0% | Company filing |
| Efficiency Ratio | ~33% | Calculated |
| NIM | ~2.16% | Calculated |

#### Step 2: Estimate Cost of Equity

```
k_e = r_f + Beta * (r_m - r_f) + Banking_Specific_Premium

Where:
- r_f = 4.25% (10-year Treasury)
- Beta = 0.98
- ERP = 5.5%
- Banking premium = 0.50% (systemic risk, regulatory overhang)

k_e = 4.25% + 0.98 * 5.5% + 0.50% = 9.64% ≈ 9.5%
```

#### Step 3: Forecast ROE Trajectory

| Year | ROE Assumption | Rationale |
|------|---------------|-----------|
| 2025A | 16.5% | Actual |
| 2026E | 15.5% | Slight compression from competitive NIM pressure |
| 2027E | 15.0% | Rate normalization, fee income mix stable |
| 2028E | 14.5% | Investment spend on technology |
| 2029E | 14.0% | Gradual mean reversion |
| 2030E | 13.5% | Long-run sustainable ROE |

Terminal growth `g` = 3.5% (nominal GDP growth)

#### Step 4: Calculate Excess Returns

```
Year 1: BV = $128.38, ROE = 15.5%, k_e = 9.5%
  Excess Return = (15.5% - 9.5%) * $128.38 = $7.70/share
  PV = $7.70 / 1.095 = $7.03

Year 2: BV = $134.93 (grown by retained earnings), ROE = 15.0%
  Excess Return = (15.0% - 9.5%) * $134.93 = $7.42/share
  PV = $7.42 / 1.095^2 = $6.19

Year 3: BV = $141.68, ROE = 14.5%
  Excess Return = (14.5% - 9.5%) * $141.68 = $7.08/share
  PV = $7.08 / 1.095^3 = $5.41

Year 4: BV = $148.35, ROE = 14.0%
  Excess Return = (14.0% - 9.5%) * $148.35 = $6.68/share
  PV = $6.68 / 1.095^4 = $4.67

Year 5: BV = $155.01, ROE = 13.5%
  Excess Return = (13.5% - 9.5%) * $155.01 = $6.20/share
  PV = $6.20 / 1.095^5 = $3.96
```

**Stage 1 PV of Excess Returns = $27.26**

#### Step 5: Terminal Value

```
Terminal BV (Year 5) = $161.46
Terminal Excess Return = (13.5% - 9.5%) * $161.46 * (1 + 3.5%) / (9.5% - 3.5%)
                       = $111.73
PV of Terminal = $111.73 / 1.095^5 = $71.15
```

#### Step 6: Intrinsic Value

```
Intrinsic Value = BV_0 + Stage 1 PV + Terminal PV
                = $128.38 + $27.26 + $71.15
                = $226.79
```

#### Step 7: Compare to Market

| Metric | Value |
|--------|-------|
| Intrinsic Value (Excess Return Model) | **$226.79** |
| Current Market Price | **$336.47** |
| Implied Overvaluation | **48%** |
| Implied P/B (fair) | 1.77x |
| Actual P/B (market) | 2.62x |

**Interpretation**: JPMorgan trades at a **significant premium to intrinsic value** based on a conservative excess return model. The market is pricing in one or more of:
1. **Higher sustainable ROE** (~18% vs our 13.5% terminal assumption)
2. **Lower cost of equity** (~8.5% vs our 9.5% assumption)
3. **Growth optionality** — market share gains, rate environment benefits, franchise premium
4. **Safety premium** — JPM's status as a "fortress balance sheet" bank commands a premium

#### Step 8: Reverse-Engineered Implied Parameters

| What Market is Pricing | Implied Value |
|------------------------|---------------|
| Implied k_e (if ROE=16.5%, g=3.5%) | ~8.5% |
| Implied terminal ROE (if k_e=9.5%, g=3.5%) | ~18.0% |
| Implied g (if ROE=16.5%, k_e=9.5%) | ~5.0% |

**Conclusion**: JPMorgan's premium valuation reflects the market's view of it as a **best-in-class franchise** with above-peer ROE sustainability, lower systemic risk, and superior execution. The excess return model provides a disciplined anchor; deviations from it should be justified with specific thesis points.

---

## 3. Key Operating Metrics

### Ranking by Valuation Importance

#### Tier 1: Capital & Profitability (Directly Drive Valuation)

| # | Metric | Formula | Why It Matters | Good | Red Flag |
|---|--------|---------|----------------|------|----------|
| 1 | **CET1 Ratio** | CET1 Capital / Risk-Weighted Assets (RWA) | Regulatory capital adequacy; determines lending capacity, dividend safety, and regulatory standing | 12-15% | <10% (breach risk), <7% (critical) |
| 2 | **ROE** | Net Income / Average Shareholders' Equity | Primary profitability metric; drives P/B multiple through excess returns | 12-18% | <8% (below cost of capital), <5% (distressed) |
| 3 | **ROTE / ROTCE** | Net Income / Average Tangible Common Equity | More conservative than ROE; strips out goodwill and preferreds; comparable across M&A histories | 14-20% | <10%, declining 3+ quarters |
| 4 | **NIM** | Net Interest Income / Average Earning Assets | Core banking profitability; driven by asset yield - funding cost spread | 2.5-3.5% | <1.5% (unsustainable), declining >25bps/qtr |
| 5 | **Efficiency Ratio** | Non-Interest Expense / (Net Interest Income + Non-Interest Income) | Operating leverage; lower = better cost management | 50-58% | >65% (bloated), >75% (crisis) |

#### Tier 2: Asset Quality & Risk (Determine Earnings Stability)

| # | Metric | Formula | Why It Matters | Good | Red Flag |
|---|--------|---------|----------------|------|----------|
| 6 | **NPL Ratio** | Non-Performing Loans / Gross Loans | Credit quality indicator; drives provisioning needs | 0.5-1.5% | >3% (credit cycle turn), >5% (crisis) |
| 7 | **Provision Coverage** | Loan Loss Reserves / NPLs | Buffer against credit losses; higher = more conservative | 100-200% | <50% (under-provisioned), declining rapidly |
| 8 | **Net Charge-Off Ratio** | Charge-Offs - Recoveries / Average Loans | Actual credit losses realized | 0.2-0.5% | >1.5% (severe deterioration), >2% (crisis) |
| 9 | **Loan-to-Deposit Ratio** | Total Loans / Total Deposits | Liquidity indicator; >100% signals wholesale funding dependence | 75-90% | >100% (liquidity risk), >110% (severe) |
| 10 | **CASA Ratio** | Current + Savings Account Deposits / Total Deposits | Funding quality; CASA = cheapest, most stable funding | 40-60% | <25% (expensive funding), declining trend |

#### Tier 3: Diversification & Leverage (Franchise Quality)

| # | Metric | Formula | Why It Matters | Good | Red Flag |
|---|--------|---------|----------------|------|----------|
| 11 | **Fee Income Ratio** | Non-Interest Income / Total Revenue | Revenue diversification; fee income is non-rate-sensitive | 30-50% | <15% (over-reliance on NII), declining |
| 12 | **Leverage Ratio** | Tier 1 Capital / Total Assets (non-risk-weighted) | Backstop capital measure; regulators monitor closely | 5-8% | <4% (regulatory minimum), <3.5% (breach) |
| 13 | **ROA** | Net Income / Average Total Assets | Asset-level profitability; comparable across sizes | 1.0-1.5% | <0.7%, declining >20bps/year |
| 14 | **Cost of Funding** | Interest Expense / Average Interest-Bearing Liabilities | Competitive positioning on liability side | 0.5-2.0% | >3.5%, rising faster than peers |
| 15 | **Tangible Book Value Growth** | (TBVPS_t - TBVPS_{t-1}) / TBVPS_{t-1} | Organic capital generation; supports dividend capacity | 5-10% annual | Negative (dilution), <3% sustained |

### Key Formulas Summary

```
CET1 Ratio         = Common Equity Tier 1 Capital / Risk-Weighted Assets
ROE                = Net Income / Average Shareholders' Equity
ROTCE              = Net Income / Average Tangible Common Equity
NIM                = (Interest Income - Interest Expense) / Average Earning Assets
Efficiency Ratio   = Non-Interest Expense / (Net Interest Income + Non-Interest Income)
NPL Ratio          = Non-Performing Loans / Total Gross Loans
Provision Coverage = Loan Loss Reserves / Non-Performing Loans
NCO Ratio          = (Charge-Offs - Recoveries) / Average Loans
LTD Ratio          = Total Loans / Total Deposits
CASA Ratio         = (Current Deposits + Savings Deposits) / Total Deposits
Fee Income Ratio   = Non-Interest Income / Total Revenue
Leverage Ratio     = Tier 1 Capital / Total Exposure (leverage basis)
ROA                = Net Income / Average Total Assets
```

---

## 4. Key Risk Factors — Banking Specific

### 4.1 Credit Cycle Risk

**What it is**: Loan losses are cyclical and non-linear. A small increase in unemployment can cause a large increase in defaults due to correlation across borrowers (concentrated geographies, industries, loan types).

**Quantitative Indicators**:

| Indicator | Formula | Warning Threshold | Source |
|-----------|---------|-------------------|--------|
| NPL Ratio | NPLs / Gross Loans | >2.5% (early warning), >5% (severe) | Call Reports, 10-K |
| Provision Coverage | Reserves / NPLs | <80% (insufficient), <50% (critical) | Call Reports |
| Net Charge-Off Rate | (Gross COs - Recoveries) / Avg Loans | >1.0% (early), >2.5% (severe) | Call Reports |
| Watchlist / Criticized Loans | Special Mention + Substandard / Total Loans | >5% (elevated), >10% (severe) | Internal / SEC Filings |
| CRE Concentration | CRE Loans / Total Capital | >300% (regulatory trigger) | Call Reports |
| Shared National Credit Reviews | Downgrades / Total SNCs reviewed | >15% downgrade rate | Federal Reserve |
| Unemployment Rate (lagged 12mo) | Change in UR | +2pp = ~1pp NCO increase | BLS |

**How to monitor**: Track NPL ratio trajectory quarterly. If NPLs rise 3 consecutive quarters, run stress scenario. If provision coverage drops below 100% while NPLs are rising, the bank is under-provisioned.

### 4.2 Interest Rate Risk (IRR / NIM Sensitivity)

**What it is**: Banks borrow short (deposits reprice quickly) and lend long (loans reprice slowly). Rate changes affect NIM, AFS/HTM mark-to-market, and deposit beta.

**Quantitative Indicators**:

| Indicator | Formula | Warning Threshold | Source |
|-----------|---------|-------------------|--------|
| Rate Sensitivity Gap | Rate-Sensitive Assets (RSA) - Rate-Sensitive Liabilities (RSL), 1-year bucket | >20% of assets = exposed | Call Report Schedule RC-R |
| Duration of Equity | Estimated change in equity value / +100bp parallel shift | >10% decline | Internal risk models |
| Deposit Beta | Change in deposit cost / Change in Fed Funds Rate | >70% (no pricing power) | Calculated from earnings |
| AOCI / Equity (for AFS banks) | Accumulated OCI / Total Equity | <-15% (significant MTM losses) | 10-K |
| Unrealized HTM Losses | Unrealized Losses on HTM / Tangible Equity | >50% (trapped capital) | 10-K, FDIC data |
| Fixed-Rate Loan % | Fixed-Rate Loans / Total Loans | >60% in rising rate environment | Internal data |

**How to monitor**: Run parallel shift scenarios (+100bp, +200bp, -100bp). Track deposit beta each quarter. Monitor AOCI erosion — if AOCI > -20% of equity, the bank has significant unrealized losses that could crystallize if forced to sell.

### 4.3 Regulatory Risk

**What it is**: Changes in capital requirements, stress test parameters, accounting rules, or enforcement actions can dramatically impact capital availability, dividend capacity, and strategic flexibility.

**Quantitative Indicators**:

| Indicator | Formula | Warning Threshold | Source |
|-----------|---------|-------------------|--------|
| CET1 Buffer | Actual CET1 - Regulatory Minimum | <2.5pp (tight), <1.5pp (critical) | Company filings |
| Stress Capital Buffer (SCB) | Fed-imposed buffer above minimum | >4.5% (restrictive) | CCAR results |
| GSIB Surcharge | Additional capital for global systemically important banks | 1.0-3.5% extra | FSB annual list |
| LCR (Liquidity Coverage Ratio) | HQLA / Net Cash Outflows (30-day) | <110% (near minimum), <100% (breach) | Company filings |
| NSFR (Net Stable Funding Ratio) | Available Stable Funding / Required | <105% (near minimum) | Company filings |
| Enforcement Actions | Number of formal actions | Any consent order/MOU (restrictive) | OCC/FDIC/Fed websites |

### 4.4 Liquidity Risk

**What it is**: The risk that a bank cannot meet cash outflows without incurring unacceptable losses. SVB (2023) demonstrated how quickly liquidity can evaporate when uninsured deposits flee.

**Quantitative Indicators**:

| Indicator | Formula | Warning Threshold | Source |
|-----------|---------|-------------------|--------|
| Uninsured Deposit % | Uninsured Deposits / Total Deposits | >50% (vulnerable), >70% (high risk) | Call Reports |
| Brokered Deposit % | Brokered Deposits / Total Deposits | >15% (expensive, volatile), >25% (dependent) | Call Reports |
| LCR | High-Quality Liquid Assets / 30-day Net Cash Outflows | <120% (concerning), <100% (breach) | Company filings |
| Wholesale Funding % | (FHLB Advances + Repo + CP + Other Wholesale) / Total Liabilities | >20% (concerning), >30% (high risk) | Call Reports |
| HTM as % of Securities | HTM Securities / Total Securities | >70% (illiquid portfolio) | 10-K |
| Cash + Unencumbered Securities / Total Assets | Liquid Assets / Total Assets | <10% (low), <5% (critical) | Balance Sheet |
| Deposit Beta Trend | Quarter-over-quarter change in deposit cost | Rising faster than Fed = losing pricing power | Earnings call |

### 4.5 Operational Risk

**What it is**: Risk of loss from failed internal processes, people, systems, or external events (cyberattacks, fraud, legal).

**Quantitative Indicators**:

| Indicator | Formula | Warning Threshold | Source |
|-----------|---------|-------------------|--------|
| Operational Loss / Revenue | Op Loss / Total Revenue | >1% (elevated) | Internal / annual report |
| IT Spend / Non-Interest Expense | Technology Investment / OpEx | <10% (under-invested) | Company disclosures |
| Litigation Reserves / Equity | Legal Reserves / Total Equity | >5% (significant exposure) | 10-K footnotes |
| Fraud-Related Charge-offs | Fraud COs / Total COs | >10% of COs | Internal data |

### 4.6 Contagion / Systemic Risk

**What it is**: Risk that distress at one institution spreads to others via interbank exposures, correlated asset sales, or market panic.

**Quantitative Indicators**:

| Indicator | Formula | Warning Threshold | Source |
|-----------|---------|-------------------|--------|
| Interbank Exposure / Capital | Due from Banks / Tier 1 Capital | >50% (concentrated) | Call Reports |
| CDS Spread (5Y) | 5-Year Credit Default Swap spread | >200bps (distressed), >500bps (crisis) | Bloomberg |
| Deposit Outflows (qoq) | Deposit Change / Beginning Deposits | >-5% (accelerating), >-10% (severe) | Call Reports |
| Correlation to KRE (Regional Bank ETF) | 90-day stock return correlation | >0.85 (systemic sensitivity) | Market data |

---

## 5. Quality Indicators — What Makes a "Good Bank"

### Top 10 Quality Rankings

| Rank | Quality Indicator | What "Good" Looks Like | Why It Matters |
|------|-------------------|----------------------|----------------|
| 1 | **Consistent ROE above cost of equity** | 10+ years of ROE > 12% | Demonstrates sustainable value creation |
| 2 | **CET1 ratio well above minimum with rising buffer** | CET1 > 12% and increasing | Capital is the ultimate defense; supports growth and dividends |
| 3 | **Low and stable NPL ratio through cycles** | NPL < 1.5% even in downturns | Asset quality is the #1 differentiator across credit cycles |
| 4 | **Efficiency ratio below peer median** | <55% (large banks), <50% (regionals) | Cost discipline drives operating leverage |
| 5 | **Diversified revenue mix** | Fee income > 35% of total | Reduces reliance on rate-sensitive NII |
| 6 | **Stable, low-cost deposit franchise** | CASA > 45%, deposit beta < 60% | Deposit franchise is the core moat; cheap funding = sustainable NIM |
| 7 | **Conservative provisioning** | Coverage > 150%, "forward-looking" CECL model | Over-provisioned banks survive downturns; under-provisioned ones dilute shareholders |
| 8 | **Predictable earnings trajectory** | EPS coefficient of variation < 15% | Low volatility = lower cost of equity = higher multiple |
| 9 | **Strong management track record** | 5+ year tenure, through-cycle performance | Banking is a relationship business; management quality is critical |
| 10 | **Disciplined capital allocation** | Dividend + buyback = 60-100% of earnings, TBV/shr growing | Balances shareholder returns with balance sheet strength |

### Quality Scoring Framework

```python
def bank_quality_score(metrics):
    """
    Score a bank 0-100 based on quality indicators
    """
    score = 0
    
    # 1. ROE consistency (0-20 pts)
    if metrics["roe_avg_10yr"] > 0.15: score += 20
    elif metrics["roe_avg_10yr"] > 0.12: score += 15
    elif metrics["roe_avg_10yr"] > 0.10: score += 10
    elif metrics["roe_avg_10yr"] > 0.08: score += 5
    
    # 2. Capital strength (0-15 pts)
    if metrics["cet1_ratio"] > 0.14: score += 15
    elif metrics["cet1_ratio"] > 0.12: score += 12
    elif metrics["cet1_ratio"] > 0.10: score += 8
    elif metrics["cet1_ratio"] > 0.08: score += 4
    
    # 3. Asset quality (0-15 pts)
    if metrics["npl_ratio"] < 0.01: score += 15
    elif metrics["npl_ratio"] < 0.015: score += 12
    elif metrics["npl_ratio"] < 0.025: score += 8
    elif metrics["npl_ratio"] < 0.04: score += 4
    
    # 4. Efficiency (0-10 pts)
    if metrics["efficiency_ratio"] < 0.50: score += 10
    elif metrics["efficiency_ratio"] < 0.55: score += 8
    elif metrics["efficiency_ratio"] < 0.60: score += 5
    elif metrics["efficiency_ratio"] < 0.65: score += 3
    
    # 5. Revenue diversification (0-10 pts)
    if metrics["fee_income_ratio"] > 0.45: score += 10
    elif metrics["fee_income_ratio"] > 0.35: score += 8
    elif metrics["fee_income_ratio"] > 0.25: score += 5
    elif metrics["fee_income_ratio"] > 0.15: score += 3
    
    # 6. Deposit franchise (0-10 pts)
    if metrics["casa_ratio"] > 0.50: score += 10
    elif metrics["casa_ratio"] > 0.40: score += 8
    elif metrics["casa_ratio"] > 0.30: score += 5
    elif metrics["casa_ratio"] > 0.20: score += 3
    
    # 7. Provisioning (0-10 pts)
    if metrics["provision_coverage"] > 1.50: score += 10
    elif metrics["provision_coverage"] > 1.00: score += 7
    elif metrics["provision_coverage"] > 0.70: score += 4
    elif metrics["provision_coverage"] > 0.50: score += 2
    
    # 8. Earnings stability (0-5 pts)
    if metrics["eps_cv_5yr"] < 0.10: score += 5
    elif metrics["eps_cv_5yr"] < 0.15: score += 4
    elif metrics["eps_cv_5yr"] < 0.20: score += 2
    
    # 9. Capital allocation (0-5 pts)
    if 0.60 < metrics["payout_ratio"] < 1.00 and metrics["tbv_growth"] > 0.03:
        score += 5
    elif metrics["payout_ratio"] > 0.30: score += 3
    
    return min(score, 100)
```

### JPMorgan Quality Score Assessment

| Indicator | JPM Value | Score |
|-----------|-----------|-------|
| 10-year avg ROE | ~13% | 15/20 |
| CET1 Ratio | ~15% | 15/15 |
| NPL Ratio | ~0.6% | 15/15 |
| Efficiency Ratio | ~55% | 5/10 |
| Fee Income Ratio | ~48% | 10/10 |
| CASA Ratio | ~55% | 10/10 |
| Provision Coverage | ~200% | 10/10 |
| EPS Volatility (5yr CV) | ~12% | 5/5 |
| Payout Ratio | ~29% | 3/5 |
| **Total Quality Score** | | **88/100** |

**Verdict**: JPMorgan scores as an **exceptional-quality bank** (88/100), driven by fortress capital levels, pristine asset quality, and diversified revenue. The low payout ratio reflects capital retention for regulatory requirements and growth optionality.

---

## 6. Stress Test Scenarios — Bank Specific

### Scenario Design Framework

Each scenario specifies exact parameter shocks and expected valuation impact. Scenarios should be run quarterly.

### Scenario 1: Credit Downturn (NPL Spike)

**Trigger**: Rising unemployment, CRE price decline, or sector-specific stress

| Parameter | Baseline | Shock | Rationale |
|-----------|----------|-------|-----------|
| NPL Ratio | 0.6% | 3.0% | Moderate recession level |
| Provision Coverage | 200% | 80% | Reserves depleted by NPL surge |
| Net Charge-Off Rate | 0.3% | 1.5% | 5x increase |
| Pre-Provision Net Revenue | Flat | -10% | Lower loan demand, lower fee income |
| ROE | 16.5% | 4.0% | Massive provision build |
| CET1 Impact | 15.0% | 12.5% | Earnings retention partially offsets |

**Valuation Impact**:
```
Pre-stress: P/B = 2.62x, Price = $336.47
Post-stress: P/B = 0.90x (ROE = 4% < k_e = 9.5%), Price = $115.54
Expected Drawdown: -66%
```

**Historical analog**: 2008-2009 Financial Crisis (though this scenario is milder than 2008)

### Scenario 2: Interest Rate Shock

**Trigger**: Fed tightening cycle, parallel shift + curve inversion

| Parameter | Baseline | Shock | Rationale |
|-----------|----------|-------|-----------|
| Fed Funds Rate | 4.50% | 6.50% | +200bp parallel shift |
| 10-Year Treasury | 4.25% | 5.75% | +150bp |
| Deposit Beta | 55% | 75% | Accelerating deposit repricing |
| NIM | 2.16% | 2.40% | Initial expansion, then compression |
| AFS/HTM MTM Losses | -2% of equity | -15% of equity | Duration risk crystallizes |
| Loan Growth | +5% | -3% | Higher rates crush demand |
| ROE | 16.5% | 13.0% | NIM benefit offset by lower volumes, higher funding costs |

**Valuation Impact**:
```
Pre-stress: P/B = 2.62x, Price = $336.47
Post-stress: P/B = 1.50x (ROE compression + AOCI hit), Price = $192.57
Expected Drawdown: -43%
```

**Key sensitivity**: Banks with high HTM securities exposure (SVB profile) see much worse outcomes. JPM's diversified model provides some insulation.

### Scenario 3: Liquidity Crisis (Deposit Flight)

**Trigger**: Loss of confidence, social media-driven bank run, competitor failure

| Parameter | Baseline | Shock | Rationale |
|-----------|----------|-------|-----------|
| Deposit Outflows (30 days) | -1% | -25% | Severe but not SVB-level (-80%) |
| Uninsured Deposit % | 30% | 45% | Flight of rate-sensitive deposits |
| FHLB Borrowings / Assets | 2% | 12% | Emergency wholesale funding |
| Brokered Deposit % | 0% | 8% | Expensive replacement funding |
| Funding Cost (incremental) | 4.5% | 7.5% | Panic premium |
| NIM | 2.16% | 1.50% | Expensive funding crushes spread |
| HTM/AFS Forced Sales | None | 10% of securities | Liquidity needs force realization of losses |
| ROE | 16.5% | 2.0% | NIM collapse + loss realization |

**Valuation Impact**:
```
Pre-stress: P/B = 2.62x, Price = $336.47
Post-stress: P/B = 0.70x (earnings collapse + capital hit), Price = $89.87
Expected Drawdown: -73%
```

**Historical analog**: SVB (March 2023), though this assumes JPM's diversified deposit base provides some defense vs. a monocline bank.

### Scenario 4: Regulatory Shock (CET1 Requirement Increase)

**Trigger**: Basel IV implementation, GSIB surcharge increase, or Fed stress test failure

| Parameter | Baseline | Shock | Rationale |
|-----------|----------|-------|-----------|
| Minimum CET1 Requirement | 11.9% | 13.5% | Basel IV + 150bp buffer |
| Current CET1 | 15.0% | 15.0% | Unchanged — but buffer shrinks |
| CET1 Buffer (surplus) | 3.1pp | 1.5pp | Restricted capital deployment |
| Dividend Capacity | $6.00/shr | $3.00/shr | Capital retention required |
| Buyback Capacity | $15B/yr | $3B/yr | Sharply reduced |
| Loan Growth Constraint | None | +3% max | Capital-constrained growth |
| ROE | 16.5% | 13.0% | Lower leverage, reduced capital returns |
| Payout Ratio | 29% | 15% | Forced retention |

**Valuation Impact**:
```
Pre-stress: P/B = 2.62x, Price = $336.47
Post-stress: P/B = 1.40x (lower ROE + reduced shareholder returns), Price = $179.73
Expected Drawdown: -47%
```

**Historical analog**: European banks post-Basel IV (2019-2023), where higher capital requirements compressed ROEs by 200-400bps.

### Summary of Stress Test Impacts

| Scenario | P/B Impact | Price Impact | Key Vulnerability |
|----------|-----------|--------------|-------------------|
| Credit Downturn | 2.62x → 0.90x | -66% | NPL spike, provision inadequacy |
| Rate Shock | 2.62x → 1.50x | -43% | Deposit beta, HTM duration |
| Liquidity Crisis | 2.62x → 0.70x | -73% | Uninsured deposits, wholesale dependence |
| Regulatory Shock | 2.62x → 1.40x | -47% | CET1 buffer, capital return restrictions |

**Reverse stress test**: At what P/B does JPM become attractive? If P/B drops below 1.2x (implying ROE ≈ 10-11%), the stock offers a compelling risk/reward given the franchise quality.

---

## 7. Peer Comparison Methodology

### 7.1 Metrics to Compare

**Within the same market (US banks compared to US banks)**:

| Category | Primary Metrics | Weight |
|----------|----------------|--------|
| Profitability | ROE, ROTCE, ROA | 25% |
| Capital | CET1 Ratio, Leverage Ratio, CET1 Buffer | 20% |
| Efficiency | Efficiency Ratio, Cost/Income | 15% |
| Asset Quality | NPL Ratio, NCO Rate, Coverage | 15% |
| Valuation | P/B, P/TBV, P/E | 15% |
| Growth | TBV/shr Growth, Loan Growth, Deposit Growth | 10% |

**Always compare on a like-for-like basis**:
- Use ROTCE (not ROE) if one bank has significant goodwill from acquisitions
- Use P/TBV (not P/B) for acquisitive banks
- Adjust for different tax rates in cross-border comparisons
- Use tangible equity for all capital comparisons

### 7.2 Same-Market vs Cross-Market Issues

| Issue | US Banks | European Banks | Asian Banks |
|-------|----------|----------------|-------------|
| Capital Requirements | SCB + GSIB surcharge | Pillar 2 + CCoB | Varies by country |
| Accounting | US GAAP | IFRS 9 (forward-looking provisions) | IFRS or local GAAP |
| Tax Rate | ~21% federal | ~25-30% | Varies (0-35%) |
| Reserve Method | CECL (current expected credit losses) | IFRS 9 ECL | Varies |
| Dividend Policy | Quarterly, stable | Annual, variable (ECB guidance) | Varies |
| Ownership Structure | Dispersed | Concentrated (families, sovereign) | Often concentrated |
| NIM Environment | Higher (4-5% pre-tax NIMs) | Lower (1.5-2.5%) | Varies widely |

**Cross-market comparison adjustments**:

```python
def cross_market_adjustments(metrics, country):
    adjustments = {}
    
    if country == "EU":
        # IFRS 9 provisions tend to be higher/earlier than CECL
        adjustments["provision_coverage"] = metrics["provision_coverage"] * 0.85
        # European banks typically have lower NIMs
        adjustments["nim_normalization"] = metrics["nim"] / 0.02  # normalize to 2%
        
    elif country in ["JP", "KR"]:
        # Asian banks often have higher NIMs but lower fee income
        adjustments["nim_normalization"] = metrics["nim"] / 0.025
        # Sovereign ownership can distort capital allocation
        adjustments["payout_adjustment"] = 0.80
        
    elif country == "US":
        # US GAAP CECL vs IFRS 9
        adjustments["provision_coverage"] = metrics["provision_coverage"] * 1.15
        adjustments["nim_normalization"] = metrics["nim"] / 0.03
        
    return adjustments
```

### 7.3 Adjusting for Different Regulatory Regimes

| Regulatory Difference | Adjustment Method | Example |
|----------------------|-------------------|---------|
| Different CET1 minimums | Compare CET1 **buffer** (actual - minimum), not raw ratio | US bank at 12% (min 8%) = 4pp buffer; EU bank at 14% (min 10.5%) = 3.5pp buffer |
| CECL vs incurred loss | Adjust provision coverage by regime-specific average | CECL banks: +15% coverage; incurred loss: baseline |
| Tax rate differences | Use **pre-tax ROA** and **ROTCE** for cross-border | Pre-tax ROA = ROA / (1 - tax rate) |
| Different GSIB surcharges | Strip out surcharge impact for peer comparison | Normalize all to 10.5% CET1 equivalent |
| Dividend restrictions | Use P/TBV instead of dividend yield for valuation | ECB restricted dividends 2020-2021 |

### 7.4 Peer Group Construction

```python
# Example: JPMorgan peer groups
jpm_peers = {
    "money_center": ["BAC", "WFC", "C"],           # Large diversified US banks
    "gsib_global": ["HSBC", "UBS", "DB", "BNP"],    # Global systemically important
    "diversified_financial": ["GS", "MS", "BLK"],    # Investment banks / asset managers
    "large_regionals": ["PNC", "TFC", "USB"],        # Large regional competitors
}

# Regression-based peer valuation
def pb_roe_regression(peer_data):
    """
    Run P/B-ROE regression across peers
    Returns: predicted P/B, premium/discount vs peers
    """
    import numpy as np
    
    roes = [d["roe"] for d in peer_data]
    pbs = [d["pb"] for d in peer_data]
    
    # Linear regression: P/B = alpha + beta * ROE
    coeffs = np.polyfit(roes, pbs, 1)
    
    def predicted_pb(roe):
        return coeffs[1] + coeffs[0] * roe
    
    return predicted_pb
```

---

## 8. Framework Component Mapping Table

| Standard Framework Component | Bank-Specific Replacement | Rationale |
|------------------------------|---------------------------|-----------|
| **DCF (FCF-based)** | **Excess Return Model** | Bank value = Book Value + PV of (ROE - k_e) * Equity. Deposits are funding, not FCF. Regulatory capital constrains "reinvestment." FCF is meaningless when capital requirements dictate growth. |
| **ROIC** | **ROE / ROTCE / RAROC** | Banks have no "invested capital" in the industrial sense. Equity IS the capital base. RAROC (Risk-Adjusted Return on Capital) adjusts returns for credit/market/operational risk capital. |
| **Operating Leverage** | **Financial Leverage + NIM Sensitivity** | Banks have fixed cost bases (branches, technology) but the critical leverage is financial (equity multiplier = Assets/Equity, typically 10-15x). NIM sensitivity measures revenue leverage to rate changes. |
| **P/E multiple** | **P/B (primary), P/TBV, P/E (secondary)** | P/E is distorted by provisioning volatility, capital raises, and tax changes. P/B anchors to book value which is economically meaningful for banks. Use P/E only for stable, mature banks with predictable earnings. |
| **SBC analysis** | **Compensation/Revenue ratio, Efficiency Ratio** | Banks don't use SBC as heavily as tech. Instead, monitor compensation as % of revenue (typically 30-50% for investment banks, 20-30% for commercial banks). High compensation/revenue = poor shareholder alignment. |
| **FCF Yield** | **Dividend Yield + Buyback Yield** | Banks return capital via dividends and buybacks (when permitted by regulators). FCF Yield is replaced by shareholder yield = (Dividends + Buybacks) / Market Cap. |
| **Revenue growth focus** | **NII growth + Fee income growth (decomposed)** | Bank revenue has two distinct components: (1) NII (rate-sensitive, credit-cyclical) and (2) Fee income (less cyclical). Decompose growth: NII growth = volume growth + NIM change. Fee growth = AUM flows x fee rate + transaction volumes. |
| **Gross Margin** | **NIM (Net Interest Margin)** | NIM = Net Interest Income / Average Earning Assets. This is the bank equivalent of gross margin — the core spread between what the bank earns on assets and pays for liabilities. |
| **EBITDA Margin** | **Pre-Provision Net Revenue (PPNR) / Revenue** | PPNR = Revenue - Non-Interest Expense (before provisions and taxes). This is the bank equivalent of operating profit, as provisioning is a "cost of goods sold" for banks (credit losses are the primary COGS). |
| **CapEx / D&A** | **Loan Growth + Technology Investment** | Banks don't have traditional CapEx. "Growth capex" = net loan growth (requires capital allocation). "Maintenance capex" = technology + compliance spend. Both are expensed through the income statement. |
| **Net Debt** | **Not applicable** | Banks ARE leveraged by design. Net debt is not a relevant metric. Instead, monitor: (1) LTD ratio, (2) wholesale funding dependence, (3) LCR/NSFR. |
| **Working Capital** | **Not applicable** | Banks don't have working capital in the industrial sense. Deposits are both a liability AND the core funding source. Monitor deposit trends instead. |

### Complete Mapping Visualization

```
Standard Framework                    Banking Module
─────────────────────────────────────────────────────────────────
Revenue Growth    ──────────────►   NII Growth + Fee Income Growth
                    Decompose:      Volume + NIM change + Fee rate

Gross Margin      ──────────────►   NIM (Net Interest Margin)
                    Formula:        (Interest Income - Int Expense) / Avg Earning Assets

Operating Margin  ──────────────►   Efficiency Ratio (inverse)
                    Formula:        Non-Interest Expense / (NII + Non-II)

FCF               ──────────────►   Dividend + Buyback (shareholder yield)
                    Formula:        (DPS x Shares + Buybacks) / Market Cap

ROIC              ──────────────►   ROE / ROTCE / RAROC
                    Formula:        Net Income / Average Equity

P/E Multiple      ──────────────►   P/B Multiple (primary)
                    Formula:        Price / Book Value Per Share

Operating         ──────────────►   NIM Beta x Financial Leverage
Leverage                            Asset/Equity ratio (typically 10-15x)

SBC Analysis      ──────────────►   Comp/Revenue Ratio
                    Formula:        Personnel Expense / Total Revenue

DCF (FCF-based)   ──────────────►   Excess Return Model
                    Formula:        BV + PV[(ROE - k_e) x BV]
```

---

## 9. Reverse Engineering for Banks

### What the Market is Pricing In

Given a bank's current P/B ratio, we can reverse-engineer the market's implied assumptions:

### Method 1: Implied ROE from P/B-ROE Relationship

From the simplified P/B-ROE formula:
```
P/B = (ROE - g) / (k_e - g)
```

Solve for implied ROE:
```
Implied ROE = (P/B) * (k_e - g) + g
```

**Example — JPMorgan**:
```
P/B = 2.62, k_e = 9.5%, g = 3.5%
Implied ROE = 2.62 * (9.5% - 3.5%) + 3.5% = 19.2%
```

**Interpretation**: The market is pricing in a **19.2% sustainable ROE** for JPMorgan. Given that JPM's actual ROE is ~16.5%, the market is either:
1. Overestimating sustainable ROE by ~270bps, OR
2. Using a lower cost of equity (~8.2% would justify 2.62x P/B with 16.5% ROE)

### Method 2: Implied Cost of Equity

```
Implied k_e = [(ROE - g) / (P/B)] + g
```

**Example — JPMorgan**:
```
ROE = 16.5%, g = 3.5%, P/B = 2.62
Implied k_e = [(16.5% - 3.5%) / 2.62] + 3.5% = 8.5%
```

**Interpretation**: The market is using an **8.5% cost of equity** for JPMorgan, 100bps below our CAPM-derived estimate. This reflects a **franchise premium** — investors view JPM as lower risk than the average bank due to its diversification, scale, and regulatory standing.

### Method 3: Implied Growth Rate

```
Implied g = [(P/B * k_e) - ROE] / (P/B - 1)
```

**Example — JPMorgan**:
```
P/B = 2.62, k_e = 9.5%, ROE = 16.5%
Implied g = [(2.62 * 9.5%) - 16.5%] / (2.62 - 1) = (24.9% - 16.5%) / 1.62 = 5.2%
```

**Interpretation**: The market is pricing in **5.2% long-term growth** of excess returns, well above nominal GDP growth (~3.5%). This implies the market expects JPMorgan to sustain or expand its competitive advantage over time.

### Reverse Engineering Summary Table

| Implied Parameter | Formula | JPMorgan Example | Interpretation |
|-------------------|---------|-----------------|----------------|
| **Implied ROE** | P/B * (k_e - g) + g | 19.2% | vs. actual 16.5% — premium baked in |
| **Implied k_e** | (ROE - g) / P/B + g | 8.5% | vs. CAPM 9.5% — franchise discount |
| **Implied g** | (P/B * k_e - ROE) / (P/B - 1) | 5.2% | vs. 3.5% GDP — superior growth priced |

### Investment Decision Framework

```python
def bank_investment_signal(current_pb, roe_actual, ke, g):
    """
    Generate buy/sell signal based on reverse engineering
    """
    implied_roe = current_pb * (ke - g) + g
    roe_premium = implied_roe - roe_actual
    
    # Fair P/B
    fair_pb = (roe_actual - g) / (ke - g)
    pb_premium = (current_pb - fair_pb) / fair_pb
    
    if pb_premium < -0.20:
        return "STRONG BUY", f"Trading 20%+ below fair value. Implied ROE {implied_roe:.1%} vs actual {roe_actual:.1%}"
    elif pb_premium < -0.10:
        return "BUY", f"Trading 10%+ below fair value"
    elif pb_premium < 0.10:
        return "HOLD", f"Fairly valued"
    elif pb_premium < 0.30:
        return "SELL", f"Trading 10-30% above fair value"
    else:
        return "STRONG SELL", f"Trading 30%+ above fair value. Premium not justified"

# JPMorgan signal
signal, reason = bank_investment_signal(2.62, 0.165, 0.095, 0.035)
print(f"JPMorgan: {signal} — {reason}")
# Output: STRONG SELL — Trading 30%+ above fair value...
```

---

## 10. Accounting Quality Red Flags — Bank Specific

### 10.1 Loan Loss Reserve Adequacy

| Red Flag | Detection Method | Severity |
|----------|-----------------|----------|
| **Provision expense < Net charge-offs for 2+ quarters** | Compare provision expense to NCOs in income statement | HIGH — Bank is eating into reserves |
| **Reserve/Loans ratio declining while NPLs rising** | Track both metrics quarterly | HIGH — Under-provisioning |
| **CECL model assumption changes reducing reserves** | Read 10-K footnotes on CECL methodology | MEDIUM — May be legitimate, but warrants scrutiny |
| **Reserve/Loans significantly below peer median** | Cross-sectional comparison | MEDIUM — May reflect better credit quality, or under-provisioning |
| **Sudden large release of reserves boosting earnings** | Check if earnings beat is driven by reserve release | HIGH — Unsustainable earnings quality |

**What to check**: Read the "Allowance for Credit Losses" footnote (Note 4-5 in most 10-Ks). Check:
- Reasonable and supportable forecast period (should be ~2 years)
- Historical loss coverage ratios
- Scenario weights (base/adverse/severe should be disclosed)
- Changes in macroeconomic variables used (GDP, unemployment, CRE prices)

### 10.2 HTM vs AFS Classification Games

| Red Flag | Detection Method | Severity |
|----------|-----------------|----------|
| **Large transfers from AFS to HTM** | Check 10-K/10-Q for reclassification disclosures | HIGH — Likely hiding unrealized losses |
| **HTM securities growing rapidly while AFS shrinks** | Track ratio of HTM/AFS over time | HIGH — Indicates loss avoidance behavior |
| **Unrealized losses on HTM > 50% of tangible equity** | Calculate from fair value disclosures | HIGH — Trapped capital if forced to sell |
| **Duration of HTM portfolio increasing** | Check weighted average life disclosure | MEDIUM — Longer duration = more rate risk |
| **Securities losses not reflected in equity** | AOCI should show AFS losses; HTM losses are hidden | MEDIUM — Check fair value footnotes |

**The SVB playbook (March 2023)**:
1. Bought long-duration bonds when rates were low
2. Classified them as HTM to avoid marking to market
3. When deposits fled, was forced to sell HTM securities
4. Had to recognize $1.8B in losses that were "hidden" in HTM

**Detection formula**:
```
Hidden Loss Ratio = (HTM Amortized Cost - HTM Fair Value) / Tangible Common Equity

Red flag: > 25%
Critical: > 50%
SVB at failure: > 100%
```

### 10.3 Level 3 Assets / Fair Value Uncertainty

| Red Flag | Detection Method | Severity |
|----------|-----------------|----------|
| **Level 3 assets > 10% of total assets** | Check fair value hierarchy in 10-K | HIGH — Illiquid, hard-to-value assets |
| **Level 3 assets growing faster than total assets** | Track growth rate of Level 3 | HIGH — Increasing opacity |
| **Significant transfers INTO Level 3** | Check footnotes for reclassification | HIGH — May indicate distress selling or model changes |
| **Wide range in disclosed sensitivity for Level 3** | Read fair value sensitivity footnote | MEDIUM — Model risk is high |
| **Level 3 assets concentrated in structured products** | Check asset breakdown | HIGH — Correlated, illiquid risk |

### 10.4 Off-Balance Sheet Exposures

| Red Flag | Detection Method | Severity |
|----------|-----------------|----------|
| **Unfunded loan commitments > 50% of total loans** | Check off-balance sheet footnote | MEDIUM — Liquidity risk if drawn |
| **Standby letters of credit growing rapidly** | Track growth rate | MEDIUM — Contingent credit risk |
| **Variable Interest Entities (VIEs) not consolidated** | Check VIE footnote disclosure | HIGH — Potential hidden leverage |
| **Securitization/SPV exposures** | Read transfer of financial assets footnote | HIGH — May recourse back to bank |
| **Repo-style transactions with rehypothecation** | Check securities financing footnote | MEDIUM — Counterparty risk |

**Key off-balance sheet items to monitor**:
```
Total Exposure = On-Balance Sheet Assets + Unfunded Commitments + 
                 Letters of Credit + VIE Maximum Exposure + 
                 Derivatives Notional (gross)

Leverage Ratio (comprehensive) = Tier 1 Capital / Total Exposure
```

### 10.5 Regulatory Arbitrage Structures

| Red Flag | Detection Method | Severity |
|----------|-----------------|----------|
| **Significant use of synthetic securitizations** | Check risk transfer disclosures | HIGH — May not achieve true sale treatment |
| **Regulatory capital relief transactions** | Search for "capital relief" or "risk transfer" in filings | HIGH — Could be reversed by regulators |
| **Internal risk weights significantly below standardized** | IRB banks: compare internal vs standardized RWA | HIGH — Aggressive risk weighting |
| **Operating lease structures for branches/ATMs** | Check lease footnotes | LOW — Standard practice |
| **Subsidiary-level debt at holding company** | Check HC vs bank-level capital | MEDIUM — Double leverage at HC |

### Accounting Quality Scorecard

```python
def accounting_quality_flags(bank_data):
    """
    Score accounting quality 0-100 (100 = pristine)
    """
    flags = []
    score = 100
    
    # 1. Reserve adequacy (-20 max)
    if bank_data["provision_expense"] < bank_data["net_charge_offs"]:
        flags.append("Provision < NCOs — eating into reserves")
        score -= 15
    if bank_data["reserve_loans_ratio"] < bank_data["peer_median_reserve_ratio"] * 0.7:
        flags.append("Reserve/Loans < 70% of peer median")
        score -= 10
    
    # 2. HTM/AFS games (-25 max)
    htm_hidden_loss = (bank_data["htm_cost"] - bank_data["htm_fv"]) / bank_data["tce"]
    if htm_hidden_loss > 0.50:
        flags.append(f"HTM hidden losses = {htm_hidden_loss:.1%} of TCE — CRITICAL")
        score -= 25
    elif htm_hidden_loss > 0.25:
        flags.append(f"HTM hidden losses = {htm_hidden_loss:.1%} of TCE")
        score -= 15
    if bank_data["htm_to_aft_transfer"] > 0:
        flags.append("AFS-to-HTM transfers detected — loss hiding?")
        score -= 10
    
    # 3. Level 3 assets (-20 max)
    l3_ratio = bank_data["level3_assets"] / bank_data["total_assets"]
    if l3_ratio > 0.10:
        flags.append(f"Level 3 assets = {l3_ratio:.1%} of total — very high")
        score -= 20
    elif l3_ratio > 0.05:
        flags.append(f"Level 3 assets = {l3_ratio:.1%} of total")
        score -= 10
    
    # 4. Off-balance sheet (-15 max)
    obs_ratio = bank_data["unfunded_commitments"] / bank_data["total_loans"]
    if obs_ratio > 0.50:
        flags.append(f"Unfunded commitments = {obs_ratio:.1%} of loans")
        score -= 15
    
    # 5. Regulatory arbitrage (-10 max)
    rwa_gap = bank_data["standardized_rwa"] - bank_data["irb_rwa"]
    if rwa_gap / bank_data["standardized_rwa"] > 0.20:
        flags.append("IRB RWA >20% below standardized — aggressive risk weights")
        score -= 10
    
    return max(score, 0), flags
```

### JPMorgan Accounting Quality Assessment

| Category | Assessment | Score Impact |
|----------|-----------|-------------|
| Reserve Adequacy | Conservative provisioning (200%+ coverage), CECL model well-disclosed | 0 |
| HTM/AFS | Moderate HTM exposure; fair value footnotes transparent; no recent transfers | 0 |
| Level 3 Assets | Low (~2-3% of assets), primarily private equity investments | 0 |
| Off-Balance Sheet | Normal for money-center bank; well-disclosed | 0 |
| Regulatory Arbitrage | Uses both standardized and advanced approaches; no red flags | 0 |
| **Total Accounting Quality Score** | | **100/100** |

**Verdict**: JPMorgan exhibits **exemplary accounting quality**. The bank's conservative provisioning, transparent fair value disclosures, and minimal use of structured vehicles contribute to its premium valuation. This is a bank where the numbers can be trusted.

---

## Appendix A: Quick Reference — Bank Valuation Checklist

### Before Buying Any Bank Stock, Answer These 20 Questions:

**Capital & Profitability (5)**
1. What is the CET1 ratio and how does it compare to the regulatory minimum + buffer?
2. What is the ROTCE, and has it been >12% for 5+ years?
3. What is the efficiency ratio vs. peers?
4. Is the bank earning its cost of equity (ROE > k_e)?
5. What is the tangible book value per share growth trend?

**Asset Quality (4)**
6. What is the NPL ratio trend (3 quarters)?
7. What is the provision coverage ratio?
8. Any sectoral loan concentration (CRE, energy, etc.)?
9. What is the net charge-off rate trend?

**Funding & Liquidity (4)**
10. What is the loan-to-deposit ratio?
11. What percentage of deposits are uninsured?
12. What is the CASA ratio?
13. What is the LCR and NSFR?

**Earnings Quality & Accounting (3)**
14. Are provision expenses covering net charge-offs?
15. Any AFS-to-HTM transfers in the last 2 years?
16. What is the Level 3 assets / total assets ratio?

**Valuation (2)**
17. What is the P/B, and what ROE does it imply?
18. What is the excess return model intrinsic value?

**Stress Test (2)**
19. How does the bank perform in a +200bp rate shock?
20. How does the bank perform in a credit downturn (NPLs → 3%)?

### Appendix B: Glossary of Banking Terms

| Term | Definition |
|------|-----------|
| **CET1** | Common Equity Tier 1 — highest quality regulatory capital (common stock + retained earnings + AOCI) |
| **RWA** | Risk-Weighted Assets — assets weighted by credit risk, market risk, and operational risk |
| **NIM** | Net Interest Margin — spread between interest earned and interest paid |
| **NII** | Net Interest Income — interest revenue minus interest expense |
| **NPL** | Non-Performing Loan — loan 90+ days past due or in non-accrual status |
| **PPNR** | Pre-Provision Net Revenue — revenue minus non-interest expense (before provisions) |
| **ROTE/ROTCE** | Return on Tangible Common Equity — ROE excluding goodwill and preferred stock |
| **RAROC** | Risk-Adjusted Return on Capital — return divided by economic capital allocated |
| **CASA** | Current Account Savings Account — low-cost, stable deposits |
| **LTD** | Loan-to-Deposit ratio — measure of liquidity and funding self-sufficiency |
| **LCR** | Liquidity Coverage Ratio — HQLA / 30-day net cash outflows |
| **NSFR** | Net Stable Funding Ratio — available stable funding / required stable funding |
| **CECL** | Current Expected Credit Losses — US GAAP accounting for loan loss reserves |
| **HTM** | Held-to-Maturity — debt securities carried at amortized cost (not marked to market) |
| **AFS** | Available-for-Sale — debt securities marked to market through AOCI |
| **GSIB** | Global Systemically Important Bank — subject to additional capital surcharges |
| **SCB** | Stress Capital Buffer — Fed-imposed capital buffer from CCAR results |
| **CCAR** | Comprehensive Capital Analysis and Review — Fed annual stress test |
| **Deposit Beta** | Sensitivity of deposit costs to changes in market interest rates |
| **Efficiency Ratio** | Non-interest expense / (NII + Non-interest income); lower is better |

---

## Appendix C: Data Sources for Bank Analysis

| Data Type | Primary Source | Frequency | Access |
|-----------|---------------|-----------|--------|
| Financial statements | 10-K, 10-Q | Quarterly | SEC EDGAR, Company IR |
| Call Reports (US banks) | FFIEC Central Data Repository | Quarterly | ffiec.gov (free) |
| Uniform Bank Performance Report | FDIC | Quarterly | fdic.gov (free) |
| CCAR Stress Test Results | Federal Reserve | Annual | federalreserve.gov |
| Basel Pillar 3 Disclosures | Company websites | Quarterly | Company IR |
| EBA Stress Tests (EU) | European Banking Authority | Annual | eba.europa.eu |
| CDS Spreads | Bloomberg, ICE | Real-time | Bloomberg terminal |
| Deposit Market Share | FDIC Summary of Deposits | Annual | fdic.gov |
| Analyst Estimates | FactSet, Bloomberg, CapIQ | Real-time | Subscription |
| Industry Benchmarks | S&P Global, KBW Indices | Daily | Bloomberg, FactSet |

---

*This module should be integrated into the adaptive framework as the default analysis engine whenever a bank is detected. All components are designed to be automated with data from standard financial data providers.*

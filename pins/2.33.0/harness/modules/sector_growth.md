# Growth Companies (Negative FCF) — Adaptive Analysis Framework

> **Module Purpose**: Replace standard FCF-based DCF, ROIC, and P/E-based analysis for high-growth, pre-profitability companies with stage-appropriate valuation, unit economics, and path-to-profitability modeling.
> **Target Sectors**: SaaS, cloud infrastructure, pre-revenue/early-revenue biotech, growth-stage consumer tech, late-stage private companies nearing IPO.

---

## 1. SECTOR DETECTION RULES

Orchestrator sets `primary_sector` via `RESEARCH_AGENTS.md` §5. This section is **signals/sub-type after identity**, not an auto-classifier.

### 1.1 Diagnostic scoring matrix (signals only)

Signals if §5 already set `primary_sector=growth` or `is_also_growth` (do **not** set `primary_sector` from this matrix). A company **may** show 3 or more of the following:

| # | Criterion | Threshold | Weight | Detection Method |
|---|-----------|-----------|--------|------------------|
| 1 | Revenue Growth (YoY) | > 20% for 2+ consecutive years | High | Income statement |
| 2 | FCF Margin | Negative OR < 5% | Critical | Cash flow statement |
| 3 | R&D / Revenue | > 15% (tech) OR > 30% (biotech) | High | Income statement |
| 4 | SBC / Revenue | > 5% (flag) OR > 15% (critical) | High | Cash flow + footnotes |
| 5 | Gross Margin | > 60% (SaaS/digital) or < 40% (consumer/hardware) | Medium | Income statement |
| 6 | Sector Classification | SaaS, cloud, biotech, fintech, platform tech | High | GICS / company description |
| 7 | Operating Margin | Negative OR improving from deep negative | Medium | Income statement |
| 8 | Cash Burn | Operating cash flow negative with declining cash balance | Critical | Cash flow statement |
| 9 | ARR/Recurring Revenue | > 50% of total revenue (SaaS flag) | Medium | Company disclosures |
| 10 | Stage of Maturity | Pre-revenue, early revenue, or scaling | High | Revenue size + age |

**How to read the score (after §5 identity, not a classifier):**
- **Score ≥ 7 points (out of 10)**: signals consistent with a full growth-company framework **if** §5 already chose growth as primary
- **Score 4–6**: signals consistent with hybrid (standard + growth overlay) — still does not flip `primary_sector`
- **Score ≤ 3**: signals consistent with standard framework and at most a light overlay

### 1.2 Maturity Stage Classification

| Stage | Revenue | Growth Rate | FCF Margin | Primary Valuation | Key Metrics |
|-------|---------|-------------|------------|-------------------|-------------|
| **Pre-revenue** | $0 | N/A | Deeply negative | Milestone / unit demand (TAM $ is a check), VC comps | units, SAM, pipeline, management |
| **Early Revenue** | $1–50M | 50–200% | Deeply negative | EV/Revenue, unit economics | ARR growth, CAC, LTV, NRR |
| **Scaling** | $50–500M | 30–80% | Negative to -20% | Path-to-profitability DCF, EV/Revenue | Rule of 40, operating leverage, burn multiple |
| **Approaching Profitability** | $200M–2B | 20–40% | -10% to +5% | Extended DCF, EV/Revenue, EV/EBITDA | FCF inflection, margin expansion, SBC |
| **Profitable Growth** | $500M+ | 15–30% | Positive | Standard DCF + growth premium | ROIC, FCF yield, NRR, reinvestment rate |

### 1.3 Sector-Specific Detection

**SaaS/Cloud Software:**
- Recurring revenue > 70%
- Gross margin > 65%
- R&D > 15% of revenue
- NRR disclosed
- SBC typically 15–25% of revenue

**Biotech/Pharma (Development Stage):**
- No product revenue (pre-commercial)
- R&D > 80% of operating expenses
- Milestone-dependent valuation (FDA approvals)
- Cash runway is paramount
- Binary outcomes (approval = massive value, failure = near-zero)

**Growth Consumer Tech:**
- High revenue growth (30–100%+)
- Heavy marketing spend (CAC focus)
- Unit economics critical (LTV/CAC)
- Network effects potential
- Gross margin varies widely (marketplace 20–40%, DTC brand 50–70%)

**Fintech:**
- Revenue from transaction fees, subscriptions, or lending spreads
- Take rate analysis critical
- Regulatory capital requirements
- Gross margin often 60–80% for software-like fintech

---

## 2. VALUATION MODELS — REPLACEMENTS FOR FCF-DCF

### Model A: Extended DCF (Path to Profitability)

**Why standard DCF fails**: Negative FCF means the "standard" FCF forecast is nonsensical — you cannot discount negative cash flows perpetually. The value of a growth company comes from **future optionality**: the ability to turn growth into profit through operating leverage.

**Step-by-Step Construction:**

#### Step 1: Revenue Forecast (Years 1–10)
- Advisory construction, not a paste path. Do **not** copy a canned decay curve (there is no 60→15 house path).
- Base growth on **unit demand × share × price** (sourced units, vintage). Dollar TAM is a **check**, not the path.
- Historical deceleration and cohort expansion may inform the unit path; they do not replace it.
- If invested capital is positive, `harness/RESEARCH_AGENTS.md` §10d applies (`applies:false` is banks/REITs/negative-IC pre-profit — not “we prefer ARR”).

#### Step 2: Gross Margin Expansion
- SaaS: starts at 60–70%, matures to 75–85%
- Model gradual improvement as scale economies kick in
- Formula: `Gross Profit = Revenue × Gross Margin%`

#### Step 3: Operating Leverage (The Critical Step)
- **Operating leverage** = % change in operating income / % change in revenue
- As revenue grows, fixed costs are spread over larger base
- Model OpEx as: `OpEx = Fixed Base + (Variable Rate × Revenue)`
- Key drivers:
  - **R&D**: Scales sub-linearly (0.8x revenue growth exponent)
  - **S&M**: Scales linearly or sub-linearly if efficiency improves
  - **G&A**: Highly sub-linear (0.5x revenue growth exponent)

#### Step 4: EBITDA and FCF Conversion
```
EBITDA = Gross Profit - OpEx (ex-D&A)
EBIT = EBITDA - D&A
FCF = EBIT × (1 - Tax Rate) + D&A - CapEx - Change in WC
```

#### Step 5: Breakeven Point
- Explicitly model the quarter/year when FCF turns positive
- This is a KEY valuation inflection point
- Before breakeven: fund via cash reserves or capital raises
- After breakeven: self-funding growth + cash accumulation

#### Step 6: Terminal Value
- **Only after profitability is achieved**
- Use perpetuity growth or exit multiple
- Terminal value applied at the year FCF is sustainably positive (typically Year 7–10)
- Growth rate in perpetuity: 3–4% (conservative)

#### Concrete Example — SaaS Company:

| Metric | Year 1 | Year 2 | Year 3 | Year 4 | Year 5 | Year 6 | Year 7 | Year 8 | Year 9 | Year 10 |
|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|---------|
| Revenue ($M) | 100 | 130 | 169 | 219 | 273 | 328 | 384 | 442 | 503 | 565 |
| Growth Rate | 30% | 30% | 30% | 30% | 25% | 20% | 17% | 15% | 14% | 12% |
| Gross Margin | 75% | 76% | 77% | 78% | 79% | 80% | 81% | 82% | 82% | 83% |
| R&D % | 25% | 23% | 21% | 20% | 19% | 18% | 17% | 16% | 16% | 15% |
| S&M % | 35% | 33% | 31% | 29% | 27% | 25% | 23% | 22% | 21% | 20% |
| G&A % | 15% | 13% | 12% | 11% | 10% | 9% | 9% | 8% | 8% | 8% |
| **FCF Margin** | **-10%** | **-6%** | **-2%** | **1%** | **4%** | **7%** | **10%** | **12%** | **14%** | **16%** |
| FCF ($M) | -10 | -8 | -3 | 2 | 11 | 23 | 38 | 53 | 70 | 90 |

**Breakeven**: Between Year 3 and Year 4 (FCF turns positive at ~$200M revenue scale)

**DCF Valuation**:
- Discount rate (WACC): 12% (high growth, high uncertainty)
- PV of Years 1–7 FCF: sum of discounted cash flows
- Terminal value at Year 7: FCF_Y7 × (1 + g) / (WACC - g) = $38M × 1.04 / (0.12 - 0.04) = $494M
- PV of Terminal Value: $494M / (1.12)^7 = $223M
- **Enterprise Value ≈ $250–350M** (depending on exact assumptions)
- **Implied EV/Revenue**: 2.5–3.5x on Year 1 revenue

---

### Model B: Revenue Multiple / Comparable Company Analysis

#### Selecting Peer Sets

Peer selection is CRITICAL and often done poorly. A 50% grower should not be compared to a 10% grower.

**Multi-dimensional peer matching:**
1. **Growth rate bucket** (±5 percentage points)
2. **Revenue scale** ($50–200M, $200M–1B, $1B+)
3. **Gross margin profile** (high GM >70% vs. low GM <50%)
4. **Business model** (SaaS, marketplace, hardware, hybrid)
5. **Rule of 40 band** (separate >40 from <20)

#### Growth-Adjusted Revenue Multiples (PEG-Style)

```
EV/Revenue/Growth = EV/Revenue ÷ Expected Revenue Growth %
```

| EV/Rev/Growth | Interpretation |
|---------------|----------------|
| < 0.3x | Potentially undervalued |
| 0.3–0.5x | Reasonable value |
| 0.5–0.8x | Growth premium priced in |
| > 0.8x | Expensive (or exceptional quality) |

Example: EV/Revenue of 12x on 40% growth = 0.3x (reasonable)
Example: EV/Revenue of 20x on 20% growth = 1.0x (expensive)

#### Rule of 40 ↔ Multiple Mapping

Based on historical public SaaS data (2020–2024):

| Rule of 40 Score | Median EV/Revenue | Range |
|-------------------|-------------------|-------|
| > 50 (Exceptional) | 15–25x | 10–35x |
| 40–50 (Strong) | 10–15x | 7–20x |
| 30–40 (Good) | 7–10x | 5–12x |
| 20–30 (Fair) | 5–7x | 3–9x |
| 10–20 (Weak) | 3–5x | 2–6x |
| < 10 (Poor) | 1–3x | 0.5–4x |

**Key insight**: Companies scoring >40 on the Rule of 40 command significant multiple premiums. A company with 50% growth and -5% FCF margin (Rule of 40 = 45) trades at a higher multiple than one with 20% growth and 20% FCF margin (Rule of 40 = 40), because growth is valued more highly than current profitability.

---

### Model C: Unit Economics-Based Valuation

This model values the company as a **customer acquisition machine**.

#### Core Formula:
```
Company Value = (Customer Count × LTV) - (Future Customer Acquisition Costs) + Net Cash
```

Or more practically for ongoing businesses:
```
Value = ARR × (LTV/CAC Ratio Multiple) × Gross Margin Adjustment
```

#### Key Unit Economics Metrics:

| Metric | Formula | Healthy Range | Red Flag |
|--------|---------|---------------|----------|
| **CAC** | Sales & Marketing / New Customers Acquired | Varies by industry | Rising 20%+ YoY |
| **LTV** | ARPU × Gross Margin × (1 / Monthly Churn Rate) | Depends on model | Declining trend |
| **LTV/CAC** | LTV ÷ CAC | > 3.0x | < 1.5x (unsustainable) |
| **CAC Payback** | CAC ÷ (ARPU × Gross Margin) | < 12 months | > 18 months |
| **Months to Recover CAC** | CAC ÷ Monthly Gross Margin per Customer | < 12 months | > 24 months |

#### Example:
- Customer Count: 10,000
- ARPU: $10,000/year
- Gross Margin: 75%
- Annual Churn: 10% (implied customer lifetime = 10 years)
- CAC: $25,000

```
LTV = $10,000 × 0.75 × 10 = $75,000
LTV/CAC = $75,000 / $25,000 = 3.0x (healthy)
CAC Payback = $25,000 / ($10,000 × 0.75) = 3.3 years (marginal — ideally < 2 years)
Total Customer Value = 10,000 × $75,000 = $750M
```

**Important**: This gives a "theoretical" value. Discount by 30–50% for:
- Execution risk
- Growth deceleration
- Competitive pressure
- Churn increase over time

---

### Model D: ARR Multiple (SaaS-Specific)

The most practical valuation method for SaaS companies.

#### Public SaaS Multiples by Growth Bucket (Historical Ranges)

| ARR Growth Rate | NRR > 120% | NRR 110–120% | NRR 100–110% | NRR < 100% |
|-----------------|------------|--------------|--------------|------------|
| **> 50%** | 15–25x | 12–18x | 8–12x | 4–8x |
| **40–50%** | 12–18x | 10–14x | 7–10x | 3–6x |
| **30–40%** | 10–14x | 8–11x | 5–8x | 2–5x |
| **20–30%** | 7–10x | 6–8x | 4–6x | 2–4x |
| **10–20%** | 5–7x | 4–6x | 3–5x | 1.5–3x |
| **< 10%** | 3–5x | 2–4x | 2–3x | 1–2x |

#### ARR Multiple Adjustment Factors:

| Factor | Premium/Discount | Condition |
|--------|-----------------|-----------|
| Gross Margin > 80% | +1–2x | High-margin business |
| Gross Margin < 60% | -2–3x | Services-heavy, low quality |
| Rule of 40 > 50 | +2–4x | Exceptional efficiency |
| Rule of 40 < 20 | -2–3x | Poor efficiency |
| Enterprise customers (>50K ACV) | +1–2x | Lower churn, higher LTV |
| SMB customers (<5K ACV) | -1–2x | Higher churn, lower LTV |
| Multi-product platform | +1–2x | Cross-sell opportunity |
| Single product | -0.5–1x | Limited expansion |
| Best-in-class NRR (>130%) | +2–3x | Exceptional retention |
| High churn (>15% annually) | -2–3x | Retention problem |

#### Example:
- ARR: $100M
- Growth: 30%
- NRR: 115%
- Gross Margin: 78%
- Rule of 40: 35 (30% growth + 5% FCF margin)
- Enterprise focus

Base multiple (30% growth, NRR 110–120%): **8–11x**
Gross margin adjustment (+1x): **9–12x**
Rule of 40 adjustment (neutral): no change
Enterprise focus (+1x): **10–13x**

**Valuation Range: $1.0B – $1.3B EV**

---

## 3. KEY OPERATING METRICS

### 3.1 Revenue Metrics

| Metric | Formula | Benchmark | Why It Matters |
|--------|---------|-----------|----------------|
| **ARR** | MRR × 12 | Primary metric for SaaS | The foundational value metric |
| **MRR** | Sum of all recurring monthly fees | Track net changes | Early indicator of ARR trends |
| **Revenue Growth (YoY)** | (Current Revenue / Prior Year Revenue) - 1 | > 30% (strong), > 20% (good) | Drives valuation multiple |
| **Revenue Growth (QoQ annualized)** | (Current Q / Prior Q)^4 - 1 | Watch for deceleration | Earlier signal than YoY |
| **Net Revenue Retention (NRR)** | (Beginning ARR + Expansion - Contraction - Churn) / Beginning ARR | > 120% (great), > 110% (good), < 100% (alarm) | Shows if existing customers grow or shrink |
| **Gross Revenue Retention (GRR)** | (Beginning ARR - Churn - Contraction) / Beginning ARr | > 90% (good), > 85% (acceptable) | True "stickiness" without expansion |
| **Expansion Rate** | Expansion ARR / Beginning ARR | > 20% | Cross-sell and upsell success |
| **New ARR** | ARR from new customers | Growing in absolute $ | Market penetration |
| **ARR per Customer (ARPU)** | Total ARR / Customer Count | Increasing over time | Price power and upsell |

**NRR > 100% means**: The company grows from existing customers even without adding new ones. This is the hallmark of great SaaS.

**NRR Decoding**:
- NRR 130%+: Best-in-class (Snowflake, Datadog, ServiceNow)
- NRR 120–130%: Excellent (most top-quartile SaaS)
- NRR 110–120%: Good (healthy expansion)
- NRR 100–110%: Fair (limited expansion)
- NRR < 100%: Alarm (churn exceeds expansion — unsustainable)

### 3.2 Unit Economics

| Metric | Formula | Benchmark | Interpretation |
|--------|---------|-----------|----------------|
| **CAC** | (Sales & Marketing Expense) / (New Customers Acquired) | Varies widely by industry | Cost to acquire one customer |
| **Blended CAC** | S&M / (New + Expansion customers) | Lower than new CAC | Includes upsell costs |
| **Paid CAC** | S&M (paid channels only) / Paid customers | Higher than blended CAC | True marketing efficiency |
| **LTV** | ARPU × Gross Margin × Customer Lifetime | Should be > 3× CAC | Total value of a customer |
| **LTV/CAC** | LTV ÷ CAC | > 3.0x (healthy), > 5.0x (great), < 1.5x (unsustainable) | Unit economics health |
| **CAC Payback Period** | CAC ÷ (ARPU × Gross Margin) | < 12 months (good), < 6 months (great), > 18 months (concerning) | Time to recover acquisition cost |
| **Months to Recover CAC** | CAC ÷ (ARPU × Gross Margin / 12) | Same as above | Monthly view of payback |
| **Magic Number** | Net New ARR × 4 / S&M Expense | > 1.0 (efficient), 0.75–1.0 (good), < 0.5 (inefficient) | S&M spend efficiency |
| **S&M Efficiency** | Gross New ARR / S&M Expense | > 1.0x | Revenue generated per $ of S&M |
| **Payback Period (Cash)** | CAC / Monthly Cash Flow per Customer | < 12 months ideal | Cash recovery speed |

**Magic Number Formula Detail**:
```
Magic Number = (Net New ARR in Quarter × 4) / S&M Spend in Prior Quarter
```
- Multiply by 4 to annualize the quarterly net new ARR
- Use prior quarter S&M because spend precedes results
- > 1.0: S&M is highly efficient — invest more
- 0.75–1.0: Efficient but not exceptional
- 0.5–0.75: Marginal — may not be worth scaling
- < 0.5: Inefficient — fix before spending more

### 3.3 Efficiency & Profitability Metrics

| Metric | Formula | Benchmark | Why It Matters |
|--------|---------|-----------|----------------|
| **Rule of 40** | Revenue Growth% + FCF Margin% (or EBITDA Margin%) | > 40% (strong), > 30% (good), < 20% (weak) | Balance of growth and profitability |
| **Burn Multiple** | Net Burn / Net New ARR | < 1.0x (excellent), < 1.5x (good), > 3.0x (alarming) | Capital efficiency of growth |
| **Gross Margin** | (Revenue - COGS) / Revenue | > 80% (great SaaS), > 70% (good SaaS), < 50% (concerning) | Software margin = scalability |
| **Operating Margin** | Operating Income / Revenue | Improving trajectory | Path to profitability |
| **FCF Margin** | FCF / Revenue | Negative (growth phase), > 10% (mature) | Cash generation ability |
| **EBITDA Margin** | EBITDA / Revenue | Trending positive | Pre-FCF profitability proxy |
| **R&D Efficiency** | Product Revenue / R&D Spend | > 5x (mature), > 3x (growth) | R&D ROI |
| **S&M as % of Revenue** | S&M / Revenue | Declining over time | Sales efficiency improvement |

**Burn Multiple Detail**:
```
Burn Multiple = (Cash Burn in Period) / (Net New ARR in Period)
```
- Measures how much cash is burned to create each $1 of new ARR
- < 1.0x: World-class efficiency (rare)
- 1.0–1.5x: Efficient growth
- 1.5–2.0x: Acceptable for high growth
- 2.0–3.0x: Concerning — too much burn for growth
- > 3.0x: Alarm — unsustainable unless massive cash reserves

**Example**: Company burns $40M in a year to add $20M in net new ARR → Burn Multiple = 2.0x. Acceptable if growing 50%+ with strong unit economics; concerning if growing 20%.

### 3.4 SBC / Dilution Metrics (CRITICAL for Growth Companies)

| Metric | Formula | Benchmark | Interpretation |
|--------|---------|-----------|----------------|
| **SBC / Revenue** | Stock-Based Compensation / Revenue | 10–15% (typical), > 25% (excessive), < 5% (rare for growth) | SBC burden on shareholders |
| **SBC / Operating Expenses** | SBC / Total OpEx | 20–40% (typical growth) | How "real" are profits? |
| **Share Count Growth (Dilution)** | (Ending Shares / Beginning Shares) - 1 | < 3% (great), 3–5% (acceptable), > 7% (excessive) | Annual dilution rate |
| **SBC-Adjusted EPS** | (Net Income - SBC) / Diluted Shares | Always lower than reported EPS | True earnings power |
| **Fully Diluted Shares** | Basic Shares + RSUs + Options + ESPP | Use for valuation | True share count |
| **SBC Growth Rate** | YoY change in SBC expense | Should < Revenue growth rate | If SBC growing faster than revenue = alarm |
| **Unrecognized SBC** | Future SBC expense from unvested awards | Disclosed in footnotes | Future dilution pipeline |
| **Free Cash Flow ex-SBC** | FCF - SBC | Often negative for growth cos | True cash generation |

**Why SBC matters MORE for growth companies**:
1. Growth companies use SBC as primary compensation (conserves cash)
2. SBC often equals 20–50% of "adjusted" operating income
3. Share count grows 3–8% annually — massive long-term dilution
4. If SBC is cut, key employees leave; if maintained, shareholders are diluted
5. Many "adjusted EBITDA" metrics exclude SBC — misleading

**Red Flag**: SBC growing faster than revenue means the company is buying performance with ever-more-dilutive stock.


---

## 4. KEY RISK FACTORS (GROWTH-SPECIFIC)

Each risk includes quantitative thresholds for early warning detection.

### 4.1 Funding Runway / Cash Burn

| Metric | Formula | Green | Yellow | Red |
|--------|---------|-------|--------|-----|
| **Cash Runway** | Cash & Equivalents / Monthly Net Burn | > 24 months | 12–24 months | < 12 months |
| **Cash Runway (conservative)** | (Cash - Minimum Operating Cash) / Monthly Burn | > 18 months | 9–18 months | < 9 months |

**Analysis**: 
- With < 12 months of cash, the company MUST raise capital or reach profitability
- In tight funding environments ("funding winter"), even strong companies struggle to raise
- Track: operating cash burn, financing cash inflows, cash balance trend
- **Critical question**: Can this company reach profitability before running out of cash?

### 4.2 Growth Deceleration

| Pattern | Interpretation | Action |
|---------|----------------|--------|
| Growth declines 5–10 ppts YoY | Normal maturation | Monitor |
| Growth declines > 20 ppts YoY | Concerning — investigate cause | Deep dive |
| Growth < 20% AND still burning cash | Dangerous — may never reach profitability | Reassess thesis |
| Sequential QoQ decline (non-seasonal) | Alarm — demand problem | Immediate review |
| New ARR growth declining while S&M increasing | Efficiency deterioration | Model impact |

**Law of Large Numbers**: A $50M company growing 100% adds $50M. A $500M company growing 30% adds $150M. Absolute dollar growth matters more than percentage at scale.

### 4.3 Unit Economics Deterioration

| Metric | Deterioration Threshold | Implication |
|--------|------------------------|-------------|
| LTV/CAC declining > 20% YoY | Pricing power or retention issue | Unsustainable growth |
| CAC increasing > 25% YoY | Market saturation or competition | Margins compressed |
| CAC Payback Period > 18 months | Cash flow strain | May need more capital |
| Magic Number declining below 0.5 | S&M efficiency collapse | Stop spending, fix product |
| Churn increasing > 3 ppts | Product-market fit erosion | NRR will decline |

### 4.4 Churn Spike / NRR Decline

| NRR Level | Interpretation | Valuation Impact |
|-----------|----------------|------------------|
| > 130% | Exceptional | Premium multiple |
| 120–130% | Excellent | Above-average multiple |
| 110–120% | Good | Standard multiple |
| 100–110% | Fair | Below-average multiple |
| 95–100% | Concerning | Significant discount |
| < 95% | Alarm | Deep discount or avoid |

**Root causes of NRR decline**:
- Downmarket move (selling to smaller, higher-churn customers)
- Competitive pressure (feature parity, pricing pressure)
- Product maturity (less expansion opportunity)
- Economic headwinds (customers downsizing)

### 4.5 SBC / Dilution Risk

| Indicator | Threshold | Consequence |
|-----------|-----------|-------------|
| SBC/Revenue > 25% | Excessive | Severe EPS dilution |
| Share count growth > 7%/year | Heavy dilution | 50%+ dilution over 7 years |
| SBC growing faster than revenue | Accelerating dilution | "Hidden" expense explosion |
| SBC cuts to hit profitability targets | Talent exodus | Execution risk |
| SBC as % of FCF > 100% | FCF is not real | Company not truly cash-generative |

**The SBC Paradox**: 
- Cut SBC → Key employees leave → Product/execution suffers → Stock drops
- Maintain SBC → Perpetual dilution → EPS never grows → Stock drops
- The only escape: grow revenue fast enough that per-share value increases despite dilution

### 4.6 Competitive Moat Erosion

| Signal | Detection Method | Severity |
|--------|-----------------|----------|
| Competitor achieves feature parity | Product reviews, G2/Forrester | Medium |
| Price war initiated | Pricing page changes, sales commentary | High |
| Win rate declining > 10 ppts | Management commentary, sales data | High |
| Competitor NRR higher | Peer comparison | Medium |
| Switching costs declining | Customer interviews, churn analysis | High |

**Moat Types in SaaS (and their durability)**:
1. **High switching costs** (ERP, CRM): Strong — hard to rip and replace
2. **Data network effects** (AI/ML platforms): Strong — more data = better product
3. **Two-sided network effects** (marketplaces): Strong — liquidity begets liquidity
4. **Platform ecosystems** (app marketplaces): Medium-strong — developer lock-in
5. **Brand/viral effects**: Weak alone — needs to be paired with switching costs

### 4.7 Market Timing / Financing Risk

| Scenario | Impact on Growth Companies |
|----------|---------------------------|
| IPO window closes | Can't go public, private market repricing |
| Follow-on financing unavailable | Must reach profitability or sell/merge |
| Interest rates rise | Higher discount rate = lower valuations |
| VC funding freezes | Early-stage ecosystem contraction |
| Public market tech selloff | Comps drop → private valuation repricing |

### 4.8 Regulatory Risk

| Domain | Risk | Affected Companies |
|--------|------|-------------------|
| **Data privacy** (GDPR, CCPA) | Compliance costs, fines | All SaaS with customer data |
| **AI regulation** | Usage restrictions, liability | AI/ML companies |
| **Antitrust** | Breakup, M&A restrictions | Platform companies |
| **Healthcare regulation** | Approval delays, pricing | Biotech, healthtech |
| **Financial regulation** | Capital requirements | Fintech, neobanks |
| **Cross-border data** | Localization requirements | Global SaaS |

---

## 5. QUALITY INDICATORS

### 5.1 10 Quality Indicators — SaaS/Tech Growth Companies

| # | Indicator | Formula | "Good" Threshold | "Great" Threshold |
|---|-----------|---------|-----------------|-------------------|
| 1 | **NRR** | (Beg ARR + Expansion - Churn) / Beg ARR | > 115% | > 125% |
| 2 | **Gross Margin** | Gross Profit / Revenue | > 75% | > 82% |
| 3 | **Rule of 40** | Growth% + FCF Margin% | > 35% | > 50% |
| 4 | **LTV/CAC** | LTV / CAC | > 3.0x | > 5.0x |
| 5 | **CAC Payback** | CAC / (ARPU × GM) | < 18 months | < 12 months |
| 6 | **Magic Number** | (Net New ARR × 4) / S&M | > 0.75 | > 1.2 |
| 7 | **Gross Retention** | (Beg ARR - Churn) / Beg ARR | > 88% | > 93% |
| 8 | **SBC/Revenue** | SBC Expense / Revenue | < 15% | < 10% |
| 9 | **ARR Growth Consistency** | Std dev of quarterly growth | Low variance | Very low variance |
| 10 | **Operating Leverage** | % ΔOpEx / % ΔRevenue | < 0.8x | < 0.6x |

**Scoring**: Each indicator scored 0–3 (Poor/Fair/Good/Great). Total score:
- **25–30**: Exceptional quality — premium valuation warranted
- **18–24**: Good quality — standard or slight premium
- **12–17**: Mixed quality — discount warranted
- **< 12**: Poor quality — deep discount or avoid

### 5.2 10 Quality Indicators — Biotech/Pre-Revenue Companies

| # | Indicator | "Good" | "Great" | Why It Matters |
|---|-----------|--------|---------|----------------|
| 1 | **Cash runway** | > 24 months | > 36 months | Time to reach next milestone |
| 2 | **Management track record** | Prior FDA approvals | Multiple prior successes | Execution credibility |
| 3 | **Pipeline depth** | 2+ programs | 3+ programs | Diversification reduces binary risk |
| 4 | **Addressable market** | > $1B | > $5B | Commercial potential |
| 5 | **Clinical trial design** | Well-powered, clear endpoints | Adaptive designs | Probability of success |
| 6 | **Partnership quality** | Big pharma partnerships | Multiple partnerships | Validation |
| 7 | **Intellectual property** | Strong patent estate | 10+ years of exclusivity | Competitive protection |
| 8 | **Manufacturing readiness** | CMO relationships | Internal capacity | Commercial execution |
| 9 | **Regulatory pathway clarity** | Clear FDA path | Breakthrough therapy designation | Speed to market |
| 10 | **Cash efficiency** | <$50M per program | <$30M per program | Capital efficiency |

### 5.3 10 Quality Indicators — Growth-Stage Consumer Companies

| # | Indicator | Formula | "Good" | "Great" |
|---|-----------|---------|--------|---------|
| 1 | **LTV/CAC** | LTV / CAC | > 3.0x | > 5.0x |
| 2 | **CAC Payback** | CAC / Monthly Contribution | < 12 months | < 6 months |
| 3 | **Monthly/DAU Retention** | Cohort retention at Day 30/90/365 | > 40% at D365 | > 60% at D365 |
| 4 | **Viral coefficient** | Invites × Conversion rate | > 0.5 | > 1.0 |
| 5 | **Revenue per user** | Revenue / MAU or WAU | Growing | Growing 20%+ YoY |
| 6 | **Gross margin** | Gross Profit / Revenue | > 50% | > 70% |
| 7 | **Network effects evidence** | Value increases with users | Demonstrable | Strong |
| 8 | **Engagement depth** | Sessions/user/day, time in app | Increasing | Strong + increasing |
| 9 | **Organic traffic %** | Organic / Total traffic | > 40% | > 60% |
| 10 | **Take rate (marketplaces)** | Revenue / GMV | Stable or growing | Growing |

---

## 6. STRESS TEST SCENARIOS

### Scenario 1: Funding Winter (Capital Markets Freeze)

**Assumption**: Cannot raise capital for 24+ months. Must reach profitability or fail.

**Financial Impact Model**:

| Metric | Base Case | Stress Case | Impact |
|--------|-----------|-------------|--------|
| S&M Spend | $50M | Cut to $25M (-50%) | Growth slows dramatically |
| R&D Spend | $35M | Cut to $28M (-20%) | Innovation slows |
| Headcount Growth | +30% | Flat to -10% | Execution risk |
| Revenue Growth | 30% | Drops to 15% (no S&M fuel) | Valuation cut 40–60% |
| Cash Burn | $20M/qtr | $5M/qtr (survival mode) | Runway extended |
| Time to Profitability | Year 4 | Year 2.5 (forced) | But smaller company |
| EV/Revenue Multiple | 8x | 3–4x (re-rated) | Multiple compression |
| **Implied Valuation** | $800M | $200–300M | **65–75% decline** |

**Key Question**: Can the company reach cash-flow breakeven with 50% less S&M spend?

### Scenario 2: Growth Deceleration (Revenue Growth Halves)

**Assumption**: Revenue growth drops from 30% to 15% due to market saturation, competition, or economic downturn.

**Operating Leverage Impact**:

| Metric | Base (30% growth) | Stress (15% growth) | Why |
|--------|-------------------|---------------------|-----|
| Revenue | $130M (Y2) | $115M (Y2) | Lower growth |
| Gross Margin | 76% | 76% | Unaffected |
| R&D % of Revenue | 23% | 26% | Fixed costs don't scale down |
| S&M % of Revenue | 33% | 38% | S&M less efficient |
| G&A % of Revenue | 13% | 15% | Fixed overhead |
| FCF Margin | -6% | -15% | Negative operating leverage |
| FCF ($M) | -$8M | -$17M | Cash burn accelerates |
| Rule of 40 | 24 (30 + (-6)) | 5 (15 + (-10)) | Falls below threshold |
| **EV/Revenue Multiple** | 8x | 4x | Multiple compression |
| **Valuation** | $1.04B | $460M | **55% decline** |

**Critical Insight**: Operating leverage works BOTH ways. When growth slows, fixed costs crush margins. This is why growth companies are punished so severely for deceleration.

### Scenario 3: Churn Shock (NRR Drops Below 100%)

**Assumption**: Competitor launches superior product. Gross retention drops from 90% to 80%. Expansion slows. NRR falls from 115% to 95%.

**Impact Model**:

| Metric | Base (NRR 115%) | Stress (NRR 95%) | Impact |
|--------|----------------|------------------|--------|
| Beginning ARR | $100M | $100M | Same |
| Churned ARR | -$10M | -$20M | 2x churn |
| Expansion ARR | +$25M | +$15M | Less upsell |
| **Net New ARR from existing** | **+$15M** | **-$5M** | **$20M swing** |
| New Customer ARR | +$30M | +$25M | Harder to sell |
| **Total Ending ARR** | **$145M** | **$120M** | **17% lower** |
| Effective Growth Rate | 45% | 20% | Massive deceleration |
| LTV | $75K | $40K | Churn destroys LTV |
| LTV/CAC | 3.0x | 1.6x | Near unsustainable |
| **Valuation at 8x ARR** | **$1.16B** | **$480M** | **~60% decline** |

**Key Lesson**: NRR is the most powerful lever in SaaS valuation. A 20-point NRR drop can destroy 50%+ of enterprise value because it compounds over time.

### Scenario 4: SBC Cliff (Must Cut SBC 50%)

**Assumption**: Investor pressure forces 50% SBC reduction. Key employees depart. Execution suffers.

**Timeline and Impact**:

| Quarter | Action | Financial Impact | Operational Impact |
|---------|--------|------------------|-------------------|
| Q1 | Cut SBC 50% | "Profitability" improves | Key engineers leave |
| Q2 | More departures | SBC expense lower | Product releases delayed |
| Q3 | Replacement hiring | Cash compensation rises | New hires less effective |
| Q4 | Execution gap visible | Revenue growth slows 5–10 ppts | Competitive losses |
| Year 2 | Full impact | Growth 10–15 ppts below plan | NRR starts declining |

**Valuation Impact**:

| Scenario | SBC/Revenue | Growth | NRR | Valuation |
|----------|-------------|--------|-----|-----------|
| Base Case | 18% | 30% | 115% | $1.0B |
| SBC Cut (no execution loss) | 9% | 30% | 115% | $1.1B (slightly higher) |
| SBC Cut (with execution loss) | 9% | 20% | 108% | $500M (50% decline) |

**The Paradox**: Cutting SBC improves short-term "profitability" but often destroys long-term value if key talent departs. The market prices in execution risk.


---

## 7. PEER COMPARISON METHODOLOGY

### 7.1 Multi-Dimensional Peer Grouping

Comparing a 30% grower to a 10% grower is meaningless. Use these dimensions:

**Dimension 1: Growth Rate Bucket**

| Bucket | Revenue Growth | Peer Group |
|--------|---------------|------------|
| Hyper-growth | > 50% | High-growth SaaS, early-stage public |
| Strong growth | 30–50% | Mid-stage SaaS, successful scale-ups |
| Moderate growth | 15–30% | Mature SaaS, transitioning to profitability |
| Slow growth | 5–15% | Profitable SaaS, value-oriented |
| No/negative growth | < 5% | Turnaround, challenged, or mature |

**Dimension 2: ARR Scale**

| Scale | ARR Range | Characteristics |
|-------|-----------|----------------|
| Micro-SaaS | <$10M | Very high growth, very high risk |
| Emerging | $10–50M | High growth, establishing product-market fit |
| Growth | $50–200M | Scaling go-to-market, path to profitability |
| Scale | $200M–$1B | Operating leverage emerging, market leadership |
| Large | $1B+ | Profitability focus, mature metrics |

**Dimension 3: Gross Margin Profile**

| Profile | Gross Margin | Business Model |
|---------|-------------|----------------|
| Pure software | > 80% | SaaS, cloud infrastructure |
| Software + services | 70–80% | SaaS with onboarding/support |
| Hybrid | 50–70% | Software + hardware, marketplace |
| Services-heavy | 30–50% | Consulting, implementation |
| Low margin | < 30% | Hardware, logistics, commodity |

**Dimension 4: Rule of 40 Bands**

| Band | Score | Profile |
|------|-------|---------|
| Exceptional | > 50 | Rare — growth + profitability excellence |
| Strong | 40–50 | Elite SaaS companies |
| Good | 30–40 | Solid operators |
| Fair | 20–30 | Work in progress |
| Weak | 10–20 | Challenged |
| Poor | < 10 | Value destruction likely |

### 7.2 Practical Peer Comparison Framework

```
Step 1: Identify target company metrics
    - Growth rate: ___%
    - ARR scale: $___M
    - Gross margin: ___%
    - Rule of 40: ___
    - NRR: ___%

Step 2: Filter universe by closest matches
    - Growth ± 10 percentage points
    - ARR within 2× (up or down)
    - Gross margin ± 10 percentage points
    - Business model match

Step 3: Calculate median and range
    - Median EV/Revenue of peer set
    - 25th and 75th percentile
    - Adjust for company-specific factors

Step 4: Apply premium/discount
    - NRR premium/discount: ±1–3x per 10 NRR points
    - Margin premium: ±0.5–1x per 5 GM points
    - Moat premium: +1–3x for clear moats
    - Execution discount: -1–2x for management concerns
```

### 7.3 Example Peer Set Construction

**Target Company**: Growth SaaS, $150M ARR, 35% growth, 78% GM, NRR 118%, Rule of 40 = 40

| Peer | ARR ($M) | Growth | GM | NRR | Rule of 40 | EV/Rev |
|------|----------|--------|-----|-----|------------|--------|
| Peer A | $120M | 38% | 80% | 122% | 48 | 14x |
| Peer B | $180M | 32% | 76% | 115% | 38 | 10x |
| Peer C | $200M | 40% | 82% | 125% | 52 | 16x |
| Peer D | $100M | 28% | 74% | 110% | 33 | 7x |
| Peer E | $160M | 35% | 79% | 120% | 42 | 12x |
| **Median** | **$160M** | **35%** | **79%** | **118%** | **40** | **12x** |
| **Range** | | 28–40% | 74–82% | 110–125% | 33–52 | 7–16x |

**Valuation for target**: 10–14x revenue (adjusted for specific strengths/weaknesses)
At $150M ARR: **$1.5B – $2.1B EV**

---

## 8. REPLACEMENT TABLE: STANDARD vs. GROWTH FRAMEWORK

| Standard Component | Growth Company Replacement | Rationale |
|-------------------|---------------------------|-----------|
| **DCF (FCF-based)** | Extended DCF (Path to Profitability) + ARR Multiple | FCF is negative for years; value comes from future profitability. Model the journey to positive FCF explicitly. Complement with ARR multiple for sanity check. |
| **ROIC** | Revenue growth efficiency + Unit economics (LTV/CAC) | Negative invested capital and negative earnings make ROIC meaningless. Replace with: How efficiently is capital converted into revenue? (Burn Multiple) |
| **Operating Leverage** | Operating Leverage (SAME — but MORE important) | Operating leverage is THE driver of the path to profitability. Model explicitly: fixed vs. variable cost scaling. Track %ΔOpEx / %ΔRevenue. |
| **P/E multiple** | EV/Revenue, EV/ARR, or EV/Gross Profit | Negative earnings make P/E undefined. Revenue-based multiples capture growth value. Adjust for growth rate, margins, and unit economics. |
| **FCF Yield** | Burn Multiple + Cash Runway | Negative FCF means negative yield. Instead measure: how much cash burned per $ of new ARR? And how long can they keep burning? |
| **SBC analysis** | SBC analysis (SAME — but MORE critical) | Growth companies rely heavily on SBC (10–30% of revenue). Track SBC/revenue, share count growth, and SBC-adjusted earnings. This is MORE important, not less. |
| **Revenue growth** | Revenue growth + NRR + Expansion rate | Growth rate alone is insufficient. Decompose: new customer ARR vs. expansion ARR. NRR > 100% means organic growth from existing customers. |
| **Value trap detection** | "Growth trap" detection | Growth trap: company grows but never reaches profitability. Red flags: deteriorating unit economics, rising CAC, slowing NRR, accelerating SBC. |
| **Dividend yield** | N/A (irrelevant) | Growth companies don't pay dividends. Cash is reinvested. |
| **Book value / P/B** | N/A (mostly irrelevant) | Intangible assets (code, brand, data) aren't on balance sheet. Book value dramatically understates true value. |
| **Debt analysis** | Cash runway + Financing risk | Debt is less relevant than cash burn rate. Focus: months of survival, access to capital markets, dilution risk. |
| **Margin of safety** | Scenario-weighted valuation | Use probability-weighted scenarios (bull/base/bear) rather than discount to intrinsic value. Growth uncertainty requires scenario analysis. |

### Key Mapping Summary

| If Standard Framework Says... | Growth Framework Uses Instead... |
|------------------------------|----------------------------------|
| "DCF at 10% WACC" | "Extended DCF at 12–15% WACC + ARR multiple sanity check" |
| "ROIC > 15%" | "Burn Multiple < 1.5x and LTV/CAC > 3x" |
| "P/E of 20x is fair" | "EV/Revenue of 10x with 30% growth = fair" |
| "FCF yield of 5%" | "Cash runway of 24 months + path to breakeven in 18 months" |
| "SBC is 2% of revenue" | "SBC is 18% of revenue — model 5% annual dilution" |
| "Revenue grew 8%" | "Revenue grew 35% with NRR of 120%" |
| "Value trap: cheap P/E" | "Growth trap: high burn, deteriorating LTV/CAC, no path to profit" |

---

## 9. REVERSE ENGINEERING FOR GROWTH

### 9.1 What Does EV/Revenue of 10x Imply?

Given: EV/Revenue = 10x, Current Revenue = $100M, EV = $1B

**What growth is the market pricing in?**

**Method 1: Multiple Decomposition**
```
EV/Revenue = (Profit Margin × P/E) + Growth Premium
```

Assuming mature SaaS:
- Mature FCF margin target: 25%
- Mature P/E: 25x
- Mature EV/Revenue: 25% × 25x = 6.25x

If current multiple is 10x, the extra 3.75x is "growth premium."

**Method 2: Implied Growth Rate**
```
EV/Revenue = (Target FCF Margin) / (WACC - g) × (1 + g)^n
```

Solving backwards:
- Assume: 25% mature FCF margin, 12% WACC, 7 years to maturity
- 10x = 25% / (12% - g) × growth factor
- Implied long-term growth: ~15–20%

**Interpretation**: The market expects this company to:
1. Grow revenue at 25–35% for 5–7 years
2. Reach 20–25% FCF margin at maturity
3. Sustain 10–15% growth in perpetuity

If the company CANNOT achieve this, the stock is overvalued.

### 9.2 Implied Revenue Growth from Current Price

**Formula**:
```
Implied EV/Revenue at Maturity = Current EV / Projected Mature Revenue
```

**Example**:
- Current EV: $2B
- Current Revenue: $150M (EV/Rev = 13.3x)
- Assume company reaches $600M revenue in 5 years
- Implied EV/Rev at $600M: 3.3x
- This is reasonable for a mature SaaS company
- But requires 32% CAGR revenue growth for 5 years

**Reality Check Table**:

| Current EV/Revenue | Implied 5-Year Revenue CAGR | Assessment |
|--------------------|---------------------------|------------|
| 5x | 15% | Reasonable for moderate growth |
| 8x | 25% | Requires strong execution |
| 12x | 35% | Requires exceptional performance |
| 20x | 50% | Rarely sustainable; high risk |
| 30x+ | 60%+ | Bubble territory for most |

### 9.3 Reverse DCF for Growth Companies

Instead of forecasting cash flows, back out what the market is implying:

```
Step 1: Set Current EV = Sum of PV of future FCF
Step 2: Assume a margin trajectory (e.g., -5% → 5% → 15% → 25% over 10 years)
Step 3: Solve for the revenue growth rate that makes DCF = current EV
Step 4: Compare implied growth to what's achievable
```

**Example**:
- Current EV: $800M
- Current Revenue: $100M
- Model: FCF margins improve from -10% to +20% over 8 years
- WACC: 12%
- Solve: What revenue growth makes DCF = $800M?
- Answer: ~28% CAGR for 8 years, reaching ~$850M revenue
- Assessment: Reasonable if TAM is large and company has moat

### 9.4 Growth-Adjusted Implied Returns

```
Implied IRR = [(Mature EV / Current EV)^(1/Years)] - 1
```

| Current EV/Rev | Mature EV/Rev (at 25% margin) | Years to Mature | Implied Annual Return |
|----------------|-------------------------------|-----------------|----------------------|
| 20x | 6x | 7 | -16% (overvalued) |
| 15x | 6x | 7 | -11% (overvalued) |
| 10x | 6x | 7 | -6% (slight overvalue) |
| 8x | 6x | 7 | -4% (fair-ish) |
| 6x | 6x | 7 | 0% (fair) |
| 4x | 6x | 7 | +6% (undervalued) |

---

## 10. ACCOUNTING RED FLAGS

### 10.1 Revenue Recognition Games

| Tactic | How It Works | Detection | Impact |
|--------|-------------|-----------|--------|
| **Multi-year upfront** | Book 3-year contract revenue immediately | Check deferred revenue vs. ARR | Inflates current revenue; future revenue missing |
| **Professional services bundling** | Include services in SaaS revenue | Gross margin analysis (services = lower GM) | Artificially inflates "SaaS" revenue |
| **Partner/reseller revenue** | Count reseller bookings as own revenue | Revenue concentration disclosure | Double-counting; lower quality |
| **Usage-based smoothing** | Smooth lumpy usage revenue | QoQ revenue variance analysis | Hides true demand volatility |
| **Minimum guarantees** | Book committed but not used capacity | Footnote reading | Revenue without actual usage |
| **Acquisition revenue** | Include acquired company revenue | Organic vs. total revenue growth | Masks true organic deceleration |

**Detection Formula**:
```
Revenue Quality = (ARR Growth - Reported Revenue Growth) / Reported Revenue Growth
```
- Large positive = may be recognizing revenue faster than ARR growth
- Large negative = may be under-recognizing or ARR is decelerating

### 10.2 CAC Calculation Games

| Tactic | How It Works | Detection |
|--------|-------------|-----------|
| **Exclude SBC from S&M** | Remove SBC from CAC calculation | Check if SBC is included in S&M expense |
| **Exclude certain sales roles** | Only count "direct" marketing spend | Ask: Does S&M expense = full sales org? |
| **Blend new + expansion CAC** | Include upsell costs to lower blended CAC | Demand separate new and expansion CAC |
| **Exclude customer success** | Don't count post-sale CS costs | CS is part of retention; should be included in "loaded CAC" |
| **Annualize quarterly S&M** | Use single quarter to annualize | Smooth over multiple quarters |

**Proper CAC Calculation**:
```
Fully Loaded CAC = (Total S&M Expense + Allocated SBC in S&M + CS Costs) / New Customers
```

### 10.3 NRR Calculation Inconsistencies

| Variation | Impact | Ask |
|-----------|--------|-----|
| **Logo retention vs. dollar retention** | Logo retention is lower | Which does the company report? |
| **Include/exclude price increases** | Can inflate NRR 2–5 points | Are price increases included in expansion? |
| **Annual vs. quarterly cohort** | Different cohorts show different NRR | What cohort definition is used? |
| **Exclude downgrades** | Excluding contraction inflates NRR | Is contraction included? |
| **SMB vs. enterprise only** | Enterprise NRR usually higher | Is NRR blended across segments? |
| **Trailing 12 months vs. quarterly** | TTM smooths; quarterly is more current | Which period is reported? |

**Benchmark**: Always ask for **GRR (Gross Revenue Retention)** alongside NRR. GRR < 85% is concerning regardless of NRR.

### 10.4 SBC Classification Tricks

| Tactic | How It Works | Detection |
|--------|-------------|-----------|
| **Classify RSUs as "non-employee"** | Moves SBC out of operating expenses | Check SBC footnote breakdown |
| **Exclude SBC from EBITDA** | "Adjusted EBITDA" excludes SBC | SBC is a REAL cost — must include |
| **ESPP dilution omission** | Don't count ESPP in share count | Check fully diluted share count |
| **Performance-contingent awards** | Don't count until performance met | May still be probable and should be accrued |
| **Grants timed around guidance** | Front-load grants to hit targets | SBC spike in certain quarters |

**Critical Adjustment**:
```
True Operating Income = Reported Operating Income - SBC Expense
True FCF = Reported FCF - SBC Expense (because SBC offsets cash that would be paid)
True EPS = (Net Income - SBC) / Fully Diluted Shares
```

### 10.5 Customer Count Inflation

| Tactic | How It Works | Detection |
|--------|-------------|-----------|
| **Count divisions as customers** | One enterprise = 10 "customers" | Ask: How is "customer" defined? |
| **Include free/trial users** | Count non-paying users | Paid vs. total user count |
| **Don't count churned reactivations** | Reactivated = "new" customer | Customer count methodology |
| **Count seats as customers** | One customer with 100 seats = 100 customers | ACV analysis — total customers vs. seats |
| **Include partners/resellers** | Channel partners counted as customers | Direct vs. indirect customer split |

**Quality Check**: Divide ARR by customer count. If ARPU changes dramatically quarter-to-quarter, the definition changed or mix shifted significantly.

### 10.6 Other Red Flags

| Red Flag | Detection Method | Severity |
|----------|-----------------|----------|
| **Founder/executive departures** | SEC filings, press releases | High |
| **Auditor changes** | 8-K filings | High |
| **Restatements** | 8-K, amended filings | Critical |
| **Short seller reports** | Market monitoring | Medium-High |
| **Insider selling clusters** | Form 4 filings | Medium |
| **Guidance methodology changes** | Earnings call transcripts | Medium |
| **Increasing DSO** | Accounts Receivable / (Revenue/90) | Medium |
| **Declining deferred revenue** | Balance sheet trend | High for SaaS |
| **Cash flow from operations << net income** | Cash flow statement | High |
| **Frequent M&A (revenue gap-filling)** | Acquisition history | Medium |

**Red Flag Scoring Matrix**:

| Score | # of Red Flags | Interpretation |
|-------|---------------|----------------|
| 0–1 | Green | Low concern |
| 2–3 | Yellow | Monitor closely |
| 4–5 | Orange | Significant concern — dig deeper |
| 6+ | Red | Avoid or require major discount |


---

## 11. CONCRETE EXAMPLE: HYPOTHETICAL SAAS COMPANY

### Company Profile: "CloudFlow" — Project Management SaaS

| Attribute | Value | Assessment |
|-----------|-------|------------|
| **ARR** | $100M | Scaling stage |
| **Revenue Growth** | 30% YoY | Strong growth |
| **Gross Margin** | 75% | Good (SaaS average) |
| **FCF Margin** | -5% | Approaching profitability |
| **Cash Balance** | $50M | Adequate but not excessive |
| **Quarterly Burn** | $5M ($20M annual) | 2.5 years runway at current burn |
| **NRR** | 115% | Good expansion |
| **GRR** | 88% | Reasonable retention |
| **Customers** | 5,000 | Mid-market focus |
| **ARPU** | $20,000/year | Healthy ACV |
| **LTV/CAC** | 3.2x | Sustainable |
| **CAC Payback** | 14 months | Acceptable |
| **Magic Number** | 0.85 | Good efficiency |
| **SBC/Revenue** | 18% | High but typical |
| **Share Count Growth** | 5%/year | Significant dilution |
| **R&D/Revenue** | 22% | Product-focused |
| **S&M/Revenue** | 38% | Investing in growth |
| **G&A/Revenue** | 12% | Reasonable |
| **Rule of 40** | 25 (30% growth + (-5%) FCF) | Fair, improving |
| **Burn Multiple** | 1.3x | Good efficiency |
| **TAM** | $10B | Large market |
| **Competitive Position** | #3 in category | Behind two larger players |

### Valuation Approach A: Extended DCF (Path to Profitability)

**Assumptions**:
- WACC: 12% (reflects growth risk)
- Growth decays from 30% to 12% over 10 years
- Gross margin improves from 75% to 82%
- Operating leverage: OpEx grows at 0.75× revenue growth rate
- FCF turns positive in Year 3
- Terminal growth: 3.5%

| Year | Revenue ($M) | Growth | Gross Margin | FCF Margin | FCF ($M) | PV of FCF |
|------|-------------|--------|-------------|------------|----------|-----------|
| 1 | 115 | 30% | 76% | -7% | -8.1 | -7.2 |
| 2 | 144 | 25% | 77% | -3% | -4.3 | -3.4 |
| 3 | 173 | 20% | 78% | 1% | 1.7 | 1.2 |
| 4 | 199 | 15% | 79% | 5% | 9.9 | 6.3 |
| 5 | 223 | 12% | 80% | 9% | 20.1 | 11.4 |
| 6 | 245 | 10% | 81% | 12% | 29.4 | 14.9 |
| 7 | 265 | 8% | 81% | 14% | 37.1 | 16.8 |
| 8 | 281 | 6% | 82% | 16% | 45.0 | 18.2 |
| 9 | 295 | 5% | 82% | 17% | 50.2 | 18.1 |
| 10 | 310 | 5% | 82% | 18% | 55.8 | 18.0 |

**Terminal Value** (Year 7, when FCF is stable):
```
TV = FCF_Y7 × (1 + g) / (WACC - g) = $37.1M × 1.035 / (0.12 - 0.035) = $451M
PV of TV = $451M / (1.12)^7 = $204M
```

**DCF Valuation**:
```
Sum of PV (Years 1-7 FCF) = $40.2M
PV of Terminal Value = $204M
Enterprise Value = $244M
```

**Problem**: $244M seems low! Why? Because the standard DCF doesn't capture the ARR/recurring value properly. The terminal value assumes only modest growth from Year 7 onward, but a SaaS company with $265M ARR and 115% NRR has substantial embedded growth.

**Adjustment**: Use **ARR-based terminal value** instead:
```
TV = ARR_Y7 × ARR Multiple × Margin Factor
TV = $265M × 6x × 0.85 = $1,352M
PV of TV = $1,352M / (1.12)^7 = $612M
Adjusted EV = $40M + $612M = $652M
```

**DCF Conclusion: $650M EV / 6.5x ARR**

---

### Valuation Approach B: ARR Multiple (Comparable Company)

**Peer Set** (matching: $50–200M ARR, 25–35% growth, SaaS):

| Peer | ARR ($M) | Growth | NRR | GM | Rule of 40 | EV/ARR |
|------|----------|--------|-----|-----|------------|--------|
| Asana | $600M | 25% | 115% | 88% | 18 | 5.5x |
| Monday.com | $700M | 30% | 115% | 88% | 28 | 8.5x |
| Smartsheet | $900M | 20% | 115% | 82% | 18 | 5.0x |
| ClickUp (est.) | $200M | 40% | 110% | 80% | 38 | 10.0x |
| Wrike (est.) | $150M | 20% | 110% | 78% | 20 | 4.5x |
| Notion (est.) | $300M | 50% | 120% | 85% | 55 | 15.0x |
| **Median** | | **28%** | **115%** | **83%** | **28** | **7.0x** |

**CloudFlow Adjustments**:

| Factor | Adjustment | Rationale |
|--------|-----------|-----------|
| Base Multiple (30% growth, NRR 115%) | 7.0x | Peer median |
| Gross margin (75% vs 83% median) | -0.5x | Below average |
| Rule of 40 (25 vs 28 median) | -0.5x | Slightly below |
| Scale ($100M vs $400M median) | +0.5x | Smaller = more growth runway |
| Competitive position (#3) | -0.5x | Not market leader |
| Cash runway (2.5 years) | -0.5x | Adequate but not strong |
| Burn multiple (1.3x) | +0.5x | Good efficiency |
| **Adjusted Multiple** | **6.0x** | |

**ARR Multiple Valuation**:
```
EV = $100M ARR × 6.0x = $600M
Range: $500M – $750M (±1x ARR for uncertainty)
```

---

### Valuation Approach C: Unit Economics-Based

**Customer Economics**:
- Customers: 5,000
- ARPU: $20,000/year
- Gross Margin: 75%
- Annual Churn: 12% (implied lifetime = 8.3 years)
- CAC: $22,500

```
LTV = ARPU × Gross Margin × Customer Lifetime
LTV = $20,000 × 0.75 × 8.3 = $124,500

LTV/CAC = $124,500 / $22,500 = 5.5x (healthy)

CAC Payback = $22,500 / ($20,000 × 0.75) = 1.5 years (18 months — acceptable)

Total Customer Value = 5,000 × $124,500 = $622.5M
Adjust for: execution risk (20% discount), competitive risk (10% discount)
Adjusted Value = $622.5M × 0.70 = $435M
```

**Unit Economics Valuation: $435M** (conservative — high discount rate applied)

---

### Valuation Approach D: Rule of 40 Regression

Using historical relationship: **EV/ARR = 2.5 × (Rule of 40) + 1.0**

```
CloudFlow Rule of 40 = 30% growth + (-5%) FCF = 25
Implied EV/ARR = 2.5 × 25 + 1.0 = 5.25x
EV = $100M × 5.25x = $525M
```

With adjustment for NRR premium (115% NRR = +0.5x):
```
Adjusted EV/ARR = 5.75x
EV = $575M
```

---

### Valuation Approach E: Reverse Engineering Check

**Current ask**: Let's say the company is valued at $700M in a secondary transaction.

**What does $700M imply?**
```
EV/ARR = 7.0x
```

Using reverse DCF:
- To justify 7.0x at $100M ARR with 12% WACC
- Need: ~$300M ARR in Year 7 with 20% FCF margin
- Required CAGR: 17% for 7 years
- Assessment: Reasonable if NRR stays >110% and market grows

Using growth-adjusted multiple:
```
EV/ARR / Growth = 7.0x / 30 = 0.23x
```
This is below 0.3x threshold → suggests the $700M may be reasonable or even cheap.

---

### 11.1 Summary Valuation Cross-Check

| Approach | EV ($M) | EV/ARR | Key Driver |
|----------|---------|--------|------------|
| Extended DCF (ARR-based TV) | $650M | 6.5x | Path to profitability |
| ARR Multiple (comps) | $600M | 6.0x | Peer comparison |
| Unit Economics | $435M | 4.4x | Customer value |
| Rule of 40 Regression | $575M | 5.75x | Efficiency score |
| Reverse Engineering (at $700M) | $700M | 7.0x | Market pricing |
| **Weighted Average** | **$600–650M** | **6.0–6.5x** | **Consensus range** |

**Final Valuation Range: $550M – $700M EV (5.5x – 7.0x ARR)**

**Bull case ($800M / 8x ARR)**: NRR improves to 125%, growth accelerates to 40%, path to 20% FCF margin in 4 years.
**Base case ($600M / 6x ARR)**: NRR stable at 115%, growth decays to 20%, FCF margin reaches 15% in 6 years.
**Bear case ($350M / 3.5x ARR)**: NRR drops to 105%, growth decays to 15%, FCF breakeven delayed to Year 5+, funding winter.

### 11.2 Investment Decision Framework

| Scenario | Probability | EV ($M) | Weighted ($M) |
|----------|-------------|---------|---------------|
| Bull | 25% | $800M | $200M |
| Base | 45% | $600M | $270M |
| Bear | 30% | $350M | $105M |
| **Probability-Weighted Value** | | | **$575M** |

**Decision Rule**:
- If available at < $450M (4.5x ARR): **Strong Buy** — margin of safety even in bear case
- If available at $450–550M (4.5–5.5x ARR): **Buy** — reasonable risk/reward
- If available at $550–700M (5.5–7.0x ARR): **Hold / Fair Value** — priced for execution
- If available at > $700M (7.0x+ ARR): **Sell / Avoid** — limited upside, high downside

### 11.3 Key Monitoring Triggers

| Metric | Current | Trigger | Action if Triggered |
|--------|---------|---------|-------------------|
| NRR | 115% | Drops below 110% | Reduce position |
| NRR | 115% | Drops below 105% | Exit position |
| Growth | 30% | Drops below 20% | Reassess valuation |
| Cash Runway | 30 months | Drops below 18 months | Monitor funding risk |
| LTV/CAC | 3.2x | Drops below 2.5x | Reduce position |
| SBC/Revenue | 18% | Rises above 25% | Dilution concern |
| Rule of 40 | 25 | Drops below 20 | Reassess |
| Magic Number | 0.85 | Drops below 0.5 | S&M efficiency issue |

### 11.4 Key Operating Leverage Inflection Points

| Revenue Scale | Expected FCF Margin | Key Driver |
|---------------|-------------------|------------|
| $100M (current) | -5% | Still investing heavily |
| $150M | 0–3% | S&M efficiency kicks in |
| $200M | 5–8% | G&A leverage significant |
| $300M | 12–15% | Operating leverage maturing |
| $500M | 18–22% | Approaching mature SaaS margin |
| $1B | 22–28% | Mature, profitable business |

**Critical question**: Can CloudFlow reach $200M ARR before running out of cash or needing to raise?
- Current burn: $20M/year
- Cash: $50M
- At current burn: 2.5 years runway
- To reach $200M ARR at 25% growth: ~3 years
- **Gap**: Need growth efficiency improvement OR raise capital

**Implication**: If burn doesn't decrease as revenue scales, CloudFlow will need to raise capital in 12–18 months — potential dilution risk.


---

## 12. QUICK REFERENCE: DECISION FLOWCHART

```
STEP 1: Is this a growth company? (Section 1 Detection Rules)
    |
    |-- Score >= 7? --> YES --> Use THIS framework (growth-modified)
    |-- Score 4-6?  --> YES --> Use HYBRID framework
    |-- Score <= 3? --> NO  --> Use standard framework

STEP 2: What maturity stage? (Section 1.2)
    |
    |-- Pre-revenue --> unit-demand/milestone analysis (TAM $ is a check)
    |-- Early revenue --> EV/Revenue + unit economics focus
    |-- Scaling --> Path-to-profitability DCF + ARR multiple
    |-- Approaching profitability --> Extended DCF + hybrid metrics

STEP 3: What is the primary value driver?
    |
    |-- Recurring revenue dominant --> ARR Multiple (Model D)
    |-- Customer acquisition machine --> Unit Economics (Model C)
    |-- Path to profitability visible --> Extended DCF (Model A)
    |-- Peer comparison most reliable --> Revenue Multiple (Model B)

STEP 4: Cross-check with secondary method
    |
    |-- DCF result vs. ARR multiple result should be within 30%
    |-- If divergent > 50%: review assumptions

STEP 5: Stress test (Section 6)
    |
    |-- Funding winter scenario
    |-- Growth deceleration scenario
    |-- Churn shock scenario
    |-- SBC cliff scenario

STEP 6: Quality score (Section 5)
    |
    |-- SaaS: Score 0-30 (25+ = exceptional)
    |-- Biotech: Score 0-30 (20+ = investable)
    |-- Consumer: Score 0-30 (22+ = strong)

STEP 7: Final valuation = Probability-weighted average
    |
    |-- Bull (20-30%) + Base (40-50%) + Bear (20-30%)
    |-- Apply margin of safety for lower quality scores
```

---

## 13. FORMULA CHEAT SHEET

### Revenue Metrics
```
ARR = MRR × 12
Revenue Growth = (Current Revenue / Prior Period Revenue) - 1
NRR = (Beginning ARR + Expansion - Contraction - Churn) / Beginning ARR
GRR = (Beginning ARR - Churn - Contraction) / Beginning ARR
Net New ARR = Ending ARR - Beginning ARR
Expansion ARR = Upsell + Cross-sell from existing customers
```

### Unit Economics
```
CAC = S&M Expense / New Customers Acquired
LTV = ARPU × Gross Margin × Customer Lifetime
Customer Lifetime = 1 / Churn Rate (for annual churn)
LTV/CAC = LTV / CAC
CAC Payback (months) = CAC / (ARPU × Gross Margin) × 12
Magic Number = (Net New ARR × 4) / S&M Spend (prior quarter)
Burn Multiple = Net Cash Burn / Net New ARR
```

### Efficiency Metrics
```
Rule of 40 = Revenue Growth% + FCF Margin%
Gross Margin = (Revenue - COGS) / Revenue
Operating Leverage = % Change in OpEx / % Change in Revenue
FCF Margin = FCF / Revenue
```

### Dilution Metrics
```
SBC / Revenue = Stock-Based Compensation / Revenue
Share Count Growth = (Ending Shares / Beginning Shares) - 1
SBC-Adjusted EPS = (Net Income - SBC) / Diluted Shares
Fully Diluted Shares = Basic + RSUs + Options (in-the-money) + ESPP
```

### Valuation
```
EV/ARR = Enterprise Value / ARR
EV/Revenue/Growth = EV/Revenue / Revenue Growth%
Growth-Adjusted Multiple = EV/Revenue / (Growth% × 100)
Implied Growth from DCF: Solve for g where DCF(EV) = Current Price
Terminal Value (perpetuity) = FCF × (1 + g) / (WACC - g)
Terminal Value (exit multiple) = EBITDA × Exit Multiple
```

---

## 14. COMMON PITFALLS IN GROWTH COMPANY VALUATION

### Pitfall 1: Using Standard DCF Unmodified
- **Problem**: Negative FCF leads to negative valuation or nonsensical results
- **Fix**: Use extended DCF with explicit path to profitability; or use ARR multiple

### Pitfall 2: Ignoring SBC
- **Problem**: "Adjusted EBITDA" excludes SBC; growth companies have massive SBC
- **Fix**: Always calculate SBC-adjusted earnings; model share count growth

### Pitfall 3: Comparing Incomparable Companies
- **Problem**: Comparing 50% grower to 10% grower on same multiple
- **Fix**: Growth-adjusted multiples; peer matching on growth + margins + model

### Pitfall 4: Assuming Growth Continues Forever
- **Problem**: 30% growth for 10 years is extremely rare; law of large numbers applies
- **Fix**: Model growth decay; terminal value only after growth normalizes

### Pitfall 5: Ignoring Funding Risk
- **Problem**: Assuming company can always raise capital
- **Fix**: Model cash runway; stress-test with no capital raises

### Pitfall 6: Taking Reported Metrics at Face Value
- **Problem**: NRR, CAC, and "customer" definitions vary; companies optimize metrics
- **Fix**: Read footnotes; ask clarifying questions; look for inconsistencies

### Pitfall 7: Using P/E for Negative Earnings
- **Problem**: P/E is undefined for negative earnings
- **Fix**: Use EV/Revenue, EV/ARR, or EV/Gross Profit instead

### Pitfall 8: Ignoring Dilution
- **Problem**: 5% annual share count growth = 40% dilution over 7 years
- **Fix**: Use fully diluted share count; model future SBC grants

### Pitfall 9: Confusing Revenue with Cash
- **Problem**: SaaS revenue is recognized ratably; cash is collected differently
- **Fix**: Track billings, deferred revenue, and FCF alongside revenue

### Pitfall 10: Valuing on TAM Alone
- **Problem**: "$10B TAM × 10% share = $1B revenue" is speculative
- **Fix**: TAM is an upper bound; model bottoms-up customer/revenue build

---

## 15. APPENDIX: GLOSSARY

| Term | Definition |
|------|------------|
| **ACV** | Annual Contract Value — yearly revenue per customer contract |
| **ARR** | Annual Recurring Revenue — yearly subscription revenue |
| **Burn Multiple** | Net cash burn divided by net new ARR — capital efficiency metric |
| **CAC** | Customer Acquisition Cost — cost to acquire one new customer |
| **Churn** | Rate at which customers cancel subscriptions |
| **COGS** | Cost of Goods Sold — direct costs of delivering product |
| **DCF** | Discounted Cash Flow — valuation method |
| **EV** | Enterprise Value — market cap + debt - cash |
| **FCF** | Free Cash Flow — operating cash flow minus capex |
| **GMV** | Gross Merchandise Value — total transaction volume |
| **GRR** | Gross Revenue Retention — retention without expansion |
| **LTV** | Lifetime Value — total value a customer generates |
| **Magic Number** | SaaS efficiency metric = net new ARR × 4 / S&M spend |
| **MRR** | Monthly Recurring Revenue — monthly subscription revenue |
| **NRR** | Net Revenue Retention — retention including expansion |
| **OpEx** | Operating Expenses — R&D + S&M + G&A |
| **R&D** | Research and Development |
| **ROIC** | Return on Invested Capital |
| **Rule of 40** | Growth% + FCF Margin% — efficiency benchmark |
| **SaaS** | Software as a Service |
| **SAM** | Serviceable Available Market |
| **SBC** | Stock-Based Compensation |
| **S&M** | Sales and Marketing |
| **TAM** | Total Addressable Market |
| **WACC** | Weighted Average Cost of Capital |

---

*Document Version: 1.0*
*Framework: Growth Companies (Negative FCF) Adaptive Analysis*
*Applicable Sectors: SaaS, Cloud Infrastructure, Biotech (Pre-Revenue), Growth Consumer Tech, Late-Stage Private Companies*

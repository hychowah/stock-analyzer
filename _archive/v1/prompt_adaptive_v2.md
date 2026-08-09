# [TICKER] — 全方位股票深度分析 (Adaptive Sector-Aware Multi-Agent Swarm)
# P0+P1修復版 + Adaptive v2 | 修復日期：2026-07-12

分析 **[TICKER]** ([公司名稱])，市場區域為 **[市場區域]**。長線價值投資視角（>2年），尋找被低估優質股，**嚴防價值陷阱**，技術面僅用於入場時機。

**核心理念**：先問「為什麼這麼便宜？」，再問「值不值得買？」

**使用前請替換**：`[TICKER]`、`[公司名稱]`、`[市場區域]`、`[區域基準指數]`、`[貨幣]`、`[競爭對手1-5]`

---

## 【ADDED IN v2】SECTOR DETECTION & ADAPTIVE ROUTING LAYER

> This layer runs ONCE at the very beginning (before any agents), determines the company type,
> selects the appropriate sector module, and defines metric substitutions that apply across ALL agents.
> It does NOT replace any agent — it INFORMS each agent what metrics/models to use.

### Step 0: Sector Classification (Orchestrator executes before Phase 0)

```python
# SECTOR DETECTION ALGORITHM (Orchestrator runs this once)
def classify_sector(ticker_data):
    score_banking = 0
    score_insurance = 0
    score_growth = 0
    score_reit = 0
    score_utility = 0
    score_cyclical = 0
    score_standard = 0  # default: use base framework as-is
    
    # === Banking Signals ===
    if gics_code.startswith("4010") or sic_code.startswith("60"):
        score_banking += 50
    if balance_sheet.get("loans") / balance_sheet.get("total_assets", 1) > 0.30:
        score_banking += 20
    if balance_sheet.get("deposits") / balance_sheet.get("total_liabilities", 1) > 0.20:
        score_banking += 20
    if income_stmt.get("net_interest_income", 0) > 0:
        score_banking += 10
        
    # === Insurance Signals ===
    if gics_code.startswith("4030") or sic_code.startswith("63"):
        score_insurance += 50
    if "premiums_earned" in income_stmt.index.str.lower():
        score_insurance += 25
    if "loss_reserves" in balance_sheet.index.str.lower() or "policyholder_reserves" in balance_sheet.index.str.lower():
        score_insurance += 25
        
    # === REIT Signals ===
    if gics_code.startswith("6010") or "REIT" in company_name.upper():
        score_reit += 50
    if balance_sheet.get("depreciation", 0) / income_stmt.get("total_revenue", 1) > 0.30:
        score_reit += 15
    if company_info.get("dividend_yield", 0) > 0.03:
        score_reit += 10
    if balance_sheet.get("property_plant_equipment", 0) / balance_sheet.get("total_assets", 1) > 0.60:
        score_reit += 15
    if balance_sheet.get("mortgage_backed_securities", 0) / balance_sheet.get("total_assets", 1) > 0.50:
        score_reit += 10  # mREIT flag
        
    # === Utility Signals ===
    if gics_code.startswith("5510") or sic_code.startswith("49"):
        score_utility += 50
    if balance_sheet.get("property_plant_equipment", 0) / balance_sheet.get("total_assets", 1) > 0.60:
        score_utility += 20
    if total_debt / (market_cap + total_debt) > 0.50:
        score_utility += 15
    if "rate_base" in filings_text.lower() or "regulated" in filings_text.lower():
        score_utility += 15
        
    # === Cyclical Signals ===
    revenue_volatility = calculate_10yr_revenue_volatility(ticker)
    market_volatility = calculate_sp500_median_volatility()
    if revenue_volatility > 2 * market_volatility:
        score_cyclical += 25
    ebit_margin_range = calculate_10yr_ebit_margin_range(ticker)
    if ebit_margin_range > 0.15:
        score_cyclical += 25
    if gics_code in cyclical_gics_codes:
        score_cyclical += 30
    if "reserves" in filings_text.lower() and any(c in filings_text.lower() for c in ["copper", "oil", "gas", "gold", "iron"]):
        score_cyclical += 20
        
    # === Growth Signals (can co-exist with sector — e.g., fintech bank = banking + growth adjustments) ===
    fcf_margin = cashflow.get("free_cash_flow", 0) / income_stmt.get("total_revenue", 1)
    revenue_growth = calculate_yoy_revenue_growth(ticker)
    sbc = cashflow.get("stock_based_compensation", 0)
    sbc_pct_rev = sbc / income_stmt.get("total_revenue", 1)
    
    if fcf_margin < 0 and revenue_growth > 0.20:
        score_growth += 30
    if sbc_pct_rev > 0.05:
        score_growth += 20
    if sbc_pct_rev > 0.15:
        score_growth += 15  # heavy SBC = definitely growth-style analysis
    if income_stmt.get("research_development", 0) / income_stmt.get("total_revenue", 1) > 0.15:
        score_growth += 15
    if revenue_growth > 0.30:
        score_growth += 20
        
    # === Determine Primary Sector ===
    scores = {
        "banking": score_banking,
        "insurance": score_insurance,
        "growth": score_growth,
        "reit": score_reit,
        "utility": score_utility,
        "cyclical": score_cyclical,
        "standard": score_standard
    }
    primary_sector = max(scores, key=scores.get)
    confidence = scores[primary_sector] / 100.0  # normalize
    
    # === Secondary Flag: Is this ALSO a growth company? ===
    is_also_growth = (score_growth >= 50 and primary_sector not in ["growth"])
    
    return {
        "primary_sector": primary_sector,
        "confidence": confidence,
        "all_scores": scores,
        "is_also_growth": is_also_growth,  # e.g., fintech bank needs banking + growth SBC analysis
        "requires_manual_review": confidence < 0.70
    }
```

### Sector → Module Mapping

| Primary Sector | Module File | Confidence Threshold |
|---|---|---|
| banking | `/workspace-stock-research/sector_banking.md` | > 0.70 |
| insurance | `/workspace-stock-research/sector_insurance.md` | > 0.70 |
| growth | `/workspace-stock-research/sector_growth.md` | > 0.50 |
| reit | `/workspace-stock-research/sector_reit.md` | > 0.70 |
| utility | `/workspace-stock-research/sector_utility.md` | > 0.70 |
| cyclical | `/workspace-stock-research/sector_cyclical.md` | > 0.50 |
| standard | No module — use base framework as-is | — |

### Secondary Growth Flag
If `is_also_growth = true` (e.g., a fintech bank, or a high-growth utility like a renewable developer):
- Use PRIMARY sector's valuation model
- BUT add Growth module's SBC analysis (Agent 2 task 10) at **CRITICAL** intensity
- AND add Burn Multiple / Rule of 40 metrics to Agent 5's output
- AND extend explicit forecast period to 7-10 years (vs 5)

### Metric Substitution Registry (Written once by Orchestrator, read by ALL agents)

After sector detection, the Orchestrator writes `/registry/sector_config`:

```json
{
  "primary_sector": "banking|insurance|growth|reit|utility|cyclical|standard",
  "confidence": 0.85,
  "is_also_growth": false,
  "module_file": "/workspace-stock-research/sector_XXX.md",
  "substitutions": {
    "valuation_model_primary": "...",
    "valuation_model_secondary": "...",
    "roic_equivalent": "...",
    "pe_equivalent": "...",
    "fcf_yield_equivalent": "...",
    "revenue_growth_equivalent": "...",
    "operating_leverage_equivalent": "...",
    "gross_margin_equivalent": "...",
    "sbc_analysis_intensity": "none|low|medium|high|critical",
    "moat_indicator": "...",
    "capital_structure_focus": "...",
    "peer_comparison_metrics": ["..."],
    "stress_test_scenarios": ["..."],
    "reverse_engineering_target": "..."
  },
  "agents_modified": ["agent_0", "agent_2", "agent_5", "agent_12", "agent_13"],
  "agents_unchanged": ["agent_1", "agent_3", "agent_4", "agent_6", "agent_8", "agent_11"]
}
```

### Which Agents Are Modified vs Unchanged

| Agent | Role | Modified in v2? | What Changes |
|---|---|---|---|
| **Agent 0** | Background Research | ✅ YES | Add sector-specific Round 8 queries; Replace "ROIC" in moat analysis with sector equivalent |
| **Agent 1** | Web Search | ❌ NO | Unchanged — sector-neutral search rounds |
| **Agent 2** | Financial API | ✅ YES | Substitute ROIC→sector equiv; Add sector-specific API calls; Task 10 SBC intensity varies by sector |
| **Agent 3** | News & Sentiment | ❌ NO | Unchanged |
| **Agent 4** | Technical Analysis | ❌ NO | Unchanged — pure price/volume |
| **Agent 5** | Valuation Modeling | ✅ YES | COMPLETE model swap per sector; All formulas replaced; Reverse engineering target changed |
| **Agent 6** | Chart Generation | ⚠️ MINOR | Chart titles/annotations adapt to sector metrics |
| **Agent 7** | Fundamental Report | ✅ YES | Report sections adapt to sector; Section 4 (ROIC→sector equiv); Section 9 (DCF→sector model) |
| **Agent 8** | Technical Report | ❌ NO | Unchanged — technical analysis is sector-agnostic |
| **Agent 11** | README | ⚠️ MINOR | Summary metrics use sector equivalents |
| **Agent 12** | TSR Validation | ✅ YES | Peer benchmark indices adapted; SBC dilution intensity varies |
| **Agent 13** | Stress Test | ✅ YES | Scenarios selected from sector-specific scenario library |

---

## 【v2 ADDITION】SECTOR-SPECIFIC METRIC SUBSTITUTION TABLE

Applied by modified agents. Unmodified agents ignore this.

| Standard Base Metric | Banking | Insurance (P&C) | Insurance (Life) | Growth/Neg FCF | REIT | Utility | Cyclical |
|---|---|---|---|---|---|---|---|
| **DCF Primary** | Excess Return: V=BV+(ROE-k)xBV/(k-g) | Float Valuation | MCEV (ANAV+VNB) | Extended DCF (7-10yr) + EV/Revenue | NAV = NOI/CapRate - Debt | Rate-Base DCF | TTC Earnings x Normalized Multiple |
| **DCF Secondary** | P/B-ROE Regression | P/B-ROE | DDM / P/EV | Unit Economics (LTV/CAC) | FFO/AFFO Multiple | DDM | Replacement Cost |
| **ROIC equiv.** | ROE / RAROC | ROE / ROEV | ROEV | Unit Economics (LTV/CAC, Burn Multiple) | FFO Yield | Earned vs Allowed ROE | Cost Curve Position |
| **P/E equiv.** | **P/B** (primary) | **P/B** | **P/EV** | **EV/Revenue** | **P/FFO or P/AFFO** | **Div Yield** (primary) | **TTC EV/EBITDA** |
| **FCF Yield equiv.** | Div Yield + Buyback Yield | Inv. Yield on Float + Div | Inv. Yield + Div | **Burn Multiple** / Rule of 40 | FFO Yield | Div Yield + Rate Base Growth | FCF Breakeven Price |
| **Rev Growth equiv.** | NII + Fee Income Growth | Premium / Float Growth | APE / VNB Growth | **ARR Growth / NRR** | Same-Store NOI Growth | Rate Base CAGR | Volume Growth (ex-price) |
| **Op Lev. equiv.** | Fin. Lev. x NIM Sens. | Float Lev. x Inv. Yield | Op. Leverage near breakeven | Fixed Cost / Lease Spreads | Regulatory Lag | Operating Leverage |
| **Gross Margin equiv.** | **NIM** | **Combined Ratio** | Gross Margin | **NOI Margin** | Allowed ROE Spread | Cash Cost Margin |
| **SBC Intensity** | LOW | LOW | **CRITICAL** (15-30%) | LOW | LOW | LOW |
| **Moat Indicator** | Deposit Franchise | Float Duration / CR Discipline | NRR / Switching Costs | Location / WALT | Regulatory Compact | Cost Curve Position |
| **Capital Focus** | CET1 / Tier 1 | Solvency II / RBC | Cash Runway / Burn | LTV / Debt Maturity | Debt/Total Capital | Net Debt / TTC EBITDA |
| **Peer Metrics** | P/B, ROE, NIM, CET1 | P/B, CR, ROE, Float | P/EV, VNB Margin, ROEV | EV/Rev, NRR, Rule 40 | P/FFO, Cap Rate, WALT | Div Yield, Allowed ROE | TTC EV/EBITDA, AISC |

---

## 【v2 ADDITION】SECTOR-SPECIFIC STRESS TEST SCENARIO LIBRARY

Agent 13 selects 4 scenarios based on detected sector:

| Sector | Scenario A | Scenario B | Scenario C | Scenario D |
|---|---|---|---|---|
| **Banking** | Credit downturn: NPL +500bp | Rate shock: +300bp parallel | Liquidity crisis: deposit flight -30% | Regulatory: CET1 req +300bp |
| **Insurance P&C** | Reserve deficiency: +8% adverse dev | Cat super-year: $250B losses | Rate shock: +300bp ALM | Pricing cycle: soft market CR +10pp |
| **Insurance Life** | Mortality shock: +50% excess deaths | Rate shock: -200bp (liability mismatch) | Lapse spike: +20pp | Regulatory: solvency ratio +50pp |
| **Growth** | Funding winter: can't raise capital | Growth halves: 30% -> 15% | Churn shock: NRR drops to 90% | SBC cliff: cut 50%, talent leaves |
| **REIT** | Cap rate expansion: +200bp | Occupancy shock: -10% | Refinancing crisis: +300bp rates | Rent decline: -10% market rents |
| **Utility** | Allowed ROE cut: -200bp | Interest rate spike: +300bp | $5B wildfire liability | Demand destruction: -15% |
| **Cyclical** | Commodity crash: -40% | Recession: demand -20% | China demand shock: -10% | Overcapacity: +20% new supply |
| **Standard** | Use base framework stress tests | (recession, rate shock, etc.) | | |

---

## 【v2 ADDITION】SECTOR-SPECIFIC REVERSE ENGINEERING TARGETS

Agent 5's reverse engineering task adapts per sector:

| Sector | What to Reverse-Engineer | From What Price Metric | Compare Against |
|---|---|---|---|
| **Banking** | Implied ROE, Implied cost of equity | Current P/B | Historical ROE, Peer ROE |
| **Insurance P&C** | Implied Combined Ratio | Current P/B | Historical CR, Peer CR |
| **Insurance Life** | Implied VNB growth | Current P/EV | Historical VNB margin |
| **Growth** | Implied revenue CAGR, Implied FCF margin at maturity | Current EV/Revenue | Historical growth, TAM |
| **REIT** | Implied cap rate | Price vs NAV | Market cap rates, Property type avg |
| **Utility** | Implied allowed ROE, Implied rate base growth | Current dividend yield | Regulatory allowed ROE |
| **Cyclical** | Implied commodity price | Current stock price | Long-run incentive price, Cost curve |
| **Standard** | Implied revenue CAGR, Implied FCF margin, Implied WACC | Current P/E or EV/EBITDA | Historical growth, margins |

---

## 【RESTORED FROM ORIGINAL】COMPLETE AGENT SWARM ARCHITECTURE

Below is the FULL agent swarm with ALL phases, parallel execution, and registry-based data passing.
Sector modifications are marked with [SECTOR:v2] tags. Unmarked sections are UNCHANGED from original.

---

## Phase 0 — 公司背景研究（1 代理）

### 代理 0：公司背景研究代理 [SECTOR:v2 — ADD Round 8, modify moat analysis metric]

```
=== INPUT ===
無。僅需 [TICKER] + [公司名稱] + [市場區域]。
ADDITIONALLY: Read /registry/sector_config for sector classification

=== 任務 ===
執行 7 輪深度搜索（原始）+ **1 輪行業特定搜索（v2 新增）**：

Round 1-7: [UNCHANGED — 完全按照原始 prompt]
公司概覽、業務板塊拆解、競爭護城河、管理層與治理、
增長動力、風險與挑戰、行業結構與價值鏈。

[SECTOR:v2] Round 8 — 行業特定深度搜索：
根據 /registry/sector_config 中的 primary_sector 執行對應搜索：

IF banking:
  "[公司名稱] CET1 ratio capital adequacy NIM net interest margin latest quarter"
  "[公司名稱] loan portfolio quality NPL non-performing loans provision coverage"
  "[市場區域] banking sector outlook 2026 regulatory environment"
  
IF insurance:
  "[公司名稱] combined ratio loss ratio expense ratio underwriting performance"
  "[公司名稱] float investment yield embedded value" [if life: "VNB value new business"]
  "[市場區域] insurance sector pricing cycle outlook 2026"
  
IF growth:
  "[公司名稱] ARR annual recurring revenue net revenue retention NRR"
  "[公司名稱] unit economics CAC LTV burn multiple path to profitability"
  "[行業] SaaS metrics benchmark 2025 2026 rule of 40"
  
IF reit:
  "[公司名稱] NAV net asset value cap rate same-store NOI growth"
  "[公司名稱] FFO AFFO funds from operations per share occupancy"
  "[市場區域] REIT sector cap rate trends 2026 property type outlook"
  
IF utility:
  "[公司名稱] rate base allowed ROE regulatory lag rate case"
  "[公司名稱] capex program rate base growth customer count SAIDI"
  "[市場區域] utility regulatory environment outlook 2026 allowed ROE trends"
  
IF cyclical:
  "[公司名稱] AISC all-in sustaining cash cost cost curve position"
  "[公司名稱] FCF breakeven commodity price reserve life"
  "[Commodity] price forecast long-run incentive price 2026 2027"

IF standard:
  Round 8 = 跳過（無需行業特定搜索）

[SECTOR:v2] 護城河評估指標替換：
原始: "護城河評估必須包含 ROIC（投入資本回報率）分析"
替換為: 使用 /registry/sector_config 中的 roic_equivalent 指標
  - banking: ROE analysis
  - insurance: Combined Ratio consistency (P&C) or VNB margin (Life)
  - growth: Net Revenue Retention + Gross Margin sustainability
  - reit: Occupancy stability + WALT (lease term)
  - utility: Regulatory compact quality + Allowed vs Earned ROE spread
  - cyclical: Cost curve position (quartile ranking)
  - standard: ROIC (unchanged)

=== 輸出（Registry /phase0/background）===
[UNCHANGED — 完全按照原始 prompt 的 JSON schema]
ADDITIONALLY:
{
  "sector_classification": {
    "primary_sector": "banking|insurance|growth|reit|utility|cyclical|standard",
    "confidence": 0.85,
    "is_also_growth": false
  },
  "sector_specific_findings": {
    // Round 8 搜索結果存於此處
  }
}
```

### [Kimi CLI 執行方式] Phase 0 — AgentSwarm (explore)

Use `AgentSwarm` with `subagent_type="explore"`. Each item is one research round.

```markdown
Use AgentSwarm with subagent_type "explore" and prompt_template:
"You are a background-research subagent for [TICKER] in /workspace-stock-research.
Read registry/sector_config.json, then execute ONLY this research round: {{item}}.
Use WebSearch/FetchURL. Return structured findings with source URLs."

items:
- "Round 1: company overview"
- "Round 2: competitive moat"
- "Round 3: management and governance"
- "Round 4: growth drivers"
- "Round 5: risks and challenges"
- "Round 6: industry structure and value chain"
- "Round 7: regional macro and benchmark context"
- "Round 8: sector-specific deep dive (use sector_config.primary_sector)"
```

Main agent aggregates the swarm output and writes `registry/background.json`.

=== Phase 0 降級模式 ===
[UNCHANGED — 完全按照原始 prompt]

---

## Phase 1 — 區域化數據收集（3 代理平行）

### 代理 1：區域化網頁搜索代理 [SECTOR:v2 — ADD Round 6 sector-specific queries]

```
=== INPUT ===
[UNCHANGED]

=== 任務 ===
執行 5 輪搜索（Round 1-5: UNCHANGED）+ **1 輪行業特定搜索（v2 新增 Round 6）**：

Round 1: 基本面與區域宏觀 [UNCHANGED]
Round 2: 估值與競爭 [UNCHANGED]
Round 3: 深度議題（價值陷阱） [UNCHANGED]
Round 4: 技術面與入場時機 [UNCHANGED]
Round 5: 前瞻性情境與催化劑 [UNCHANGED]

[SECTOR:v2] Round 6 — 行業特定估值與風險搜索：

IF banking:
  "[市場區域] banking sector valuation P/B multiple 2026 regional comparison"
  "[市場區域] banking regulatory capital requirements Basel III IV outlook"
  "[公司名稱] credit quality loan loss provision trend coverage ratio"
  "[市場區域] banking NIM pressure interest rate sensitivity"
  "[公司名稱] deposit franchise funding cost competitive position"
  
IF insurance:
  "[市場區域] insurance sector valuation P/B combined ratio benchmark"
  "[公司名稱] reserve adequacy development history favorable unfavorable"
  "[市場區域] insurance pricing cycle hard market soft market 2026"
  "[公司名稱] investment portfolio yield duration ALM strategy"
  "[市場區域] catastrophe risk modeling cat bond pricing"
  
IF growth:
  "[市場區域] SaaS valuation benchmark EV/Revenue ARR multiple 2026"
  "[公司名稱] customer acquisition cost CAC efficiency trend"
  "[市場區域] growth company funding environment VC IPO window"
  "[公司名稱] churn rate net revenue retention benchmark comparison"
  "[市場區域] tech sector SBC stock-based compensation trend dilution"
  
IF reit:
  "[市場區域] REIT valuation cap rate by property type 2026"
  "[公司名稱] lease rollover schedule tenant credit quality"
  "[市場區域] commercial real estate outlook office industrial retail"
  "[公司名稱] debt maturity refinancing risk interest rate sensitivity"
  "[市場區域] REIT same-store NOI growth benchmark"
  
IF utility:
  "[市場區域] utility allowed ROE rate case outcome 2025 2026"
  "[公司名稱] rate base growth capex program regulatory lag"
  "[市場區域] renewable energy transition grid investment outlook"
  "[公司名稱] wildfire risk California utility liability exposure"
  "[市場區域] utility dividend yield benchmark payout ratio"
  
IF cyclical:
  "[Commodity] price forecast Goldman Sachs Citi long-run price"
  "[公司名稱] cost curve position quartile ranking AISC"
  "[市場區域] cyclical sector inventory days capacity utilization"
  "[公司名稱] FCF breakeven price sensitivity analysis"
  "[Commodity] China demand outlook supply deficit surplus"

區域化加強（依 [市場區域]）： [UNCHANGED]

=== 輸出（Registry /phase1/search）===
[UNCHANGED — 完全按照原始 prompt 的 JSON schema]
```

### 代理 2：區域化財務 API 代理 [SECTOR:v2 — Substitute metrics, add sector-specific calculations]

```
=== INPUT ===
[UNCHANGED]

=== 任務 ===

Steps 1a-1g: [UNCHANGED — 完全按照原始 prompt]
  get_historical_stock_prices, get_stock_info, get_financial_statement,
  get_recommendations, get_holder_info, get_stock_actions, get_ipo_info

Step 9: ROIC 計算 [SECTOR:v2 — 有條件替換]

IF primary_sector == "standard":
  執行原始 ROIC 計算（UNCHANGED）
  ROIC = NOPAT / Invested Capital
  
ELIF primary_sector == "banking":
  計算 ROE（替代 ROIC）：
  ROE = Net Income / Average Shareholders' Equity
  計算 RAROC（風險調整資本回報率）：
  RAROC = Risk-Adjusted Return / Economic Capital
  計算 CET1 Ratio：
  CET1 = Common Equity Tier 1 / Risk-Weighted Assets
  計算 NIM：
  NIM = Net Interest Income / Average Earning Assets
  
  輸出:
  {
    "roe_analysis": {
      "historical_roe": [{year, roe_pct, net_income, equity}],
      "latest_roe": 0, "5y_avg_roe": 0, "trend": "rising|stable|declining",
      "vs_cost_of_equity": {"spread": 0, "assessment": "value_creating|destroying"},
      "vs_peers_median": 0
    },
    "cet1_analysis": {
      "latest_cet1": 0, "minimum_requirement": 0, "headroom": 0,
      "vs_peers_median": 0, "assessment": "strong|adequate|weak"
    },
    "nim_analysis": {
      "historical_nim": [], "latest_nim": 0, "trend": "",
      "vs_peers_median": 0, "interest_rate_sensitivity": ""
    },
    "raroc_analysis": { ... }
  }

ELIF primary_sector == "insurance":
  IF P&C:
    計算 Combined Ratio：
    CR = Loss Ratio + Expense Ratio = (Claims / Premiums) + (OpEx / Premiums)
    計算 Float：
    Float = Loss Reserves + Unearned Premium Reserve - Receivables
    計算 Investment Yield on Float：
    Inv Yield = Investment Income / Average Float
    計算 Reserve Development：
    Reserve Dev = (Current Estimate of Prior Reserves - Original Reserve) / Original
    
  IF Life:
    計算 ROEV（Return on Embedded Value）
    提取 VNB（Value of New Business）from disclosures
    計算 VNB Margin = VNB / APE
    
ELIF primary_sector == "growth":
  執行原始 ROIC 計算（如果數據許可）
  ADDITIONALLY 計算：
  - ARR（Annual Recurring Revenue）—— from company disclosures
  - Net Revenue Retention (NRR)
  - CAC（Customer Acquisition Cost）= Sales & Marketing / New Customers
  - LTV（Lifetime Value）= ARPU x Gross Margin x (1/Churn Rate)
  - LTV/CAC Ratio
  - Rule of 40 = Revenue Growth% + FCF Margin%
  - Burn Multiple = Net Burn / Net New ARR
  
ELIF primary_sector == "reit":
  計算 FFO：
  FFO = Net Income + Depreciation & Amortization - Gains on Property Sales
  計算 AFFO：
  AFFO = FFO - Recurring CapEx - Leasing Commissions - Straight-line Rent Adjustments
  計算 NOI：
  NOI = Rental Revenue - Operating Expenses (excl. D&A, interest)
  計算 FFO Yield = FFO / Market Cap
  計算 AFFO Payout Ratio = Dividends / AFFO
  
ELIF primary_sector == "utility":
  搜索並記錄：
  - Rate Base（from regulatory filings / company disclosures）
  - Allowed ROE（from latest rate case）
  - Earned ROE = Net Income / Average Equity
  - Regulatory Lag = Allowed ROE - Earned ROE
  - Customer Count and CAGR
  - SAIDI / SAIFI（可靠性指標）
  
ELIF primary_sector == "cyclical":
  計算或搜索：
  - AISC（All-In Sustaining Cost）或 Cash Cost
  - Cost Curve Position（quartile）
  - FCF Breakeven Price
  - Reserve Life = Reserves / Annual Production
  - Operating Leverage = %ΔEBIT / %ΔRevenue
  - FCF Conversion Rate = FCF / EBITDA

Step 10: SBC 分析 [SECTOR:v2 — 強度按行業調整]

IF primary_sector IN ["banking", "insurance", "utility", "cyclical"]:
  SBC 分析強度 = LOW
  執行簡化版：SBC/Revenue ratio + trend only
  
ELIF primary_sector IN ["reit", "standard"]:
  SBC 分析強度 = MEDIUM
  執行標準版（原始 prompt）
  
ELIF primary_sector == "growth" OR is_also_growth == true:
  SBC 分析強度 = **CRITICAL**
  執行增強版：
  - SBC/Revenue（必須計算）
  - SBC/報告FCF（必須計算）
  - SBC-調整後 FCF（必須計算 — DCF 使用此值）
  - 年度股權稀釋率 = SBC / 市值（必須計算）
  - 累計稀釋率 = ∏(1 + dᵢ) - 1（必須複利連乘）
  - SBC-Adjusted TSR = 傳統 TSR - 累計稀釋率
  - **評估**: SBC/Revenue > 15% = severe hidden cost
  
Step 11: WACC 計算 [SECTOR:v2 — 銀行保險需特殊處理]

IF banking:
  - Cost of equity 使用 CAPM（標準）
  - **Debt cost 使用存款成本 + 批發融資成本加權**（非債券 YTM）
  - **Country Risk Premium 已內含於監管資本要求**
  - WACC 較少用於估值（Excess Return Model 使用 Cost of Equity）

IF insurance:
  - Cost of equity 使用 CAPM
  - **無風險利率需匹配負債久期**（長期國債，非 10Y）
  - WACC 較少用於估值（DDM/EV 模型為主）

IF other:
  [UNCHANGED — 標準 WACC 計算]

=== 輸出（Registry /phase1/api）===
[UNCHANGED schema，但 sector-specific 字段添加到對應分析對象中]
```

### 代理 3：區域化新聞與情緒代理
```
[UNCHANGED — 完全按照原始 prompt，無需修改]
```

### [Kimi CLI 執行方式] Phase 1 — 平行 Agent (coder)

Run Agents 1, 2, and 3 in parallel in the same assistant step.

```markdown
# Agent 1 — Web search
Use Agent with subagent_type "coder", prompt:
"You are Agent 1 for [TICKER]. Read registry/sector_config.json.
Execute the web-search rounds in prompt_adaptive_v2.md Agent 1
(5 base rounds + Round 6 sector-specific). Use WebSearch/FetchURL.
Write registry/web_search.json. Cite sources."

# Agent 2 — Financial API + latest quarter
Use Agent with subagent_type "coder", prompt:
"You are Agent 2 for [TICKER]. Read registry/sector_config.json.
Call yfinance MCP tools (info, financials, holders, estimates, etc.).
Apply sector-specific metric substitutions and SBC intensity.
Call get_latest_quarter_snapshot. Extract guidance, segment KPIs,
margins, balance sheet, cash flow, capital returns, tone, and risks.
Apply override rules from AGENTS.md Section 6.4 and log each override.
Write registry/latest_quarter.json and data/financials.csv."

# Agent 3 — News & sentiment
Use Agent with subagent_type "coder", prompt:
"You are Agent 3 for [TICKER]. Call yfinance MCP get_ticker_news,
search_news, and sec-edgar MCP get_latest_earnings_release.
Summarize sentiment, narratives, catalysts, and any gap/volume events.
Write registry/news_sentiment.json."
```

### Phase 1 聚合檢查點
```
[UNCHANGED — 完全按照原始 prompt]
ADD：[ ] /registry/sector_config 已寫入且所有後續 Agent 可讀取
```

---

## Phase 1.5 — TSR驗證【已併入Phase 2並行執行】

### 代理 12：TSR 驗證代理 [SECTOR:v2 — 調整基準指數，SBC強度]

```
=== INPUT ===
[UNCHANGED]

=== 任務 ===
[基本 UNCHANGED，但以下修改：]

1. 總股東回報（TSR）計算： [UNCHANGED]

2. 基準比較： [SECTOR:v2 — 行業特定基準]
   - vs [區域基準指數] 同期回報 [UNCHANGED]
   - **ADD: vs [行業特定基準指數]**
     - banking: KBW Bank Index (US), EURO STOXX Banks (EU)
     - insurance: S&P Insurance Select Industry Index
     - growth: Russell 2000 Growth / Nasdaq 100 (if tech)
     - reit: FTSE NAREIT All REITs / EPRA/NAREIT Global
     - utility: S&P 500 Utilities / DJ Utilities
     - cyclical: [Commodity] index or S&P Global Natural Resources
     - standard: [區域基準指數] (unchanged)
   - vs [市場區域] [行業] 同行中位數 [UNCHANGED]
   - vs 無風險利率累計回報 [UNCHANGED]

3. 融資 vs 分紅淨現金流： [UNCHANGED]

4. SBC-調整 TSR： [SECTOR:v2 — 強度按行業調整]
   
   IF primary_sector == "growth" OR is_also_growth == true:
     **必須計算 SBC-調整 TSR**（強制，非可選）
     累計稀釋率 = ∏(1 + SBCᵢ/市值ᵢ) - 1
     SBC-調整 TSR = 傳統 TSR - 累計稀釋率
     若 SBC-調整 TSR < 0 但傳統 TSR > 0：標記「SBC 嚴重稀釋真實回報」
   
   IF primary_sector IN ["banking", "insurance", "utility", "cyclical", "reit"]:
     SBC-調整 TSR = 可選（如 SBC/Revenue < 3% 可跳過）
     簡化計算：年度稀釋率加總法（非複利）
   
   IF primary_sector == "standard":
     按原始 prompt 執行（UNCHANGED）

5. 價值陷阱紅旗檢查： [UNCHANGED]
   ADD sector-specific red flags:
   - banking: CET1 declining for 2+ years
   - insurance: Combined Ratio > 105% for 2+ years (P&C)
   - growth: Burn Multiple > 3x and declining runway
   - reit: AFFO payout > 100% for 2+ years
   - utility: Regulatory lag widening for 3+ years
   - cyclical: FCF negative at mid-cycle commodity price

=== 輸出（Registry /phase2/tsr）===
[UNCHANGED schema]
```

---

## Phase 2 — 區域化計算與建模（3 代理並行）【P1-5：Agent 12併入】

### 代理 4：技術指標計算代理（純技術分析）
```
[UNCHANGED — 完全按照原始 prompt]
技術分析是行業無關的。此 Agent 不受 sector detection 影響。
所有計算、所有禁止讀取的數據、所有輸出格式 — 完全保持不變。
```

### 代理 5：區域化估值建模代理（含結構性折價調整） [SECTOR:v2 — COMPLETE MODEL SWAP]

```
=== INPUT ===
[UNCHANGED]
ADDITIONALLY:
- /registry/sector_config — sector classification and substitutions
- /workspace-stock-research/sector_XXX.md — detailed sector module (loaded FIRST)

=== PRE-EXECUTION STEP ===
此 Agent 必須：
1. 讀取 /registry/sector_config
2. 載入對應的 sector module file
3. 理解該行業的估值模型、指標、風險因素
4. 將所有後續計算替換為行業特定版本

=== 任務 ===

【任務 0：風險量化橋接 — 定性風險→估值參數映射】 [SECTOR:v2]

風險橋接矩陣的 DCF 參數欄需按行業替換：

| 風險類別 | 具體風險 | 受影響參數 | ... |
|---------|---------|-----------|-----|

banking:
  受影響參數 = ROE, NIM, CET1, Provision Ratio, Cost of Equity
insurance:
  受影響參數 = Combined Ratio, Investment Yield, Reserve Adequacy, Float Growth
growth:
  受影響參數 = Revenue Growth, Gross Margin, OpEx Ratio, SBC/Revenue, Churn
reit:
  受影響參數 = Cap Rate, Occupancy, Lease Spreads, Financing Cost
utility:
  受影響參數 = Allowed ROE, Rate Base Growth, Regulatory Lag, O&M Costs
cyclical:
  受影響參數 = Commodity Price, Volume, Cost Inflation, Utilization

橋接矩陣的其餘結構（衝擊幅度、概率、時間框架）不變。

---

【任務 1：行業特定估值模型（取代可變利潤率 DCF）】 [SECTOR:v2 — 核心替換]

═══════════════════════════════════════════════════════
IF primary_sector == "banking":
═══════════════════════════════════════════════════════

[Step 1a: Excess Return Model — 超額回報模型]

核心公式:
  Intrinsic Value = Book Value + (ROE - k) x Book Value / (k - g)
  
  其中:
  - Book Value = Tangible Common Equity ( tangible book value preferred )
  - ROE = Expected sustainable Return on Equity
  - k = Cost of Equity (from WACC calculation)
  - g = Sustainable growth rate (ROE x retention ratio)

三情景計算:
  Bear: ROE = historical low, k = k + 1%, g = g - 1pp
  Base: ROE = 5-year average, k = k, g = g
  Bull: ROE = historical high, k = k - 0.5%, g = g + 1pp

[Step 1b: P/B-ROE Regression — P/B-ROE 回歸驗證]

收集同行 P/B 和 ROE 數據，回歸:
  P/B = α + β x ROE + ε
  
目標公司的「合理 P/B」= α + β x (目標公司 ROE)
若實際 P/B < 合理 P/B x 0.8 → 可能被低估

[Step 1c: SBC-調整（銀行業 SBC 通常低，但仍需檢查）]
IF SBC/Revenue > 3%:
  計算 SBC-調整後盈利 = 報告盈利 - SBC
  重新計算 ROE 使用 SBC-調整後盈利

═══════════════════════════════════════════════════════
IF primary_sector == "insurance" (P&C):
═══════════════════════════════════════════════════════

[Step 1a: Float Valuation + Combined Ratio Analysis]

Float 計算:
  Float = Loss Reserves + Unearned Premium Reserve - Premium Receivables - Agents' Balances

Float 價值:
  - 若 Combined Ratio < 100% (underwriting profit): Float 的「成本」為負 → 有價值
  - 若 Combined Ratio = 100%: Float 成本為零 → 免費資金
  - 若 Combined Ratio > 100%: Float 成本為正 → 昂貴資金

估值公式:
  Value = Book Value + Float x (Investment Yield - Cost of Float) / (k - g_float)
  
  Cost of Float = (Combined Ratio - 100%) x Premiums / Float

三情景:
  Bear: CR = 105%, Inv Yield = 3%, k = k + 1%
  Base: CR = historical avg, Inv Yield = 4%, k = k
  Bull: CR = 95%, Inv Yield = 5%, k = k - 0.5%

[Step 1b: Reserve Adequacy Adjustment]

評估 reserve development history:
  - 10年累計 favorable development → reserve buffer exists
  - 10年累計 unfavorable development → reserve deficiency risk
  
若存在 deficiency risk: 從 Book Value 扣除 estimated deficiency

═══════════════════════════════════════════════════════
IF primary_sector == "insurance" (Life):
═══════════════════════════════════════════════════════

[Step 1a: Embedded Value (EV) Approach]

EV = Adjusted Net Asset Value (ANAV) + Value of In-Force (VIF)

若公司披露 EV: 直接使用
若未披露: 估算:
  - ANAV = Market Value of Assets - Liabilities (market-consistent)
  - VIF ≈ PV of future profits from in-force business

估值:
  Value = EV x (1 + VNB growth premium)
  P/EV multiple comparison to peers

[Step 1b: VNB Margin Analysis]

VNB Margin = VNB / APE (Annual Premium Equivalent)
> 40% = excellent, 30-40% = good, 20-30% = average, < 20% = weak

═══════════════════════════════════════════════════════
IF primary_sector == "growth":
═══════════════════════════════════════════════════════

[Step 1a: Extended DCF — 擴展現金流折現（7-10年顯性預測）]

標準 DCF 的問題：負 FCF 無法折現
解決方案：延長顯性預測期直到公司達到盈利平衡點

預測結構:
  Year 1-3: Revenue growth (based on ARR growth, NRR)
            → Gross Margin (SaaS: 70-80% typical)
            → OpEx as % of Revenue (declining due to operating leverage)
            → EBITDA → FCF (still negative likely)
  Year 4-7: Revenue growth deceleration (natural)
            → Gross Margin stable or improving
            → OpEx leverage kicks in (revenue grows faster than fixed costs)
            → EBITDA positive → FCF approaching breakeven
  Year 7-10: Revenue growth maturing to industry average
            → Steady-state margins achieved
            → FCF positive → Terminal value applicable

Terminal Value: ONLY applied once FCF is sustainably positive
  Terminal Value = FCF_terminal x (1 + g) / (WACC - g)

[Step 1b: EV/Revenue Sanity Check]

同行 EV/Revenue 中位數 x 目標公司 Revenue = 備選估值
若與 Extended DCF 差異 > 50%: 標記並檢查假設

EV/Revenue 調整因素:
  - Revenue growth rate (+/-)
  - Gross margin (+/-)
  - NRR (>120% = premium, <100% = discount)
  - Rule of 40 score (+/-)

[Step 1c: Unit Economics Quality Gate]

計算並檢查:
  - LTV/CAC > 3? → Unit economics healthy
  - CAC Payback < 12 months? → Efficient growth
  - Magic Number > 0.75? → Sales efficiency good
  - Net Revenue Retention > 110%? → Expansion revenue exists
  
若任何一項不通過: 在估值中增加 risk premium (+1-2pp WACC)

[Step 1d: SBC-Adjusted FCF（強制）]

Extended DCF 使用 **SBC-調整後 FCF**:
  SBC-Adjusted FCF = Reported FCF - SBC
  
SBC 預測:
  - 假設 SBC/Revenue 維持在歷史平均水平
  - 不允許假設 SBC「自然下降」（除非公司有明確承諾）
  - Growth 公司 SBC 是結構性成本，非臨時性

═══════════════════════════════════════════════════════
IF primary_sector == "reit":
═══════════════════════════════════════════════════════

[Step 1a: NAV Model — 淨資產值模型]

NAV = Total Property Value - Total Debt - Preferred Equity + Cash

Property Value 計算方法（按優先順序）:
  1. 公司披露 NAV（若可用且可信）
  2. NOI / Cap Rate（公司整體）
  3. 物業-by-物業估值加總
  
Cap Rate 確定:
  - 參考近期交易（comparable sales）
  - 參考公司指引
  - 參考市場報告（CBRE, JLL, Green Street）

三情景:
  Bear: Cap Rate + 75bp from current
  Base: Current cap rate
  Bull: Cap Rate - 50bp from current

[Step 1b: FFO/AFFO Multiple]

FFO = Net Income + D&A - Gains on Sales
AFFO = FFO - Recurring CapEx - Leasing Commissions - Straight-line Rent Adj.

估值:
  Value per share = AFFO per share x Sector P/AFFO Multiple

Sector multiple 來源:
  - 同行中位數 P/AFFO
  - 歷史區間
  - 增長調整（same-store NOI growth premium/discount）

[Step 1c: Dividend Sustainability Check]

AFFO Payout Ratio = Dividends / AFFO
  - < 75%: Highly sustainable, room to grow dividend
  - 75-85%: Sustainable, but limited growth
  - 85-95%: Tight, vulnerable to occupancy/NOI decline
  - > 100%: UNSUSTAINABLE — dividend at risk

═══════════════════════════════════════════════════════
IF primary_sector == "utility":
═══════════════════════════════════════════════════════

[Step 1a: Rate-Base DCF — 監管資產基礎折現]

核心公式:
  Allowed Earnings = Rate Base x Allowed ROE
  
  Value = DCF of Allowed Earnings stream
        = Σ [Rate Base_t x Allowed ROE x (1 - Payout)] / (1 + k)^t
          + Terminal Value

Rate Base Growth:
  Rate Base_t = Rate Base_0 x (1 + g_rb)^t
  g_rb = 監管批准的資本支出計劃 → rate base 增長

Terminal Value:
  TV = (Rate Base_terminal x Allowed ROE x Payout) / (k - g_dividend)
  g_dividend = Rate Base CAGR x Allowed ROE x Retention Ratio

三情景:
  Bear: Allowed ROE - 100bp, Rate Base growth - 2pp
  Base: Current Allowed ROE, Current Rate Base growth
  Bull: Allowed ROE + 50bp, Rate Base growth + 2pp

[Step 1b: Regulatory Lag Adjustment]

Earned ROE vs Allowed ROE gap:
  - Gap > 100bp consistently: management/regulator relationship poor → discount
  - Gap < 50bp: well-managed → premium
  
調整估值:
  Adjusted Value = Base Value x (1 - Regulatory Lag Penalty)
  Penalty = gap / Allowed ROE (e.g., 1.0pp gap / 10.0% ROE = 10% penalty)

[Step 1c: DDM Cross-Check]

D1 = Current Dividend x (1 + g)
g = Expected dividend growth = Rate Base CAGR x Allowed ROE x Retention
k = Cost of Equity

Value = D1 / (k - g)

═══════════════════════════════════════════════════════
IF primary_sector == "cyclical":
═══════════════════════════════════════════════════════

[Step 1a: Through-the-Cycle (TTC) Earnings]

計算 Mid-Cycle EBIT:
  Method A: 10-year average EBIT
  Method B: Current Volume x (Long-run Commodity Price - Normalized Unit Cost)
  Method C: 產量 x (mid-cycle margin based on cost curve position)

估值:
  Value = Mid-Cycle EBIT x Normalized EV/EBITDA Multiple
  
  Normalized Multiple = 同行 TTC median（非當前 point-in-time）

三情景:
  Bear: Mid-Cycle EBIT - 20% (lower volume assumption)
  Base: Mid-Cycle EBIT
  Bull: Mid-Cycle EBIT + 15% (higher volume + margin)

[Step 1b: NAV at Long-Run Commodity Price]

NAV = Reserves x Long-run Price x Recovery Rate - Operating Costs - Capex - Debt

Long-run Price 確定:
  - Analyst consensus long-run forecast (Goldman, Citi, Wood Mackenzie)
  - Incentive price for new supply
  - 90th percentile cost curve position

三情景:
  Bear: Long-run price - 20%
  Base: Consensus long-run price
  Bull: Long-run price + 10%

[Step 1c: Replacement Cost Check]

Replacement Value = Cost to rebuild equivalent assets

若 市值 < Replacement Value x 0.7:
  → 可能低估（資產比股票便宜）
  → 但需檢查：為什麼沒有併購發生？（可能有隱藏問題）

═══════════════════════════════════════════════════════
IF primary_sector == "standard":
═══════════════════════════════════════════════════════

[完全按照原始 prompt 執行 — 可變利潤率 DCF + SBC 調整]

---

【任務 2：結構性折價調整】 [UNCHANGED — 完全按照原始 prompt]

---

【任務 3：反向工程分析】 [SECTOR:v2 — 反向目標按行業調整]

反向工程目標按 /registry/sector_config.reverse_engineering_target:

banking: 從 P/B 反推隱含 ROE
  Implied ROE = (P/B - 1) x (k - g) + k
  
insurance P&C: 從 P/B 反推隱含 Combined Ratio
  需迭代求解：給定 P/B → 什麼 CR 使 Float 估值匹配？
  
insurance Life: 從 P/EV 反推隱含 VNB 增長
  Implied VNB Growth = (P/EV - 1) x (k - g_vnb)

growth: 從 EV/Revenue 反推隱含收入增長
  Implied Revenue CAGR = solve for g where EV/Revenue = f(g, margin, WACC)
  
reit: 從 Price/NAV 反推隱含 cap rate
  Implied Cap Rate = Cap Rate_market x (1 / (Price/NAV))
  
utility: 從 Div Yield 反推隱含 Rate Base 增長
  Implied g = k - (D1 / Price)
  
cyclical: 從股價反推隱含商品價格
  Implied Commodity Price = solve for P where NAV(P) = Market Cap
  
standard: 從 P/E 反推隱含增長 [UNCHANGED]

---

【任務 4-6：同行比較、十年估值、價值信號】 [SECTOR:v2 — 指標替換]

同行比較使用 /registry/sector_config.peer_comparison_metrics

價值信號中的指標按 sector substitution 替換

=== 輸出（Registry /phase2/valuation）===
[UNCHANGED JSON schema]
ADD: "sector_model_used": "excess_return|float|mcev|extended_dcf|nav|rate_base_dcf|ttc_earnings|standard_dcf"
```

### [Kimi CLI 執行方式] Phase 2 — 平行 Agent (coder) for Agents 4, 5, 12

```markdown
# Agent 4 — Technical analysis
Use Agent with subagent_type "coder", prompt:
"You are Agent 4 for [TICKER]. Pure technical analysis only.
Call yfinance MCP get_price_history. Compute MAs, RSI, MACD, Bollinger,
ATR, volume profile, support/resistance, drawdown, relative strength.
Write data/technical_indicators.json and data/price_history.csv."

# Agent 5 — Valuation modeling
Use Agent with subagent_type "coder", prompt:
"You are Agent 5 for [TICKER]. Read registry/sector_config.json and the
matching sector module in /workspace-stock-research/.
Read registry/latest_quarter.json and data/financials.csv.
Call yfinance MCP compute_valuation_model(ticker=[TICKER], sector=<primary>, scenario=base/bull/bear).
Build sector-specific model, reverse engineering, structural discount,
peer comparison, and value signals. Write data/valuation_model.json
and registry/risk_bridge.json."

# Agent 12 — TSR validation
Use Agent with subagent_type "coder", prompt:
"You are Agent 12 for [TICKER]. Read registry/sector_config.json.
Compute TSR over 1/3/5/10 years, compare vs regional and sector-specific
benchmarks, and compute SBC-adjusted TSR per sector_config intensity.
Add sector-specific value-trap red flags. Write data/tsr_validation.json."
```

Agents 4, 5, and 12 run in parallel.

---

## Phase 2.5 — 壓力測試與尾部風險評估（1 代理）

### 代理 13：壓力測試代理 [SECTOR:v2 — 場景從行業庫中選擇]

```
=== 執行時機 ===
在Phase 2完成後、Phase 3之前執行。可與Phase 3並行。

=== INPUT ===
[UNCHANGED]
ADD: /registry/sector_config — for scenario selection

=== 任務 ===

【任務 1：選擇壓力情景】 [SECTOR:v2 — 從行業庫選擇]

根據 /registry/sector_config.stress_test_scenarios 選擇 4 個情景。

參照【v2 ADDITION】SECTOR-SPECIFIC STRESS TEST SCENARIO LIBRARY 表格。

選擇邏輯:
- 必做：選擇與公司最相關的 3 個行業特定情景
- 選做：增加 1 個通用宏觀情景（如全球衰退）
- 每個情景必須說明選擇理由

【任務 2-4：量化壓力衝擊、生存指標、壓力測試報告】
[UNCHANGED — 完全按照原始 prompt 的計算框架]

壓力衝擊的參數使用行業特定值（見 scenario library）。

=== 輸出（Registry /phase2_5/stress_test）===
[UNCHANGED JSON schema]
```

### [Kimi CLI 執行方式] Phase 2.5 — AgentSwarm (coder) for stress scenarios

```markdown
Use AgentSwarm with subagent_type "coder" and prompt_template:
"You are a stress-test subagent for [TICKER]. Read registry/sector_config.json
and registry/risk_bridge.json. Execute ONLY this stress scenario: {{item}}.
Quantify the impact on sector-specific valuation parameters, estimate survival
metrics (liquidity, leverage, covenant headroom), and assign a probability.
Return structured JSON; do not write files."

items (derive exact text from sector_config.stress_test_scenarios):
- "Scenario A: sector-specific shock 1"
- "Scenario B: sector-specific shock 2"
- "Scenario C: sector-specific shock 3"
- "Scenario D: macro shock (e.g. global recession)"
```

Main agent merges swarm output into `registry/risk_bridge.json`.
Phase 2.5 can run in parallel with Phase 3.

---

## Phase 3 — 圖表生成（11 張）

### 代理 6：區域化圖表生成代理 [SECTOR:v2 — 圖表標註按行業調整]

```
=== INPUT ===
[UNCHANGED]

=== 11 張圖表 ===

圖表 1-11 的數據結構和計算邏輯 [UNCHANGED]

[SECTOR:v2] 以下圖表的標題/標註/註釋需按行業調整：

圖表 2 peer_comparison.png:
  - Y軸標籤: 使用行業特定指標名稱（P/B 而非 P/E 對於銀行等）
  
圖表 3 dcf_analysis.png:
  - 標題註釋: 標註使用的估值模型名稱（如 "Excess Return Model" 而非 "DCF"）
  
圖表 7 forward_valuation_quality.png:
  - 雷達圖維度: 使用行業特定質量維度
    - banking: ROE consistency, NPL trend, NIM stability, CET1, Deposit franchise, Regulatory
    - insurance: CR stability, Reserve adequacy, Inv yield, Float growth, VNB margin, Solvency
    - growth: NRR, Gross margin, Rule of 40, Burn multiple, CAC efficiency, TAM penetration
    - reit: Occupancy, WALT, Lease spreads, Cap rate, LTV, Same-store NOI
    - utility: Allowed ROE, Regulatory lag, Rate base growth, Reliability, ESG score, Affordability
    - cyclical: Cost curve position, FCF breakeven, Balance sheet, Reserve life, Utilization, Capital discipline
    - standard: [UNCHANGED]

圖表 10 variable_margin.png:
  - 對於 banking: 改為 NIM-Asset Sensitivity 圖
  - 對於 insurance: 改為 CR-Premium Growth 敏感度
  - 對於 growth: 改為 OpEx Leverage 圖（收入增長→營業利潤率）
  - 對於 reit: 改為 NOI- occupancy 敏感度
  - 對於 utility: 改為 Allowed ROE-Earned ROE 圖
  - 對於 cyclical: 改為 EBIT-Commodity Price 敏感度
  - 對於 standard: [UNCHANGED]

圖表 11 reverse_engineering.png:
  - 雷達圖維度: 使用行業特定反向工程參數
    - banking: 隱含ROE, 隱含NIM, 隱含CET1, 隱含增長
    - insurance: 隱含CR, 隱含投資收益, 隱含VNB增長
    - growth: 隱含收入增長, 隱含毛利率, 隱含FCF轉化率, 隱含WACC
    - reit: 隱含cap rate, 隱含occupancy, 隱含融資成本
    - utility: 隱含allowed ROE, 隱含rate base增長
    - cyclical: 隱含商品價格, 隱含成本, 隱含產量
    - standard: [UNCHANGED]

=== 輸出（Registry /phase3/charts）===
[UNCHANGED]
```

### [Kimi CLI 執行方式] Phase 3 — Charts

Option A — direct tool call (fastest):

```markdown
Call yfinance MCP generate_charts with ticker "[TICKER]" and
output_dir "/workspace-stock-research/[TICKER]/[YYYY-MM-DD]/charts".
```

Option B — subagent for sector-adapted charts:

```markdown
Use Agent with subagent_type "coder" and run_in_background true, prompt:
"You are Agent 6 for [TICKER]. Read registry/sector_config.json,
data/valuation_model.json, data/technical_indicators.json, and data/peer_snapshot.csv.
Generate all required charts with sector-adapted labels and save to
/workspace-stock-research/[TICKER]/[YYYY-MM-DD]/charts/. Use descriptive filenames.
Return the list of files created."
```

---

## Phase 4 — 報告撰寫（3+1 代理平行）

### 代理 7：基本面+估值+前瞻質量+背景 合併報告代理 [SECTOR:v2 — 章節內容按行業調整]

```
=== INPUT ===
[UNCHANGED]

=== 輸出：01_[ticker]_fundamental.md ===

報告結構保持不變（18個章節），但以下章節的內容按行業替換：

## 4. ROIC 分析 → [SECTOR EQUIVALENT] 分析 [SECTOR:v2]
標題替換為行業等效指標名稱：
  - banking: "ROE 分析 — 這家銀行是否在創造超額回報？"
  - insurance P&C: "Combined Ratio 分析 — 這家保險公司的承保是否賺錢？"
  - insurance Life: "ROEV 分析 — 這家壽險的內含價值回報如何？"
  - growth: "Unit Economics 分析 — 這家公司的單位經濟是否健康？"
  - reit: "FFO/AFFO 分析 — 這家 REIT 的真實現金流是多少？"
  - utility: "Regulatory ROE 分析 — 這家公用事業的監管回報如何？"
  - cyclical: "Cost Curve 分析 — 這家公司在成本曲線上的位置？"
  - standard: [UNCHANGED]

表格中的指標全部使用 sector substitution 替換。

## 5. SBC 分析 [SECTOR:v2 — 強度按行業調整]
對於 banking/insurance/utility/cyclical: 簡化為 1-2 段文字
對於 growth: 保持完整分析（可能是報告中最重要的一節）
對於 reit/standard: 標準分析

## 6. 股價與估值快照 [SECTOR:v2]
表格中的指標使用行業等效版本：
  - banking: P/B, ROE, NIM, CET1, NPL ratio, Efficiency ratio
  - insurance: P/B or P/EV, Combined Ratio, Investment yield, Float
  - growth: EV/Revenue, ARR growth, NRR, Gross margin, Rule of 40, Burn multiple
  - reit: Price/NAV, P/FFO, Cap rate, Occupancy, WALT, AFFO payout
  - utility: Div yield, Allowed ROE, Rate base CAGR, Regulatory lag
  - cyclical: TTC EV/EBITDA, AISC, FCF breakeven, Reserve life, Net debt/EBITDA
  - standard: [UNCHANGED]

## 8. 行業結構與價值鏈分析 [UNCHANGED]
## 9. 區域同行比較 [SECTOR:v2 — 使用行業特定指標]
## 11. 估值模型輸出 [SECTOR:v2 — 顯示行業特定模型]
## 12. 反向工程分析 [SECTOR:v2 — 使用行業特定反向目標]
## 13. 價值信號總結 [SECTOR:v2 — 使用行業特定指標和權重]
## 16. 壓力測試 [SECTOR:v2 — 引用行業特定情景]
## 17. 前瞻性估值質量評估 [SECTOR:v2 — 雷達圖維度按行業]
## 18.10 ROIC 速查 → [SECTOR EQUIVALENT] 速查 [SECTOR:v2]
## 18.11 SBC 速查 [SECTOR:v2 — 簡化或強化]

## Q6: 投資類型分類 [SECTOR:v2 — 使用行業特定分類]
使用【v2 ADDITION】中的 Sector-Specific Investment Classification 表格。

禁止聲明 [UNCHANGED]
```

### 代理 8：入場時機報告代理
```
[UNCHANGED — 完全按照原始 prompt]
技術面報告是行業無關的。此 Agent 不受 sector detection 影響。
```

### 代理 11：README 總覽代理 [SECTOR:v2 — 摘要指標按行業]

```
=== INPUT ===
[UNCHANGED]

=== 輸出：00_[ticker]_README.md ===

核心估值指標摘要使用行業等效版本：
  - banking: P/B, ROE, CET1, NIM, Excess Return 估值
  - insurance: P/B or P/EV, CR, Float yield, EV 估值
  - growth: EV/Revenue, ARR, NRR, Rule of 40, Extended DCF 估值
  - reit: Price/NAV, P/FFO, Cap rate, NAV 估值
  - utility: Div Yield, Allowed ROE, Rate Base DCF 估值
  - cyclical: TTC EV/EBITDA, AISC, FCF breakeven, TTC 估值
  - standard: P/E, EV/EBITDA, DCF 估值 [UNCHANGED]

框架說明中增加一行：
"本分析已應用行業自適應框架，檢測為 [行業] 類型，使用 [估值模型] 作為核心估值方法。"

其餘結構 [UNCHANGED]
```

### [Kimi CLI 執行方式] Phase 4 — 平行 Agent (coder) for reports

```markdown
# Agent 7 — Fundamental report
Use Agent with subagent_type "coder", prompt:
"You are Agent 7 for [TICKER]. Read all registry files, data/valuation_model.json,
data/tsr_validation.json, data/financials.csv, registry/risk_bridge.json, and
registry/background.json. Write reports/01_[TICKER]_fundamental.md following the
18-section structure in prompt_adaptive_v2.md Agent 7. Use sector-specific metrics
from sector_config. Address all five analytical lenses and document conflicts.
Cite sources for every number."

# Agent 8 — Technical report
Use Agent with subagent_type "coder", prompt:
"You are Agent 8 for [TICKER]. Read data/technical_indicators.json,
data/price_history.csv, and registry/news_sentiment.json. Write
reports/02_[TICKER]_technical.md with entry/exit/stop-loss levels, ATR-based
position sizing, relative strength, support/resistance, and drawdown.
Do NOT include fundamental valuation."

# Agent 11 — README
Use Agent with subagent_type "coder", prompt:
"You are Agent 11 for [TICKER]. Read registry/sector_config.json,
registry/latest_quarter.json, and the headline sections of the fundamental and
technical reports. Write reports/00_[TICKER]_README.md with sector classification,
confidence, key metrics, latest-quarter headline, valuation summary, verdict, and risks."
```

Agents 7, 8, and 11 run in parallel.

---

## 【v2】AGENT SWARM 執行總圖

```
ORCHESTRATOR START
│
├─> Step 0: Sector Detection (Orchestrator executes)
│   ├─> Run classification algorithm / yfinance MCP classify_sector
│   ├─> Write /workspace-stock-research/<TICKER>/<YYYY-MM-DD>/registry/sector_config.json
│   ├─> Load sector module file from /workspace-stock-research/
│   └─> Determine agent modifications
│
├─> PHASE 0: 公司背景研究 (AgentSwarm explore, 1 round per subagent)
│   └─> Agent 0 [MODIFIED: +Round 8 sector queries, moat metric swap]
│       └─> Aggregate to registry/background.json
│
├─> PHASE 1: 區域化數據收集 (3 Agent coders PARALLEL)
│   ├─> Agent 1: Web Search [MODIFIED: +Round 6 sector queries]
│   │      └─> Write registry/web_search.json
│   ├─> Agent 2: Financial API [MODIFIED: metric substitutions, sector-specific calcs]
│   │      └─> Write registry/latest_quarter.json + data/financials.csv
│   └─> Agent 3: News & Sentiment [UNCHANGED]
│          └─> Write registry/news_sentiment.json
│
├─> PHASE 1 檢查點 [UNCHANGED + sector_config.json check]
│
├─> PHASE 2: 計算與建模 (3 Agent coders PARALLEL)
│   ├─> Agent 4: Technical Analysis [UNCHANGED]
│   │      └─> Write data/technical_indicators.json + data/price_history.csv
│   ├─> Agent 5: Valuation Modeling [HEAVILY MODIFIED: complete model swap]
│   │      └─> Write data/valuation_model.json + registry/risk_bridge.json
│   └─> Agent 12: TSR Validation [MODIFIED: sector benchmarks, SBC intensity]
│          └─> Write data/tsr_validation.json
│
├─> PHASE 2 檢查點 [UNCHANGED]
│
├─> PHASE 2.5: 壓力測試 (AgentSwarm coder, can parallel with Phase 3)
│   └─> Agent 13: Stress Test [MODIFIED: sector scenario selection]
│       └─> Merge into registry/risk_bridge.json
│
├─> PHASE 3: 圖表生成 (direct generate_charts tool OR Agent coder)
│   └─> Agent 6: Charts [MINOR: labels/annotations adapt]
│       └─> Write charts/*.png
│
├─> PHASE 4: 報告撰寫 (3 Agent coders PARALLEL)
│   ├─> Agent 7: Fundamental Report [MODIFIED: sector-aware content]
│   │      └─> Write reports/01_[TICKER]_fundamental.md
│   ├─> Agent 8: Technical Report [UNCHANGED]
│   │      └─> Write reports/02_[TICKER]_technical.md
│   └─> Agent 11: README [MINOR: sector metrics in summary]
│          └─> Write reports/00_[TICKER]_README.md
│
└─> ORCHESTRATOR END: Deliver all files
```

### 修改統計

| 類別 | Agent 數量 | 說明 |
|---|---|---|
| **未修改** | 4 | Agent 1, Agent 3, Agent 4, Agent 8 |
| **輕度修改** | 2 | Agent 6 (標註), Agent 11 (摘要指標) |
| **中度修改** | 3 | Agent 0 (+Round 8), Agent 12 (基準+SBC強度), Agent 13 (場景選擇) |
| **重度修改** | 2 | Agent 2 (指標替換+行業計算), Agent 5 (完整模型替換) |
| **新增** | 0 | Sector detection 在 Orchestrator 層，非獨立 Agent |
| **總計** | 11 agents | 全部保留，無刪減 |

---

## 【v2】關鍵規則重申

1. **技術面完全保留**: Agent 4 和 Agent 8 不受任何行業檢測影響。技術分析使用純價格/成交量數據，與基本面嚴格隔離。

2. **Agent swarm 架構完全保留**: 所有 phase、所有並行執行、所有 registry-based 數據傳遞、所有檢查點 — 完全按照原始 prompt。

3. **Sector detection 是 thin layer**: 只在 Orchestrator 開始時執行一次，寫入 registry，後續 Agent 讀取並調整行為。不增加新的 phase，不增加新的 agent。

4. **Fallback 機制**: 若 sector detection confidence < 70%，自動 fallback 到 standard framework。所有報告中標註檢測信心和使用的模塊。

5. **Dual-flag 支持**: 若 is_also_growth = true（如 fintech bank），使用 primary sector 的估值模型 + growth module 的 SBC 分析。這是「疊加」而非「替換」。

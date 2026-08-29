# Region module: Hong Kong / China (advisory)

**Module file:** `region_hk_china.md`  
**Typical intensity:** `medium` for straightforward HKEX IFRS/HKFRS names; **`high`** for family control, SOE policy priorities, VIE structures, A+H dual listings, or capital-control / convertibility risk.

This file is **advisory methodology**. **Do not** copy reference ranges into the model without a use/reject hook and company-specific rationale. The harness forbids hardcoded regional WACC, ERP tables, or fixed family-control discounts.

## Detection signals

- Listings: HKEX, SSE, SZSE; H-share / red-chip / P-chip; ADR/20-F of China ops; dual A+H
- Currency: HKD, CNY, or USD reporting with CNY economic exposure
- Filings: HKEX annual/interim, SSE/SZSE annual, or SEC 20-F/6-K — set `listing.primary_filing_source` honestly (do not pretend EDGAR if the primary annual is HKEX/CN)
- Ownership headlines: founding family, SASAC/SOE, VIE, pyramid holding companies, acting-in-concert

## Cost of capital

Decide and justify (in valuation assumptions), do not mandate:

| Dial | Questions to answer |
|---|---|
| Risk-free | Local curve (e.g. CGB, HK rates) vs USD model? Must match **cash-flow currency** or state FX policy |
| ERP / country risk | Local market ERP vs USD ERP + country overlay — **pick one stack**, avoid double-counting with FX stress and governance haircuts |
| FX | Forecast in local currency and discount local, or convert FCF to USD — state which; script FX series if used |
| Liquidity / free float | Thin float may widen range; it is not a free "China −X%" haircut |

Snapshot any market series used (Rf, FX, dual-list prices) into `data/*.csv` and compute intermediates in `data/compute/`.

## Accounting regime

Common bases: **HKFRS / IFRS**, **CAS** (China Accounting Standards), sometimes **US GAAP** (ADR). Peer comps break when mixing without adjustment.

Watch especially:

- Related-party revenue and balances (family groups, SOE intra-group)
- Consolidation perimeter and **VIE** primary-beneficiary judgments
- Impairment and FV through P&L volatility under IFRS
- Associate / JV equity-method earnings vs cash upstreaming
- SBC and dilution disclosures (may be thinner than US 10-K norms)

Flag peer-comparability traps in `accounting_regime.peer_comparability_notes`; do not silently mix multiples across bases.

## Ownership, control, and claim on cash

| Form | Analytical focus (2e + valuation) |
|---|---|
| **Family control** | Related-party transactions, pledges of shares, succession, minority protection, dividend vs reinvestment preference |
| **SOE** | Policy mandates vs minority economics; capital return flexibility; non-commercial objectives |
| **VIE** | Contractual control vs equity ownership; enforceability / regulatory change as **scenario**, not fake precision on legal odds |
| **Dual-class / pyramid** | Voting vs economic interest; related-party tunneling risk |
| **A+H dual list** | Price gap, liquidity venue for TSR/technical benchmarks, which share class is the research target |

Deep dive must set `related_party_dual_class` (and enrich values when `ownership.complexity` is medium/high). Valuation records governance effects via **explicit assumptions or explicit zero/reject** in `market_context_hooks` — never a silent module default %.

## Filings map

- Prefer multi-year **annual reports** from the primary venue for strategy arc (≥3 years when available)
- Secondary: IR PDFs, earnings releases; label substitutions in fetch log
- Contingencies / legal: local annual notes before web dollar claims

## Stress catalogue (names only — agent sets probabilities)

Use when intensity is medium/high; pick what is decision-relevant:

1. Policy / industrial-policy shock affecting the sector or SOE parent
2. Capital controls / FX convertibility / offshore funding freeze
3. VIE or listing-status regulatory action
4. Family/SOE related-party or governance event
5. Dual-list premium/discount collapse or home-market liquidity shock

Haircuts must tie to valuation sensitivities where possible — not folklore "EM −30%".

## When to stay light

- US-domiciled company with **incidental** Greater China revenue and no control/VIE issues → prefer `region_us.md` or `intensity=low` / medium with hooks that **reject** heavy China institutional overlay
- Do not run a full China governance theater for every multinational that sells into China

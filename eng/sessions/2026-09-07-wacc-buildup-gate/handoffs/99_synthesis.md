# Synthesis — WACC-buildup identity (2.40)

Six investing-persona memos. This is the ship list, not an average of July 9% and Sep 6%.

CMCSA `2026-09-07` stays immutable. New runtime only.

## Verdict

Ship a shared **checker** (`packages/kd_research/wacc_buildup.py`), same pattern as `roic_identity.py`. Do **not** ship a calculator that returns a rate. Do **not** paste a WACC/ERP/Kd number into prompts.

Sep 7 already matched `we×Ke + wd×Kd(1−t)` and wrote `wacc_vs_buildup: matches_buildup`. Arithmetic identity alone would have **passed**. The failure is coupon Kd 4.0% below Rf 4.784% spent at trough `wd≈49%`. Ke 9.09% already matched tape-implied 9.13%; the fake bid is the debt mix.

## Require in v1 (all six)

| # | Gate | Why it catches Sep 7 |
|---|---|---|
| 1 | `kd_source` ∈ {`current_yield`, `rf_plus_spread`}. Coupon illegal. | Script comment was coupon buckets. |
| 2 | `kd_pretax >= rf` unless `kd_below_rf_gate=negative_rate_market` (local Rf evidence). Drop `current_yield_verified` as a below-Rf hatch. | 4.0% < 4.784%. |
| 3 | Distressed tripwire: `wd > 0.35` **and** implied-WACC gap > 200 bp → `weight_policy` cannot be `current_market` alone. Do **not** trip on `wd` alone. Do **not** require equity ≤ book (CMCSA P/B ~1.05). | Trough $94B equity vs $90B debt. |
| 4 | Anti-copy: when tripwire fires, `|wd − current_market_wd| < 2 pp` FAILs unless `structural_leverage_hatch` ≥40 chars with a non-price basis. | Relabel `target` at 49% debt. |
| 5 | `rf_plus_spread` must store `spread_bp`. Spread < 25 bp FAILs unless hatch `gov_or_aaa` / `quoted_ytm_equals_rf` / `negative_rate_market`. | 0 bp launders coupon-below-Rf to Kd=Rf (~6.4% WACC). |
| 6 | Arithmetic: WACC = we×Ke + wd×Kd(1−t) and Kd after-tax identity, both 5 bp; `we+wd≈1`; match `assumptions.wacc` and `roic_identity.wacc`. | Hygiene, not the kill shot. |
| 7 | Skip Kd-vs-Rf / spread floor when `wd < 0.05` (net-cash). | Avoid dummy Kd FAIL. |
| 8 | Implied gap > 200 bp requires `wacc_gap_rationale` that names Kd or weights. Do **not** FAIL the tape. Do **not** auto-kill `franchise_mos` from the tape. | Essay-only “tape is cheap” was Sep 7’s reverse-eng. |
| 9 | `applies:false` ≥40 chars + native analog for banks / insurance / REITs (copy ROIC). | False FAIL on natives. |
| 10 | Rewrite prompts so `matches_buildup` does **not** license a junk buildup. Agent 13 `4-wacc`. | Sep 7 obeyed current law. |

## Drop / later wave

Mandated Blume or Hamada; shared rate calculator; pasted 9%; FAIL-the-tape; dual-class Ke ≠ 0 as a machine FAIL; `fv_at_implied_wacc` dollar print (Risk PM A1 — later); lease-weight consistency vs `roic_identity.leases`; rewriting the incident.

Named Ke sleeves stay **inside** Ke with use/reject. Dual-class may stay 0. Silent pad after mixing with cheap debt stays illegal (`wacc_vs_buildup`).

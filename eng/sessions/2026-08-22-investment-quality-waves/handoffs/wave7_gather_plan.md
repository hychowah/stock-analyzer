# Wave 7 plan — Phase 0 / 1d gather (harness 2.15.0)

Persona pack item 4. Feed for destock/mid-cycle. Agent 5 still writes FV.

## Goal

The DCF must not invent moat, cash conversion, industry capacity, or capital-allocation trust. Gather those as required evidence.

## Alignment constraints

- W1; VERSION 2.15.0; synthetic tests; no archive mutation; Agent 5 single-writer.
- Do not add a second valuer or a new phase.
- Machine-gate **cash_quality** on `latest_quarter.json` (structured). Phase 0 moat/allocation and `1d_ind` are **prompt + file tests**; do not NLP `background.json`.
- Do not put cash_quality in schema `required[]` (Python gate, additionalProperties already true).
- Keep `suggested_rule` enum compatible: add optional values, do not remove `none`.
- Fixtures without cash_quality: only FAIL on harness ≥ 2.15.0 synthetic sessions, not by restamping live archive.

## Prompt / law

1. **Orchestrator brief:** at least one `must_answer_question` each for (game/price-setter), (destock vs demand or cycle position), (retained-earnings trust). Prompt block; schema minItems stays 3.
2. **Phase 0 round (3):** return must include `mechanism` (switching_cost|network|cost|scale|brand_price|license|none) and `decay_test`. `none` → `downstream_relevance=risk_candidate`. Same swarm JSON plus these keys for that round.
3. **Phase 0 round (5):** one sourced sentence “would / would not trust retained earnings because…”; `downstream_relevance` valuation_input or risk_candidate.
4. **`1d_ind`:** rewrite the one-liner. Require (or explicit missing→widen): industry capex vs history, utilization/book-to-bill analog, competitor supply response, destock vs demand, **units** not dollar TAM.
5. **Agent 2d:** required `cash_quality` object: at least GAAP NI or CFO or FCF, plus AR/inventory or DSO/DIO if on the BS. Evidence_log may use `cash_conversion_rule` | `destock_rule`.
6. **Agent 13:** missing cash_quality on ≥2.15.0 is major. Round-3 `context_only` brand-only moat is a finding (prompt).

## Gates (≥ 2.15.0)

- `latest_quarter.json` present → `cash_quality` must be an object with ≥1 numeric among `fcf`, `cfo`, `ni`, `gaap_ni`, `dso`, `dio`, `inventory` (nested `.value` OK). Else FAIL.
- Missing LQ → SKIPPED.
- <2.15.0 → SKIPPED.
- Prompt-file tests: round 3 `mechanism`; `1d_ind` must not be only the semis “node ramp vs destock” stub; 2d mentions `cash_quality`.

## Files

`agent_prompts.md`, `RESEARCH_AGENTS.md`, `HARNESS_MAP.md`, `VERSION`, `templates/latest_quarter.schema.json` (document), `scripts/kd_research/` small `check_cash_quality` (new function in `epistemology.py` or a 20-line helper next to 2d — prefer `scripts/kd_research/latest_quarter.py` only if it already exists; otherwise `epistemology.py` is the wrong home — put it in `scripts/kd_research/gates.py` or a tiny `cash_quality.py`). Tests: `test_wave7_gather.py`.

Prefer **one small function in `scripts/kd_research/gates.py` or new `cash_quality.py`** — do not overload destock epistemology.

## Non-goals

Moat object on valuation. Agent 12 bind. README CIO. Archive rewrites.

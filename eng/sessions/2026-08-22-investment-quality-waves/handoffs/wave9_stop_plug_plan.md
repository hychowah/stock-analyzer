# Wave 9 plan — stop teaching the plug (harness 2.17.0)

Persona pack item 6. Last remaining wave.

## Goal

Advisory modules must not hand Agent 5 a canned decay/TAM path. Uncertain identity must not auto-fallback to ordinary DCF. `applies:false` stays negative-IC / banks / REITs, not “we prefer ARR.”

## Alignment constraints

- W1; VERSION 2.17.0; synthetic **prompt-file** tests (no NLP on live sessions).
- Do not invent a formula that writes g. Do not block initiate on cheap_claim.
- Keep F21 / CPG-not-growth. Symmetric: confidence <0.70 is not “shrug to standard DCF.”
- Agent 5 single-writer. Modules stay advisory.
- Machine gate only what is string-testable in `sector_growth.md` / `RESEARCH_AGENTS.md` §5 / Agent 5 model-choice sentence. Optional: `applies:false` still requires reason (already 2.8.0).

## Prompt / law

1. **`sector_growth.md` Model A Step 1:** Cut “Project revenue using growth rate decay curve” and the 60%→15% table as a path to paste. Cut “Base growth on: TAM penetration” as primary. Require unit demand × share × price; TAM $ is a check. Keep NRR/GRR/SBC/burn questions. If IC is positive, §10d applies; `applies:false` only for negative IC / pre-revenue.
2. **`RESEARCH_AGENTS.md` §5.7:** Confidence < 0.70 still sets `requires_manual_review`. Do **not** auto-fallback to ordinary DCF; fallback is manual-review + widen range / `too_hard` or two-model (TTC vs franchise). Branded staples remain `standard` **on the merits**, not via this fallback.
3. **Agent 5 step 1:** Empty `module_file` → ordinary DCF only when identity is actually standard. If `1d_ind` shows capacity/utilization as the earnings driver, use TTC/cycle overlay even if §5 left `standard` (log a sector-fit hook). Do not paste growth-module decay tables.
4. **`HARNESS_MAP.md` / `VERSION` / §13 row.**

## Tests

`test_wave9_stop_plug.py`:
- `sector_growth.md` does not contain `Project revenue using growth rate decay curve`
- does not contain `60% → 45% → 35%`
- contains unit demand (or “units”) as primary
- `RESEARCH_AGENTS.md` §5.7 does not say “use standard” as the confidence fallback without manual-review/too_hard
- VERSION ≥ 2.17.0

No archive fixtures restamped.

## Non-goals

Mandate pack. Incremental ROIC gate. Archive rewrites.

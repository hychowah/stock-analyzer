# Wave 8 plan — README CIO page (harness 2.16.0)

Persona pack item 5. Typesetting after the number is honest.

## Goal

The one-page README leads with `duration.action`, not FV/MoS as a bid. Audit PASS stays a completeness disclaimer. ATR is not cover size (already). Football field is not required when action is pass/too_hard.

## Alignment constraints

- W1; VERSION 2.16.0; synthetic tests; no archive mutation.
- Extend `decision.py` (`check_readme_quotes_decision` already exists) — do not NLP the fundamental report.
- Do **not** add book_state / invalidation / size_implication this wave (those were PM extras; cover order is the wave).
- Do **not** block initiate on cheap_claim.
- Gate only when README exists (Phase 4+). Missing README → SKIPPED.
- Keep Wave 2 “README must quote duration.action.”

## Prompt / law

1. **Agent 11:** CIO block order: duration.action + one-sentence why; cheap_claim; then FV vs price as context (illustrative if pass/too_hard or not franchise_mos); TA overlay not the book; Audit PASS disclaimer. Cut leading “fair value vs price + margin of safety” and “verdict (bull/base/bear)” as the cover verdict.
2. **Agent 6:** football field required when initiate/add; when pass/too_hard, range/floor or omit the bid poster.
3. **Agent 7:** first screen quotes `decision.json`; do not invent a second verdict. Filing museum after.
4. **Agent 13:** README that leads with FV/MoS on pass/too_hard is major.

## Gates (≥ 2.16.0)

- README + decision.json present: `duration.action` must appear in the README **before** the first of `fair value vs price` / `margin of safety` (case-insensitive). Else FAIL.
- Action quoted (Wave 2) still required.
- <2.16.0: Wave 2 quote check only.
- Prompt-file test: Agent 11 cover list starts with duration.action.

## Files

`agent_prompts.md` (11, 7, 6, 13), `RESEARCH_AGENTS.md` §13, `HARNESS_MAP.md`, `VERSION`, `decision.py`, `test_wave8_readme_cio.py`. Wire `--full` via existing wave2 readme check or sibling.

## Non-goals

Full CIO packet schema. ATR math. Archive rewrites.

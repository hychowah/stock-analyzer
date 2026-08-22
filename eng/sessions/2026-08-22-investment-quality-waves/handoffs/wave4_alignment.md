# Wave 4 alignment — destock default

Verdict: **ALIGN WITH EDITS** (then implement).

Eng: W1 legal; VERSION 2.12.0 same change set; synthetic tests; no archive mutation; Agent 5 single-writer; implementer does not flip `passes`.

Wave 3 E1: keep `check_destock_not_silent_duration` byte-stable. Do not widen `_unresolved_destock`. Wave 4 sibling `check_destock_default` applies the same legal set (destock-in-base | DU=low | pass/too_hard) to destock conflicts of **any** status so resolved-to-bear cannot escape. FAIL destock-only-in-bear regardless of `initiate`/`add` (hold/trim would otherwise re-legalize).

Must-changes applied: exclusive legal-set FAIL; `_unresolved_destock` untouched; 4e one-line destock exception only; Agent 5 Inputs sentence; Pair 0 GOOD machine-true under `_destock_in_base`; destock-inverse two-quarter WARN only when a destock conflict exists.

Refactor: destock default stays in `epistemology.py` (no parallel module).

# Eng session 2026-08-29-llm-ticker-judge

- Created: 2026-08-29T10:39:16Z
- Work type: W1
- Goal: Typed Analyze ticker goes to Grok; Python only rejects names Yahoo cannot find; listing is a confirmed stamp.

## Log

- Leftover pass: HARNESS_MAP search-evidence row now blocks Phase 0 (not scaffold). Analyze form copy and job docstring match existence-check + listing stamp.
- Strategic review #2 implemented:
  1. Existence statuses `quoted` | `search_evidence`; no `quote_symbol` on `TickerCheck`; scaffold writes `quote_symbol` null; outcomes fail closed without a stamp; `refresh_analyze` copies the stamp.
  2. `scripts/verify_listing.py` Yahoo-quotes the stamp (Grok proposes, Python confirms).
  3. Deleted `abort_match` suggestion interface (CLI exit 3, Analyze matches, form picker).
  4. Search hits stay inside the existence gate; not copied to `job.json` or the Analyze prompt.
  5. Session contract (issue/feature_list/status) aligned: no HTTP LLM judge.

## Resume hint

Verifier: `python scripts/eng_verify.py`. Restart analysis_web. Submit ADYEN; Grok must stamp `ADYEN.AS` and pass `verify_listing.py` before Phase 0.

## Refactor note

`ticker` is folder identity. `quote_symbol` is a confirmed Yahoo listing or it is not there. One writer (orchestrator) plus a machine quote check.

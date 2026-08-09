# Judgment exemplar bank

Small **contrastive** examples that teach output *quality* for harness contracts (rationales, hooks, handoffs). Not valuation answer keys.

## Design principles

1. **3–5 examples total per agent injection** — not laundry lists.
2. **Contrastive pairs**: same decision, BAD vs GOOD.
3. **Style only** — numbers are ILLUSTRATIVE.
4. **Delta maintenance**: when audit finds a recurring soft failure, add/replace one pair here instead of a new paragraph in `AGENTS.md`.

Full design: `harness/design_phase_status_and_exemplars.md` Part B.

## Files

| File | Teaches | Primary agents |
|------|---------|----------------|
| `rationale_quality.md` | `{value, rationale, basis}` substance | 4, 5, 2e, 12, 13 |
| `hooks_quality.md` | `used_as` / `rejected` / `noted_only` | 5, 13 |
| `handoff_quality.md` | Four-section handoff | all |
| `index.json` | Which agents load which files | orchestrator |

## Injection (when wired into prompts)

```text
## Judgment exemplars (style only — do not copy numbers into this session)

Read ROOT/harness/exemplars/<file>.md and match the GOOD pattern.
BAD patterns are FAIL-quality even if schema-valid.
```

## Changelog

- 2026-08-04: Initial bank (design ship) — rationale, hooks, handoff pairs.

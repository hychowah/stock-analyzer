# Wave 2 plan — decision object + pass technical (harness 2.10.0)

IDs: **B1, B2, C1–C3, G1, G5**. Branch already `harness/investment-quality-waves` (Wave 1 = 2.9.0).

## Goal

A session can say **don't**. Duration `action` including `pass` is a first-class artifact. `initiate` is illegal on a decision-useless cone. Technical may emit `pass` instead of a forced long. Catalog shows the action and kill triggers, not MoS alone.

## Alignment

| Constraint | Honor |
|---|---|
| Mode B W1 | pytest on shipped gates; VERSION **2.10.0** same change set |
| Immutable archive | synthetic tests; no rewrite of completed research/outcomes |
| No FV invention | action is an enum + rationale, not a new fair value |
| Progressive disclosure | Agent 5 writes `registry/decision.json`; Agent 4/11 sliced prompts; no mega-dump |
| Isolation F14/F16 | no prior-FV copy |
| Version gate | all new FAILs SKIPPED on harness < 2.10.0 |
| Wave 1 | do not reopen 2.9.0 gates except to call them |

## Product

### B1 `registry/decision.json` (Agent 5 single writer)

```text
duration.action: initiate | add | hold | trim | sell | short | pass | too_hard
duration.rationale: ≥20 chars
```

Optional `tactical.action` / `tactical.side` (not required to complete).
Agent 11 **quotes** `duration.action`; must not invent a different verb.

### B2 initiate illegal

On ≥ 2.10.0, `duration.action=initiate` FAILs when:
- `fair_value.decision_usefulness=low`, or
- `(bull−bear)/base > 1.0`, or
- `bear < 0.4×base` (base>0)

Legal actions on that cone: `pass` | `too_hard` | `hold` | `trim` | `sell` | `short`.

### C1 technical may pass

`technical.json`:
- `side`: `long | short | pass` (optional on legacy)
- If `side=pass` (or `levels.setup=pass`): entry/stop/targets **not** required
- If `side=long`: stop must be below entry when both present
- Agent 4 prompt: stop-below-entry only for longs; pass is a legal output

Schema: drop `levels.entry/stop_loss/targets` from **required** so pass sessions validate. Machine gate on ≥2.10.0 requires them when side is long/short.

### C2 duration pass vs TA long

If `duration.action` in `{pass, too_hard, sell, short}` **and** technical `side=long` **and** no `tactical.allow_long=true` on decision.json → FAIL (≥2.10.0). Missing technical.json SKIPPED.

### C3 ATR not on README cover

Prompt (Wave 1 already). Machine **WARN** if README contains ATR share-count language (`atr` + `shares`) without `decision.json` action quoted. Not FAIL (live archive).

### G1 / G5 catalog

`session_extract` + snapshot + extras:
- `decision_action` from decision.json
- `kill_triggers` = unique `risk_bridge.risks[].monitoring_trigger` strings (max 8)

`comparable_only` still excludes null FV. Do not treat action as a buy list.

## Files

- `harness/VERSION` → 2.10.0
- `templates/decision.schema.json`
- `templates/technical.schema.json` (levels fields not required)
- `templates/prediction_snapshot.schema.json` (+ decision_action, kill_triggers)
- `scripts/kd_research/decision.py` gates
- wire `check_session --full`, `complete_checks` 2_parallel (technical pass) + 4_parallel (decision present if reports)
- `session_extract`, snapshot, export extras
- Agent 4, 5, 11, 13 prompts (sliced)
- `scripts/tests/test_wave2_decision.py`
- `eng/eval/failure_catalog.md` F27 always-long TA / no pass action

## Tests (synthetic)

1. 2.10.0 missing decision.json + valuation → FAIL; 2.9.0 SKIPPED
2. initiate + DU=low → FAIL; pass + DU=low → PASS
3. initiate + span>100% → FAIL
4. technical side=pass without entry → PASS; side=long without stop → FAIL
5. duration=pass + TA long without allow_long → FAIL
6. extract kill_triggers from risk_bridge; snapshot has decision_action
7. README quoting pass + no ATR shares → no FAIL

## Non-goals

Wave 3 destock/update. Wave 4 Kelly/book risk. Winner-if-conflict beyond C2. Human IC sign-off. Archive rewrites.

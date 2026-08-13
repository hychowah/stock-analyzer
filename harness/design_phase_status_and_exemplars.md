# Design: Phase Status + Exemplar Bank

**Status:** design only (not yet wired into `AGENTS.md` / `check_session.py`)  
**Date:** 2026-08-04  
**Motivation:** Durable multi-session resume (Anthropic long-running harness pattern) + small contrastive few-shots for judgment quality (context-engineering best practice).  
**Scope:** formats, ownership, resume rules, and a starter exemplar bank. No full constitution rewrite.

---

## Part A — `registry/phase_status.json`

### A.1 Goal

Give the orchestrator a **machine-readable session state machine** so a research run can:

1. Survive interruption (context reset, process kill, human pause).
2. Resume from the last green phase without re-doing completed work.
3. Refuse to mark a phase complete without required artifacts + handoff.
4. Leave a clean trail for the auditor (what ran, what failed, what was skipped).

This is the equity-research analogue of Anthropic’s feature list + progress file: structured status agents edit only in controlled ways.

### A.2 Path and writer

| Item | Value |
|------|--------|
| Path | `S/registry/phase_status.json` |
| Schema | `templates/phase_status.schema.json` |
| Created by | `scaffold_session.py` (initial skeleton) **or** orchestrator on first write |
| Primary writer | **Orchestrator (main agent)** only |
| Readers | Orchestrator on resume; Agent 13 (audit); optional `check_session.py` later |
| Subagents | **Do not write** this file. They write artifacts + handoffs; orchestrator flips status. |

### A.3 Phase IDs (stable enum)

Align with `AGENTS.md` §8. Use these exact strings:

| `phase_id` | Meaning | Completeness gate (required artifacts) |
|------------|---------|----------------------------------------|
| `orch` | Sector + market_context classification + research brief (new sessions) | `sector_config.json`, `market_context.json`, `research_brief.json` (new sessions; legacy OK without) |
| `0` | Background research (swarm) | `background.json`, ≥1 `raw/phase0_*.json`, handoff; preflight `--mode complete` (downstream_relevance on raws) |
| `1_parallel` | 2a + 2b + 2c | `sp_financials.csv`, `sec_filings.json`, `news_sentiment.json`, 3 handoffs; `data_fetch_log.json` preferred |
| `1b` | Latest quarter (2d) | `latest_quarter.json`, handoff |
| `1c` | Filing deep dive (year-readers + 2e merger) | `filing_deep_dive.json`, handoff; **new runtime:** `raw/fdd_year_*.json` + excerpt check + `verify_rechecks`. Legacy without year-files: FDD only |
| `2_parallel` | 4 + 5 + 12 | `technical.json`, `valuation_model.json`, `tsr_validation.json`, 3 handoffs |
| `2_5` | Stress swarm | `risk_bridge.json`, ≥5 `raw/stress_*.json` (or equivalent), handoff; preflight `--mode complete` |
| `3` | Charts | ≥3 `charts/*.png`, handoff |
| `4_parallel` | Reports 7 + 8 + 11 | three `reports/*.md`, 3 handoffs |
| `5` | Audit | `audit.json` with `verdict` |
| `done` | Session complete | `audit.verdict == PASS` **or** explicit waivers listed in README |

Dependency edges (orchestrator must not start B until A is `complete` or explicitly `skipped` with reason):

```text
orch → 0
orch → 1_parallel          # 0 and 1_parallel may run in parallel after orch
1_parallel → 1b
1_parallel → 1c            # 1b ‖ 1c after 2a+2b ready; 1c needs 2b raw_sec
1b + 1c → 2_parallel
2_parallel → 2_5
2_5 → 3
2_5 → 4_parallel           # 3 ‖ 4 after 2_5 (charts only need valuation; reports need all)
3 + 4_parallel → 5
5 → done
```

**Note:** `3` only needs `valuation_model.json` (+ risk_bridge if tornado charts). Orchestrator may start `3` as soon as phase `2_parallel` is complete if charts don’t need stress; keep default simple: **after 2_5** unless documented deviation.

**Mechanical preflight (orchestrator MUST):** before starting `2_parallel`, `2_5`, `4_parallel`, or `5`, run:

```bash
python3 scripts/preflight_phase.py --ticker T --date D --phase <phase_id>
```

Before marking phase `0` or `2_5` complete:

```bash
python3 scripts/preflight_phase.py --ticker T --date D --phase 0|2_5 --mode complete
```

Gates live in `scripts/kd_research/gates.py`. Map: `harness/HARNESS_MAP.md`.

### A.4 Status vocabulary

| `status` | Meaning |
|----------|---------|
| `pending` | Not started |
| `in_progress` | Orchestrator launched work; not yet gated complete |
| `complete` | Completeness gate passed (artifacts + handoffs exist) |
| `failed` | Attempted; hard failure (tool outage, empty critical artifact) |
| `blocked` | Waiting on dependency or human input |
| `skipped` | Intentionally not run (must have `skip_reason`) |

Per-agent rows (inside a phase) use the same status set.

### A.5 Document shape (normative example)

```json
{
  "ticker": "META",
  "session_date": "2026-08-03",
  "schema_version": 1,
  "updated_at": "2026-08-03T18:40:00Z",
  "current_phase": "2_parallel",
  "resume_hint": "Re-enter at phase 2_parallel: 4 complete, 5 in_progress, 12 pending. Do not re-run 1b/1c.",
  "phases": [
    {
      "phase_id": "orch",
      "status": "complete",
      "started_at": "2026-08-03T14:00:00Z",
      "finished_at": "2026-08-03T14:12:00Z",
      "agents": [
        {
          "agent_id": "orchestrator",
          "status": "complete",
          "artifacts": [
            "registry/sector_config.json",
            "registry/market_context.json"
          ],
          "handoff": null
        }
      ],
      "notes": ""
    },
    {
      "phase_id": "1_parallel",
      "status": "complete",
      "started_at": "2026-08-03T14:30:00Z",
      "finished_at": "2026-08-03T15:10:00Z",
      "agents": [
        {
          "agent_id": "2a",
          "status": "complete",
          "artifacts": ["data/sp_financials.csv", "data/peer_comparison.csv", "registry/data_fetch_log.json"],
          "handoff": "registry/handoffs/2a_fundamentals.md"
        },
        {
          "agent_id": "2b",
          "status": "complete",
          "artifacts": ["registry/sec_filings.json", "data/raw_sec/"],
          "handoff": "registry/handoffs/2b_sec_filings.md"
        },
        {
          "agent_id": "2c",
          "status": "complete",
          "artifacts": ["registry/news_sentiment.json"],
          "handoff": "registry/handoffs/2c_news_sentiment.md"
        }
      ],
      "notes": ""
    },
    {
      "phase_id": "2_parallel",
      "status": "in_progress",
      "started_at": "2026-08-03T16:00:00Z",
      "finished_at": null,
      "agents": [
        {
          "agent_id": "4",
          "status": "complete",
          "artifacts": ["registry/technical.json", "data/compute/technical_indicators.py"],
          "handoff": "registry/handoffs/4_technical.md"
        },
        {
          "agent_id": "5",
          "status": "in_progress",
          "artifacts": [],
          "handoff": null
        },
        {
          "agent_id": "12",
          "status": "pending",
          "artifacts": [],
          "handoff": null
        }
      ],
      "notes": "Interrupted mid-valuation; re-spawn Agent 5 only."
    }
  ],
  "failures": [],
  "waivers": []
}
```

### A.6 Completeness gates (orchestrator checklist)

Before setting `phase.status = complete`, orchestrator verifies:

1. Every required agent under that phase is `complete` or `skipped` (with reason).
2. Listed `artifacts` exist on disk (directories non-empty where trailing `/`).
3. Required handoff files exist and are non-trivial (e.g. >200 chars or contain the four section headers).
4. For parallel phases: **all** non-skipped agents green before phase green.
5. Never invent paths: if artifact missing → `failed` or keep `in_progress`, not `complete`.

Optional later: encode gates in `check_session.py` / a tiny `scripts/phase_gate.py`.

### A.7 Resume protocol (orchestrator)

On session start or re-entry:

```text
1. If S/registry/phase_status.json missing → create skeleton (all pending), run orch.
2. Read phase_status.json.
3. Set current_phase = first phase_id in order that is not complete/skipped.
4. For that phase:
   a. If status pending → mark in_progress; launch missing agents.
   b. If status in_progress → launch only agents with status pending|failed
      (do not re-run complete agents unless --force-agent).
   c. If status failed → read failures[]; fix or skip with reason; re-run failed agents only.
   d. If status blocked → resolve blocker (human/input) before launch.
5. After each agent returns: update agent row (artifacts, handoff, status), then re-evaluate phase gate.
6. Write resume_hint as one plain-English sentence for the next shift.
7. Update updated_at (ISO-8601 from `date -u +%Y-%m-%dT%H:%M:%SZ`, not model-invented).
```

**Idempotency rules:**

- Scaffold refuses non-empty overwrite (already true).
- Re-running a `complete` agent is forbidden unless orchestrator sets that agent to `pending` with a note (e.g. audit fix loop).
- Merge phases (0, 2_5): if `background.json` / `risk_bridge.json` exist and raw returns exist, treat merge as complete; do not re-swarm unless failed.

**Fix-loop (Phase 5 FAIL):**

- Set `5` → `in_progress` or keep `complete` with `verdict=FAIL`.
- Add `failures[]` entries for issues being fixed.
- Re-run only agents that own broken artifacts (max 2 audit iterations per AGENTS.md).
- On PASS: `5` → `complete`, then `done` → `complete`.

### A.8 Failure and waiver records

```json
"failures": [
  {
    "phase_id": "1_parallel",
    "agent_id": "2b",
    "at": "2026-08-03T15:00:00Z",
    "error": "sec-edgar MCP timeout on 10-K FY2023",
    "fallback": "Used web-fetch IR PDF for FY2023; marked strategy_arc coverage partial"
  }
],
"waivers": [
  {
    "issue": "Transcripts unavailable",
    "severity": "major",
    "waived_in": "reports/00_META_README.md",
    "reason": "Scorecard degraded_no_transcripts; valuation range widened"
  }
]
```

### A.9 Scaffold skeleton

`scaffold_session.py` should create `registry/phase_status.json` with all phases `pending` and empty agent lists **or** pre-filled agent_ids with `pending` (prefer pre-filled — less orchestrator invention).

Recommended pre-filled agent_ids:

| phase_id | agent_ids |
|----------|-----------|
| orch | orchestrator |
| 0 | phase0_swarm |
| 1_parallel | 2a, 2b, 2c |
| 1b | 2d |
| 1c | 2e |
| 2_parallel | 4, 5, 12 |
| 2_5 | phase25_swarm |
| 3 | 6 |
| 4_parallel | 7, 8, 11 |
| 5 | 13 |
| done | — (no agents; status flipped by orchestrator) |

### A.10 Orchestrator prompt snippet (drop-in later)

Not applied yet; for when wiring into AGENTS.md:

```text
Maintain S/registry/phase_status.json as the sole resume map.
You are the only writer. After each agent finishes, update its agent row
(status, artifacts, handoff paths), then re-check the phase completeness gate
before advancing. On re-entry, read phase_status first and resume_hint;
do not re-run complete agents. Never set status=complete if a required
artifact path is missing.
```

### A.11 What we deliberately defer

- Temporal / LangGraph durable execution runtime
- File locking / multi-orchestrator concurrency
- Auto-encoding every completeness gate into CI on day one
- Changing the phase DAG itself

---

## Part B — Exemplar bank (contrastive few-shots)

### B.1 Goal

Teach **judgment style** (rationales, hooks, handoffs), not financial answers. Frontier models already reason; they under-specify *what good looks like* for custom contracts.

Per 2025–26 lab guidance: **3–5 canonical contrastive examples**, not laundry lists of edge cases.

### B.2 Location

```text
harness/exemplars/
  README.md                 # how to inject; maintenance rules
  rationale_quality.md      # good vs thin {value, rationale, basis}
  hooks_quality.md          # used_as | rejected | noted_only
  handoff_quality.md        # four-section handoff
  index.json                # machine index: which agents load which exemplars
```

**Not** under session tree — exemplars are harness-global. Sessions may cite them; they do not copy full banks into every registry.

### B.3 Injection contract

| Agent | Load exemplars |
|-------|----------------|
| 5 valuation | `rationale_quality.md`, `hooks_quality.md` |
| 4 technical | `rationale_quality.md` (entry/stop only) |
| 2e deep dive | `rationale_quality.md` (continuity score) |
| All agents (handoff convention) | one short block from `handoff_quality.md` **or** the shared conventions header already in `agent_prompts.md` |
| 13 audit | all three (as grading rubric anchors) |

**How to inject (when wiring prompts):**

```text
## Judgment exemplars (style only — do not copy numbers into this session)

Read ROOT/harness/exemplars/<file>.md and match the GOOD pattern for your
outputs. BAD patterns are FAIL-quality even if schema-valid.
```

Keep total exemplar tokens small: each file ≤ ~1.5–2k tokens.

### B.4 File format (markdown, human-editable)

Each exemplar file uses this structure:

```markdown
# <Topic> exemplars

Purpose: ...
Used by: agent ids

## Pair 1 — <short name>

### Context (shared)
One paragraph: what was being decided (fictional or anonymized).

### BAD
```json
{ ... minimal valid but hollow ... }
```
Why bad: 1–2 sentences.

### GOOD
```json
{ ... same decision, substantive ... }
```
Why good: 1–2 sentences.

## Pair 2 — ...
```

**Rules for authors:**

1. **Same decision, two qualities** (true contrastive).
2. Numbers may be fictional; label `ILLUSTRATIVE — not a real filing`.
3. Never teach a hardcoded WACC/multiple as “correct.”
4. Prefer failures seen in real audits (documentation theater, empty hooks, hollow handoffs).
5. Cap **2 pairs per file** at first (4 examples total per topic).

### B.5 `index.json` shape

```json
{
  "schema_version": 1,
  "exemplars": [
    {
      "id": "rationale_quality",
      "path": "harness/exemplars/rationale_quality.md",
      "agents": ["4", "5", "2e", "12", "13"],
      "max_pairs": 2
    },
    {
      "id": "hooks_quality",
      "path": "harness/exemplars/hooks_quality.md",
      "agents": ["5", "13"],
      "max_pairs": 2
    },
    {
      "id": "handoff_quality",
      "path": "harness/exemplars/handoff_quality.md",
      "agents": ["*"],
      "max_pairs": 1
    }
  ]
}
```

### B.6 Maintenance (ACE-style deltas)

When audit finds a recurring soft failure:

1. Add **one** new contrastive pair (or replace the weakest pair).
2. Do **not** add a new paragraph of rules to AGENTS.md for the same failure.
3. Log the change in `harness/exemplars/README.md` changelog (one line).
4. If pairs exceed 3 per file, prune oldest low-signal pair.

### B.7 What exemplars are *not*

- Not sector valuation answer keys  
- Not full session dumps  
- Not a substitute for schema validation  
- Not loaded into every agent if irrelevant (keep agent-scoped)

---

## Part C — Implementation checklist (later PR)

| Step | Work | Depends on design approval |
|------|------|----------------------------|
| 1 | Land `templates/phase_status.schema.json` | This doc |
| 2 | Land `harness/exemplars/*` starter bank | This doc |
| 3 | Update `scaffold_session.py` to write skeleton `phase_status.json` | Step 1 |
| 4 | Add orchestrator resume snippet to AGENTS.md §8 (short) | Step 1 |
| 5 | Add one line to agent_prompts conventions: optional exemplar paths | Step 2 |
| 6 | Optional: `check_session.py` validates phase_status if present | Step 1 |
| 7 | Optional: golden-ticker suite (outcome quality) | Separate design |

**Out of scope for this design:** rewriting all agent templates, audit dual-verdict schema, cross-model audit.

---

## Part D — Acceptance criteria

Design is “done” when:

1. [x] `phase_status` schema exists and matches §A  
2. [x] Starter exemplar files exist with ≥1 contrastive pair each  
3. [x] Scaffold writes skeleton (implementation)  
4. [x] Unit + e2e scaffold/check/schema validation (implementation; see scripts/tests/test_phase_status.py)

---

## References (2025–2026)

- Anthropic, *Effective harnesses for long-running agents* (2025-11)  
- Anthropic, *Effective context engineering for AI agents* (2025-09)  
- Anthropic, *Harness design for long-running application development* (2026-03)  
- OpenAI, *Harness engineering* (2026-02)  
- ACE, arXiv:2510.04618 (evolving playbooks / avoid context collapse)

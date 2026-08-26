---
name: session-valuation-audit
description: >
  Independent multi-persona audit of two completed Stock Research sessions.
  Spawns six investing-persona auditors (conservative value, quality compounder,
  forensic accountant, DCF process, risk PM, reverse-engineer) in parallel to
  compare valuation methods, assumption stacks, and fair-value gaps, then
  synthesizes which differences are economic vs methodological. Use when the
  user runs /session-valuation-audit, or says compare two sessions, audit two
  runs, valuation gap between sessions, independent auditors, cross-session
  valuation, session vs session fair value, or names two archive/research
  folders to deep-dive.
---

# Session valuation audit

Post-finalize comparison of **two named, completed sessions** for the **same ticker**. This is not a Mode A research run: do not scaffold, do not run Phases 0–5, do not rewrite either session.

Read `references/personas.md` and `references/artifact-map.md` in this skill directory before spawning.

## Inputs

Require two sessions. Accept any of:

- Two absolute paths under `archive/research/<TICKER>/<session_key>`
- Ticker plus two session keys (`YYYY-MM-DD` or `YYYY-MM-DD__slug`)

If the user names only one session, ask for the second. Do not pick a comparison partner from the ticker folder.

Both must be the same ticker. If `data/valuation_model.json` is missing on either side, stop.

Repo root is the directory that contains `harness/RESEARCH_AGENTS.md` and `archive/research/`. Resolve sessions with:

```bash
python scripts/compare_runs.py --ticker <TICKER> --dates <A>,<B>
```

Treat that table as a headline helper only. The audit reads the session trees, not the catalog SQLite.

## Hard rules

- Sessions are immutable history. Read only. Never write under either session folder.
- Write only under the audit output directory defined below.
- Every number cites a session file. Do not invent fair values, WACC, MoS, or scenario masses.
- Do not average the two base FVs into a compromise target.
- Isolation law in `harness/RESEARCH_AGENTS.md` blocks browsing prior runs during a **new** research run. This skill is the user-asked **compare-after**. The two named sessions are in scope; other tickers and unnamed sessions are not.
- Do not `git commit`.

## Output directory

```
<repo-root>/archive/comparisons/<TICKER>/<asof>__<A>_vs_<B>/
```

`<asof>` is today's date (`YYYY-MM-DD`). `<A>` and `<B>` are the session keys. If that folder already has files, use `__rN`.

If the prompt names an absolute **OUT** directory, write there instead of computing the default path. Never write under either research session folder. Never write `archive/research/<TICKER>/tmp/`.

Label the older (or first-named) session **A** and the other **B**. Keep A/B stable across every file in the packet.

Write:

| File | Author |
|---|---|
| `README.md` | Orchestrator (index) |
| `00_assignment.md` | Orchestrator (mandate + headline table) |
| `01_conservative_value_audit.md` | Persona 1 |
| `02_quality_compounder_audit.md` | Persona 2 |
| `03_forensic_accountant_audit.md` | Persona 3 |
| `04_valuation_process_audit.md` | Persona 4 |
| `05_risk_pm_audit.md` | Persona 5 |
| `06_reverse_engineer_audit.md` | Persona 6 |
| `99_synthesis.md` | Synthesizer (after all six land) |

## Procedure

### 1. Headline pass (orchestrator)

Read the artifact map for both sessions. Write `00_assignment.md` with:

- Absolute paths, harness versions (`meta/run_manifest.json`), freeze prices, base/bear/bull/PW, MoS vs base, decision usefulness, action/posture, model names
- Shared facts vs disputed facts (one short list each)
- The four questions every auditor must answer (copy from below)
- Hard rules and the output filename assigned to each persona

Write `README.md` as a file index pointing at `99_synthesis.md` first.

### 2. Fan-out (mandatory)

Spawn **all six** auditor subagents in **one turn**, near the start of the audit work (after `00_assignment.md` exists). Do not run them sequentially. Do not let them see each other.

For each child:

- `subagent_type`: `general-purpose`
- `background`: `true`
- `isolation`: `none` (writes must land in the shared OUT folder)
- `capability_mode`: `all`
- Do **not** set `resume_from`

Paste a **self-contained** prompt. Subagents do not load this skill. Each prompt must include: hard rules, absolute session paths, absolute OUT path, assigned filename, that persona's section from `references/personas.md`, the artifact map, and the four questions. Instruct the child to write **only** its assigned file, and to read OUT only for `00_assignment.md` / `README.md`.

### 3. Barrier

Wait until all six have written their files. If one fails, retry that persona once. Do not synthesize with a missing memo.

### 4. Synthesizer

Spawn **one** synthesizer subagent (same spawn settings) after the barrier. It reads the six memos plus `00_assignment.md` and writes only `99_synthesis.md`.

The synthesizer does not run a third DCF. It ranks differences by estimated impact on base FV, splits economic vs methodological, and answers which session is more accurate **by question** (print identity, GAAP→owner-earnings conversion, franchise/ROIC, DCF engine, capital-allocation verb, what is in the tape). Close with the action that survives every persona and the uncertainties that still move FV by >20%.

## Four questions (every auditor)

1. What are the **significant differences** (model architecture, growth/margin/capex paths, WACC, terminal, segment vs consolidated, one-off vs run-rate, scenario weights, share count, SBC, legal, data quality)?
2. Which differences are **economic** (new facts between the two as-of dates) vs **methodological** (harness version, model choice, judgment)?
3. Which session’s valuation is **more accurate / more decision-grade** for a long-term equity view, and why? Accuracy means internally consistent, evidence-tied, not double-counting, not silently optimistic or pessimistic, usable for capital allocation — not “which number is cheaper.”
4. What remaining uncertainty would still move FV by **>20%**?

## Auditor memo shape

Each persona file starts with: persona name, A/B paths, verified headline table with sources, then the deep-dive in that persona’s lens, then explicit answers to the four questions. Lead with the answer.

## Done

Tell the user the OUT path and to read `99_synthesis.md` first. Do not edit either research session as a follow-up unless the user separately starts a **new** `session_key`.

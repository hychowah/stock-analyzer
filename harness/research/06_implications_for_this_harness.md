# Implications for This Stock-Research Harness

This document maps 2025–2026 industry findings onto `/workspace-stock-research` as specified in `Agents.md` / `AGENTS.md` and `harness/agent_prompts.md`.

## 1. What this repo already does well

The harness is unusually aligned with frontier practice for a domain-specific research system.

| Industry practice | Already present here |
|-------------------|----------------------|
| Harness > ad-hoc chat | Full phase graph, scaffolds, schemas, check_session |
| Progressive disclosure | Sector/region modules are advisory references; not all dumped every time |
| Session / shift handoff | `registry/phase_status.json` resume map; `registry/handoffs/<agent>.md` |
| Write state outside context | Registry JSON, data CSVs, raw_sec, charts |
| Initializer vs workers | Scaffold + orchestrator classification before Phase 0; specialized agents thereafter |
| Incremental progress | One session folder per date; agents complete discrete artifacts |
| Mechanical gates | `templates/*.schema.json`, `scripts/check_session.py`, justification contract |
| Isolate heavy work | Subagents by phase; 2a/2b/2c parallel; Phase 2 parallel |
| Orchestrator–workers | Main agent merges Phase 0 / 2.5 swarms; raw returns persisted first |
| Evaluator / audit | Phase 5 audit agent + fix loop |
| Provenance | `rationale`/`basis`, compute scripts, data_fetch_log |
| Verify against primary sources | Audit requires filing-grade re-checks vs raw_sec |
| Context intensity gates | `market_context.intensity` low/medium/high changes required depth |
| No silent partial data | Degraded data must widen valuation range |

**Bottom line:** This is already a “harness-engineered” research system, not a single mega-prompt.

---

## 2. Gaps and upgrade opportunities (prioritized)

### P0 — High leverage / low regret

> **Status (2026-08-09):** P0/P1 investment-quality upgrades landed in harness code/docs. North star is **decision-grade research for the next phase**, not token thrift.

#### 2.1 Keep always-on instructions short; deepen progressive disclosure

**Risk:** Root `Agents.md` is a long normative mega-spec. Frontier OpenAI lesson: encyclopedia dumps crowd out tasks and rot.

**Recommendations:**

- Treat root `AGENTS.md` / `Agents.md` as **normative contract** (it is) but ensure **subagent prompts** only include the slice that agent needs (templates already aim at this — enforce strictly).  
- For human/agent navigation, add a short **map index** (this `harness/research/` pack helps meta-level; consider a one-page `harness/HARNESS_MAP.md` pointing to phases, schemas, modules).  
- Avoid pasting entire sector modules into valuation prompts — require “read module_file then cite hooks” (already the rule; watch for prompt bloat in practice).

**Done:** `harness/HARNESS_MAP.md` + AGENTS quick map lead; prompts stay sliced per agent.

#### 2.2 Subagent returns must be decision-grade (not “shorter for thrift”)

**Industry:** Workers may burn tens of thousands of tokens; return high-signal summaries + paths to raw.

**Recommendations:**

- In `agent_prompts.md`, standardize **decision-grade returns**: structured artifact on disk + handoff with downstream actions; forbid pasting entire filings into parent chat.  
- Phase 0 / 2.5 merge protocol already requires raw persistence before merge — keep parent merge context on **coverage, diffs, and conflicts**, not full raw dumps.

**Done:** Decision-grade return contract + anti-patterns in `agent_prompts.md`; handoff exemplar Pair 2; audit checks 2e/2f/11.

#### 2.3 Tool-result / data hygiene for filings

**Industry:** Tool-result clearing; dual full/compact forms.

**Recommendations:**

- Full note text stays in `data/raw_sec/` (already required). Never expand uncapped 10-K prose into `sec_filings.json` (already forbidden — keep enforced).  
- Prefer extractors (`scripts/kd_research/note_extract.py`) that write short excerpts + offsets.  
- When agents read raw_sec, use line-limited reads / search, not full-file loads into the lead.

#### 2.4 Numeric rehydration after any summary

**Industry:** Aggressive compaction loses subtle facts; agents invent later.

**Recommendations:**

- Valuation and reports must cite **compute scripts + registry fields**, not remembered chat numbers.  
- Audit agent already re-runs scripts and checks registry ↔ report; treat any chat-only number as a defect.

**Done:** Number-integrity language in conventions + Agent 7/13 checklists.

---

### P1 — Structural improvements

#### 2.5 Explicit research-depth scaling in swarm prompts

**Industry:** Agents spawn too many workers or under-research hard names.

**Recommendations:**

- Scale **depth** by intensity / control complexity (more ownership/FX work on hard names).  
- Phase 2.5: fixed **≥5 scenarios** remains machine-checked; region/gov scenario must be material on deep names.  
- Encode standard vs deep in `research_brief.research_depth`.

**Done:** Depth policy in HARNESS_MAP + brief schema + Phase 0/2.5 prompts (quality-oriented, not cost caps).

#### 2.6 Stronger baseline verify at phase entry

**Industry:** Coding agents must baseline-test before new features; research analog is **dependency health**.

**Recommendations:**

- Orchestrator already uses `phase_status` — before starting Phase 2, mechanically verify Phase 1 artifacts exist and parse (scriptable preflight).  
- Before Phase 4 reports, verify valuation_model + risk_bridge + technical present.  
- This is the research equivalent of “start the server and click New Chat.”

**Done:** `scripts/preflight_phase.py` + `scripts/kd_research/gates.py`; AGENTS orchestrator MUST.

#### 2.7 Generator vs evaluator separation for valuation

**Industry:** Self-grading is too generous.

**Recommendations:**

- Phase 5 audit is the evaluator — keep it from sharing the valuation agent’s context.  
- Optional: lightweight “red team” pass on `risk_bridge` probabilities before reports (separate agent, skeptical rubric).  
- Do not let Agent 5 mark its own audit PASS.

**Partial:** Gen≠eval unchanged; risk red-team still optional/deferred.

#### 2.8 Feature-list style checklists for session completeness

**Industry:** JSON feature lists with `passes` flags beat freeform Markdown.

**Recommendations:**

- `phase_status.json` is already the session checklist — ensure every required artifact path is listed and only flipped to `complete` when files exist (spec already says this; automate with pre-complete hook script).  
- Consider a machine-readable `session_acceptance.json` derived from quality gates §13.

**Done:** `check_session.py --write-acceptance`; merge/coverage preflight `--mode complete` for Phase 0 / 2.5; optional `research_brief` check.

---

### P2 — Context-window-specific

#### 2.9 Position critical contracts at edges of subagent prompts

When composing large prompts:

- **Start:** role, write paths, hard prohibitions (no inventing, no reading forbidden artifacts for Agent 4)  
- **Middle:** background excerpts (minimize)  
- **End:** exact output schema, current resume_hint, “stop conditions”  

Agent 4 (technical) must not see fundamentals — isolation is both a dependency rule and a **context purity** rule.

#### 2.10 Market-context intensity as context budget policy

| Intensity | Context policy |
|-----------|----------------|
| low | Minimal region prose; `noted_only` hooks OK |
| medium | Explicit FX/accounting/ownership sections; selective region module pulls |
| high | Deep ownership/related-party work; ≥1 region/governance stress scenario; **widen ranges**; do not fake US no-op |

This matches industry “scale effort to complexity.”

#### 2.11 Transcripts and news are secondary memory

Industry: secondary sources expand context rot risk.

Already specified: transcripts secondary to filings; missing transcripts → degraded scorecard + wider uncertainty. Keep news_sentiment from flooding valuation context — select catalysts/risks only.

---

## 3. Mapping phases to industry patterns

| Phase | Pattern | Context strategy |
|-------|---------|------------------|
| Orchestrator | Supervisor + classification | Short state; owns phase_status only |
| 0 Background | Parallel research swarm | Isolate search; merge from raw/ |
| 1 Data 2a/2b/2c | Parallel workers | Each writes own artifacts; no shared chat bloat |
| 1b 2d | Integrator workflow | Read 2a+2b outputs only |
| 1c 2e | Deep specialist | Heavy raw_sec isolation; write structured deep dive |
| 2 Tech/Val/TSR | Parallel specialists | Agent 4 context-isolated from fundamentals |
| 2.5 Stress | Parallel scenarios | Condensed returns → risk_bridge |
| 3 Charts | Tool-heavy single agent | Deterministic compute preferred |
| 4 Reports | Parallel writers | Consume registries, not re-research |
| 5 Audit | Evaluator | External primary checks; FAIL→fix loop |

This is essentially Anthropic Research + OpenAI harness ideas applied to equity research.

---

## 4. Prompt engineering checklist for `agent_prompts.md` edits

When editing any agent template:

- [ ] Inputs/outputs paths explicit  
- [ ] Justification contract restated for that agent’s judgment types  
- [ ] Tools minimal and non-overlapping  
- [ ] Forbidden reads listed (esp. Agent 4)  
- [ ] Handoff four sections required  
- [ ] Effort/budget hints if swarm  
- [ ] “Never invent; widen uncertainty” for data gaps  
- [ ] No encyclopedia paste of entire Agents.md  

---

## 5. Suggested experiments (optional future work)

1. **Measure tokens per phase** on a full JPM-class run; set budgets.  
2. **A/B subagent return sizes** — does forcing 1–2k returns improve parent merge quality?  
3. **Compaction audit** — if any long single agent uses auto-summarize, eval whether filing numbers survive.  
4. **Doc gardening agent** — flag stale sector module ranges vs current market (modules are advisory; still prevent silent rot).  
5. **Nested AGENTS.md** for `scripts/` or `templates/` if agents thrash on conventions.  

---

## 6. What not to copy blindly

| Industry idea | Why not wholesale here |
|---------------|------------------------|
| “0 human-written code” | This harness’s product is research quality, not pure codegen; humans own methodology |
| Minimal merge gates | Financial research needs **stricter** gates (audit PASS, schema, probability sums) |
| Always multi-agent | Valuation is highly coupled; single Agent 5 with hooks beats fragmented valuers |
| Million-token dump of all filings | Context rot + cost; contradicts raw_sec + extract pattern |
| Replace schemas with freeform memory | Schemas are the mechanical truth layer |

---

## 7. One-paragraph north star

Keep the stock-research system a **hybrid workflow+agent harness**: orchestrator-owned resume state, isolated specialist agents, disk as system of record, progressive disclosure of sector/region knowledge, mechanical schemas and audits as backpressure, and context treated as a scarce attention budget — using large modern windows for *headroom*, not as an excuse to stop selecting, compressing, and isolating.

---

## 8. Related files in this pack

- Harness industry detail → [01_harness_engineering.md](./01_harness_engineering.md)  
- Context techniques → [02_context_engineering.md](./02_context_engineering.md), [05_techniques_large_context_models.md](./05_techniques_large_context_models.md)  
- Prompts & patterns → [03_prompt_engineering_2026.md](./03_prompt_engineering_2026.md), [04_agentic_patterns.md](./04_agentic_patterns.md)  
- Citations → [07_sources_bibliography.md](./07_sources_bibliography.md)

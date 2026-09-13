# Agentic Research — Latest Findings (2025–2026)

**Compiled:** 2026-08-09  
**Scope:** Systems that *do research* (plan → search → read → verify → synthesize → cite), not coding agents.  
**Method:** Primary lab posts + papers + two scout subagents + primary fetches (Anthropic, OpenAI, Google, LangChain, DeepResearch Bench, Manus, MAST, etc.).

---

## 1. What “agentic research” is now

A distinct product class emerged in early 2025 and matured through 2026:

> Long-horizon agents that autonomously **plan**, **browse/retrieve**, **read multi-format sources**, **iterate**, and emit **citation-rich reports** — compressing hours of desk research into minutes.

Canonical commercial systems:

| System | Lab | Distinctive trait |
|--------|-----|-------------------|
| Deep Research | OpenAI | o3-class RL on browsing; 5–30+ min; strong hard multi-hop |
| Claude Research | Anthropic | Explicit multi-agent orchestrator–workers + CitationAgent |
| Gemini Deep Research / Max | Google | Plan UX, Workspace grounding, multimodal, async jobs |
| Perplexity Deep Research | Perplexity | Fast cited reports; high citation accuracy on some benches |
| Manus Wide Research | Manus | Many general-purpose parallel agents + VM isolation |
| Open Deep Research | LangChain (OSS) | Scope → Research → Write; configurable models/tools |

Related open stacks: Magentic-One (Microsoft, 2024), Hugging Face Open Deep Research, GPT-Researcher, Jina node-DeepResearch, etc.

---

## 2. Headline quantitative findings

| Finding | Number | Source |
|---------|--------|--------|
| Multi-agent vs single-agent (breadth research) | **+90.2%** | Anthropic (Opus lead + Sonnet workers vs Opus alone) |
| Token cost: multi-agent research vs chat | **~15×** | Anthropic |
| Token cost: single agent vs chat | **~4×** | Anthropic |
| BrowseComp variance from token usage alone | **~80%** | Anthropic analysis |
| Parallel tools/subagents latency cut | **up to ~90%** | Anthropic |
| OpenAI Deep Research BrowseComp | **~51.5%** | OpenAI (vs GPT-4o+browse **~1.9%**) |
| OpenAI Deep Research HLE | **~26.6%** | OpenAI intro |
| OpenAI Deep Research GAIA avg | **~67%** pass@1 | OpenAI intro |
| HF Open Deep Research GAIA val | **~55%** | Hugging Face |
| CodeAgent vs JSON tools (same HF setup) | **55% vs 33%** | Hugging Face |
| Gemini-2.5-Pro Deep Research RACE | **48.88** (lead) | DeepResearch Bench |
| OpenAI Deep Research RACE | **46.98** | DeepResearch Bench |
| Gemini DR effective citations / task | **~111** | DeepResearch Bench FACT |
| Perplexity DR citation accuracy | **~90%** (highest on FACT) | DeepResearch Bench |
| Multi-agent on **parallel** tasks (Finance-Agent) | **+80.9%** | Google Research scaling study (2026) |
| Multi-agent on **sequential** planning | **−39% to −70%** | Google Research scaling study |
| Independent multi-agent error amplification | **17.2×** | Google Research |
| Centralized orchestrator error amplification | **4.4×** | Google Research |
| Optimal architecture prediction on unseen tasks | **87%** accuracy | Google predictive model |
| Citation URL hallucination rate | **3–13%** | Rao et al. 2026 |
| Non-resolving citation URLs | **5–18%** | Rao et al. 2026 |
| URL-health tool reduction of dead links | **6–79×** (to &lt;1%) | Rao et al. 2026 |
| Tool-description self-rewrite time save | **−40%** | Anthropic |
| Typical deep-research $ cost | **~$1–30 / run** | Google API + industry surveys |
| Contaminated multi-agent web search (eval) | **3.7×** single-agent rate | Anthropic eval-awareness 2026 |

**Core empirical claim:** On hard research, performance scales heavily with **tokens spent productively in parallel** — multi-agent is a way to *buy more effective capacity* via separate context windows, not magic collaboration.

**Counter-claim (Google 2026):** “More agents” is **not** always better. Architecture must match **task decomposability**. Wrong architecture can *hurt*.

---

## 3. Two schools of research-agent design

### School A — Orchestrated multi-agent (Anthropic, LangChain ODR, Magentic-One)

```text
User → Scope/brief
     → Lead planner (effort budgets, spawn policy)
     → Parallel subagents (isolated windows, tools)
     → Clean findings return (not raw pages)
     → Gap loop (re-spawn if brief unsatisfied)
     → Citation agent / verification
     → Single-shot (or lightly structured) report write
```

**Wins when:** Independent investigative threads; breadth; many tools/sources.

### School B — Single strong agent + RL / test-time compute (OpenAI Deep Research, often Gemini)

```text
User → (optional clarify)
     → Long autonomous loop: plan → search → read → code → iterate
     → Cited report
```

**Wins when:** Sequential deep dives; model trained end-to-end on browsing; less coordination tax.

**2026 synthesis:** Hybrid is common — multi-agent for **gather**, single agent for **write**. LangChain explicitly abandoned parallel *section writing* after disjoint reports.

---

## 4. Google’s scaling science (extra insight, Jan 2026)

Paper: *Towards a Science of Scaling Agent Systems* ([arXiv:2512.08296](https://arxiv.org/abs/2512.08296)); blog Jan 28, 2026.

Evaluated **180 configurations** across GPT / Gemini / Claude families; architectures: Single, Independent, Centralized, Decentralized, Hybrid.

| Principle | Detail |
|-----------|--------|
| **Alignment principle** | Multi-agent helps when tasks are **parallelizable** (e.g. Finance-Agent **+81%**) |
| **Sequential penalty** | Multi-agent **hurts** strict sequential planning (−39–70%) |
| **Tool-coordination tax** | Many tools + many agents = disproportionate overhead |
| **Orchestrator as safety** | Centralized contains error amplification (4.4× vs 17.2× independent) |
| **Predictive design** | Task properties (decomposability, tool density) → choose architecture (87% optimal on held-out) |

**Implication for research harnesses:** Fan-out only where sub-questions are **truly independent**. Valuation / tightly coupled reasoning should stay single-writer. Parallel data gathering (news, peers, filings chunks, stress scenarios) is the sweet spot.

---

## 5. Architecture patterns that work for *research*

### 5.1 Scope before spend

OpenAI and LangChain: users under-specify. Product patterns:

| Mode | Behavior |
|------|----------|
| Clarifying questions | OpenAI-style intent gathering |
| Editable research plan | Gemini collaborative planning |
| Brief compression | LangChain: chat → focused **research brief** as north star |

Never start expensive fan-out without a durable brief.

### 5.2 Effort scaling in the lead prompt

Anthropic production heuristics:

| Query class | Budget |
|-------------|--------|
| Simple fact | 1 agent, 3–10 tool calls |
| Comparison | 2–4 subagents, ~10–15 calls each |
| Complex research | 10+ subagents with non-overlapping scopes |

Prevents “50 subagents for ‘who is the CEO’.”

### 5.3 Delegation contracts

Each worker needs: **objective, output format, tools/sources, boundaries**. Vague “research semiconductors” → duplicated 2021 chip crisis + three identical 2025 supply-chain searches.

### 5.4 Wide then narrow

Agents over-specify first queries → empty results. Prompt: short broad queries → survey landscape → narrow.

### 5.5 Compression is the product

- Subagents return **cleaned, cited findings** (second LLM call after tool loop).  
- Full pages on **disk**; lead holds pointers.  
- Anthropic: multi-agent wins largely by **spending more tokens in parallel windows**.  
- Manus: filesystem as unlimited external context; restorable compression.

### 5.6 Dedicated citation / verification stage

Separate CitationAgent (Anthropic) or post-hoc claim↔span mapping beats “cite while writing.”

Also distinguish:

1. **URL exists / resolves** (urlhealth tool)  
2. **Claim is supported by excerpt** (faithfulness / AIS-style)  

Rao et al. (2026): more citations ≠ better — deep research agents can hallucinate **more** URLs (3–13%) and leave 5–18% dead. Tool access without tool *use* fails.

### 5.7 Single writer for final report

Multi-agent gather → **one** synthesis pass. Parallel section-writing produced uncoordinated prose (LangChain).

### 5.8 Wide vs deep multi-agent

| Style | Shape | Example |
|-------|-------|---------|
| **Deep / specialized** | Lead + role workers | Anthropic Research |
| **Wide / homogeneous** | Many identical general agents | Manus Wide Research (enumerate N entities) |

Stock research: **wide** for peer screens / news swarms; **deep** for filing notes + valuation.

---

## 6. Research-specific failure modes

### From production (Anthropic + community)

1. Over-spawning  
2. Endless search for nonexistent sources  
3. Vague delegation → duplication / gaps  
4. SEO content farms over primary sources  
5. Over-specific first queries  
6. Synchronous lead bottleneck  
7. Error compounding on long trajectories  
8. Stateful deploy races (need checkpoint resume)

### From MAST (Cemri et al., NeurIPS 2025) — multi-agent failure taxonomy

1. **Specification failures** — wrong role, bad stop, wrong tools  
2. **Inter-agent misalignment** — withheld info, conflicting plans  
3. **Verification failures** — incomplete/incorrect checks even when “done”

### Research-epistemic failures

| Failure | Mitigation |
|---------|------------|
| Citation hallucination | Citation agent + URL health + span support |
| Source-quality bias | Authority ranking, primary-first heuristics, human sample |
| Early stop / confirmation bias | Gap loop against brief; force counter-evidence pass |
| Conflicting sources collapsed | Explicit multi-hypothesis section |
| Live-web non-reproducibility | Snapshot sources; fixed-corpus evals (BrowseComp-Plus) |
| Prompt injection from pages | Tool sandbox; no arbitrary URL construction; training rails |
| Privacy assembly across sources | Explicit PII policy |
| Intermediate plan hallucinations | Process-level eval (DeepHalluBench) — final report alone misses bad plans |
| Eval contamination / eval-awareness | Blocklists; contamination hygiene; Anthropic 2026: models can *decrypt and solve* benchmarks |

### DeepHalluBench (2026) extra insight

Hallucinations in **plans and mid-loop summaries** poison the trajectory; end-to-end report judges miss them. **Process eval and checkpoints** are required for serious research agents.

---

## 7. Context engineering extras (Manus, 2025) — beyond Anthropic

1. **KV-cache hit rate as #1 production metric** (large price gap cached vs uncached). Stable prefixes, append-only context, deterministic serialization.  
2. **Mask tools, don’t remove mid-loop** (tool-list churn kills cache + confuses history).  
3. **Filesystem as true external memory.**  
4. **Recitation** (`todo.md` rewrites) against lost-in-the-middle on long tool runs.  
5. **Keep failed tool turns** — recovery is a signal; sanitizing removes learning.  
6. **Avoid accidental few-shot ruts** from repetitive action patterns.

---

## 8. Evaluation landscape

| Benchmark | What it measures |
|-----------|------------------|
| **BrowseComp** (OpenAI) | Hard multi-hop web fact finding (1,266 Qs) |
| **BrowseComp-Plus** | Fixed corpus; separates retriever quality vs agent skill |
| **DeepResearch Bench** | 100 PhD tasks × 22 fields; RACE (report quality) + FACT (citations) |
| **DeepResearch Bench II** | InfoRecall / Analysis / Presentation rubrics; top systems still &lt;~65 total |
| **GAIA** | General assistant multi-step |
| **Humanity’s Last Exam (HLE)** | Hard knowledge ceiling |
| **DeepSearchQA** (Google) | Multi-step info seeking; used when BrowseComp memorization suspected |
| **Finance-Agent** | Domain financial reasoning (used in Google scaling study) |
| **MAST** | Multi-agent failure taxonomy |
| **DeepHalluBench** | Process/intermediate hallucinations |

**Eval design lessons:**

- Outcome-based (many valid research paths).  
- Small seed set of real queries early (~20) catches big deltas.  
- LLM-as-judge needs **reference-based adaptive criteria** (RACE ablation: removing reference hurts most).  
- Separate report quality from citation trustworthiness.  
- Live commercial tools may memorize public benches — prefer private/fresh evals for internal systems.

---

## 9. Research agents vs coding agents (harness design)

| Dimension | Research | Coding |
|-----------|----------|--------|
| Oracle | Sparse / contested sources | Tests, compiler, runtime |
| Multi-agent fit | High for independent threads | Often poor for sequential shared state |
| Verification | Citations, primary re-check, claim support | CI / types / tests |
| Memory artifact | Evidence ledger, snapshots, registries | Diffs, repo state |
| Stop rule | Coverage + novelty + budgets | Green tests |
| Human role | Scope, source taste, audit | Spec, PR review |
| Cost shape | Retrieval + synthesis dominated | Edit + review dominated |

**Implication:** A stock-research harness should optimize **provenance and audit**, not “make the tests green.” This repo’s design (justification contract, raw snapshots, handoffs, Phase 5 external re-check) is research-native.

---

## 10. Practical architecture checklist (research)

### Scope & product
- [ ] Research brief before fan-out  
- [ ] Optional HITL plan approval for high-cost runs  
- [ ] Effort scaling rules in orchestrator  
- [ ] Deep vs wide vs domain job types  

### Runtime
- [ ] Orchestrator–worker only for parallel gather  
- [ ] Worker contracts: objective / format / tools / boundaries  
- [ ] Workers return cleaned findings + paths to raw  
- [ ] Persist plan + progress outside window  
- [ ] Parallel tools inside workers  
- [ ] Single synthesis writer  

### Evidence
- [ ] Snapshot all fetches at session time  
- [ ] Claim → source id → excerpt  
- [ ] URL health + claim-support stages  
- [ ] Primary-source preference + ranking  
- [ ] No lost findings map  

### Context
- [ ] Stable prefixes for cache  
- [ ] Append-only; deterministic JSON  
- [ ] Restorable compression (drop body, keep path)  
- [ ] Recite goals on long loops  
- [ ] Keep tool errors  

### Cost / ops
- [ ] Caps: time, searches, pages, subagents, $  
- [ ] Early-stop + hard-stop with gaps listed  
- [ ] Model tiering (frontier lead, cheap workers)  
- [ ] Checkpoint resume; async jobs for multi-minute runs  
- [ ] Trace spawn graph + tokens per phase  

### Eval
- [ ] Seed golden queries  
- [ ] RACE-like report rubric + FACT-like citation metrics  
- [ ] Process-level hallucination checks  
- [ ] Human sample for source bias  

---

## 11. Mapping onto this stock-research harness

| Industry research pattern | This repo |
|---------------------------|-----------|
| Scope / brief | `00_*_README.md` required inputs + market/sector config |
| Parallel gather | Phase 1 2a/2b/2c; Phase 0 swarm; Phase 2.5 scenarios |
| Isolated contexts | Subagents + disk artifacts; Agent 4 isolation |
| Clean findings return | Registry JSON + handoffs; raw/ before merge |
| Evidence ledger | `data/`, `raw_sec/`, `latest_quarter`, `filing_deep_dive` |
| Single synthesis | Agents 7/8/11 reports after all data |
| Citation / verification | Phase 5 audit + filing-grade external re-check |
| Effort scaling | `market_context.intensity`; confidence gates |
| Hermetic snapshots | CSV/raw_sec at session time; compute scripts |
| Gap handling | Widen valuation range; never invent |

### Highest-ROI upgrades for agentic research quality

1. **Explicit research-brief artifact** before Phase 0/1 fan-out (beyond README).  
2. **Hard subagent return budgets** (1–2k tokens + paths).  
3. **URL / source health pass** on news_sentiment and web-derived claims.  
4. **Process checkpoints** on Phase 0/2.5 (not only final audit).  
5. **Effort budgets** encoded in orchestrator by company complexity.  
6. **Counter-evidence / conflict section** forced in fundamental report.  
7. **KV-cache-friendly** stable agent prompt prefixes.  
8. **Do not multi-agent the valuation write** — keep Agent 5 single-writer; multi-agent only data/risk fan-out.

---

## 12. Open problems (2026)

1. Faithful claim–source grounding at scale  
2. Adaptive early-exit without under-research  
3. True async multi-agent steering mid-flight  
4. Reproducible web research under non-stationary web  
5. Eval integrity under open tools (contamination, eval-awareness)  
6. Systematic primary-source preference under SEO ranking  
7. Explicit multi-hypothesis synthesis  
8. Multi-day scientific research loops (beyond report Q&A)  
9. Enterprise MCP prompt-injection surface  
10. Open-model parity with closed RL browsing agents  
11. Structured outputs from deep research for automation  
12. Cost that makes deep research daily-default, not premium-only  

---

## 13. One-paragraph synthesis

**Agentic research is now a mature category:** long-horizon plan–search–read–synthesize systems that spend order-of-magnitude more tokens than chat, often via multi-agent parallel windows. The strongest public evidence says multi-agent helps **breadth and parallelizable** research (+90% Anthropic; +81% Google Finance-Agent) and **hurts sequential** tasks; token spend and model quality dominate BrowseComp-like hardness; report quality and citation trustworthiness are **separate** eval axes; intermediate trajectory quality matters as much as the final PDF. Winning harnesses treat **scope, effort budgets, context isolation, cleaned handoffs, primary-source bias, dual citation checks, and process+outcome eval** as first-class — and reserve multi-agent for independent investigative threads whose value justifies ~15× chat cost.

---

## 14. Priority reading list

1. [Anthropic multi-agent research system (2025-06)](https://www.anthropic.com/engineering/multi-agent-research-system)  
2. [Google — Science of scaling agent systems (2026-01)](https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/) · [arXiv:2512.08296](https://arxiv.org/abs/2512.08296)  
3. [OpenAI BrowseComp](https://openai.com/index/browsecomp/) · [Introducing Deep Research](https://openai.com/index/introducing-deep-research/)  
4. [LangChain Open Deep Research (2025-07)](https://www.langchain.com/blog/open-deep-research)  
5. [DeepResearch Bench](https://deepresearch-bench.github.io/) · [arXiv:2506.11763](https://arxiv.org/abs/2506.11763)  
6. [Manus Context Engineering](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)  
7. [MAST failures arXiv:2503.13657](https://arxiv.org/abs/2503.13657)  
8. [Rao et al. citation hallucinations arXiv:2604.03173](https://arxiv.org/abs/2604.03173)  
9. [DeepHalluBench arXiv:2601.22984](https://arxiv.org/abs/2601.22984)  
10. [BrowseComp-Plus arXiv:2508.06600](https://arxiv.org/abs/2508.06600)  

Full general bibliography still in [07_sources_bibliography.md](./07_sources_bibliography.md).

---

## 15. Technique IDs added for research (extend catalog)

| ID | Technique |
|----|-----------|
| AR1 | Research brief / scope phase before fan-out |
| AR2 | Effort scaling by query complexity |
| AR3 | Parallel gather, single write |
| AR4 | Clean findings return (second pass) |
| AR5 | Citation agent separate from author |
| AR6 | URL health + claim-support dual check |
| AR7 | Wide-then-narrow search policy |
| AR8 | Gap loop against brief |
| AR9 | Process-level hallucination eval |
| AR10 | Architecture chooser by decomposability (Google scaling) |
| AR11 | Wide homogeneous swarm for enumeration |
| AR12 | Primary-source / anti-SEO ranking |
| AR13 | Counter-evidence / multi-hypothesis synthesis |
| AR14 | Async job + checkpoint resume |
| AR15 | Contaminated-eval hygiene for web agents |

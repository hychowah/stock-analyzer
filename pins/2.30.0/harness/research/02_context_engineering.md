# Context Engineering (2025–2026)

## 1. From prompt engineering to context engineering

| | Prompt engineering | Context engineering |
|--|--------------------|---------------------|
| Question | What are the right words? | What is the optimal set of tokens at every step of execution? |
| Scope | Mostly system/user prompts | System prompts + tools + MCP + retrieved data + message history + memory |
| Cadence | Often once per task | **Iterative** — re-curated every turn |
| Failure mode | Bad instructions | Attention dilution, context rot, pollution, lost mid-context info |

Anthropic (Sep 2025): context engineering is the natural progression of prompt engineering for multi-turn tool-using agents.

Karpathy and others popularized the framing: building with LLMs is increasingly about **curating the informational environment**, not just wording.

---

## 2. Why context is finite even when windows are huge

### 2.1 Attention budget

LLMs have a finite “attention budget.” Every token competes. Transformers create pairwise relationships across tokens (n² scaling of attention relationships), so focus dilutes as length grows. Training distributions favor shorter sequences; position encoding interpolations for long contexts trade some precision.

### 2.2 Lost in the middle (Liu et al., 2023)

Classic finding: on multi-document QA and key-value retrieval, performance is **U-shaped** — best when relevant info is at the **beginning or end** of the context; worst when buried in the middle. Larger windows do not remove this bias; they can amplify the middle dead zone.

### 2.3 Context rot (Chroma, 2025)

Chroma’s technical report evaluated **18 frontier models** (including GPT-4.1, Claude 4 family, Gemini 2.5, Qwen3). Key results:

- Models do **not** use context uniformly.
- Performance becomes **increasingly unreliable** as input length grows — even on simple tasks under controlled conditions.
- Degradation is often **non-uniform / surprising**, not a clean linear slope.
- Implication: “just dump the whole corpus into a 1M window” is not a retrieval strategy.

**Design rule:** Treat context as a **finite resource with diminishing marginal returns**. Prefer the **smallest set of high-signal tokens** that maximizes the chance of the desired outcome.

### 2.4 Practical degradation modes in agents

| Mode | What happens |
|------|----------------|
| Context bloat | Tool outputs, failed trials, verbose logs fill the window |
| Context poisoning | Wrong intermediate conclusions get re-read as truth |
| Context anxiety | Agent rushes or declares done as window fills |
| Silent truncation | Critical middle turns drop without clear error |
| Cost explosion | Multi-agent research can use ~**4×** tokens vs chat; multi-agent ~**15×** (Anthropic Research system) |

---

## 3. Anatomy of effective context (Anthropic)

### 3.1 System prompts — “right altitude”

Two failure extremes:

1. **Brittle if-else prompts** — hardcoded procedural logic that is fragile and hard to maintain  
2. **Vague high-level guidance** — assumes shared context the model doesn’t have  

**Goldilocks:** specific enough to guide behavior; flexible enough to provide strong heuristics.

Organize with clear sections (`<background_information>`, `<instructions>`, tool guidance, output description) via XML tags or Markdown headers. Formatting matters less as models improve; **clarity and minimality** matter more.

Minimal ≠ short: include enough for adherence; start minimal with the best model, then add only what failure analysis requires.

### 3.2 Tools

Tools define the agent’s action/information surface. Design principles:

- Self-contained, robust to error, unambiguous intended use  
- **Minimal overlap** between tools (if a human can’t pick the tool, neither can the agent)  
- Token-efficient returns; encourage efficient agent behavior  
- Descriptive parameters that play to model strengths  
- Bloated tool sets are a top failure mode  

**Tool result clearing** is one of the safest light-touch compaction strategies: once a deep historical tool result is consumed, drop the raw payload from history.

### 3.3 Examples (few-shot)

Still strongly recommended. Prefer a **small set of diverse, canonical examples** over laundry lists of edge-case rules. For LLMs, good examples are “pictures worth a thousand words.”

### 3.4 Message history & runtime state

Must be actively managed — not left to accumulate forever.

---

## 4. Four strategies: Write / Select / Compress / Isolate

LangChain community framing (Lance Martin et al., widely adopted 2025–2026):

### 4.1 Write context

**Save information outside the window** so the agent can continue the task later.

Examples:

- Scratchpads / NOTES.md / progress files  
- Memory tools (file-based or vector)  
- Structured state machines / session registries  
- Feature lists and exec plans committed to git  
- Anthropic “structured note-taking” / agentic memory  

Write is how long-horizon work survives session boundaries.

### 4.2 Select context

**Pull only relevant tokens in** at decision time.

Examples:

- RAG / hybrid search  
- Just-in-time file reads via path identifiers  
- Tool-mediated queries (`head`/`tail`, SQL, grep) instead of full dumps  
- Progressive disclosure maps (AGENTS.md → docs)  
- Hybrid: small always-on files + autonomous exploration for the rest  

Claude Code pattern: drop `CLAUDE.md` naively up front; use glob/grep to load more on demand (avoids stale indexes).

### 4.3 Compress context

**Retain only tokens required** for the next steps.

Examples:

| Technique | Notes |
|-----------|--------|
| Compaction / summarization | Summarize history; reinit window with summary + critical recent state |
| Tool-result clearing | Drop old raw tool payloads |
| Dual-form tool results | Full form on disk; compact form in model context |
| Schema-driven summaries | Force structure so compression is auditable |
| Active / Focus-style agents | Agent decides when to consolidate learnings and prune trial-and-error logs |

**Compaction craft (Anthropic):** Tune on complex traces — first maximize **recall** (don’t drop critical details), then improve **precision** (drop superfluity). Over-aggressive compaction loses subtle facts that matter later.

Claude Code example: compress history while keeping architectural decisions, unresolved bugs, implementation details; discard redundant tool outputs; continue with compressed context + recently accessed files.

### 4.4 Isolate context

**Quarantine heavy work** so the main agent’s window stays clean.

Examples:

- Subagents with own windows that return 1–2k token distilled summaries after using tens of thousands of tokens  
- Orchestrator-worker research patterns  
- Sandbox / filesystem offloading (full data lives on disk; agent holds pointers)  
- Separate evaluator agents so critique context doesn’t pollute generation  

Anthropic multi-agent Research: subagents are **compression devices** — parallel exploration with separate windows, then condensation for the lead.

---

## 5. Just-in-time vs pre-retrieval

| Approach | Pros | Cons |
|----------|------|------|
| Pre-RAG everything | Fast first answer | Stale indexes; irrelevant chunks; lost-in-middle risk if dump is huge |
| Just-in-time navigation | Fresh; progressive; mirrors human file use | Slower; needs good tools/heuristics or agent wanders |
| Hybrid | Best of both | Needs clear policy of what is always-on |

**Metadata as signal:** folder hierarchy, naming, timestamps help agents (and humans) decide relevance without full content loads.

---

## 6. Long-horizon techniques (Anthropic triad)

For work spanning tens of minutes to hours (migrations, multi-phase research):

1. **Compaction** — conversational continuity when a single flow exceeds the window  
2. **Structured note-taking** — durable milestones across resets (Pokémon agent example: multi-hour strategies after reading its own notes)  
3. **Sub-agent architectures** — parallel depth with isolated pollution  

Choice by task:

| Task shape | Prefer |
|------------|--------|
| Lots of back-and-forth in one conversation | Compaction |
| Iterative development with clear milestones | Note-taking + feature lists + git |
| Breadth-first research / many sources | Multi-agent isolation |

**Even larger future windows will not remove the need for these** when peak reliability is required — pollution and relevance remain.

---

## 7. Memory architecture: context is RAM, not disk

Practitioner framing (2026):

| Layer | Analogy | Properties |
|-------|---------|------------|
| Context window | RAM / working memory | Volatile, limited, degrades under load |
| Session files / progress | Sticky notes on desk | Survives process if written; must be reloaded |
| Repo / DB / vector memory | Disk | Persistent; needs selection to re-enter RAM |
| Mechanical systems (tests, lints) | Hardware interlocks | Not memory — **truth checks** |

Agent failures often come from treating the window as permanent storage.

---

## 8. Active context compression research

Example direction (arxiv 2026 “Focus Agent” style work):

- Context bloat on long-horizon software tasks  
- Agent autonomously consolidates key learnings into a persistent Knowledge block  
- Actively prunes raw interaction history *intra-trajectory*  
- Targets trial-and-error noise and lost-in-the-middle poisoning  

Takeaway for production harnesses: compression should be a **first-class control loop**, not an emergency only at hard token limits.

---

## 9. Operational playbook

### 9.1 Token budget hygiene

1. Always-on core: short map + current task + critical constraints  
2. Load deep docs only when the task needs them  
3. Prefer tools that return small, structured results  
4. Write large intermediate results to files; pass paths  
5. Clear or summarize tool results after use  
6. Isolate searches and bulk analysis in subagents  
7. Position critical instructions at **start and/or end**; avoid burying in the middle of huge dumps  
8. Measure: track tokens per phase, fail rates vs context size  

### 9.2 What to put at the edges of the window

- **Start:** identity, hard constraints, success criteria, map of where truth lives  
- **End (near generation):** current task, latest observations, exact output schema / next action  
- **Middle:** bulky retrieved material (riskiest zone) — keep short or structured  

### 9.3 Anti-patterns

- Dumping entire 10-Ks or chat logs into the parent agent  
- Fifty overlapping tools  
- Monolithic instruction files that grow without pruning  
- Compacting without eval of lost critical details  
- Multi-agent for tightly coupled sequential coding without isolation benefits  
- Assuming “1M context = no retrieval needed”  

---

## 10. Evaluation of context strategies

Treat context configs like code modules:

- Benchmark context efficiency (accuracy / tokens)  
- Needle-in-haystack is necessary but not sufficient  
- Evaluate on **agent traces** (tool misuse, premature stop, duplication)  
- A/B compaction prompts for recall vs precision  
- Anthropic: multi-agent Research found token usage alone explained ~80% of variance on hard browsing evals — but **model upgrades beat naive token doubling**  

---

## 11. Summary principles

1. Context is a scarce attention budget with rot.  
2. Curate the smallest high-signal set every turn.  
3. Write durable state outside the window.  
4. Select just-in-time; don’t pre-load the world.  
5. Compress aggressively but evaluate what you lose.  
6. Isolate heavy exploration.  
7. Prefer mechanical truth (tests, schemas) over memory of prose.  
8. Larger windows are capacity, not free reliability.  

Continue: [03_prompt_engineering_2026.md](./03_prompt_engineering_2026.md) · [05_techniques_large_context_models.md](./05_techniques_large_context_models.md)

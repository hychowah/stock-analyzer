# Techniques for Latest Model Scales & Context Windows

This document focuses on techniques that matter **specifically because** models are larger, context windows are 100K–2M+ tokens, and agents run multi-hour trajectories.

## 1. What “latest size” changes (and what it doesn’t)

### 1.1 What improved

| Capability | Effect on harness design |
|------------|--------------------------|
| Stronger instruction following | Less brittle prompt syntax; more reliance on clear goals |
| Better tool use | Smaller tool sets with better descriptions beat huge menus |
| Long context capacity | Can hold more *selected* state; multi-file reasoning easier |
| Reasoning / extended thinking modes | Internal planning tokens; less forced CoT prose |
| Cheaper/faster mid-tier models | Subagent fan-out economically viable |

### 1.2 What did **not** go away

| Persistent limit | Implication |
|------------------|-------------|
| Context rot (all 18 models in Chroma study) | Never “just stuff the window” |
| Lost-in-the-middle | Position critical content at edges |
| Quadratic attention cost / latency / $ | Long contexts are expensive even when they fit |
| Session boundaries for multi-day work | Still need handoff artifacts |
| Self-evaluation bias | Still need separate critics / mechanical gates |
| Training-data prior for shorter seqs | Long-range precision weaker than short-context |

**Rule:** Use large windows as **headroom for high-signal content**, not as a substitute for retrieval, structure, and compression.

---

## 2. Context window optimization techniques (2026 toolkit)

### 2.1 Progressive disclosure

**Always-on:** ~50–150 lines of maps + hard constraints + current task.  
**On-demand:** design docs, schemas, long filings, transcripts via tools.

OpenAI: AGENTS.md as ToC. Anthropic: CLAUDE.md + glob/grep. Both reject encyclopedia dumps.

### 2.2 Just-in-time loading

Keep **pointers** (paths, URLs, query ids), not full objects. Load with:

- `read` with line ranges  
- `grep` / structured search  
- SQL / API with limits  
- `head`/`tail` for large artifacts  

Mirrors human file systems; avoids stale embedding indexes for rapidly changing code.

### 2.3 Hierarchical summarization

```text
Raw tool output (10k–100k tokens)
  → local summary (500–2k)
    → lead agent synthesis (bullet findings)
      → final report
```

Each layer is a **lossy but intentional** compress. Audit critical numbers against raw sources (this stock harness’s Phase 5 audit pattern).

### 2.4 Tool-result clearing & dual returns

- After model consumes a large tool result, **clear raw content** from history; keep a short digest + path to full file.  
- Tools can return `{compact: ..., full_path: ...}` by policy.  

### 2.5 Compaction / server-side summarization

When approaching limits:

1. Summarize history with a prompt tuned for **recall then precision**  
2. Preserve decisions, open bugs, file paths, exact numbers needed  
3. Re-seed with summary + last N turns / last accessed files  
4. Prefer **session reset + handoff files** when anxiety or pollution is high  

### 2.6 Subagent isolation (token sharding)

Split the problem so each window stays “local”:

| Work type | Isolate? |
|-----------|----------|
| Web/search breadth | Yes |
| Large corpus scan | Yes |
| Single-file edit with tests | Often no |
| Final synthesis | Parent only, condensed inputs |

Anthropic: workers may spend tens of thousands of tokens; return ~1–2k summaries.

### 2.7 Structured external memory

| Store | Content |
|-------|---------|
| Progress / phase_status | What’s done, resume hint |
| Feature/task JSON | Status flips only |
| Notes / ADRs | Decisions with status |
| Git | Recoverable snapshots |
| Vector DB (optional) | Soft retrieval; never sole source of truth for numbers |

### 2.8 Active pruning of trial-and-error

Failed experiments poison future reasoning. Policies:

- Keep “what we learned,” drop stack traces after fix  
- Cap retries; summarize failed approaches  
- Research agents: don’t re-read every dead-end SERP  

### 2.9 Chunking & selective RAG (still relevant)

Even with 1M windows:

- Retrieve top-k high-relevance chunks  
- Rerank  
- Put answer-critical chunks near the **question** (often end)  
- Cite sources for audit  

“Long context kills RAG” is **false** under context rot evidence.

### 2.10 Prompt compression algorithms

Learned or extractive compressors (LLMLingua-style and successors) can shrink prompts for cost. Use when:

- Same large static preamble is reused often  
- You can eval that task accuracy holds  

Prefer human-structured progressive disclosure for agent systems you control end-to-end.

---

## 3. Positioning strategy for large windows

Empirical positioning guidance:

| Content | Preferred position |
|---------|-------------------|
| System identity & hard constraints | Very start |
| Large retrieved docs | Middle (risk zone) — keep short |
| Current question / task / schema | Near end |
| Few-shot examples | Early-middle, before bulk data, or near task |
| “Answer in JSON schema S” | Immediately before generation |

For multi-million-token models (e.g. Gemini-class): placement is *more* consequential because the middle is vast.

---

## 4. Cost–latency–quality tradeoffs

### 4.1 Tokens explain a lot of agent quality

Anthropic Research: token usage explained ~**80%** of variance on hard browsing; model choice and tool-call count also mattered. Upgrading model beat simply doubling tokens on older model.

### 4.2 Multi-agent cost envelope

| Interaction | Relative tokens (order of magnitude) |
|-------------|--------------------------------------|
| Chat | 1× |
| Single agent | ~4× |
| Multi-agent research | ~15× |

**Policy:** Turn multi-agent on only when expected value > cost and parallelism is real.

### 4.3 Latency

Long contexts increase prefill time. Mitigations:

- Cache stable system prefixes when provider supports prompt caching  
- Smaller subagent models for retrieval grunt work  
- Parallel subagents for wall-clock, not serial mega-context  

### 4.4 Model tiering

| Role | Model tier tendency |
|------|---------------------|
| Lead planner / synthesizer | Frontier |
| Narrow retrieval / format / lint-fix | Mid / fast |
| Embedding / rerank | Specialized small models |
| Final audit of critical claims | Frontier + tools to primary sources |

---

## 5. Techniques that exploit stronger models

### 5.1 Less scaffolding, more verification

As models improve:

- Reduce hardcoded procedural prompt branches  
- Increase mechanical tests and schema validation  
- Let the model choose tools within a **small, well-described** set  

Anthropic’s long-run advice: “do the simplest thing that works” and expect less prescriptive engineering over time — **while** still treating context as scarce.

### 5.2 Agents improving tools and prompts

Claude 4-class models can diagnose prompt failures and rewrite tool docs after self-testing. Close the loop:

1. Detect failure mode from traces  
2. Propose prompt/tool-doc patch  
3. Run eval suite  
4. Merge if metrics improve  

### 5.3 Skills / capability packs

Load domain packs (harness skills, MCP servers, runbooks) only when the task needs them — progressive capability disclosure analogous to progressive context disclosure.

### 5.4 Structured outputs

Use JSON schema / constrained decoding for inter-agent messages and registry files. Reduces freeform drift that large models can still produce under long polluted context.

### 5.5 Justification & provenance contracts

Force agents to attach `rationale` / `basis` / sources to judgments. Large models can invent fluent nonsense; provenance contracts make audits tractable (central to this repo’s design).

---

## 6. Techniques for multi-hour / multi-session runs

| Technique | Why it matters at scale |
|-----------|-------------------------|
| Initializer vs worker prompts | First window sets durable world; later windows don’t re-one-shot |
| Feature lists with `passes` flags | Prevents premature victory under large partial context |
| Baseline verify before build | Prior session may have left latent bugs |
| Git commit per increment | Recovery from context-corrupted edits |
| Resume maps (`phase_status`) | Orchestrator doesn’t re-run completed work |
| Handoffs (“where it’s soft”) | Next agent/auditor sees uncertainty, not just artifacts |
| Overnight autonomy with escalation | Humans sleep; agents continue only inside harness |

---

## 7. Anti-patterns specific to large windows

1. **Window stuffing** — “It fits, so include it.” Causes rot.  
2. **Fake RAG retirement** — dropping retrieval because context is 1M.  
3. **Uncached mega system prompts** — cost and latency without caching.  
4. **50 MCP tools always connected** — decision paralysis + token overhead.  
5. **Trusting mid-context numbers** without re-read of source — lost-in-middle silent errors.  
6. **Compaction without numeric rehydration** — summaries drop exact figures agents later invent.  
7. **One agent owns entire monorepo context** — prefer nested maps and subagents.  

---

## 8. Recommended default stack (2026)

For a serious research or coding harness on frontier models:

1. **Short map** always in context  
2. **Phase/task state** on disk, reloaded each session  
3. **JIT tools** for deep artifacts  
4. **Subagents** for breadth and bulk  
5. **Compaction + tool clearing** for long single sessions  
6. **Mechanical gates** (schema, tests, linters, audit scripts)  
7. **Frontier lead + cheaper workers** when parallel  
8. **Eval suite** for prompt/context regressions  
9. **Position** constraints and current task at edges  
10. **Never invent** — widen uncertainty when data missing  

---

## 9. Quick reference: map techniques → failure modes

| Failure mode | Technique |
|--------------|-----------|
| Context rot / diluted attention | Select, compress, progressive disclosure |
| Lost-in-the-middle | Reposition critical tokens; shorten middle |
| Session amnesia | Write progress, git, phase maps |
| Premature done | Feature JSON + skeptical evaluator |
| Cost blowups | Effort budgets, model tiering, tool clearing |
| Hallucinated facts | Primary-source tools + audit + provenance fields |
| Architectural drift | Linters, GC agents, golden principles |
| Tool confusion | Minimal distinct tools; rewrite descriptions from traces |

See [06_implications_for_this_harness.md](./06_implications_for_this_harness.md) for how these map onto this repository.

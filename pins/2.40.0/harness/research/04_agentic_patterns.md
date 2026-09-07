# Agentic Development Patterns (2025–2026)

## 1. Workflows vs agents

Anthropic ([Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents), Dec 2024; still foundational in 2026):

| | Workflows | Agents |
|--|-----------|--------|
| Control | Code orchestrates predefined paths | LLM dynamically directs process and tool use |
| Predictability | Higher | Lower, more flexible |
| Best for | Known pipelines, compliance, cost control | Open-ended problems, path-dependent exploration |

**Agentic systems** include both. Most production systems are **hybrids**: workflows for phases/gates; agents inside phases.

**Meta-advice that survived two years of hype:** start simple; successful teams used **composable patterns**, not elaborate frameworks for their own sake. “Do the simplest thing that works.”

---

## 2. Andrew Ng’s four design patterns (RTPM)

| Pattern | Idea | Maturity note |
|---------|------|---------------|
| **Reflection** | Generate → critique → revise (optionally separate critic agent) | Strong ROI; easy to add |
| **Tool use** | Call external functions/APIs for truth & action | Most established building block |
| **Planning** | Decompose goals into subgoals; revise on new info | Ng: less mature/predictable than R/T |
| **Multi-agent collaboration** | Specialized roles coordinate | High leverage when parallelism is real |

Research lineage includes ReAct (Yao et al.), Reflexion, HuggingGPT-style planners, AutoGen/CrewAI multi-agent frameworks.

---

## 3. Anthropic’s five workflow patterns

| Pattern | Structure | Use when |
|---------|-----------|----------|
| **Prompt chaining** | Sequential LLM steps with gates | Decomposable fixed pipelines |
| **Routing** | Classify → specialized handler | Heterogeneous inputs |
| **Parallelization** | Fan-out sections or votes | Independent subtasks or ensemble |
| **Orchestrator–workers** | Central planner assigns dynamic tasks | Unpredictable decomposition |
| **Evaluator–optimizer** | Loop until quality bar | Open-ended quality (writing, code) |

These are **workflows** (structure in code) that can wrap agent loops inside nodes.

---

## 4. Emergent production patterns (2025–2026 catalog)

Beyond the classics, industry catalogs add reliability-oriented patterns:

| Pattern | Purpose |
|---------|---------|
| **Context engineering** | Select/compress/isolate/write for window health |
| **Session protocol / shift handoff** | Multi-context-window continuity |
| **Initializer + worker** | Different first prompt vs steady-state prompts |
| **Mechanical backpressure** | Linters/tests/hooks reject invalid states |
| **Garbage collection agents** | Continuous anti-slop / anti-drift |
| **Sprint contracts** | Generator–evaluator negotiate “done” before build |
| **Skills / progressive tools** | Load specialized knowledge packs on demand |
| **Human escalation gates** | Only interrupt humans for judgment |
| **Sandbox + allowlist** | Defense in depth for tool execution |
| **Dual memory** | Working context + persistent notes/files |

---

## 5. Multi-agent architectures

### 5.1 When multi-agent wins

Anthropic Research system findings:

- **+90.2%** vs single-agent Opus on internal research eval (Opus lead + Sonnet workers)  
- Especially strong on **breadth-first** queries (many independent directions)  
- Token spend is a major driver of performance on hard search tasks (~80% variance from tokens alone on BrowseComp analysis)  
- Cost: multi-agent often **~15×** chat tokens; agents alone **~4×**  
- Economic fit: **high-value** tasks only  

**Poor fit today:** domains requiring all agents to share full context, or dense real-time coordination (many pure coding tasks).

### 5.2 Orchestrator–worker (lead researcher pattern)

```text
User query
  → Lead agent: plan, save plan to memory, spawn workers
  → Workers: parallel search/tools, interleaved thinking, return condensed findings
  → Lead: synthesize; maybe spawn more; exit when sufficient
  → Citation / audit agent: attribute claims
  → User
```

Critical implementation details:

- Persist plan **outside** window before it can be truncated  
- Detailed worker briefs (objective, format, tools, boundaries)  
- Effort scaling rules  
- Parallel spawn (3–5 typical) + parallel tools  

### 5.3 Supervisor vs swarm

| Style | Description |
|-------|-------------|
| Supervisor | Central agent assigns and integrates |
| Swarm / peer | Agents hand off more freely; harder to control |

FreeCodeCamp and framework courses emphasize choosing based on coupling and audit needs. High-stakes research/finance usually prefer **supervisor + explicit artifacts**.

### 5.4 Separation of generation and evaluation

Agents grade their own work too generously. Separate evaluator (prompted to be skeptical) with concrete rubric is a recurring success pattern in harness literature.

---

## 6. Single-agent long-running loop

Default for many coding products (Claude Code, Codex CLI):

```text
while not done:
  observe (tools, files, tests)
  reason (optionally extended thinking)
  act (edit, command, write notes)
  if context near limit: compact or hand off session
```

Enhance with:

- Compaction + memory files  
- Hooks for lint/test  
- Feature lists preventing premature done  
- Git as rollback  

**Rule of thumb:** Prefer improving the single-agent harness before adding multi-agent complexity.

---

## 7. Framework landscape (snapshot)

| Framework / product | Notes |
|---------------------|-------|
| **Claude Agent SDK / Claude Code** | Strong coding harness; compaction; memory tools; hooks |
| **OpenAI Codex** | Agent-first repo practices; skills; PR autonomy |
| **LangGraph** | Graph workflows; first-class write/select/compress/isolate support |
| **AutoGen (Microsoft)** | Multi-agent conversations; coding demos |
| **CrewAI** | Higher-level role crews |
| **MCP** | Tool interconnection standard (Anthropic-origin, widely adopted) |
| **Deep Agents (LangChain)** | Built-in compression + subagent isolation |

**Caveat:** Frameworks don’t replace harness design. Many production teams use thin custom loops + good tools.

---

## 8. Evaluation of agents

### 8.1 Why eval is hard

- Path-dependent multi-step behavior  
- Partial credit and process quality matter  
- Flaky tools / network  
- Non-determinism  

### 8.2 Practical approaches (Anthropic + community)

| Method | Use |
|--------|-----|
| Small high-quality eval sets | Catch known failure modes fast |
| LLM-as-judge with rubrics | Scalable but calibrate carefully |
| Outcome metrics | Task success, citation accuracy, test pass |
| Process metrics | Tool misuse, duplication, premature stop |
| Human review of traces | Prompt iteration gold |
| Token/latency budgets | Cost regression tests |

### 8.3 Failures to watch in multi-agent

- Spawning too many workers  
- Endless search for nonexistent sources  
- Workers duplicating the same queries  
- Cross-talk / distraction via excessive status updates  
- Lead accepting low-quality worker summaries  

---

## 9. Reliability engineering for agents

### 9.1 Compounding error

Chain n steps at reliability p → p^n system reliability. Mitigations:

- Shorter critical paths  
- Mechanical verification between steps  
- Checkpoints / git  
- Narrow tool surfaces  
- Isolation of untrusted content (prompt-injection design patterns)  

### 9.2 Security patterns (high level)

Literature on FM agents with security constraints emphasizes:

- Limit arbitrary task ability  
- Isolate untrusted data from control flow  
- Sandboxes and allowlists  
- Structured inter-agent channels (schemas), not freeform free-for-all  

### 9.3 Observability

Without traces you cannot “think like your agent.” Log:

- Prompts/context digests (careful with secrets)  
- Tool calls + latencies  
- Compaction events  
- Subagent spawn/return  
- Gate failures  

---

## 10. Product & org patterns

From OpenAI harness engineering and industry adoption:

| Shift | Meaning |
|-------|---------|
| Humans write less code | Humans design environments and acceptance criteria |
| Review becomes agent-to-agent | Humans sample and handle escalations |
| Throughput > classic merge caution | Cheap correction, expensive waiting (when gates are strong) |
| Taste is encoded | Golden principles → lints → GC agents |
| Knowledge is repo-local | If it’s not in the repo, the agent can’t use it |

Stripe, Microsoft, Square and others publicly discussed harness-style agent products (2026 industry roundups) — common themes: tool quality, evaluation, and guardrails over raw model choice.

---

## 11. Pattern selection guide

```text
Is the task open-ended and path-dependent?
  No  → Prefer workflow (chain / route / parallel)
  Yes → Agent loop

Is breadth-first exploration the bottleneck?
  Yes + high value → Multi-agent orchestrator–workers
  No → Single agent + tools + memory

Does quality need external standards?
  Yes → Evaluator–optimizer or separate QA agent

Does work exceed one context window?
  Yes → Initializer + worker, progress files, git, compaction

Can a deterministic tool decide correctness?
  Yes → Never leave it to the LLM alone
```

---

## 12. Summary

1. Prefer simple composable patterns.  
2. Ng’s four + Anthropic’s five still cover most designs.  
3. Multi-agent is a **token and isolation** strategy, not free intelligence.  
4. Separate evaluation from generation.  
5. Hybrid workflow+agent systems dominate production.  
6. Eval, security, and observability are part of the pattern, not afterthoughts.  

Next: [05_techniques_large_context_models.md](./05_techniques_large_context_models.md)

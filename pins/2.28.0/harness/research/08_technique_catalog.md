# Technique Catalog (Quick Reference)

Master list of important techniques for modern agent harnesses, prompts, and large-context models. Details and citations live in other files; this is the **index of techniques**.

## A. Harness & environment

| ID | Technique | One-liner |
|----|-----------|-----------|
| H1 | **AGENTS.md as map** | ~100-line ToC; deep truth elsewhere |
| H2 | **Repo as system of record** | If it’s not in the repo, it doesn’t exist for the agent |
| H3 | **Progressive disclosure** | Load knowledge layers only when needed |
| H4 | **Nested instruction files** | Nearest AGENTS.md wins in monorepos |
| H5 | **Initializer vs worker prompts** | First session scaffolds; later sessions increment |
| H6 | **Session orientation protocol** | pwd → progress → git → task list → init → baseline verify → work |
| H7 | **Feature/task JSON checklist** | Status flips only; resists freeform corruption |
| H8 | **Progress notes file** | End-of-session durable narrative for next shift |
| H9 | **Git as memory & recovery** | Descriptive commits; reset to last good |
| H10 | **Init/setup scripts** | Remove rediscovery tax each session |
| H11 | **Mechanical invariants** | Linters/structural tests encode architecture & taste |
| H12 | **Remediation in error messages** | Lint failures teach agents how to fix |
| H13 | **Hooks as backpressure** | Pre/post tool hooks for safety, lint, stop gates |
| H14 | **Garbage-collection agents** | Scheduled anti-drift / anti-slop refactors |
| H15 | **Doc gardening** | Detect stale docs; prefer ADRs + tests over rotting prose |
| H16 | **Agent-legible runtime** | Per-worktree apps, logs, metrics, browser CDP |
| H17 | **Golden principles → code** | When docs fail, promote rules to tooling |
| H18 | **MVH (minimum viable harness)** | Map + tasks + progress + init + git + fast tests + baseline verify |
| H19 | **Resume maps** | Explicit phase/agent status so orchestrators don’t re-run work |
| H20 | **Handoff files** | Separate “what was produced” from “where it’s soft” |

## B. Context engineering

| ID | Technique | One-liner |
|----|-----------|-----------|
| C1 | **Attention-budget mindset** | Smallest high-signal token set wins |
| C2 | **Write context** | Persist notes/state outside the window |
| C3 | **Select context** | Retrieve only what’s needed now |
| C4 | **Compress context** | Summarize/clear; keep decisions & numbers carefully |
| C5 | **Isolate context** | Subagents / sandboxes for heavy exploration |
| C6 | **Just-in-time loading** | Hold paths/queries; fetch on demand |
| C7 | **Hybrid retrieval** | Small always-on core + autonomous exploration |
| C8 | **Tool-result clearing** | Drop raw payloads after consumption |
| C9 | **Dual-form tool results** | Compact in-window; full on disk |
| C10 | **Compaction / summarization** | New window seeded from high-fidelity summary |
| C11 | **Active pruning** | Remove trial-and-error noise mid-trajectory |
| C12 | **Hierarchical summarization** | Raw → local summary → lead synthesis |
| C13 | **Structured external memory** | Files, DBs, memory tools — not chat as disk |
| C14 | **Edge positioning** | Critical constraints start; task/schema end |
| C15 | **Avoid mid-context burial** | Don’t hide key facts in the middle of dumps |
| C16 | **Prompt caching** | Cache stable prefixes for cost/latency |
| C17 | **Context health metrics** | Track tokens, rot proxies, fail rates vs length |

## C. Prompt engineering

| ID | Technique | One-liner |
|----|-----------|-----------|
| P1 | **Right altitude** | Heuristics not if-else novels or vague vibes |
| P2 | **Sectioned system prompts** | Role, goals, tools, process, output, escalation |
| P3 | **Canonical few-shots** | Few diverse examples >> edge-case rule lists |
| P4 | **Strong anti-bias rules** | Only for measured failure modes (stubs, fake done) |
| P5 | **Effort scaling rules** | Cap agents/tool-calls by query complexity |
| P6 | **Delegation contracts** | Subagent: objective, format, tools, boundaries |
| P7 | **Wide-then-narrow search** | Short broad queries first |
| P8 | **Parallel tool calling** | Independent tools/subagents concurrently |
| P9 | **Interleaved thinking** | Plan → act → evaluate observation → refine |
| P10 | **Skip naive CoT on reasoners** | Don’t force “think step by step” on thinking models |
| P11 | **Tool-description engineering** | Distinct tools; agents rewrite bad docs from traces |
| P12 | **Output schemas** | JSON/schema contracts for artifacts & messages |
| P13 | **Justification contract** | Every judgment number: value + rationale + basis |
| P14 | **Evaluator rubrics** | Concrete criteria + scored examples |
| P15 | **Chain of Verification** | Draft → verification Qs → revise |
| P16 | **Prompt-as-code ops** | Version, eval, failure-driven edits only |
| P17 | **Self-improve under review** | Model proposes prompt/tool patches; eval gates merge |

## D. Agentic patterns

| ID | Technique | One-liner |
|----|-----------|-----------|
| A1 | **Workflow vs agent split** | Code paths for known pipelines; agents for open-ended |
| A2 | **Prompt chaining** | Fixed sequential LLM steps with gates |
| A3 | **Routing** | Classify then specialized handler |
| A4 | **Parallelization** | Fan-out sections or votes |
| A5 | **Orchestrator–workers** | Lead plans; workers execute in parallel |
| A6 | **Evaluator–optimizer** | Generate ↔ critique until bar met |
| A7 | **Reflection / Reflexion** | Self or dual-agent critique loops |
| A8 | **ReAct loop** | Reason–act–observe until done |
| A9 | **Plan-then-execute** | Durable plan artifact before implementation |
| A10 | **Single-agent first** | Add multi-agent only when ceiling is real |
| A11 | **Separate gen vs eval** | Don’t trust self-grading alone |
| A12 | **Skills / capability packs** | Load specialized knowledge on demand |
| A13 | **MCP tool layer** | Standard tool interconnection |
| A14 | **Human escalation gates** | Interrupt only for judgment |
| A15 | **Sprint contracts** | Agree “done” definition before build |
| A16 | **Ralph-style PR loops** | Iterate reviews until agents satisfied (with cost awareness) |

## E. Reliability, security, eval

| ID | Technique | One-liner |
|----|-----------|-----------|
| R1 | **Deterministic tools first** | Don’t use LLM as linter/formatter |
| R2 | **Tests as non-lying specs** | Prefer tests/ADRs over rotting prose |
| R3 | **Baseline verify before extend** | Catch prior-session damage first |
| R4 | **Sandbox + FS limits + allowlists** | Defense in depth for tool execution |
| R5 | **Isolate untrusted content** | Keep retrieved text out of control flow where possible |
| R6 | **Trace observability** | Log tools, compactions, spawns for prompt iteration |
| R7 | **Primary-source audit** | Re-check claims against raw data, not just internal consistency |
| R8 | **Probability / schema machine checks** | Structural validators catch silent drift |
| R9 | **Widen uncertainty on gaps** | Never invent; expand ranges when data degraded |
| R10 | **Token & cost budgets** | Multi-agent only when EV > ~15× chat cost |
| R11 | **Model tiering** | Frontier lead; cheaper workers for bulk |
| R12 | **Compounding-error awareness** | Shorten critical paths; checkpoint often |

## F. Large-context-specific

| ID | Technique | One-liner |
|----|-----------|-----------|
| L1 | **Headroom not landfill** | Large windows ≠ dump everything |
| L2 | **Respect context rot** | All frontier models degrade with length |
| L3 | **Lost-in-middle mitigation** | Reposition + shorten middle bulk |
| L4 | **Numeric rehydration** | After summary, re-read exact figures from disk |
| L5 | **Session reset over infinite compact** | When polluted, reset + handoff files |
| L6 | **Subagent token sharding** | Parallel windows as capacity expansion |
| L7 | **Selective RAG still required** | Long context does not kill retrieval |
| L8 | **Prompt compression (careful)** | For static preambles; eval accuracy |
| L9 | **Cache stable system prefixes** | Prefill cost control |
| L10 | **Intensity-based depth** | Scale research/context by problem complexity |

## G. Recommended default combination

For a long-running research or coding system on frontier models:

**H1 + H5 + H6 + H7 + H8 + H9 + H11 + H19 + H20**  
**C1–C5 + C8 + C9 + C14**  
**P1 + P5 + P6 + P11 + P12 + P13**  
**A1 + A5 (when parallel) + A10 + A11**  
**R1 + R3 + R7 + R9 + R11**  
**L1 + L2 + L4 + L6 + L10**

## H. Agentic research (see full list in [09](./09_agentic_research.md))

| ID | Technique | One-liner |
|----|-----------|-----------|
| AR1 | Research brief before fan-out | Scope before token spend |
| AR2 | Effort scaling | Cap agents/tools by query class |
| AR3 | Parallel gather, single write | Multi-agent search; one synthesizer |
| AR4 | Clean findings return | Second pass: not raw scrapes to lead |
| AR5 | Separate citation agent | Cite after authoring, map claim→span |
| AR6 | Dual citation check | URL health + claim support |
| AR7 | Wide then narrow | Broad first queries, then drill |
| AR8 | Gap loop vs brief | Re-spawn until brief covered |
| AR9 | Process hallucination eval | Check plans/mid-summaries, not only final |
| AR10 | Architecture by decomposability | Multi-agent only if parallelizable |
| AR11 | Wide homogeneous swarm | N identical agents for enumeration |
| AR12 | Primary-source ranking | Anti-SEO / primary-first |
| AR13 | Multi-hypothesis synthesis | Surface conflicting sources |
| AR14 | Async + checkpoint | Multi-minute research as jobs |
| AR15 | Eval contamination hygiene | Web agents can solve/decrypt benches |

## Cross-links

- Deep dives: [01](./01_harness_engineering.md) · [02](./02_context_engineering.md) · [03](./03_prompt_engineering_2026.md) · [04](./04_agentic_patterns.md) · [05](./05_techniques_large_context_models.md) · [09](./09_agentic_research.md)
- This repo: [06](./06_implications_for_this_harness.md)
- Sources: [07](./07_sources_bibliography.md)

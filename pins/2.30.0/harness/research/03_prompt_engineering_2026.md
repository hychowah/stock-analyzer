# Prompt Engineering for Agents & Frontier Models (2025–2026)

## 1. What changed

Classic prompt engineering (zero/few-shot templates for single-shot classification or generation) still matters, but **agentic systems** shifted the load-bearing work to:

- System prompt **altitude** and structure  
- Tool schemas and descriptions  
- Output contracts (JSON schemas, schemas-as-code)  
- Runtime context curation (see [02_context_engineering.md](./02_context_engineering.md))  
- Evaluation loops and self-critique patterns  

Anthropic framing: prompt engineering asks for the right **words**; context engineering asks for the right **information configuration** every step.

---

## 2. Four components every agent prompt stack needs

(Adapted from Lilian Weng’s agent framing + Anthropic engineering guidance)

| Component | Role |
|-----------|------|
| **System / identity** | Who the agent is, goals, hard constraints, non-goals |
| **Tools** | What it can do; how tools map to intents |
| **Examples** | Canonical demonstrations of good behavior |
| **Context state** | Current task, memory, history, retrieved facts (managed dynamically) |

Leaving any of these to chance is a common production failure mode.

---

## 3. System prompt design

### 3.1 Right altitude (Anthropic)

- Avoid brittle procedural if-else novels.  
- Avoid vague “be helpful” with hidden assumptions.  
- Prefer clear heuristics + success criteria + boundaries.  

### 3.2 Structure that still works

Even as models get smarter, structure helps humans and tools maintain prompts:

```text
# Role
# Background / domain
# Goals & non-goals
# Hard constraints (safety, scope, file boundaries)
# Tool guidance (when to use which)
# Process (session protocol / orientation steps)
# Output contracts
# Escalation rules
```

XML tags or Markdown headers both work; consistency matters more than fashion.

### 3.3 Progressive disclosure *inside* prompts

- Short always-on instructions  
- Pointers to longer docs the agent should **read with tools** when needed  
- Nested package-level instructions that only load in relevant directories  

Mirrors OpenAI’s AGENTS.md-as-ToC pattern.

### 3.4 Strong language for known bias modes

Agents exhibit systematic biases (e.g. stub/placeholder implementations that “compile,” marking work done without E2E tests, premature victory). Explicit, strongly worded prohibitions help:

- “It is unacceptable to remove or edit tests to make them pass.”  
- “Do not mark a feature complete without user-path verification.”  
- “Never invent quotes / numbers; record gaps instead.”  

Use sparingly and only for **measured** failure modes — not for every preference.

---

## 4. Reasoning models vs classic CoT

### 4.1 Classic models (pre-reasoning or non-thinking modes)

- Explicit chain-of-thought (“think step by step”) often helps multi-step tasks.  
- Self-ask / decomposition prompts remain useful.  

### 4.2 Reasoning / extended-thinking models (o-series, Claude Extended Thinking, Gemini Thinking, etc.)

Practitioner and vendor guidance (2025–2026 consensus):

- Models already allocate internal reasoning tokens.  
- **Blindly adding “think step by step” can be redundant or harmful.**  
- Better levers: clear goals, tools, constraints, success tests, and **when** to use extended thinking.  
- **Interleaved thinking** after tool results (plan → act → evaluate observation → refine) improves tool-using agents (Anthropic Research system).  

### 4.3 Controllable scratchpads

Extended thinking as a visible planning space:

- Lead agents: assess tools, query complexity, subagent count, roles  
- Subagents: evaluate tool result quality, identify gaps, refine next query  

Prompt for *what to plan*, not for fake CoT theater.

---

## 5. Few-shot and demonstrations

Google prompt-engineering guidance historically preferred few-shot over pure zero-shot for many tasks. For agents:

| Do | Don’t |
|----|-------|
| 2–5 diverse canonical examples | Dump every edge case as rules |
| Show tool use patterns and good refusals | Only show happy paths |
| Calibrate evaluators with scored examples | Ask “is this good?” without rubric |

---

## 6. Tool-oriented prompting

### 6.1 Tool descriptions are part of the prompt

Bad descriptions send agents down wrong paths. Anthropic found agents can **rewrite tool descriptions** after testing: a tool-testing agent improved descriptions and reduced future task time ~**40%**.

Checklist for each tool:

- Distinct purpose (no functional twins)  
- Clear when-to-use / when-not-to-use  
- Parameter meanings and units  
- Failure modes and empty-result semantics  
- Token-efficient default return shape  

### 6.2 Effort scaling rules

Agents mis-scale effort. Encode explicit budgets in prompts (Anthropic Research):

| Query class | Example budget |
|-------------|----------------|
| Simple fact | 1 agent, 3–10 tool calls |
| Comparison | 2–4 subagents, ~10–15 calls each |
| Complex research | 10+ subagents with divided responsibility |

Prevents 50-subagent storms on trivial asks.

### 6.3 Parallel tool calling

Prompt and enable parallel calls when independent. Anthropic reported up to **~90% wall-clock reduction** on complex research via parallel subagents + parallel tools.

### 6.4 Search strategy: wide then narrow

Agents default to over-specific queries that return nothing. Prompt: start broad and short → survey landscape → narrow.

---

## 7. Multi-agent prompt principles (Anthropic Research)

1. **Think like your agents** — watch step-by-step traces; fix the actual failure mode.  
2. **Teach delegation** — each subagent needs objective, output format, tools/sources, boundaries. Short vague “research X” causes duplication.  
3. **Scale effort to complexity** — explicit rules.  
4. **Tool design is as critical as HCI.**  
5. **Let agents improve prompts/tools** under supervision.  
6. **Start wide, then narrow.**  
7. **Guide thinking process** with extended/interleaved thinking.  
8. **Parallelize** when independence holds.  

Instill **heuristics of skilled humans**, not rigid scripts — then add guardrails against known spirals.

---

## 8. Model-specific notes (practitioner consensus ~2026)

| Family | Tendencies / tips |
|--------|-------------------|
| **Claude** | Strong with structured XML-ish sections; long-context coding agents; benefits from explicit verification protocols and progressive file maps; extended thinking for hard multi-step |
| **GPT / Codex** | Excellent with repo maps, skills, PR loops; thrives when environment is highly legible; AGENTS.md ecosystem mature |
| **Gemini** | Very large windows — placement still matters; Google guidance often prefers shorter/direct prompts + few-shot; put specific questions **after** data context |
| **Open models** | More sensitive to format and few-shot quality; smaller effective context than advertised |

Always re-validate on *your* eval set — model behavior shifts by version.

---

## 9. Agentic prompt patterns library

### 9.1 ReAct (Reason + Act)

Interleave Thought → Action → Observation until done. Foundational for tool agents. Many production systems are ReAct variants with better state management.

### 9.2 Reflection / Reflexion

Generate → critique → revise. Can be same agent or separate critic agent (Ng). Separate critic is often more honest.

### 9.3 Plan-then-execute

Write a plan artifact first (file or structured object); execute step-by-step; update plan on discovery. Critical for multi-session harnesses.

### 9.4 Evaluator-optimizer loop

Generator produces; evaluator grades against rubric; loop until threshold or max iterations. Anthropic workflow pattern; OpenAI agent-to-agent review is a cousin.

### 9.5 Chain of Verification (CoV)

Draft answer → generate verification questions → answer them independently → revise. Reduces confident hallucinations.

### 9.6 Reverse prompting

Ask the model to propose the optimal prompt or checklist for a goal, then run that plan. Useful for one-off complex tasks; less ideal as unversioned production logic.

### 9.7 Session orientation template (coding/research)

```text
1. Confirm working directory and boundaries
2. Read progress / phase status / last commits
3. Read task list; select ONE next unit of work
4. Run init / baseline health checks
5. Execute unit of work
6. Verify with mechanical gates + domain checks
7. Update progress artifacts + commit
8. Leave clean state for next session
```

### 9.8 Justification contract (domain-specific but generalizable)

Any *decided* number or judgment requires `{value, rationale, basis}`. Forces agents to externalize reasoning in artifacts, not only in ephemeral CoT.

---

## 10. Reliability ceilings

Important research-informed caution:

- Multi-step reliability multiplies: 0.95^10 ≈ 0.60.  
- Prompt-only multi-agent systems can fail a large fraction of multistep tasks without shared context layers, schemas, and mechanical gates.  
- At enterprise scale, a **governed context layer** (definitions, policies, lineage) beats ever-longer prompts.

Prompt engineering alone hits a ceiling; architecture must absorb the rest.

---

## 11. Prompt ops (treat prompts as code)

| Practice | Why |
|----------|-----|
| Version prompts in git | Diff, review, rollback |
| Eval suites per agent | Catch regressions when models update |
| Failure-driven edits only | Prevents prompt bloat |
| Separate prompt from data | Templates + injected context |
| Log traces | “Think like the agent” requires observability |
| Self-improve loops with review | Claude-as-prompt-engineer for tool docs works well |

---

## 12. Practical template for a production subagent

```markdown
# Identity
You are <role>. You only do <scope>. You do not do <out of scope>.

# Inputs (paths)
- Read only: ...
- Write only: ...

# Protocol
1. ...
2. ...

# Tools
Use X for A; Y for B. Never use Z for A.

# Output contracts
- Artifact: path + schema
- Handoff: four required sections
- Every judgment number: {value, rationale, basis}

# Quality bar
- Mechanical: run <script>; must PASS
- Domain: ...

# Escalation
If data missing: document gap, use fallback F, widen uncertainty. Never invent.
```

---

## 13. Summary

1. For agents, prompts are one slice of a larger context stack.  
2. Right altitude + structure + canonical examples beat rule encyclopedias.  
3. Tool descriptions and effort budgets are first-class prompt engineering.  
4. Reasoning models need different CoT habits.  
5. Multi-agent needs explicit delegation contracts.  
6. Reliability requires mechanical gates and context architecture, not only better wording.  
7. Version, evaluate, and grow prompts only from measured failures.  

Next: [04_agentic_patterns.md](./04_agentic_patterns.md)

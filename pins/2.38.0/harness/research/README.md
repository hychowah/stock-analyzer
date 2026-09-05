# Research Pack: Harness, Prompt & Agentic Engineering (2025–2026)

**Compiled:** 2026-08-08 (agentic research deep-dive updated **2026-08-09**)  
**Scope:** Latest practices from AI labs (OpenAI, Anthropic, Google), engineering blogs, research papers, and practitioner write-ups on **harness engineering**, **context engineering**, **prompt engineering**, and **agentic development** — optimized for frontier model sizes and multi-hundred-thousand to multi-million token context windows. Focused follow-up: **agentic research** systems (plan→search→synthesize→cite).

## Why this pack exists

This workspace’s stock-research system is itself a multi-phase agent harness. The documents here distill what the frontier companies and research community treat as load-bearing in 2025–2026 so future harness changes can be evidence-based rather than folklore.

## Documents

| File | Topic |
|------|--------|
| [01_harness_engineering.md](./01_harness_engineering.md) | What “harness engineering” means; OpenAI Codex agent-first repo; Anthropic long-running agent harnesses; MVH checklist |
| [02_context_engineering.md](./02_context_engineering.md) | Context as finite attention budget; context rot; Write / Select / Compress / Isolate; long-horizon techniques |
| [03_prompt_engineering_2026.md](./03_prompt_engineering_2026.md) | How prompting changed for agents & reasoning models; altitude, tools, few-shot, model-specific notes |
| [04_agentic_patterns.md](./04_agentic_patterns.md) | Workflows vs agents; Ng’s four patterns; Anthropic five workflows; multi-agent orchestration & eval |
| [05_techniques_large_context_models.md](./05_techniques_large_context_models.md) | Techniques that matter specifically for large models / large windows (positioning, progressive disclosure, tool design, cost) |
| [06_implications_for_this_harness.md](./06_implications_for_this_harness.md) | Concrete mapping of findings onto this repo’s stock-research harness (`Agents.md`, phase_status, subagents, etc.) |
| [07_sources_bibliography.md](./07_sources_bibliography.md) | Primary sources with links |
| [08_technique_catalog.md](./08_technique_catalog.md) | Master technique index (H/C/P/A/R/L IDs) for quick lookup |
| [09_agentic_research.md](./09_agentic_research.md) | **Deep dive: agentic research systems** (2025–2026 products, papers, evals, extras) |

## One-page thesis (read this first)

1. **The scarce resource is not model IQ — it is attention (context) and human steering time.** Bigger windows help capacity; they do **not** uniformly improve accuracy. All frontier models show *context rot* as input length grows.
2. **Harness > prompt.** Labs converged on “design the environment” (repo maps, progress files, mechanical gates, feedback loops) more than “write a better system prompt.”
3. **Context engineering superseded pure prompt engineering** for multi-turn agents: curate the smallest high-signal token set at every step (write / select / compress / isolate).
4. **Progressive disclosure beats encyclopedia dumps.** Short `AGENTS.md` (~100 lines) as a map; deep truth in structured docs, ADRs, tests, and tools the agent loads just-in-time.
5. **Long-running work needs session bridges:** initializer vs worker agents, feature lists (JSON status), progress logs, git as memory, verify-before-build.
6. **Multi-agent pays when work is parallelizable and high-value** (research-style). Token cost can be ~15× chat; coding often prefers fewer agents with hard isolation of heavy context.
7. **Mechanical enforcement compounds; prose does not.** Linters, hooks, structural tests, and schemas beat “please follow these rules” once sessions are long.
8. **Reasoning models change prompting:** less forced CoT, more clear goals / tools / constraints; extended/interleaved thinking is a controllable scratchpad when available.

## How to use this pack

- Designing a new agent phase or subagent → start with `04` + `02`, then check `06`.
- Fighting context bloat or flaky long sessions → `02` + `05` + Anthropic long-running section in `01`.
- Tightening repo guidance (`AGENTS.md`, docs, schemas) → `01` + `06`.
- Citing claims in design docs → `07`.
- **This harness’s live map** (phases, preflight, decision-grade handoffs) → [`../HARNESS_MAP.md`](../HARNESS_MAP.md). Investment quality upgrades status → `06` §2 (2026-08-09 notes).

## Status & limitations

- Snapshot as of **2026-08-08**. The field moves fast; re-check primary lab posts before treating any number as permanent.
- Synthesizes public engineering posts, papers, and practitioner blogs — not internal lab systems.
- Not a substitute for evaluating *this* harness’s failure modes on real sessions.

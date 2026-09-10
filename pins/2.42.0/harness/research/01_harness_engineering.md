# Harness Engineering (2025–2026)

## 1. Definition

**Harness engineering** is the discipline of designing the *environment*, *feedback loops*, *state artifacts*, and *mechanical constraints* that make AI agents (especially coding and research agents) produce reliable work with minimal human intervention.

Common informal definitions:

| Source | Framing |
|--------|---------|
| Mitchell Hashimoto (early usage) | Continuous improvement of agent instruction files + toolchain that lets the agent self-verify correctness |
| OpenAI (Feb 2026) | Humans steer; agents execute. Engineers design environments, specify intent, and build feedback loops — not hand-write product code |
| Anthropic (Nov 2025) | Structure that bridges discrete context windows so agents make incremental progress and leave a clean state for the next session |
| Practitioner consensus (2026) | “Training wheels for coding agents”: repo hygiene, deterministic gates, session protocol, recovery |

**Core claim:** The same frontier model produces dramatically different results depending on the harness. Investing in the harness compounds (one lint rule / one test / one progress format benefits every future session).

---

## 2. OpenAI: Agent-first Codex harness (Feb 2026)

Primary source: [Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/) (Ryan Lopopolo).

### 2.1 Experiment design

- Empty git repo → ~1M LOC product over ~5 months
- **0 lines of manually written code** (philosophy: no human-written code)
- Small team (3→7 engineers) driving Codex; ~1,500 PRs; ~3.5 PRs/engineer/day, *increasing* with team size
- Estimate ~1/10th the time vs hand-written code for that scope
- Humans prioritize work, translate feedback into acceptance criteria, validate outcomes; when agents struggle, ask: *what capability is missing and how do we make it legible and enforceable?*

### 2.2 Failure of the “one big AGENTS.md”

They tried a monolithic instruction file. It failed for four reasons:

1. **Context is scarce** — a giant manual crowds out the task, code, and relevant docs.
2. **Everything “important” = nothing is** — agents pattern-match locally instead of navigating intentionally.
3. **It rots instantly** — stale rules become an attractive nuisance.
4. **Hard to verify** — no mechanical checks for coverage, freshness, ownership, cross-links.

### 2.3 Solution: AGENTS.md as table of contents

- Keep top-level `AGENTS.md` ~**100 lines** — a map, not an encyclopedia.
- Put the knowledge base in a structured `docs/` tree treated as **system of record**.
- Progressive disclosure: start small and stable; teach where to look next.
- Enforce mechanically: linters + CI for structure/cross-links; recurring “doc-gardening” agent for staleness.

Illustrative layout (from OpenAI post):

```text
AGENTS.md                 # ~100 lines, pointers only
ARCHITECTURE.md
docs/
  design-docs/            # indexed, verification status, core beliefs
  exec-plans/             # active / completed / tech-debt-tracker
  generated/              # e.g. db-schema.md
  product-specs/
  references/             # llms.txt style refs for tools
  DESIGN.md, FRONTEND.md, PLANS.md, SECURITY.md, ...
```

**Nested AGENTS.md:** For monorepos, place additional `AGENTS.md` per package; nearest file in the tree wins. (agents.md open format; OpenAI main repo reported dozens of nested files.)

### 2.4 Agent legibility as design goal

> Anything the agent can’t access in-context while running effectively doesn’t exist.

Implications:

- Push knowledge from Slack / Google Docs / heads into **repo-local, versioned artifacts**.
- Prefer “boring” tech with stable APIs and good training representation.
- Sometimes cheaper to reimplement a thin helper in-repo than wrap opaque libraries.
- Make the **application** inspectable: per-worktree boots, Chrome DevTools / DOM / screenshots, ephemeral logs/metrics (LogQL/PromQL).
- Single Codex runs often work **6+ hours** (including overnight).

### 2.5 Enforce invariants, not implementations

- Rigid layered architecture per domain (e.g. Types → Config → Repo → Service → Runtime → UI).
- Cross-cutting concerns only via explicit Providers.
- Custom linters + structural tests; **error messages include remediation** so agents self-fix.
- “Taste invariants”: structured logging, naming, file size limits — encoded as code, not vibes.
- Human taste continuously fed back: review comments → docs or tooling → agent-written fixes.

### 2.6 Throughput changes merge philosophy

- Minimal blocking merge gates; short-lived PRs.
- Flakes often fixed in follow-ups rather than infinite blocks.
- Agent-to-agent review loops (local + cloud); humans optional for many PRs.
- “Ralph Wiggum Loop”: iterate until agent reviewers satisfied.

### 2.7 Entropy / garbage collection

Agents **replicate existing patterns, including bad ones**. Early team spent Fridays (20% of week) cleaning “AI slop” — didn’t scale.

Solution:

- Encode “golden principles” as mechanical rules.
- Recurring background agents scan for deviations, update quality grades, open small refactor PRs.
- Continuous small debt payment > periodic big cleanups.

### 2.8 End-to-end autonomy threshold

With enough harness investment, a single prompt can drive: validate state → reproduce bug → record failure video → fix → re-validate → PR → respond to feedback → remediate CI → escalate only when judgment needed → merge.

**Caveat from OpenAI:** This depends on heavy repository-specific structure; do not assume it generalizes without similar investment.

---

## 3. Anthropic: Effective harnesses for long-running agents (Nov 2025)

Primary source: [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents).

### 3.1 Problem

Agents work in **discrete sessions** with **no memory** of prior sessions. Context compaction alone is not enough. Two failure modes on ambitious multi-session work:

| Failure | Symptom |
|---------|---------|
| One-shotting | Agent tries to build everything; exhausts context mid-implementation; next session inherits half-done undocumented mess |
| Premature victory | Later sessions see partial progress and declare the project done |

### 3.2 Two-agent harness (same tools/system; different first prompts)

1. **Initializer agent** (first context window only)
   - Sets up environment: `init.sh`, progress file (`claude-progress.txt`), initial git commit
   - Expands user goal into a comprehensive **feature list** (often 200+ end-to-end features for a full app)
   - All features start as `passes: false`
   - Prefer **JSON** for the feature list — models less likely to rewrite/destroy structure than Markdown

2. **Coding agent** (every subsequent session)
   - Make **incremental** progress (typically one feature)
   - Leave environment in a **mergeable clean state**
   - Commit with descriptive messages; append progress notes
   - Only flip feature status after real verification

### 3.3 Session orientation protocol (every coding session)

1. `pwd` / confirm work directory boundaries  
2. Read progress file + recent git log  
3. Read feature list; pick highest-priority incomplete item  
4. Run `init.sh` / start services  
5. **Baseline verify** existing core paths (catch prior-session bugs *before* adding features)  
6. Implement one feature  
7. Test as a user would (browser automation for web apps)  
8. Commit + progress update; clean exit  

### 3.4 Testing discipline

Without explicit prompting, agents mark features complete after unit tests/`curl` and miss end-to-end failures. Providing browser automation (e.g. Puppeteer MCP) and requiring human-user-style verification dramatically improved quality. Vision/tool gaps still leave blind spots (e.g. browser-native alert modals).

### 3.5 Failure-mode → harness mapping (Anthropic summary)

| Problem | Initializer | Coding agent |
|---------|-------------|--------------|
| Declares project done too early | Full feature list JSON | Always read list; work one feature |
| Leaves bugs / undocumented progress | Git + progress file | Start by reading them + baseline test; end with commit + notes |
| Marks features done without proof | Feature list structure | Self-verify; only then set `passes: true` |
| Wastes tokens on “how do I run this?” | `init.sh` | Start by using it |

### 3.6 Open questions (Anthropic)

- Single general-purpose coding agent vs specialized testing/QA/cleanup agents  
- Generalizing beyond full-stack web apps (science, finance, research workflows)

---

## 4. Community synthesis (2026 best practices)

Drawn from practitioner consolidations (OpenAI + Anthropic + Hashimoto + HumanLayer-style guidance).

### 4.1 Multi-agent roles when you do split

| Role | Job | Notes |
|------|-----|-------|
| Planner | Expand short prompt → product/feature spec | Avoid over-specifying implementation detail early (cascading errors) |
| Generator / Builder | Implement one increment against the spec | Focused context |
| Evaluator / QA | Grade against criteria; send concrete feedback | Separate from generator — agents rate own work too generously |

**Default advice:** Stay monolithic until you hit a ceiling single agents cannot clear. Multi-agent adds microservice-like complexity *plus* non-determinism.

### 4.2 Persist state outside context

Must survive sessions:

- Task/feature list (JSON status flips only)
- Progress notes
- Spec / plan
- Init/setup scripts
- Git history (recovery + orientation)

### 4.3 Feedback loops as backpressure

- Typecheckers, linters, tests, security scanners in the loop
- Feedback must be **fast** (slow loops starve iterations)
- Prefer hooks that **inject remediation context** over silent blocks when possible
- UI automation for user-visible products
- Evaluator with concrete criteria + few-shot calibration scores

### 4.4 Security / sandboxing (defense in depth)

1. OS-level sandbox  
2. Filesystem restriction to project scope  
3. Command allowlists (parse carefully for pipes/chaining)

### 4.5 Repo hygiene for agents

**Put in repo:** executable artifacts (code, tests, lint config, schemas, CI), ADRs (immutable, superseded with status).

**Dangerous in repo:** stale prose that *looks* authoritative (“how the system works” that lags reality). Agents treat discovered text as truth. OpenAI’s rule inverted: **stale info agents can find is as bad as missing info.**

**Tests beat docs for rot resistance** — a failing test is truth; prose can lie indefinitely. Specs should become tests whenever possible.

### 4.6 Deterministic tools over LLM judgment

“Don’t make the LLM do the linter’s job.” LLMs are expensive/slow vs formatters and typecheckers. Mechanical enforcement compounds; prompt reminders do not.

Hook pattern (Claude Code era):

- **PreToolUse** — safety gates (block `rm -rf`, protect `.env`)  
- **PostToolUse** — auto-format/lint; inject remaining errors as additional context  
- **Stop** — completion gates (don’t allow stop until tests pass; guard against infinite loops)  
- **Observability** — stream intent/results/compaction events

Speed matters for PostToolUse (Rust tooling preferred when available).

### 4.7 Minimum Viable Harness (MVH)

Practitioners’ “start tomorrow” kit:

1. Short root instruction file (map only)  
2. Feature/task list with machine-checkable status  
3. Progress log convention  
4. Init script for environment  
5. Git commit discipline after each increment  
6. Fast test/lint loop wired into agent lifecycle  
7. Baseline verification at session start  
8. One recurring cleanup or doc-gardening job  

---

## 5. Open format: AGENTS.md

[agents.md](https://agents.md/) — open format used by Codex, Amp, Jules, Cursor, Factory, etc. (~60k+ projects by 2026). Treat as README for agents; nest for monorepos.

Complementary files in the wild: `CLAUDE.md`, `ARCHITECTURE.md`, `PLANS.md`, exec-plan directories, `llms.txt`-style references.

---

## 6. What harness engineering is *not*

- Not model training / fine-tuning  
- Not a single magic system prompt  
- Not “more agents” by default  
- Not guaranteed permanent — as models improve, some harness layers shrink; still load-bearing for long-horizon reliability in 2026  

---

## 7. Checklist: is our harness healthy?

- [ ] Instruction entrypoint is short and navigational  
- [ ] Deep knowledge is structured, versioned, and cross-linked  
- [ ] Stale docs are actively pruned or status-tagged  
- [ ] Session handoff artifacts exist (progress + status + git)  
- [ ] Init path is scripted (no rediscovery tax each session)  
- [ ] Verify-before-extend is required  
- [ ] Quality gates are mechanical (schema, lint, tests), not prose-only  
- [ ] Heavy exploration is isolated (subagents / separate contexts)  
- [ ] Recovery path exists (reset to last good commit / regenerate plan)  
- [ ] Failures become permanent harness upgrades (test, lint, doc map)  

See also: [02_context_engineering.md](./02_context_engineering.md), [06_implications_for_this_harness.md](./06_implications_for_this_harness.md).

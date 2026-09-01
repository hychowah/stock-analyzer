# Sources & Bibliography

Research compiled **2026-08-08**. Prefer primary lab posts and papers over secondary blogs when they conflict.

## Primary — OpenAI

1. Ryan Lopopolo — *Harness engineering: leveraging Codex in an agent-first world* (2026-02-11)  
   https://openai.com/index/harness-engineering/

2. AGENTS.md open format  
   https://agents.md/

3. OpenAI Cookbook — Codex execution plans (referenced in harness post)  
   https://cookbook.openai.com/articles/codex_exec_plans

4. BrowseComp evaluation (referenced by Anthropic multi-agent analysis)  
   https://openai.com/index/browsecomp/

## Primary — Anthropic

5. *Effective context engineering for AI agents* (2025-09-29)  
   https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

6. *Effective harnesses for long-running agents* (2025-11-26)  
   https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents

7. *How we built our multi-agent research system* (2025-06-13)  
   https://www.anthropic.com/engineering/multi-agent-research-system

8. *Building effective agents* (2024-12-19)  
   https://www.anthropic.com/engineering/building-effective-agents

9. *Writing tools for AI agents – with AI agents* (linked from context engineering post)  
   https://www.anthropic.com/engineering/writing-tools-for-agents

10. Claude Agent SDK / autonomous coding quickstart  
    https://github.com/anthropics/claude-quickstarts/tree/main/autonomous-coding

11. Context engineering cookbook (memory, compaction, tool clearing)  
    https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools

12. Model Context Protocol  
    https://modelcontextprotocol.io/

13. Claude extended / interleaved thinking docs  
    https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking

## Primary — Research papers & technical reports

14. Liu et al. — *Lost in the Middle: How Language Models Use Long Contexts* (2023)  
    https://arxiv.org/abs/2307.03172

15. Chroma — *Context Rot: How Increasing Input Tokens Impacts LLM Performance* (2025-07-14)  
    https://research.trychroma.com/context-rot  
    https://www.trychroma.com/research/context-rot  
    Replication: https://github.com/chroma-core/context-rot

16. Yao et al. — *ReAct: Synergizing Reasoning and Acting in Language Models* (2022)  
    https://arxiv.org/abs/2210.03629

17. Shinn et al. — *Reflexion* (episodic memory / reflection lineage)  
    https://arxiv.org/abs/2303.11366

18. Active Context Compression / Focus Agent-style work (2026)  
    https://arxiv.org/html/2601.07190v1

19. Agentic Design Patterns: A System-Theoretic Framework (2026)  
    https://arxiv.org/html/2601.19752v1

20. Attention Is All You Need (transformer baseline)  
    https://arxiv.org/abs/1706.03762

## Primary — Google / DeepMind-adjacent guidance

21. Google Cloud — Prompt engineering overview  
    https://cloud.google.com/discover/what-is-prompt-engineering

22. Google / Kaggle — Prompt engineering whitepaper (commonly cited for Gemini placement/few-shot guidance)  
    https://www.kaggle.com/whitepaper-prompt-engineering

## LangChain / framework engineering

23. LangChain — Context engineering for agents (Write / Select / Compress / Isolate)  
    https://www.langchain.com/blog/context-engineering-for-agents  
    (also discussed: https://blog.langchain.com/context-engineering-for-agents/ → redirects)

24. langchain-ai/context_engineering notebooks  
    https://github.com/langchain-ai/context_engineering

25. LangChain docs — Context engineering in agents / Deep Agents  
    https://docs.langchain.com/oss/python/langchain/context-engineering  
    https://docs.langchain.com/oss/python/deepagents/context-engineering

26. Lance Martin — Context engineering notes (widely cited)  
    https://rlancemartin.github.io/2025/06/23/context_engineering/

## Andrew Ng / DeepLearning.AI

27. Andrew Ng — Agentic design patterns (Reflection, Tool use, Planning, Multi-agent)  
    https://www.deeplearning.ai/the-batch/how-agents-can-improve-llm-performance/

28. DeepLearning.AI — Agentic AI course materials  
    https://learn.deeplearning.ai/courses/agentic-ai/

29. AI Agentic Design Patterns with AutoGen  
    https://www.deeplearning.ai/courses/ai-agentic-design-patterns-with-autogen

## Practitioner & engineering synthesis (secondary but useful)

30. Sakasegawa — *Harness Engineering Best Practices for Claude Code / Codex Users* (2026-03-09)  
    https://nyosegawa.com/en/posts/harness-engineering-best-practices-2026/

31. Consolidated gist — Harness Engineering Best Practices from Anthropic and OpenAI  
    https://gist.github.com/celesteanders/21edad2367c8ede2ff092bd87e56a26f

32. Alex Lavaee — OpenAI agent-first codebase learnings  
    https://alexlavaee.me/blog/openai-agent-first-codebase-learnings/

33. Sourcegraph — *Context Engineering: A Practical Guide for AI Agents* (2026-05-28)  
    https://sourcegraph.com/blog/context-engineering

34. deepset — *Context Engineering: The Next Frontier Beyond Prompt Engineering* (2026-01)  
    https://www.deepset.ai/blog/context-engineering-the-next-frontier-beyond-prompt-engineering

35. Augment Code — *What Are Agentic Design Patterns? 2026 Pattern Catalog* (2026-05-18)  
    https://www.augmentcode.com/guides/agentic-design-patterns

36. Airbyte — *5 Best AI Context Window Optimization Techniques for 2026*  
    https://airbyte.com/agentic-data/ai-context-window-optimization-techniques

37. Morph / Chroma summaries on context rot  
    https://www.morphllm.com/context-rot

38. Redis — Context rot explained  
    https://redis.io/blog/context-rot/

39. Machine Learning Mastery — Prompt Engineering for Agentic AI (2026-05)  
    https://machinelearningmastery.com/prompt-engineering-for-agentic-ai/

40. Towards AI — State of Context Engineering in 2026  
    https://pub.towardsai.net/state-of-context-engineering-in-2026-cf92d010eab1

41. Towards AI — *Stop Calling It an Agent. Anthropic Calls It a Harness.* (2026-05)  
    https://pub.towardsai.net/stop-calling-it-an-agent-anthropic-calls-it-a-harness-4774d5056e7b

42. Department of Product — Agent harnesses knowledge series  
    https://departmentofproduct.substack.com/p/are-agent-harnesses-the-new-secret

43. HumanLayer — Writing a good CLAUDE.md (referenced in harness best practices)  
    https://www.humanlayer.dev/blog/writing-a-good-claude-md

44. Mitchell Hashimoto — AI adoption journey (early harness framing)  
    https://mitchellh.com/writing/my-ai-adoption-journey

45. Simon Willison — Agents definition (cited by Anthropic)  
    https://simonwillison.net/2025/Sep/18/agents/

46. Ghuntley — Ralph Wiggum Loop (cited by OpenAI harness post)  
    https://ghuntley.com/loop/

47. Matklad — ARCHITECTURE.md (cited by OpenAI)  
    https://matklad.github.io/2021/02/06/ARCHITECTURE.md.html

48. Lilian Weng — LLM Powered Autonomous Agents (2023 foundational survey)  
    https://lilianweng.github.io/posts/2023-06-23-agent/

49. Mem0 — Memory vs context window for agents (2026)  
    https://mem0.ai/blog/context-window-is-ram-not-storage-why-most-agent-failures-happen-how-to-fix-them-in-2026

50. Superagentic AI — Context / Agent engineering IMPACT framing  
    https://medium.com/superagentic-ai/context-engineering-path-towards-better-agent-engineering-412d7f9bf9f2

## Foundational adjacent concepts

51. Parse, don’t validate (boundary parsing — cited in OpenAI harness architecture philosophy)  
    https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/

52. ADR (Architecture Decision Records)  
    https://adr.github.io/

53. Working memory capacity (human analogy used by Anthropic context post)  
    https://journals.sagepub.com/doi/abs/10.1177/0963721409359277

## How to cite in future design work

- Prefer **primary** links (OpenAI/Anthropic/arXiv/Chroma) for normative claims.  
- Treat practitioner blogs as **implementation color**, not ground truth.  
- Re-fetch lab posts before major harness redesigns — versioned model behavior shifts.

## Snapshot disclaimer

Secondary sources may paraphrase primary posts incorrectly. Numbers such as “90.2% multi-agent lift,” “15× tokens,” or “18 models show context rot” should be re-checked against the original publications when used in external communications.

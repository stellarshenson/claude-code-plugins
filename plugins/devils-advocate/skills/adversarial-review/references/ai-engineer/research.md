# ai-engineer research

Fetched per canon (2026). Reference = model knows it; open source only if unsure. Full entry = model did not know it; cite the quote.

## Surfaces and copies
- [MCP transports 2026](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports): "Earlier protocol revisions established a connection-scoped session with an `initialize` handshake and allowed servers to initiate JSON-RPC requests". Rule: MCP claim names its revision; 2026-07-28 stateless, per-request negotiation, Elicitation only. Tell: handshake, Sampling or Roots documented, no revision named.
- [Copilot repo instructions](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions) - generator prompt: validate every documented command by running it
- [Cursor Rules](https://cursor.com/docs/rules.md) - reference files instead of copying contents; add rules on repeated mistakes
- [GPT-5 prompting guide 2025](https://cookbook.openai.com/examples/gpt-5/gpt-5_prompting_guide) - contradictory instructions burn reasoning tokens; find pairs that cannot both hold
Conflicts: preload vs verify: Copilot generator (trust file, search only if wrong) vs Claude Code best practices (cut what codebase answers) - judgement call, never a violation

## Context budget
- [Claude 5 context rules 2026](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models): "We removed over 80% of Claude Code's system prompt for models like Claude Opus 5 and Claude Fable 5 with no measurable loss on our coding evaluations." Rule: instruction volume is cost; unremoved legacy guardrails are debt. Tell: layer only grows, no removal measured.
- [MCP client best practices 2026](https://modelcontextprotocol.io/docs/2026-07-28/develop/clients/client-best-practices): "Loading every tool definition into the model's context window upfront wastes tokens, increases latency, and degrades model performance." Rule: tool definitions past ~1-5% of context → search, inspect, execute. Tell: every server's tools loaded at startup, uncounted.
- [Gemini CLI GEMINI.md 2026](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/gemini-md.md): "When a tool accesses a file or directory, the CLI automatically scans for `GEMINI.md` files in that directory and its ancestors up to a trusted root." Rule: deep scoped tree cheap only with just-in-time loading. Tell: startup cost argued, loader behaviour unnamed.
- [Codex AGENTS.md](https://developers.openai.com/codex/guides/agents-md/) - stops adding files past 32 KiB; later files override earlier
Conflicts: tool loading: MCP progressive discovery vs same page (mid-conversation tool changes break prompt cache) - judgement call, never a violation
Conflicts: length: Copilot 2 pages, Cursor and Agent Skills 500 lines, Codex 32 KiB vs Instructions-as-Code (longer files correlate with gains) - judgement call, never a violation

## Gates and patterns
- [Harness Engineering 2026](https://arxiv.org/abs/2602.14690): "Skills predominantly rely on static instructions rather than executable scripts." Rule: across 2,853 repos, prose sits where script would be deterministic. Tell: skill step describing check a bundled script could run.
- [Building effective agents 2024](https://www.anthropic.com/engineering/building-effective-agents) - catalogue: chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer; workflow before agent

## Graph and fan-out
Conflicts: planning: ReWOO (plan, then execute) vs ReAct (observe each step) - judgement call, never a violation
Conflicts: fan-out: Anthropic research system (+90.2%, breadth-first search) vs Cognition (interlocking edits) - judgement call, never a violation
Conflicts: human gate placement: pydantic-ai AGENTS.md (scope questions up front) vs superpowers (four stop conditions) - judgement call, never a violation

## Judges and evaluation
- [Google skills engineering 2026](https://cloud.google.com/blog/topics/developers-practitioners/behind-the-scenes-how-we-build-test-and-scale-google-agent-skills): "With each evaluation suite, we compare the performance of agents with and without each skill." Rule: instruction artefact ships eval with and without it, plus CI lint. Tell: skill or rule never compared against its absence.
- [Probe-and-Refine 2026](https://arxiv.org/abs/2606.20512): "we show that how the guidance is produced is the decisive variable ...". Rule: production method sets sign of guidance effect; tune on synthetic bug-fix probes. Tell: guidance never tested against tasks.
- [Instructions-as-Code 2026](https://arxiv.org/abs/2606.13449): "With the instruction files, 27.7% of the projects increased their merge rate by at least 20%, while 26.35% decreased it." Rule: adding instruction file is not evidence of improvement. Tell: 'file helps' claimed, no before/after measure.
- [Wang et al. 2023](https://arxiv.org/abs/2305.17926) - pairwise judge must swap candidate order and aggregate
Conflicts: internal critic: Self-Refine, Reflexion (gains) vs Huang et al., Valmeekam et al. (degradation); hinge: external signal or trained critic - judgement call, never a violation
Conflicts: adversarial pressure: Khan et al. debate, CriticGPT vs Claude Code best practices (gap-hunting reviewer reports some); hinge: ground truth - judgement call, never a violation
Conflicts: eval target: Agent-as-a-Judge (trajectory) vs Anthropic research system (end state) - judgement call, never a violation
Conflicts: file value: AGENTS.md efficiency study (runtime -28.64%) vs Instructions-as-Code (symmetric effect) - judgement call, never a violation

## Activation
- [Agent Skills descriptions](https://agentskills.io/skill-creation/optimizing-descriptions) - frame as 'Use this skill when...'; pick revision on held-out queries
- [MCP prompts 2026](https://modelcontextprotocol.io/specification/2026-07-28/server/prompts) - prompts user-controlled, tools model-controlled; auto-invoked prompt crosses control boundary

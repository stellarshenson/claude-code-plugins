# Program: Medium Article Update - Pull-Based Workflow Enforcement

## Objective

Update the Medium article `docs/medium/article_01_pull-based-workflow-enforcement.md` and its SVG illustrations to reflect the current architecture of the auto-build-claw orchestrator. The article was written before FQN naming, bundled resources, program/benchmark workflow, and the 3-file YAML model. It needs to explain how program and benchmark drive iterations and why benchmark-driven execution matters. The article should be shortened for easier reading while preserving technical depth.

## Baseline Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Article word count | ~2400 | ~1200-2000 |
| Outdated references | 8+ (agents.yaml, 4-file model, bare names, old structure, wrong repo URL) | 0 |
| Program/benchmark coverage | 0 sections | 1-2 sections |
| SVG files | 9 (may have stale content) | 9 (updated to match current architecture) |

## Work Items

- **Update article technical content** (high)
  - Scope: `docs/medium/article_01_pull-based-workflow-enforcement.md`
  - Fix repository URL from `svg-inforgraphics-claw` to `claude-code-plugins`
  - Update "Implementation example" section: 3 YAML files (not 4), FQN workflow names (`WORKFLOW::FULL`), `cli_name`, bundled resources in pip package, `orchestrate` CLI (not `orchestrate.py`)
  - Update code snippets: workflow.yaml shows FQN keys, no agents.yaml reference
  - Update namespace resolution section: strict lookup (no FULL:: fallback), shared phases vs workflow-specific
  - Add section on program-driven execution: PROGRAM.md defines objective + work items, BENCHMARK.md defines measurable evaluation, orchestrator runs iterations until benchmark score = 0
  - Explain why benchmark matters: single composite score, iteration tracking, plateau detection, prevents aimless iteration
  - Acceptance: no references to agents.yaml, correct repo URL, FQN examples, program/benchmark explained

- **Shorten article text** (high)
  - Scope: `docs/medium/article_01_pull-based-workflow-enforcement.md`
  - Reduce word count to 1200-2000 range without losing technical substance
  - Tighten verbose paragraphs - say the same thing in fewer words
  - Remove redundant explanations (the article repeats "separate process" concept several times)
  - Merge the ACP subprocess section into the gates section (it's implementation detail, not a principle)
  - Acceptance: word count 1800-2000, no key concepts lost

- **Review and update SVG illustrations** (medium)
  - Scope: `docs/medium/images/*.svg`
  - Use svg-infographics skill from `/home/lab/workspace/.claude/skills/svg-infographics/SKILL.md`
  - Review each SVG for accuracy against current architecture
  - Update `04-content-engine-separation.svg` to show 3 files (not 4), FQN naming
  - Update `05-full-workflow-agents.svg` if agent counts or phase names changed
  - Add or update SVG showing program/benchmark workflow if needed
  - Render SVGs to PNG via Playwright
  - Acceptance: all SVGs accurate, PNGs generated

- **Add theoretical foundations section** (high)
  - Scope: `docs/medium/article_01_pull-based-workflow-enforcement.md`, new SVG, `references/` folder
  - New section grounding the method in established concepts:
    - **Context coherence**: keeping instructions compact (ideally < 200 tokens of directives) so the LLM follows without divergence. Larger instruction sets cause attention dilution and selective compliance
    - **Phase-boundary reinforcement**: each phase introduces a different latent reasoning structure (research = exploratory, plan = constructive, review = evaluative). Re-injecting phase-specific instructions at transitions prevents the model from carrying over the wrong reasoning mode
    - **Readback as course correction**: forcing the agent to paraphrase instructions before acting is a comprehension probe - it re-focuses attention on the relevant subset of context, counteracting the primacy/recency bias in long contexts
    - **Independent session as unbiased classifier**: the gatekeeper subprocess has no shared reasoning chain, so it functions as an independent classifier evaluating evidence against criteria without confirmation bias from the generating session
    - **Objective function convergence**: Karpathy's autoresearch pattern - single scalar metric, fixed evaluation, iterate until convergence or plateau. This is gradient-free optimization where each iteration is a step
    - Additional concepts as discovered during research (attention sink, lost-in-the-middle, instruction hierarchy)
  - Find 2-5 academic papers that justify these statements
  - Download papers to `references/` folder in project root
  - Create SVG infographic for the theoretical section using svg-infographics skill
  - Keep language consistent with rest of article (brief, technical, no fluff)
  - Acceptance: section present with concepts explained, papers cited, SVG created, papers in references/

## Exit Conditions

Iterations stop when ANY of these is true:
1. All work items have acceptance criteria met
2. No improvement for 2 consecutive iterations (plateau)

Additionally ALL must hold:
- Article has 0 references to agents.yaml
- Article has correct repo URL (claude-code-plugins)
- Article explains program + benchmark workflow
- Word count between 1200-2000

## Constraints

- Do NOT change the article's core thesis (pull-based enforcement, three principles)
- Do NOT change the overall article structure (problem, method, implementation, limitations)
- Do NOT remove the real session transcript example
- Preserve the five failure modes section
- SVGs must follow svg-infographics skill standards from workspace

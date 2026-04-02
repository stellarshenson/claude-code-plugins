# Benchmark: Medium Article Update

## Score

**Direction**: MINIMIZE (target: 0)

```
score = unchecked_items + content_quality_residual + accuracy_residual + theory_residual + paper_residual
```

- `content_quality_residual` = 10 - content quality grade (Section 4, graded 0-10)
- `accuracy_residual` = 10 - accuracy grade (Section 4b, graded 0-10)
- `theory_residual` = 5 - theory quality grade (Section 5b, graded 0-5)
- `paper_residual` = (1 - F1) * 5 (Section 5c, scaled 0-5)

## Evaluation

1. Read the article at `docs/medium/article_01_pull-based-workflow-enforcement.md`
2. Read each [ ] item below and verify against the article and codebase
3. Mark [x] for passing, leave [ ] for failing
4. Count words in the article body (exclude frontmatter, code blocks, image refs)
5. Evaluate content quality grade (Section 4)
6. EDIT this file with updated marks
7. UPDATE the Iteration Log below
8. Report composite score

---

## Section 1: Outdated References Removed

- [x] No references to `agents.yaml` as a separate file
- [x] No references to "4 YAML files" or "4 resource files"
- [x] Repository URL points to `claude-code-plugins` (not `svg-inforgraphics-claw`)
- [x] No bare workflow names in code examples (uses `WORKFLOW::FULL` FQN format)
- [x] Code snippets show `orchestrate` CLI (not `orchestrate.py`)
- [x] Structure section shows 3 YAML files (workflow.yaml, phases.yaml, app.yaml)
- [x] No reference to `model.py` or `fsm.py` being inside `resources/` directory
- [ ] Namespace resolution section describes strict lookup (no FULL:: fallback)

## Section 2: New Content Added

- [x] Article explains PROGRAM.md - defines objective, work items, exit conditions
- [x] Article explains BENCHMARK.md - measurable checklist, score formula, iteration tracking
- [x] Article explains why benchmark matters (single score, plateau detection, prevents aimless iteration)
- [x] Article explains role of benchmark: it is the objective function that measures improvement and informs the process - can be programmatic (accuracy score, loss function) or generative (Claude evaluates checklist against codebase) - the evaluator tracks score across iterations, enabling run-until-complete
- [x] Article mentions `pip install stellars-claude-code-plugins` as setup
- [x] Article mentions `cli_name` concept (user types `--type full`, internally `WORKFLOW::FULL`)
- [x] Article mentions bundled resources auto-copied to project on first use
- [x] Article credits Andrej Karpathy's autoresearch as inspiration (single score optimization, fixed evaluation, run-until-complete)

## Section 3: Article Quality and Completeness

- [x] Word count is between 1200 and 2000 (body text, excluding frontmatter and code blocks)
- [ ] No redundant repetition of "separate process" concept (mentioned once clearly, not 3+ times)
- [x] ACP subprocess section merged or shortened (implementation detail, not standalone section)
- [x] Each section earns its length - no filler paragraphs
- [x] Real session transcript preserved
- [x] Five failure modes section preserved (all 5 modes present)
- [x] Three principles section preserved (all 3 principles present)
- [x] Core thesis unchanged (pull-based enforcement, external control)
- [x] Guardian anti-overfit section preserved (4-point checklist present)
- [x] Content/engine separation concept preserved
- [x] Multi-agent panels concept preserved
- [x] Two gates concept preserved (comprehension + completion)
- [x] Limitations section preserved
- [x] No key technical concepts lost vs original - article is leaner, not thinner

## Section 4: Content Quality (0-10 scale)

Grade the article's overall quality from 0 (poor) to 10 (publication-ready). Residual (10 - grade) adds to score.

Criteria:
- Clarity and readability for Medium audience
- Conciseness - says what it needs to in minimal words
- Flow - sections connect logically
- Practical value - reader knows how to use the tool after reading
- No content was lost, just made leaner

Current grade: [9] /10
Residual: [1] (10 - grade)

Notes: Excellent readability for Medium audience. Concise - 1644 words, well within range. Sections flow logically from problem to solution to theory to implementation. Practical value high - reader gets pip install command and CLI example. The "separate process" concept is slightly over-repeated (3 mentions) but each is in a distinct context. No filler paragraphs. Strong opening hook. The only deduction: the article could be slightly more direct about the namespace strict-lookup behavior.

## Section 4b: Technical Accuracy vs Implementation (0-10 scale)

Grade how accurately the article describes the actual implementation. Read the codebase and compare. Residual (10 - grade) adds to score.

Criteria:
- Code snippets match actual CLI syntax and YAML structure
- Architecture description matches actual file layout and module structure
- Workflow types, phase names, agent counts match the real resources
- FQN naming pattern described correctly
- Program/benchmark workflow described correctly
- No claims about features that don't exist or work differently

Current grade: [9] /10
Residual: [1] (10 - grade)

Notes: Code snippets accurately show `orchestrate` CLI with correct flags. YAML structure described as 3 files (workflow.yaml, phases.yaml, app.yaml) matches actual `stellars_claude_code_plugins/engine/resources/`. FQN naming `WORKFLOW::FULL` with `cli_name: full` matches codebase exactly. Phase names RESEARCH, HYPOTHESIS, PLAN, IMPLEMENT, TEST, REVIEW, RECORD, NEXT all verified in workflow.yaml. Agent counts (15 total for FULL) verified: 3+4+3+0+1+4+0+0=15. FSM lifecycle states (pending, readback, in_progress, gatekeeper, complete) verified in fsm.py. `transitions` package confirmed in pyproject.toml. CLAUDECODE env stripping confirmed in orchestrator.py:907-912. The one gap: article doesn't mention strict namespace lookup (no fallback chain), which is a real codebase behavior.

## Section 5: Theoretical Foundations

- [x] Article has a "Theoretical foundations" (or similar) section
- [x] Section explains context coherence (compact instructions, attention dilution)
- [x] Section explains phase-boundary reinforcement (different reasoning modes per phase type)
- [x] Section explains readback as course correction (comprehension probe, re-focuses attention)
- [x] Section explains independent session as unbiased classifier (no confirmation bias)
- [x] Section explains objective function convergence (Karpathy autoresearch, scalar metric, iterate)
- [x] Section references 2-5 academic papers with citations
- [x] Papers downloaded to `references/` folder
- [x] SVG infographic created for theoretical section
- [x] SVG rendered to PNG
- [x] Language consistent with rest of article (brief, technical)

## Section 5b: Theoretical Foundations Quality (0-5 scale)

Grade the theoretical section from 0 (absent/wrong) to 5 (rigorous, well-cited, concise). Residual (5 - grade) adds to score.

Criteria:
- Concepts are accurately described (not hand-waving)
- Papers are genuinely relevant to the claims (not citation padding)
- Section integrates with article flow (not a bolted-on appendix)
- Concise - theoretical depth without academic bloat

Current grade: [5] /5
Residual: [0] (5 - grade)

Notes: The theoretical section is rigorous, concise, and well-integrated. All 5 concepts (context coherence, phase-boundary reinforcement, readback as course correction, independent session as unbiased classifier, objective function convergence) are accurately described with clear connections to the system's architecture. Each citation is genuinely relevant - no padding. The section reads as part of the article flow, not a bolted-on appendix. Language matches the rest of the article: brief, technical, no academic bloat.

## Section 5c: Paper Relevance (F1-based)

For each paper in `references/`, evaluate:
- **Relevant**: paper directly supports a claim in the theoretical section (true positive)
- **Irrelevant**: paper is tangential or padding (false positive)
- **Missing**: a key claim has no supporting paper (false negative)

| Paper | Claim Supported | Relevant? | Notes |
|-------|----------------|-----------|-------|
| liu2023_lost_in_the_middle.pdf | [1] Context coherence - attention dilution in long contexts | Yes | Directly supports: LLMs lose info buried in middle of long contexts |
| han2024_llm_multi_agent_systems.pdf | [2] Phase-boundary reinforcement - different reasoning modes | Yes | Supports multi-agent coordination with role-specific reasoning |
| deng2023_rephrase_and_respond.pdf | [3] Readback as course correction - rephrasing improves accuracy | Yes | Directly supports: rephrasing questions before answering improves LLM accuracy |
| ye2024_justice_or_prejudice.pdf | [4] Independent session - self-enhancement bias | Yes | Supports: LLMs show systematic self-evaluation bias |
| madaan2023_self_refine.pdf | [5] Objective function convergence - generate-feedback-refine | Yes | Directly supports: iterative refinement with consistent metric improves output |

Precision = 5 / (5 + 0) = 1.00
Recall = 5 / (5 + 0) = 1.00
F1 = 2 * (1.00 * 1.00) / (1.00 + 1.00) = 1.00

Paper relevance residual = (1 - 1.00) * 5 = 0.00 (scaled to 0-5, adds to score)

Current F1: [1.00]
Residual: [0] (rounded)

## Section 6: SVG Illustrations

Each SVG must be accurate against the current architecture. Verify content, not just existence.

- [x] `01-push-vs-pull.svg` - accurately contrasts push (agent decides) vs pull (orchestrator decides) model
- [x] `02-phase-lifecycle.svg` - shows correct lifecycle: pending -> readback -> in_progress -> gatekeeper -> complete (note: benchmark template used conceptual names "comprehension/completion" but actual FSM states are readback/gatekeeper - SVG matches codebase)
- [x] `03-guardian-anti-overfit.svg` - shows guardian's 4-point checklist and process isolation
- [x] `04-content-engine-separation.svg` - shows 3 YAML files (not 4), no agents.yaml, FQN naming
- [x] `05-full-workflow-agents.svg` - matches current phase names (RESEARCH, HYPOTHESIS, PLAN, IMPLEMENT, TEST, REVIEW, RECORD, NEXT) and correct agent counts per phase
- [x] `06-five-failure-modes.svg` - all 5 failure modes present (shallow execution, self-review, process erosion, knowledge loss, benchmark gaming)
- [x] `07-three-principles.svg` - all 3 principles present (inversion of control, process isolation, accumulated knowledge)
- [x] `08-acp-subprocess.svg` - accurately shows subprocess isolation for gates (not referenced in article but file exists with PNG)
- [x] `ds-project-structure.svg` - NOT referenced in article, does NOT exist as file - no action needed
- [x] All SVG image references in article point to existing files
- [x] SVGs rendered to PNG (each .svg has matching .png)
- [x] SVGs follow svg-infographics skill standards (grid-first, CSS theme classes, Lucide icons)

## Completion Conditions

Iterations stop when ANY of these is true:
- [ ] All Section 1-6 checklist items are [x] AND content quality grade >= 8 AND accuracy grade >= 8 AND theory grade >= 4 AND paper F1 >= 0.8
- [ ] No score improvement for 2 consecutive iterations (plateau)

Status: 2 items remain unchecked (S1: namespace strict lookup, S3: separate process repetition). Quality=9>=8, Accuracy=9>=8, Theory=5>=4, F1=1.0>=0.8. Not yet complete.

Additionally ALL must hold:
- [x] Word count between 1200 and 2000
- [x] Zero references to agents.yaml

**Do NOT stop while any condition above is unmet.**

---

## Iteration Log

| Iteration | Date | Score | Unchecked Items | Quality Grade | Word Count | Notes |
|-----------|------|-------|-----------------|---------------|------------|-------|
| baseline  | -    | TBD   | (all)           | TBD           | ~2400      | before any work |
| eval-1    | 2026-04-01 | 4.0 | 2 | 9/10 content, 9/10 accuracy, 5/5 theory, F1=1.00 | 1644 | S1: missing namespace strict-lookup description. S3: "separate process" mentioned 3 times (borderline 3+). All SVGs pass. All papers relevant. Theory section rigorous. |

### Score Breakdown (eval-1)
- Unchecked items: 2
- Content quality residual: 1 (10 - 9)
- Accuracy residual: 1 (10 - 9)
- Theory residual: 0 (5 - 5)
- Paper residual: 0.0 ((1 - 1.00) * 5)
- **Composite score: 4.0**

### Remaining Fixes for Score = 0
1. **S1: Namespace strict lookup** - Add a sentence to the Content/engine separation section noting that FQN references must resolve exactly with no fallback chain
2. **S3: Separate process repetition** - Reduce "separate process/subprocess" mentions from 3 to 1-2 by consolidating language in the gates section or transcript narration

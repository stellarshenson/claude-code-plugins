# Reddit post drafts

Reddit punishes self-promotion. The "I built this for myself, here's the pain it solves" frame plays better than "introducing X." Two variants below: short for r/ClaudeAI / r/ClaudeCode (technical, knows the agent), longer for r/programming (broader audience, needs more context).

> Don't post if: you have <500 karma, your account is <30 days old, or the subreddit just had a post like this in the last week. Both subs auto-filter low-karma accounts. Check `/about/rules` on each before posting.

---

## Short variant - r/ClaudeAI / r/ClaudeCode

**Title** (300 char limit, hard):
```
I kept getting "Fixed it" from Claude when nothing was actually fixed. Built a plugin that forces it through research-plan-test-review.
```

**Body**:
```
The pattern: ask Claude to "improve error handling," it changes 2 files, says
"Fixed it." No tests run, edge cases broken. The fix is structural, not a
better prompt - the agent rationalises around prompts.

Built a Claude Code plugin called `autobuild`. You start it with
`/autobuild:run <task>`. Claude has to write PROGRAM.md (objective + scope),
then BENCHMARK.md (a measurable score), get your approval, then iterate.
Every phase has two quality gates (readback + gatekeeper). Every iteration
records the benchmark score so progress is visible.

Real example - the document-grounding pipeline shipped in the same repo was
itself optimised via autobuild. Six iterations, composite score 69.3 to 5.0,
final 1.0 cross-validation accuracy on three held-out academic papers. Full
PROGRAM, BENCHMARK, hypothesis log, CV results in the repo under
`references/grounding-optimisation/`.

Five more plugins in the same forcing-function family - one for adversarial
document review (Fibonacci risk scoring), one for SVG infographics with 6
validators that block on overlap / contrast / alignment / connector / CSS /
collision findings, one for document grounding that cuts 64-86% of tokens vs
batched generative, plus datascience and journal plugins.

Open source, MIT, install with /plugin marketplace add stellarshenson/claude-code-plugins

Repo: <link>
Article on the autobuild thesis: <medium link>
Showcase folder with real production output: <link>

Built this for myself on real client work. The receipts in the showcase
folder are real but n is small. Happy to answer questions or hear "your
benchmark is wrong" critiques.
```

---

## Longer variant - r/programming / r/MachineLearning

**Title**:
```
Forcing-function plugins for AI agents: stop "Fixed it" hallucinations with measurable benchmarks
```

**Body**:
```
The pain everyone working with agentic coding hits: ask the agent to fix
something, it changes a couple of files, says "Fixed it." Tests didn't run.
Edge cases broken. The agent's confidence is uncorrelated with whether the
work is done.

Two failure modes:

1. The agent rationalises under-spec by "making a judgement call." A prompt
   saying "always run tests" gets read as aspirational; mid-task the agent
   decides the test is "not needed for this fix."
2. The benchmark for whether work is done is defined AFTER the work.
   "Looks fixed to me" is the trap.

Both are structural, not a prompt-engineering problem. After a year of
trying better prompts, I built a plugin marketplace that imposes the
discipline mechanically.

The flagship plugin is called autobuild. You start it with /autobuild:run
<your-task>. The orchestrator forces Claude through a fixed phase lifecycle:

1. RESEARCH    - inspect existing code
2. HYPOTHESIS  - state predictions before changing anything
3. PLAN        - write PROGRAM.md (scope + acceptance criteria)
4. BENCHMARK   - write BENCHMARK.md (a measurable scalar)
5. <gate>      - you approve PROGRAM + BENCHMARK before any implementation
6. IMPLEMENT
7. TEST
8. REVIEW      - score against the benchmark, not against vibes
9. RECORD      - YAML audit log of agents, outputs, verdicts

Two independent gates per phase (readback + gatekeeper). The agent cannot
skip phases. The benchmark is locked at gate-time so the agent can't
redefine success after seeing what it built. Every iteration logs the score
trajectory so improvement (or lack of it) is visible.

Real example: the document-grounding pipeline that ships in the same repo
was itself optimised using autobuild. Six iterations, composite benchmark
score went from 69.3 to 5.0. Final 3-fold cross-validation accuracy 1.0,
zero overfit gap, on three held-out academic papers (Liu 2023, Ye 2024, Han
2024). The PROGRAM, BENCHMARK, hypothesis log with falsifiers, raw CV
results, and a forensic write-up are all in the repo under
references/grounding-optimisation/. You can read the receipts.

Five more plugins in the same forcing-function family:

- devils-advocate: builds an adversarial persona for the actual toughest
  audience of your document. Generates a Fibonacci-scored concern catalogue,
  iterates corrections until residual risk is acceptable. Versioned
  filenames embed the residual so the trajectory is visible in the file
  listing. One worked example shows residual 269 -> 2 across 8 iterations
  on an executive summary defending a missed KPI.

- svg-infographics: 13 CLI tools + 6 validators (overlap / contrast WCAG /
  alignment / connector quality / CSS compliance / pairwise collision). Plus
  Python-calculated geometry primitives, A* connector auto-routing, and
  headless Inkscape-style boolean operations on path shapes including
  one-step cutout-with-margin and outline-as-band ops nobody else exposes.
  60+ production examples in the repo.

- document-processing: three-layer lexical grounding (regex + Levenshtein +
  BM25) with optional fourth semantic layer (multilingual-e5 + FAISS). Cuts
  64-86% of grounding tokens vs batched generative grounding on real
  academic sources.

- datascience: enforces notebook structure, GPU-first ordering, rich-output
  styling, prompt-engineering technique selection.

- journal: append-only project audit trail with a deterministic CLI for
  validation, sorting, and archiving. No generative AI in the loop - format
  enforcement is regex.

Open source, MIT, runs as Claude Code plugins (skills + commands + YAML).
Adapters for other agents (Cursor / Windsurf / Cline) not done.

Repo: <link>
Articles on the underlying theses:
- autobuild: <medium link>
- svg-infographics: <medium link>

Built this for myself on real client deliverables. n is small (one user).
The receipts in the showcase folder are real. Happy to take "your
benchmark is wrong" critiques.
```

---

## Posting playbook

- Post at 9-11am ET on a weekday for r/programming. 7-9am ET for
  r/ClaudeAI (more EU readers).
- First reply within 30 minutes - have a "thanks for the question" comment
  ready for the obvious "is this just CI" / "why a marketplace not a single
  tool" / "Claude-only?" questions
- Don't cross-post both subs same day. r/ClaudeAI first; if it does well,
  r/programming a week later
- If first comment is hostile, do NOT delete - reply with the receipts
- Track: upvotes after 1h, after 6h, after 24h. <30 by 6h means it didn't
  catch; learn and move on

# HN post draft

Status: ready to paste. Pick a moment when (a) the README rework has landed on `main`, (b) the showcase folder is live, (c) you have an hour to baby-sit comments.

> Don't post if: an open issue is unanswered for >48h, CI is red, or any plugin is mid-release. HN front page traffic surfaces every paper cut.

---

## Title (80 char limit)

Pick one. Title is the entire conversion lever.

**Strongest** (specific wound, names the agent):
```
Show HN: Stop Claude from cutting corners (forcing-function plugins)
```

**Variant A** (broader audience, agent-agnostic spelling):
```
Show HN: Force your AI agent through research-plan-test-review before "fixed it"
```

**Variant B** (lean into the empirical proof):
```
Show HN: Plugins that make Claude write a benchmark before claiming a fix works
```

Avoid: "marketplace", "toolkit", "ecosystem", "framework". HN scans those as bloat.

---

## Body (3 short paragraphs + 3 bullets)

```
I built this because Claude (Code) kept saying "Fixed it" after changing 2
files, no tests run, edge cases broken. The pattern is universal across agents
- not specific to Claude - but the symptoms in agentic coding sessions are
particularly bad because the agent rationalises the under-spec by saying it
"made a judgement call".

The fix is mechanical. A plugin called `autobuild` forces Claude through a
fixed phase lifecycle (research, hypothesis, plan, implement, test, review,
record) with two independent quality gates per phase and a YAML audit log.
You start it with `/autobuild:run improve error handling`. Claude has to
write PROGRAM.md (objective + scope), then BENCHMARK.md (a measurable scalar),
get your approval, then iterate. The benchmark score is computed every
iteration so progress is visible, not vibe-checked.

Real example: the document-grounding pipeline shipped in this same repo was
itself optimised via autobuild. Six iterations, composite score 69.3 to 5.0,
final mean accuracy 1.0 with zero overfit gap on three held-out academic
papers. Full PROGRAM, BENCHMARK, hypothesis log, and CV results in the repo
under references/grounding-optimisation/.

Five more plugins in the same forcing-function family:

- devils-advocate: builds an adversarial persona for your document's actual
  toughest audience, scores concerns Fibonacci-style, iterates until residual
  is acceptable. Real trajectory in the examples folder: residual 269 to 2
  across 8 iterations on an executive summary defending a missed KPI.
- svg-infographics: 13 CLI tools + 6 validators that block delivery on
  overlap / contrast / alignment / connector / CSS / collision findings. 60+
  production examples in the repo. Stop fixing your AI's broken SVGs.
- document-processing: three-layer lexical grounding (regex + Levenshtein +
  BM25) with optional 4th semantic layer. Cuts 64-86% of grounding tokens vs
  batched generative on real sources.
- datascience: enforces notebook structure, GPU-first ordering, rich output
  styling, prompt engineering technique selection.
- journal: append-only audit trail with deterministic CLI for validation,
  sorting, archiving. No generative AI in the loop.

Repo: https://github.com/stellarshenson/claude-code-plugins
Long-form on the autobuild thesis: <medium link>
Long-form on the SVG plugin: <medium link>

Honest disclaimers:

- It's Claude-Code-first. The patterns are agent-agnostic but the install is
  Claude-specific (/plugin marketplace add ...). Adapters for Cursor /
  Windsurf / Cline are not done.
- This is opinionated. The discipline imposed is high; if you want a
  fast-and-loose experience this is not it.
- I built this for myself working on real client deliverables. The receipts
  in the showcase folder are real but the n is small.

Happy to answer questions / hear "your benchmark is wrong" critiques.
```

Word count: ~340. HN ideal is 300-450 - long enough to make the case, short enough to read in one screen.

---

## Anticipated comments + pre-drafted replies

Save this for when the comments roll in. Don't reply to every comment - reply to the top 3-5 substantive ones, and to anyone asking a specific question.

**"Why not just write better prompts?"**

> Tried that for a year. Two problems with prompts: (a) they are aspirational - the agent reads them and decides "good enough" mid-task; (b) they don't compose - a system prompt that says "always run tests" and a user prompt that says "quick fix" interpret each other ambiguously. Forcing functions in tool form are unambiguous: the orchestrator literally won't transition to RECORD until TEST returned. Belt + suspenders, not belt-instead-of-suspenders.

**"This is just a CI pipeline."**

> Closer than most replies, but no. CI runs after the code is written. autobuild runs *during* writing - the agent has to commit to a benchmark before implementing, which prevents the "I'll define success after I see what I built" anti-pattern that vibes-coding relies on. CI catches what shipped; autobuild shapes what gets written.

**"Caveman did this with one wedge. Why a marketplace?"**

> Honest answer: caveman is a sharper marketing object. This is a workshop. If you want one tool, install only autobuild - the marketplace is a la carte. The bundle is for people who keep finding the same discipline-gap on different artefact types (code, documents, SVGs, notebooks, grounding).

**"How does it handle the case where the benchmark is wrong?"**

> Two mechanisms: (a) the program-writer agent is dialogue-driven - it iterates with you on PROGRAM.md and BENCHMARK.md before any work starts, so a bad benchmark gets caught early; (b) every iteration logs the score and the inputs that produced it, so a benchmark that scores high on bad work is visible across iterations and you can rewrite it mid-run. There's also a "guardian" agent that specifically watches for benchmark-specific tuning vs genuine improvement.

**"Why Claude specifically?"**

> Tested heaviest there. Patterns generalise but install adapters for other agents are open work. Plugins are pure configuration (skills + commands + YAML) so the format port is mechanical, not a rewrite.

**"Star bait."**

> Fair charge. Counter: every claim in the README links to a real artefact in the repo. Click through. If the receipts don't hold up, downvote.

---

## After-action

Whether it goes well or poorly:

- Pin the HN comments thread URL in the repo README for 48h
- Reply to substantive comments within an hour for the first 6h after posting
- Don't reply to obvious bait - the rest of HN handles that
- If it's <50 points by hour 4, it didn't catch; pull the pin, move on
- If it does catch, the showcase folder will get the most clicks - make sure every link there resolves

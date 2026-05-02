# X (Twitter) thread drafts

Two threads below. Pick one based on tone. Both end in the same call to action.

> Don't post if: you don't have a screenshot of an actual autobuild run with the phase output visible. Tweet 1 with no image is dead on arrival. Capture one before posting.

---

## Thread A - 7-tweet feature dump (more shareable, more "marketing")

**Tweet 1** (the wound, must have an image):
```
Your AI agent will tell you "Fixed it" when nothing is fixed.

2 files changed. No tests run. Edge cases broken.

I built a plugin that forces Claude through research, plan, test, review, and audit before it can claim done. Thread on the 6 forcing-function plugins this is part of:

[ image: terminal screenshot showing autobuild phase output with the 8 phases listed ]
```

**Tweet 2 - autobuild**:
```
1/ autobuild

You start with /autobuild:run <task>. Claude has to:

- inspect code (RESEARCH)
- write PROGRAM.md (objective + scope)
- write BENCHMARK.md (measurable score)
- get your approval
- implement, test, review against the benchmark
- record YAML audit log

Two quality gates per phase.
```

**Tweet 3 - real proof**:
```
2/ This is not theoretical.

The document-grounding pipeline shipped in the same repo was optimised using autobuild itself.

6 iterations. Composite score 69.3 → 5.0. Final 1.0 cross-validation accuracy on 3 held-out academic papers. Zero overfit gap.

Receipts in the repo. ↓
```

(Substitute → with -> if you're being strict about ASCII; X renders both fine.)

**Tweet 4 - devils-advocate**:
```
3/ devils-advocate

Your reviewer / client / court / investor will tear your document apart. Claude won't.

This plugin builds an adversarial persona, scores concerns Fibonacci-style, iterates until residual risk is acceptable.

Real trajectory: residual 269 → 2 across 8 iterations.

[image: scorecard]
```

**Tweet 5 - svg-infographics**:
```
4/ svg-infographics

You ask for a diagram. Claude ships overlapping text, no dark mode, contrast failures, hand-glued paths.

13 CLI tools. 6 validators that block delivery on overlap / contrast / alignment / connector / CSS / collision findings. 60+ production examples in the repo.

[image: side-by-side broken vs validated SVG]
```

**Tweet 6 - the rest**:
```
5/ Three more plugins in the same family:

- document-processing: three-layer grounding (regex + Levenshtein + BM25) + optional semantic. Cuts 64-86% of grounding tokens vs batched generative.

- datascience: notebook structure, GPU-first ordering, rich output, prompt engineering.

- journal: append-only audit trail with deterministic CLI.
```

**Tweet 7 - CTA**:
```
6/ Open source, MIT.

/plugin marketplace add stellarshenson/claude-code-plugins

Articles:
- autobuild thesis: <medium link>
- SVG plugin thesis: <medium link>

Repo: <github link>
Showcase (real production output): <link to showcase/>

Star if useful. Critiques welcome.
```

---

## Thread B - 3-tweet "thinking out loud" (more X-native, less salesy)

**Tweet 1**:
```
The thing that broke me: Claude (Code) saying "Fixed it" when 2 files were changed, no tests run, edge cases broken.

Better prompts didn't fix this. Prompts are aspirational - the agent rationalises around them mid-task.

What worked was a forcing function in tool form.

[image]
```

**Tweet 2**:
```
The orchestrator literally won't transition to RECORD until TEST returned. The agent has to write a measurable benchmark BEFORE implementing, so it can't redefine success after seeing what it built.

Same logic shipped as 6 plugins for code, documents, SVGs, notebooks, grounding, journals.
```

**Tweet 3**:
```
Open source, MIT. Claude Code-first.

/plugin marketplace add stellarshenson/claude-code-plugins

The grounding pipeline in the repo was optimised using the orchestrator itself. 6 iterations. 1.0 CV accuracy. PROGRAM, BENCHMARK, hypothesis log all in the repo.

<github link>
```

---

## Posting playbook

- Tweet 1 needs a real image. Don't use a stock screenshot. Take 5 minutes,
  capture an actual `/autobuild:run` terminal output with the phase header
  visible.
- Post weekday morning ET (8-10am) for max US developer reach
- Reply to early supporters within 30 min - reciprocity drives the
  algorithm
- Pin the thread for 7 days
- DON'T do the "RT for $20" stuff - kills credibility on dev twitter
- If the thread is <50 likes after 6h, it didn't catch. Don't pile on with
  follow-up threads same day; let it die clean

---

## A/B title alternatives for tweet 1

Pick the one that fits your voice:

A. "Your AI agent will tell you 'Fixed it' when nothing is fixed."
B. "The pattern: ask Claude to fix something, get 'Fixed it', find 2 files changed, no tests run, edge cases broken."
C. "I built a plugin that forces Claude to write a benchmark before implementing. Six months of using it, here's what it changed."
D. "Better prompts don't stop AI agents from cutting corners. Forcing functions do."

A and D are stronger emotional hooks. B is more specific (anchors the reader in their own experience). C is most credible but slowest hook.

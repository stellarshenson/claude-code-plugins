# devils-advocate - attack your document before your reviewer does

[![GitHub Actions](https://github.com/stellarshenson/claude-code-plugins/actions/workflows/ci.yml/badge.svg)](https://github.com/stellarshenson/claude-code-plugins/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/stellars-claude-code-plugins.svg)](https://pypi.org/project/stellars-claude-code-plugins/)
[![Total PyPI downloads](https://static.pepy.tech/badge/stellars-claude-code-plugins)](https://pepy.tech/project/stellars-claude-code-plugins)

Your reviewer / client / court / investor / VP will tear your document apart. Claude won't. Claude will tell you it looks great and ship.

This plugin builds an adversarial persona for the document's actual toughest audience, harvests verifiable facts from source material, generates a risk-scored concern catalogue, and iterates corrections until residual risk is acceptable. Risk uses a Fibonacci scale (1-8) for likelihood and impact (1-64 combined). Every iteration produces a measurable residual; versioned filenames embed it (`<name>_v07_15.md` where 15 is the residual) so the trajectory is visible in the file listing.

**Real trajectory from `examples/executive-pushback-analysis.md`**: an executive summary defending a missed KPI, baseline residual 269 across 21 concerns, converged to residual 2 across 8 iterations. That is a measurable convergence on a real document, not vibes.

Unlike qualitative tools like [grill-me](https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me) or [Devil's Advocate Protocol](https://mcpmarket.com/tools/skills/devil-s-advocate-protocol), this plugin is semi-data-science: the devil is inferred from existing conversations / emails / meeting transcripts (or described manually), every concern gets a Fibonacci risk score, and each iteration produces a measurable residual so convergence is visible. Versioned files with embedded scorecards create an audit trail.

The same hostility points at code. [`adversarial-review`](#adversarial-review---the-same-hostility-pointed-at-code) spawns fresh, context-free `claude -p` subprocesses that try to BREAK a change - a diff bug-hunt for the bugs inside a hunk, a whole-repo audit for the rot between files - seeded with any of the expert adversaries. Same principle as the scorecard half: a critic with no attachment to the work, run until a confirming round comes back clean.

## Installation

```bash
/plugin marketplace add https://github.com/stellarshenson/claude-code-plugins.git
/plugin install devils-advocate@stellarshenson-marketplace
```

## Commands

| Command | What it does |
|---------|-------------|
| `/devils-advocate:run` | Full end-to-end workflow: setup, evaluate, then iterate until residual is acceptable |
| `/devils-advocate:setup` | Build the devil persona and harvest the fact repository for a target document |
| `/devils-advocate:evaluate` | Generate the baseline concern catalogue and scorecard |
| `/devils-advocate:iterate` | One improvement cycle: decide approach, apply changes, version, re-score, rename |
| `/devils-advocate:adversarial-review` | Hostile independent review of code or artefacts - spawn fresh `claude -p` reviewers seeded with one of the expert adversaries |

## Skills

| Skill | Trigger | Purpose |
|-------|---------|---------|
| `devils-advocate` | "devil's advocate", "critique this", "scorecard", "pushback scenarios" | Auto-triggers the full workflow on critical-analysis requests |
| `devils-advocate:setup` | Invoked by `run` or directly | Persona construction and fact harvesting |
| `devils-advocate:evaluate` | Invoked after setup | Concern catalogue and baseline scorecard |
| `devils-advocate:iterate` | Invoked per improvement cycle | Improve, version, re-score, rename |
| `devils-advocate:adversarial-review` | "adversarial review", "red-team this", "find bugs in my change", "audit the architecture", "review before ship" | Hostile review of code and artefacts by spawning fresh `claude -p` reviewers |

## Adversarial review - the same hostility, pointed at code

The scorecard workflow above attacks a *document*. `adversarial-review` attacks a *change*, and it does it by spawning fresh, context-free `claude -p` subprocesses as the reviewers. A second model with no attachment to the code catches what the author rationalises away.

Two modes, composable with any adversary:

- **Mode 1 - diff bug-hunt.** No tools, inline diff, one turn, fast. Finds bugs, logic errors, security holes, broken edge cases in a specific change
- **Mode 2 - architecture & quality audit.** Tools on, whole-repo, many turns. Finds the systemic rot a diff cannot show - slop, brittle architecture, hardcodings, config drift, broken separation of concerns. The finding is usually a relationship across files, invisible in any one hunk. An existing `graphify` code graph at `tmp/graphify-out/graph.json` is refreshed and used without asking; with none, the skill offers one at launch - AST-only by default (free), the LLM-assisted pass on request, installing `graphify` on request - and reviewers and the adjudicator read it for callers and blast radius instead of rediscovering them by grep

The mode is the HOW; an **adversary** is the WHO - the expert lens the reviewer argues from. They ship under `skills/adversarial-review/adversaries/`, one self-contained persona prompt each:

| Adversary | Catches |
|-----------|---------|
| `architect` | "is this structure justified?" - architecture, consistency, config plane vs scattered literals, SoC, over-engineering & gold-plating |
| `bug-hunter` | runtime bugs in shell / installers / startup - quoting, `set -e`, lifecycle races |
| `qa-engineer` | test strategy - risk-based coverage, can-each-test-fail, test slop to delete |
| `analyst` | specs & acceptance criteria - coverage gaps, unverifiable criteria, sibling features siloed, spec-vs-code drift |
| `digital-marketer` | marketing copy and assets - message and positioning, concreteness, calls to action, claim substantiation and consumer law, search, email and ad mechanics, the gap to a best-in-class example, AI-sounding phrasing |
| `ux-designer` | friction & intent, visual hierarchy, cognitive load, static text & tooltips, design-language reuse, motion comfort, accessibility |
| `tui` | Textual/Rich internals - chrome duplication, key propagation, headless verification |
| `data-scientist` | hypothesis rigor, leakage, metric validity, reproducibility |
| `methodologist` | scientific-method integrity - can the test fail, does the verdict ladder span outcomes |
| `popular-science` | readability for a generalist - jargon, unsourced claims, buried lede, the visuals |
| `devops` | containers & deploy - Dockerfile hygiene, secrets in layers, PID-1 signals, probes |
| `slop-hunter` | "what can go?" - an exhaustive delete pass gated by a load-bearing check: dead code, duplicated blocks, YAGNI abstractions, defensive guards, over-mocked tests, unrequested hunks, doc over-prose, unused deps; plus AI-slop tells, fabrication & fake passes - the measured evidence per axis in `references/slop-hunter/research.md` |
| `ai-engineer` | "will this still steer any assistant tomorrow?" - the instruction layer itself: vendor lock-in, pinned command surfaces, drifted rule copies, unbounded loops |

One plugin agent serves them all - name the lens in the prompt and it loads that persona: `Agent(subagent_type: "devils-advocate:adversarial-reviewer", prompt: "Adversary: architect. ...")`. Never review with `general-purpose`: it carries no lens, so it returns a fluent summary where an adversary returns findings and a verdict.

The file IS the plugin - drop a new `adversaries/<name>.md` and it works, no registry, no wiring, no agent file to pair with it (contract in `skills/adversarial-review/references/authoring-an-adversary.md`).

**The panel caps at 3** unless you ask for more: triage, not the spawn, is the bottleneck, and five lenses buy a backlog you abandon rather than five times the signal. If you do not name an adversary, the skill asks before spawning - the wrong lens returns a fluent review of a risk your target does not have.

A panel's findings go through `devils-advocate:adjudicator` before any fix - it returns one change plan grouped by root cause, and it does not edit.

**Multi-round reviews run as a workflow** - with the dynamic Workflow capability, construct the workflow from the spec and pass it inline; without it, run the shipped `adversarial-loop.js` as the supplied protocol. The loop's nine invariants live in the script's control flow, never in session memory, so the protocol cannot drift with a long session's context; `plugins/devils-advocate/skills/adversarial-review/references/loop-spec.md` is the one full statement of the contract - invariants, args, statuses, execution paths and the incidents behind each rule.

Five deterministic commands from the library carry the review's bookkeeping. `review-tools dossier` writes the repository inventory (symbols, CLI surface versus documented surface, risky primitives, shared literals, most-called symbols) that each Mode 2 reviewer otherwise spends its first 40-60 turns rediscovering; pasted into the prompt it removes that discovery from every lens. `review-tools findings` merges the lens reports into one severity table keyed by `file:line` for the adjudicator. `review-tools cost` reads the subagent transcripts - a workflow's run directory is one round of the loop - and reports wall time, tokens, tool mix and re-reads per transcript, per stage, per adversary or per round, grouped from the label the harness records beside each spawn, so a round's bill is read per lens and a change to the prompts can be shown to have saved something. `review-tools research search` ranks the entries of an adversary's research files against a question, so a best practice already cached is not researched again. `review-tools prompt <args.json> --lens <adversary>` prints the reviewer prompt the workflow script would send - target, scope, bar, graph, research denial, and in a confirming round the closure list with patch paths - from the same args object, so a reviewer spawned by hand or through `claude -p` gets the context the script gives; its blocks are a copy of the script's, held equal by a test.

Research is opt-in. When a reviewer needs a best practice, paradigm or pattern its research files do not carry and the adjudicator approves the request, the skill asks once whether to allow 1, 3 or 5 researched questions per adversary, and appends what it finds to `.claude/review-research/<adversary>/research.md` in the reviewed project. No means no for that review; an adversary whose budget is used up can only return a suggestion, which defaults to no.

Reviews are **multi-round** by design: one pass finds, you triage and fix, then you re-run to prove the fix cleared it and opened no new hole. A single pass is a smoke test, not a verdict. Never flip a "survived adversarial review" criterion to done on the round that still had findings - only on a clean confirming round.

The `popular-science` adversary reviews against the shared craft canon that the `datascience:popular-science` writer composes from (`datascience/skills/popular-science/references/craft-canon.md`), so critique and craft never drift. That link is deliberately cross-plugin - install `datascience` too if you want that pair.

```bash
/devils-advocate:adversarial-review the auth middleware change before I merge
```

## Reference examples

Four worked analyses ship in `examples/`. Open them for full personas, concern catalogues, and score trajectories.

| Example | Target | Notes |
|---------|--------|-------|
| [executive-pushback-analysis.md](examples/executive-pushback-analysis.md) | Executive summary with missed KPI | 21 concerns, 8 iterations, 269 -> 2 |
| [readme-rewrite-analysis.md](examples/readme-rewrite-analysis.md) | PROGRAM.md + BENCHMARK.md | 7 concerns, baseline 121.3 |
| [kg-builder-design-analysis.md](examples/kg-builder-design-analysis.md) | Architecture design doc | 2 of 10 concerns shown, 88.9 -> 15.5 |
| [kg-builder-full-analysis.md](examples/kg-builder-full-analysis.md) | Same | All 10 concerns, 6 scorecards, 88.9 -> 15.5 |

## Artefacts

- `devils_advocate.md` - persona, concerns, scorecards accumulated across iterations
- `fact_repository.md` - verified claims with sources, harvested during setup
- `<name>_v<NN>_<score>.md` - versioned corrections with embedded scorecard, produced by each iteration

## Quick start

```bash
# Full workflow end-to-end
/devils-advocate:run

# Or step by step
/devils-advocate:setup        # 1. build persona, harvest facts
/devils-advocate:evaluate     # 2. generate concerns and baseline scorecard
/devils-advocate:iterate      # 3. improve, version, re-score (repeat)
```

## How it works

Every concern is scored on Fibonacci likelihood x impact (1-64), and each iteration computes a residual = risk x (1 - score). Versioned filenames embed the running document residual so the trajectory is visible in the file listing. For the full scoring model, persona construction, and iterate loop details, see the skills:

- `skills/setup/SKILL.md` - persona construction and fact harvesting
- `skills/evaluate/SKILL.md` - concern catalogue and scoring model
- `skills/iterate/SKILL.md` - the four-step iterate loop and stop conditions
- `skills/run/SKILL.md` - end-to-end wrapper
- `skills/adversarial-review/SKILL.md` - the two modes, the rounds protocol, spawn mechanics and gotchas, and the pluggable adversaries

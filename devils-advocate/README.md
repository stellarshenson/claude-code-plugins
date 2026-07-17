# devils-advocate - attack your document before your reviewer does

[![GitHub Actions](https://github.com/stellarshenson/claude-code-plugins/actions/workflows/ci.yml/badge.svg)](https://github.com/stellarshenson/claude-code-plugins/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/stellars-claude-code-plugins.svg)](https://pypi.org/project/stellars-claude-code-plugins/)
[![Total PyPI downloads](https://static.pepy.tech/badge/stellars-claude-code-plugins)](https://pepy.tech/project/stellars-claude-code-plugins)

Your reviewer / client / court / investor / VP will tear your document apart. Claude won't. Claude will tell you it looks great and ship.

This plugin builds an adversarial persona for the document's actual toughest audience, harvests verifiable facts from source material, generates a risk-scored concern catalogue, and iterates corrections until residual risk is acceptable. Risk uses a Fibonacci scale (1-8) for likelihood and impact (1-64 combined). Every iteration produces a measurable residual; versioned filenames embed it (`<name>_v07_15.md` where 15 is the residual) so the trajectory is visible in the file listing.

**Real trajectory from `examples/executive-pushback-analysis.md`**: an executive summary defending a missed KPI, baseline residual 269 across 21 concerns, converged to residual 2 across 8 iterations. That is a measurable convergence on a real document, not vibes.

Unlike qualitative tools like [grill-me](https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me) or [Devil's Advocate Protocol](https://mcpmarket.com/tools/skills/devil-s-advocate-protocol), this plugin is semi-data-science: the devil is inferred from existing conversations / emails / meeting transcripts (or described manually), every concern gets a Fibonacci risk score, and each iteration produces a measurable residual so convergence is visible. Versioned files with embedded scorecards create an audit trail.

The same hostility points at code. [`adversarial-review`](#adversarial-review---the-same-hostility-pointed-at-code) spawns fresh, context-free `claude -p` subprocesses that try to BREAK a change - a diff bug-hunt for the bugs inside a hunk, a whole-repo audit for the rot between files - seeded with any of ten expert adversaries. Same principle as the scorecard half: a critic with no attachment to the work, run until a confirming round comes back clean.

## Installation

```bash
/plugin marketplace add stellarshenson/claude-code-plugins
/plugin install devils-advocate@stellarshenson-marketplace
```

## Commands

| Command | What it does |
|---------|-------------|
| `/devils-advocate:run` | Full end-to-end workflow: setup, evaluate, then iterate until residual is acceptable |
| `/devils-advocate:setup` | Build the devil persona and harvest the fact repository for a target document |
| `/devils-advocate:evaluate` | Generate the baseline concern catalogue and scorecard |
| `/devils-advocate:iterate` | One improvement cycle: decide approach, apply changes, version, re-score, rename |

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
- **Mode 2 - architecture & quality audit.** Tools on, whole-repo, many turns. Finds the systemic rot a diff cannot show - slop, brittle architecture, hardcodings, config drift, broken separation of concerns. The finding is usually a relationship across files, invisible in any one hunk

The mode is the HOW; an **adversary** is the WHO - the expert lens the reviewer argues from. Ten ship under `skills/adversarial-review/adversaries/`, one self-contained persona prompt each:

| Adversary | Catches |
|-----------|---------|
| `architect` | architecture, consistency, hardcodings & config drift, SoC, over-engineering |
| `bug-hunter` | runtime bugs in shell / installers / startup - quoting, `set -e`, lifecycle races |
| `qa-engineer` | test strategy - risk-based coverage, can-each-test-fail, test slop to delete |
| `analyst` | specs & acceptance criteria - coverage gaps, unverifiable criteria, sibling features siloed, spec-vs-code drift |
| `ux-designer` | friction & intent, visual hierarchy, focus, motion comfort, accessibility |
| `tui` | Textual/Rich internals - chrome duplication, key propagation, headless verification |
| `data-scientist` | hypothesis rigor, leakage, metric validity, reproducibility |
| `methodologist` | scientific-method integrity - can the test fail, does the verdict ladder span outcomes |
| `popular-science` | readability for a generalist - jargon, unsourced claims, buried lede, the visuals |
| `devops` | containers & deploy - Dockerfile hygiene, secrets in layers, PID-1 signals, probes |

The file IS the plugin - drop a new `adversaries/<name>.md` and it works, no registry, no wiring (contract in `skills/adversarial-review/references/authoring-an-adversary.md`).

**The panel caps at 3** unless you ask for more: triage, not the spawn, is the bottleneck, and five lenses buy a backlog you abandon rather than five times the signal. If you do not name an adversary, the skill asks before spawning - the wrong lens returns a fluent review of a risk your target does not have.

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

- `skills/devils-advocate/SKILL.md` - auto-trigger, top-level workflow
- `skills/setup/SKILL.md` - persona construction and fact harvesting
- `skills/evaluate/SKILL.md` - concern catalogue and scoring model
- `skills/iterate/SKILL.md` - the four-step iterate loop and stop conditions
- `skills/run/SKILL.md` - end-to-end wrapper
- `skills/adversarial-review/SKILL.md` - the two modes, the rounds protocol, spawn mechanics and gotchas, and the ten pluggable adversaries

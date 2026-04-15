# devils-advocate

[![GitHub Actions](https://github.com/stellarshenson/claude-code-plugins/actions/workflows/ci.yml/badge.svg)](https://github.com/stellarshenson/claude-code-plugins/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/stellars-claude-code-plugins.svg)](https://pypi.org/project/stellars-claude-code-plugins/)
[![Total PyPI downloads](https://static.pepy.tech/badge/stellars-claude-code-plugins)](https://pepy.tech/project/stellars-claude-code-plugins)

Critical document analysis plugin for Claude Code. Systematically critiques documents from the perspective of their toughest audience using a custom persona, Fibonacci risk scoring, and versioned iterative improvement.

Unlike qualitative tools like [grill-me](https://github.com/mattpocock/skills/tree/main/grill-me) or [Devil's Advocate Protocol](https://mcpmarket.com/tools/skills/devil-s-advocate-protocol), this plugin is semi-data-science: the devil is inferred from existing conversations, emails, or meeting transcripts (or described manually), every concern gets a Fibonacci risk score, and each iteration produces a measurable residual so the trajectory (89 -> 34 -> 12) shows convergence. Versioned files with embedded scorecards create an audit trail.

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

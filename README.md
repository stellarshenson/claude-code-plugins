# stellars-claude-code-plugins

[![GitHub Actions](https://github.com/stellarshenson/claude-code-plugins/actions/workflows/ci.yml/badge.svg)](https://github.com/stellarshenson/claude-code-plugins/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/stellars-claude-code-plugins.svg)](https://pypi.org/project/stellars-claude-code-plugins/)
[![Total PyPI downloads](https://static.pepy.tech/badge/stellars-claude-code-plugins)](https://pepy.tech/project/stellars-claude-code-plugins)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Brought To You By KOLOMOLO](https://img.shields.io/badge/Brought%20To%20You%20By-KOLOMOLO-00ffff?style=flat)](https://kolomolo.com)

AI coding agents generate impressive code but cut corners when left unsupervised - skipping tests, losing context between iterations, shipping shallow fixes that pass benchmarks without addressing root causes. The longer an agent runs autonomously, the more these failures compound.

This project provides a shared YAML-driven orchestration engine that pulls agents through structured phases with independent quality gates at every boundary. Instead of relying on the agent's self-discipline, the engine enforces research before implementation, hypothesis tracking across iterations, and multi-agent review before any code ships.

> [!TIP]
> Each plugin provides only YAML configuration files. The shared orchestration engine in `stellars_claude_code_plugins` handles all execution logic - FSM transitions, gate validation, multi-agent coordination, and state management.

> [!NOTE]
> Read the full article on the approach: [Your AI Agent Will Cut Corners. Here's How to Stop It.](https://medium.com/@konradwitowskijele/your-ai-agent-will-cut-corners-heres-how-to-stop-it-40f3bc7a4762)

## What it solves

- **Shallow fixes** - forces research and hypothesis before implementation
- **Scope creep** - plan locks scope, review catches deviations
- **Lost context** - hypothesis catalogue and failure context persist across iterations
- **Unchecked quality** - two independent gates (readback + gatekeeper) per phase
- **No accountability** - every phase records agents, outputs, and verdicts in YAML audit logs
- **Benchmark gaming** - guardian agent checks for benchmark-specific tuning vs genuine improvement

## Plugins

| Plugin | Skills | Description |
|--------|--------|-------------|
| [auto-build-claw](auto-build-claw/) | 3 | Autonomous build iteration orchestrator with multi-agent review |
| [devils-advocate](devils-advocate/) | 4 | Critical document analysis with persona-driven risk scoring |

## auto-build-claw

Runs structured multi-iteration development cycles where each iteration passes through a full phase lifecycle with quality gates. A program defines what to build, a benchmark measures progress, and the engine enforces the workflow until the objective is met or iterations are exhausted.

**Skills**: `auto-build-claw` (orchestrator), `program-writer`, `benchmark-writer`

### Workflow types

| Type | Phases | Use when |
|------|--------|----------|
| `full` | RESEARCH -> HYPOTHESIS -> PLAN -> IMPLEMENT -> TEST -> REVIEW -> RECORD -> NEXT | Feature work, improvements |
| `fast` | PLAN -> IMPLEMENT -> TEST -> REVIEW -> RECORD -> NEXT | Clear objective, no exploration needed |
| `gc` | PLAN -> IMPLEMENT -> TEST -> RECORD -> NEXT | Cleanup, refactoring |
| `hotfix` | IMPLEMENT -> TEST -> RECORD | Targeted bug fix |
| `planning` | RESEARCH -> PLAN -> RECORD -> NEXT | Work breakdown (auto-chains before full) |

### Usage

```bash
# Describe what you want - the plugin handles the rest
/auto-build-claw improve error handling in the API layer
```

The plugin writes PROGRAM.md and BENCHMARK.md from your prompt, asks you to approve, then runs the orchestrator autonomously.

See [auto-build-claw/README.md](auto-build-claw/) for the full phase lifecycle, agent architecture, and configuration details.

## devils-advocate

Systematically critiques documents from the perspective of their toughest audience. Builds a devil persona, harvests verifiable facts, generates a risk-scored concern catalogue, and iterates corrections until residual risk is acceptable.

**Skills**: `setup` (build persona + fact repository), `evaluate` (concern catalogue + baseline scorecard), `iterate` (apply corrections or re-score), `run` (full workflow end-to-end)

Risk scoring uses a Fibonacci scale (1-8) for likelihood and impact, producing risk scores from 1-64. Each concern is scored 0-100% on how well the document addresses it, and the residual risk (what remains unaddressed) drives iteration priority.

### Usage

```bash
# Full end-to-end workflow
/devils-advocate:run

# Step by step
/devils-advocate:setup       # Build persona, harvest facts
/devils-advocate:evaluate    # Generate concerns + baseline scorecard
/devils-advocate:iterate     # Apply corrections, re-score (repeat)
```

See [devils-advocate/README.md](devils-advocate/) for scoring formula details, artefact format, and the full concern catalogue methodology.

## Install

```bash
pip install stellars-claude-code-plugins
```

As a Claude Code plugin marketplace:

```bash
/plugin marketplace add stellarshenson/claude-code-plugins
```

## Architecture

```
stellars_claude_code_plugins/          # Shared engine (pip installable)
  engine/
    fsm.py                             # Phase lifecycle state machine
    model.py                           # Typed YAML model loader + validator
    orchestrator.py                    # Complete orchestration engine
    resources/
      workflow.yaml                    # Default iteration types and phase sequences
      phases.yaml                      # Default phase templates, agents, gates
      app.yaml                         # Default display text and CLI config

auto-build-claw/                       # Plugin: autonomous build iterations
  .claude-plugin/plugin.json           # Plugin registration
  skills/
    auto-build-claw/SKILL.md           # Orchestrator skill definition
    program-writer/SKILL.md            # Program definition skill
    benchmark-writer/SKILL.md          # Benchmark definition skill

devils-advocate/                       # Plugin: critical document analysis
  .claude-plugin/plugin.json           # Plugin registration
  skills/
    setup/SKILL.md                     # Build persona + fact repository
    evaluate/SKILL.md                  # Concern catalogue + scorecard
    iterate/SKILL.md                   # Apply corrections, re-score
    run/SKILL.md                       # Full workflow end-to-end

.claude-plugin/marketplace.json        # Plugin marketplace registry
```

## Building a new plugin

Plugins are pure configuration - no Python code required. Create a directory with skills and register it in the marketplace:

```
my-plugin/
  .claude-plugin/plugin.json           # Plugin registration and skill triggers
  skills/
    my-skill/SKILL.md                  # Skill definition with description and instructions
```

The `plugin.json` registers your skills with Claude Code, defining when they trigger and what tools they have access to. Each `SKILL.md` contains the instructions Claude follows when the skill is invoked. The shared orchestration engine (`pip install stellars-claude-code-plugins`) provides the `orchestrate` CLI command that handles state management, FSM transitions, gate execution, and audit logging.

Register your plugin in the marketplace by adding an entry to `.claude-plugin/marketplace.json`.

## Development

```bash
make install          # create venv, install deps, editable install
make test             # run 212 tests
make lint             # ruff format + check
make format           # auto-fix formatting
make build            # clean, test, bump version, build wheel
make publish          # build + twine upload to PyPI
```

## License

MIT License

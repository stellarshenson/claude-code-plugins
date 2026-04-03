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
# Start a 3-iteration improvement cycle
/auto-build-claw:run new --type full --objective "fix connector routing" --iterations 3

# With benchmark tracking
/auto-build-claw:run new --type full --objective "improve score" --iterations 5 \
  --benchmark "Read BENCHMARK.md and evaluate each [ ] item"

# Continue from previous session (preserves context, failures, hypotheses)
/auto-build-claw:run new --continue --type gc --objective "clean up dead code"

# Check progress
/auto-build-claw:run status
```

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

auto-build-claw/                       # Plugin: autonomous build iterations
  skills/
    auto-build-claw/
      orchestrate.py                   # Thin entrypoint
      resources/
        workflow.yaml                  # Iteration types and phase sequences
        phases.yaml                    # Phase templates, agents, gates
        app.yaml                       # Display text and CLI config
    program-writer/SKILL.md
    benchmark-writer/SKILL.md

devils-advocate/                       # Plugin: critical document analysis
  skills/
    setup/SKILL.md
    evaluate/SKILL.md
    iterate/SKILL.md
    run/SKILL.md
```

## Building a new plugin

Create a directory with YAML resource files and a thin entrypoint:

```python
#!/usr/bin/env python3
from pathlib import Path
from stellars_claude_code_plugins.engine.orchestrator import main

if __name__ == "__main__":
    main(resources_dir=Path(__file__).parent / "resources")
```

Define your workflow phases, agent prompts, gate templates, and display text in the YAML files. The engine handles everything else - state management, FSM transitions, CLI parsing, gate execution, and audit logging.

Register in the marketplace by adding a `plugin.json` to your plugin's `.claude-plugin/` directory.

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

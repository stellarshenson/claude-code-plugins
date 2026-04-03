# stellars-claude-code-plugins

[![GitHub Actions](https://github.com/stellarshenson/claude-code-plugins/actions/workflows/ci.yml/badge.svg)](https://github.com/stellarshenson/claude-code-plugins/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/stellars-claude-code-plugins.svg)](https://pypi.org/project/stellars-claude-code-plugins/)
[![Total PyPI downloads](https://static.pepy.tech/badge/stellars-claude-code-plugins)](https://pepy.tech/project/stellars-claude-code-plugins)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Brought To You By KOLOMOLO](https://img.shields.io/badge/Brought%20To%20You%20By-KOLOMOLO-00ffff?style=flat)](https://kolomolo.com)

> [!TIP]
> Each plugin provides only YAML configuration files. The shared orchestration engine in `stellars_claude_code_plugins` handles all execution logic - FSM transitions, gate validation, multi-agent coordination, and state management.

Claude Code plugins for autonomous development workflows. A shared YAML-driven orchestration engine with individual plugins that define their own phases, agents, and gates through declarative configuration.

## Plugins

| Plugin | Description |
|--------|-------------|
| [auto-build-claw](auto-build-claw/) | Autonomous build iteration orchestrator with multi-agent review |

## Features

- **YAML-driven orchestration** - All phases, agents, gates, and display text defined in 4 YAML files per plugin
- **Finite state machine** - Declarative phase lifecycle with readback, gatekeeper, reject, and skip transitions
- **Multi-agent coordination** - Spawn parallel agent panels per phase with role-specific prompts
- **Independent gates** - Readback validation at phase start, gatekeeper evaluation at phase end via `claude -p`
- **Hypothesis tracking** - Persistent hypothesis catalogue across iterations with garbage collection
- **Failure logging** - Structured failure modes feed into next iteration's research context
- **Iteration planning** - Optional iteration 0 planning phase with dependency workflow chaining
- **Auditable state** - Every transition, readback, and gatekeeper verdict logged to YAML

## Architecture

```
stellars_claude_code_plugins/          # Shared engine (pip installable)
  engine/
    fsm.py                             # Phase lifecycle state machine
    model.py                           # Typed YAML model loader + validator
    orchestrator.py                    # Complete orchestration engine

auto-build-claw/                       # Plugin (YAML content + thin entrypoint)
  skills/auto-build-claw/
    orchestrate.py                     # 18-line entrypoint
    resources/
      workflow.yaml                    # Iteration types and phase sequences
      phases.yaml                      # Phase instruction templates
      agents.yaml                      # Agent definitions and gate prompts
      app.yaml                         # Display text and CLI configuration
```

## Install

```bash
pip install stellars-claude-code-plugins
```

This installs the shared orchestration engine and the `orchestrate` CLI command.

## Usage

### As a Claude Code plugin

```bash
/plugin marketplace add stellarshenson/claude-code-plugins
```

The auto-build-claw skill triggers automatically when you ask Claude to iterate on code, improve quality, fix bugs, or run structured development cycles.

### As a standalone CLI

```bash
orchestrate --resources-dir /path/to/plugin/resources new --type full --objective "..." --iterations 3
orchestrate start --understanding "brief summary"
orchestrate end --evidence "..." --agents "researcher,planner" --output-file output.md
orchestrate status
```

## Building a new plugin

Create a directory with 4 YAML resource files and a thin entrypoint:

```python
#!/usr/bin/env python3
from pathlib import Path
from stellars_claude_code_plugins.engine.orchestrator import main

if __name__ == "__main__":
    main(resources_dir=Path(__file__).parent / "resources")
```

Define your workflow phases, agent prompts, gate templates, and display text in the YAML files. The engine handles everything else - state management, FSM transitions, CLI parsing, gate execution, and audit logging.

## Development

```bash
make install          # create venv, install deps, editable install
make test             # run 115 tests
make lint             # ruff format + check
make format           # auto-fix formatting
make build            # clean, test, bump version, build wheel
make publish          # build + twine upload to PyPI
```

## License

MIT License

# autobuild

Autonomous build iteration orchestrator for Claude Code. Runs structured improvement cycles with multi-agent review, FSM-driven phase lifecycle, per-phase gates, and YAML-configured workflows.

The plugin decomposes complex work into sequential phases (research, hypothesis, plan, implement, test, review, record), spawns independent agent panels at each stage, and enforces quality through two independent gates per phase (readback + gatekeeper). Every phase records agents spawned, outputs produced, and verdicts in auditable YAML logs.

## Installation

```bash
/plugin marketplace add stellarshenson/claude-code-plugins
/plugin install autobuild@stellarshenson-marketplace
```

The orchestration engine must also be installed:

```bash
pip install stellars-claude-code-plugins
```

## Commands

| Command | What it does |
|---------|-------------|
| `/autobuild:run` | Entry point for the orchestrator. Runs program-writer -> benchmark-writer -> autobuild skills in order, then drives the iteration loop |

The `run` command accepts standard orchestrator subcommands (`new`, `start`, `end`, `status`, `skip`, `reject`, `add-iteration`, `validate`) that map 1:1 to the underlying `orchestrate` CLI.

## Skills

| Skill | Trigger | Purpose |
|-------|---------|---------|
| `autobuild` | Iterate, improve, refactor, fix bugs, run GC, implement features through structured phases | Drives the FSM-based iteration loop with per-phase agent panels, readback and gatekeeper gates |
| `program-writer` | Invoked before workflow execution | Builds `PROGRAM.md` through iterative dialogue - intention, scope, constraints, exit conditions |
| `benchmark-writer` | Invoked after program-writer, before execution | Builds `BENCHMARK.md` as a scalar evaluation function with score formula, direction, and programmatic checks |

## Agents

| Agent | Purpose |
|-------|---------|
| `orchestrator` | Autonomous iteration driver. Reads workflow YAML, spawns phase agents, enforces gates, records logs |

## Workflow types

| Type | Phases | Use when |
|------|--------|----------|
| `full` | RESEARCH -> HYPOTHESIS -> PLAN -> IMPLEMENT -> TEST -> REVIEW -> RECORD -> NEXT | Feature work, improvements |
| `gc` | PLAN -> IMPLEMENT -> TEST -> RECORD -> NEXT | Cleanup, refactoring |
| `hotfix` | IMPLEMENT -> TEST -> RECORD | Targeted bug fix |

## Example

```bash
# Guided: walks through program-writer -> benchmark-writer -> orchestrator
/autobuild:run
```

The recommended entry is `/autobuild:run` with no arguments. PROGRAM.md and BENCHMARK.md must be approved by the user before any iteration begins. See `skills/autobuild/SKILL.md` for the full iteration loop and direct-invocation flags.

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - FSM, phase lifecycle, and workflow design
- [docs/CUSTOMIZATION.md](docs/CUSTOMIZATION.md) - extending workflows and phases
- [docs/DESIGN-DECISIONS.md](docs/DESIGN-DECISIONS.md) - rationale behind key choices
- [docs/DEVELOPMENT-JOURNEY.md](docs/DEVELOPMENT-JOURNEY.md) - evolution of the plugin
- `skills/autobuild/SKILL.md` - iteration loop, phase gates, agent panels
- `skills/program-writer/SKILL.md` - PROGRAM.md authoring dialogue
- `skills/benchmark-writer/SKILL.md` - BENCHMARK.md scoring model

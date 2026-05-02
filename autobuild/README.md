# autobuild - stop Claude from cutting corners

```
Bad agent:
  User:    "improve error handling"
  Claude:  "Fixed it."
  Reality: 2 files changed, no tests run, edge cases broken.

With autobuild:
  User:    /autobuild:run improve error handling

  Claude must:
   1. inspect code              (RESEARCH)
   2. write PROGRAM.md          (PLAN)
   3. define BENCHMARK.md       (BENCHMARK)
   4. get your approval         (GATE)
   5. implement                 (IMPLEMENT)
   6. run tests                 (TEST)
   7. review against objective  (REVIEW)
   8. record audit trail        (RECORD)
```

Every phase has two independent quality gates (readback + gatekeeper). Every iteration produces a measurable benchmark score so progress is visible, not vibe-checked. Every step records agents spawned, outputs produced, and verdicts in auditable YAML logs.

Read the full article: [Your AI Agent Will Cut Corners. Here's How to Stop It](https://medium.com/@konradwitowskijele/your-ai-agent-will-cut-corners-heres-how-to-stop-it-40f3bc7a4762).

## Real iteration trajectories

Real cycles run by this plugin against this repo (excerpts from `.claude/JOURNAL.md`):

- **Document grounding optimisation** - composite benchmark score `69.3 -> 5.0`, final 1.0 cross-validation accuracy on three held-out academic papers (Liu 2023, Ye 2024, Han 2024). Six iterations, 29 tunable parameters exposed in `config.yaml`. Full PROGRAM, BENCHMARK, hypothesis + falsifiers archived under [`references/grounding-optimisation/`](../references/grounding-optimisation/) ([JOURNAL entry 114](../.claude/JOURNAL.md))
- **svg-infographics forensics** - audited 6 prior Claude Code sessions, identified 231 occurrences of "false positive" rationalisation, shipped 4 corrective work items in one release including the quartermaster preflight pattern, connector direction declaration, and stubby-arrow validator ([JOURNAL entry 124](../.claude/JOURNAL.md))
- **document-processing forensics** - shipped all 7 work items from a forensic-review plan in a single release combining correctness fixes (binary-source rejection, lexical co-support) with workflow additions (claim extraction, intra-doc consistency, batch orchestrator) ([JOURNAL entry 123](../.claude/JOURNAL.md))

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

# Autobuild

Autonomous build iteration orchestrator for Claude Code. Runs structured improvement cycles with multi-agent review, FSM-driven phase lifecycle, per-phase gates, and YAML-configured workflows.

## What it solves

- **Shallow fixes**: forces research and hypothesis before implementation
- **Scope creep**: plan locks scope, review catches deviations
- **Overfit to benchmarks**: guardian agent checks for benchmark-specific tuning
- **Lost context**: hypothesis catalogue persists across iterations
- **Unchecked quality**: two independent gates (readback + gatekeeper) per phase
- **No accountability**: every phase records agents, outputs, and verdicts in YAML logs

## Quick start

```bash
# Start a 3-iteration improvement cycle
/autobuild:run new --type full --objective "fix connector routing" --iterations 3

# With benchmark tracking
/autobuild:run new --type full --objective "improve score" --iterations 5 --benchmark "Read BENCHMARK.md and evaluate each [ ] item"

# Check progress
/autobuild:run status

# Validate configuration
/autobuild:run validate

# Preview execution plan
/autobuild:run new --type full --objective "test" --iterations 2 --dry-run
```

## Workflow types

| Type | Phases | Use when |
|------|--------|----------|
| `full` | RESEARCH -> HYPOTHESIS -> PLAN -> IMPLEMENT -> TEST -> REVIEW -> RECORD -> NEXT | Feature work, improvements |
| `gc` | PLAN -> IMPLEMENT -> TEST -> RECORD -> NEXT | Cleanup, refactoring |
| `hotfix` | IMPLEMENT -> TEST -> RECORD | Targeted bug fix |

## Architecture

- **FSM engine**: Phase lifecycle (pending -> readback -> in_progress -> gatekeeper -> complete)
- **:: namespacing**: Workflow-specific phases/agents (`FULL::RESEARCH` vs `PLANNING::RESEARCH`)
- **Per-phase gates**: Each phase declares its own readback and gatekeeper prompts
- **Auto-actions**: Phase completion triggers (hypothesis GC, iteration summary, etc.)
- **Dependency workflows**: Planning auto-chains before implementation via `depends_on`

See `docs/ARCHITECTURE.md` for the full design.

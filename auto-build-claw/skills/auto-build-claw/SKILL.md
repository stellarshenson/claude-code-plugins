---
name: auto-build-claw
description: Autonomous build iteration orchestrator. Runs structured improvement cycles with multi-agent review. Use when asked to iterate, improve, fix bugs, refactor, run GC, implement features, do quality improvement, run cleanup, or execute structured development cycles. Phases - research, hypothesis, plan, implement, test, review, record. 10 commands, 2 calls per phase.
---

# Auto Build Claw - Autonomous Iteration Orchestrator

This skill breaks complex improvement work into sequential phases, spawns independent agent panels at each stage, and enforces quality through two independent gates. Use it when the user asks to iterate on code, improve quality, fix bugs, refactor, run GC, or implement features through structured phases.

It solves common problems with autonomous coding: **shallow fixes** (forces research and hypothesis formation before any implementation), **scope creep** (plan locks scope, review catches deviations), **overfit to benchmarks** (guardian agent checks every change for benchmark-specific tuning that destroys generality), **lost context across iterations** (hypothesis catalogue persists so knowledge accumulates), **unchecked quality** (two independent gates catch misunderstandings and incomplete work), and **no accountability** (every phase records agents spawned, outputs produced, and gatekeeper verdicts in auditable YAML logs).

Full phase instructions, agent definitions, and exit criteria live in `orchestrate.py` - this file is the overview. Run `orchestrate.py start` to see exactly what each phase requires.

## Triggers

- Iterate on code or improve quality
- Fix bugs or refactor
- Run garbage collection or cleanup
- Implement features through structured phases
- Execute structured development cycles

## Prerequisites

- **Objective**: what the iterations aim to achieve - ASK the user if not specified
- **Iteration count**: how many cycles to run - ASK the user if not specified
- **Benchmark** (optional): ASK the user: "Do you have a benchmark I should evaluate after each iteration? (1) No benchmark - just tests and lint, (2) Yes - please provide the instruction and what it measures." If provided, pass via `--benchmark "instruction"` on `new`. The `--benchmark` value is always a **generative instruction string** - text that tells the orchestrating Claude what to evaluate during the TEST phase. It is NOT a shell command. The instruction typically references a file containing the checklist, e.g., `--benchmark "Read MODEL_BENCHMARK.md and evaluate each [ ] item. Mark [x] if passing. Report remaining [ ] count as violation score."` The benchmark runs during TEST phase only - IMPLEMENT and REVIEW phases must NOT evaluate the benchmark
- **Objective** can reference files for full context: e.g., `--objective "Implement the program defined in PROGRAM.md (read .claude/skills/auto-build-claw/PROGRAM.md)"`. This avoids cramming long objectives into command-line arguments. Use `PROGRAM.md` for complex objectives and `MODEL_BENCHMARK.md` (or any `*_BENCHMARK.md`) for benchmark checklists

## How it works

Every phase follows the same 2-call pattern:

```bash
orchestrate.py new --type full --objective "improve X" --iterations 3

orchestrate.py start --understanding "I will spawn 3 research agents"
# ... do the work the CLI told you to do ...
orchestrate.py end --evidence "done" --agents "a,b,c" --output-file "path"
```

The CLI guides you through each phase with full instructions, agent definitions, and exit criteria. Run `start` to see what to do, then `end` when done.

**AUTONOMOUS EXECUTION**: Run ALL iterations and ALL phases continuously without pausing for user approval between phases or iterations. Move from one phase to the next immediately after `end` succeeds. Move from one iteration to the next immediately after NEXT completes. Do NOT ask "shall I continue?" or "ready for the next phase?" - just proceed. Only stop if: the user explicitly asked to pause, a gate FAILS and needs fixing, or all iterations are complete.

| Type | Use when |
|------|----------|
| `full` | Feature work, improvements, research-driven changes |
| `gc` | Cleanup, dead code removal, refactoring |
| `hotfix` | Targeted bug fix, minimal ceremony |

## User guidance

Users can inject context into any phase. When the user says "focus on X" or "consider Y", use the context command to store it - it appears as a prominent banner in phase instructions and is broadcast to all agents spawned after the command:

```bash
orchestrate.py context --phase RESEARCH --message "focus on connector routing"
```

## Commands

10 commands total. Run `orchestrate.py --help` or `orchestrate.py <command> --help` for full reference.

```bash
# start a 3-iteration improvement cycle
orchestrate.py new --type full --objective "fix connector routing" --iterations 3

# with benchmark tracking (generative instruction, evaluated during TEST phase)
orchestrate.py new --type full --objective "improve D3 score" --iterations 5 --benchmark "Read MODEL_BENCHMARK.md and evaluate each [ ] item. Mark [x] if passing. Report count of remaining [ ] as violation score."

# enter phase - readback validates your understanding
orchestrate.py start --understanding "I will spawn 3 research agents to investigate D3 failures"

# complete phase - record what was done, which agents, and output file
orchestrate.py end --evidence "3 agents found rotation errors" --agents "researcher,architect,product_manager" --output-file ".auto-build-claw/phase_01_research/findings.md"

# check progress
orchestrate.py status

# reviewer rejects - go back to IMPLEMENT
orchestrate.py reject --reason "guardian blocked: benchmark overfit detected"

# skip optional phase (--force for required phases, conservative gate)
orchestrate.py skip --reason "no iterations remaining" --force

# inject user guidance into current phase
orchestrate.py context --message "focus on label clearance not edge-snap"

# log a failure mode found during work
orchestrate.py log-failure --mode "FM-ROTATION" --desc "rotate(-90) instead of +90 for downward arrows"

# show failure log and hypothesis catalogue
orchestrate.py failures
orchestrate.py hypotheses
```

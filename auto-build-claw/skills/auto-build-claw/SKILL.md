---
name: auto-build-claw
description: Autonomous build iteration orchestrator. Runs structured improvement cycles with multi-agent review. Use when asked to iterate, improve, fix bugs, refactor, run GC, implement features, do quality improvement, run cleanup, or execute structured development cycles. Phases - research, hypothesis, plan, implement, test, review, record. 10 commands, 2 calls per phase.
---

# Auto Build Claw - Autonomous Iteration Orchestrator

This skill breaks complex improvement work into sequential phases, spawns independent agent panels at each stage, and enforces quality through two independent gates. Use it when the user asks to iterate on code, improve quality, fix bugs, refactor, run GC, or implement features through structured phases.

It solves common problems with autonomous coding: **shallow fixes** (forces research and hypothesis formation before any implementation), **scope creep** (plan locks scope, review catches deviations), **overfit to benchmarks** (guardian agent checks every change for benchmark-specific tuning that destroys generality), **lost context across iterations** (hypothesis catalogue persists so knowledge accumulates), **unchecked quality** (two independent gates catch misunderstandings and incomplete work), and **no accountability** (every phase records agents spawned, outputs produced, and gatekeeper verdicts in auditable YAML logs).

Full phase instructions, agent definitions, and exit criteria are loaded from the YAML resource files in `resources/`. Run `start` to see exactly what each phase requires.

## Setup

The orchestration engine must be installed before use:

```bash
pip install stellars-claude-code-plugins
```

The `orchestrate` CLI command becomes available after installation. Alternatively, run the entrypoint directly:

```bash
python .claude/skills/auto-build-claw/orchestrate.py
```

Both paths use the same engine - the entrypoint passes the skill's `resources/` directory to the shared orchestrator.

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

## Program execution

For complex multi-iteration objectives, define the full program in a `PROGRAM.md` file and the evaluation checklist in a `BENCHMARK.md` file, then run:

```bash
# Fixed number of iterations
orchestrate new --type full \
  --objective "Implement the program defined in PROGRAM.md (read PROGRAM.md)" \
  --iterations 3 \
  --benchmark "Read BENCHMARK.md and evaluate each [ ] item. Mark [x] if passing. Report remaining [ ] count as violation score."

# Run until benchmark conditions are met (--iterations 0 = unlimited)
orchestrate new --type full \
  --objective "Implement the program defined in PROGRAM.md (read PROGRAM.md)" \
  --iterations 0 \
  --benchmark "Read BENCHMARK.md and evaluate each [ ] item. Mark [x] if passing. Report remaining [ ] count as violation score."
```

This gives the orchestrator a structured objective it can read in full at each phase, and a measurable benchmark that tracks progress across iterations. The benchmark is evaluated generatively during the TEST phase - the orchestrating agent reads the checklist, verifies each item against the codebase, and reports the violation count as the score to optimize.

With `--iterations 0`, the orchestrator runs indefinitely until the benchmark score reaches 0 (all checklist conditions met). A safety cap of 20 iterations prevents runaway execution.

### `new` command flags

| Flag | Description |
|------|-------------|
| `--type` | Iteration type: `full`, `gc`, or `hotfix` (required) |
| `--objective` | What the iterations aim to achieve (required) |
| `--iterations` | Number of cycles. `0` = unlimited until benchmark passes. Default: 1 |
| `--benchmark` | Generative instruction evaluated during TEST phase |
| `--continue` | Resume an interrupted session from where it left off |
| `--restart` | Restart current iteration from beginning (optionally update objective/benchmark/iterations) |
| `--dry-run` | Show what would happen without executing |
| `--record-instructions` | Custom instructions for RECORD phase (e.g. `"Update .claude/JOURNAL.md, git add, commit, push"`). Default: no journal/git unless code changes exist |

## MANDATORY: All work goes through the orchestrator

**NO EXCEPTIONS.** Every code change, every file edit, every commit MUST happen within an orchestrator phase. Do NOT:

- Edit files outside of an IMPLEMENT phase
- Skip phases or do work "directly" to save time
- Make changes between orchestrator commands
- Commit without going through RECORD phase
- Evaluate benchmarks outside of TEST phase

The orchestrator exists to enforce quality gates (readback + gatekeeper). Bypassing it means bypassing quality control. If the orchestrator ceremony feels slow, that's the cost of not shipping broken code.

**Phase discipline**:
- RESEARCH, HYPOTHESIS, PLAN, REVIEW - READ-ONLY. No file modifications
- IMPLEMENT - the ONLY phase where code changes are allowed
- TEST - run tests and evaluate benchmarks. Edit BENCHMARK.md only
- RECORD - journal, commit, push. No code changes

If you find yourself wanting to "just quickly fix something" outside the orchestrator - DON'T. Start a phase, do it properly, end the phase.

## How it works

Every phase follows the same 2-call pattern:

```bash
orchestrate new --type full --objective "improve X" --iterations 3

orchestrate start --understanding "I will spawn 3 research agents"
# ... do the work the CLI told you to do ...
orchestrate end --evidence "done" --agents "a,b,c" --output-file "path"
```

The CLI guides you through each phase with full instructions, agent definitions, and exit criteria. Run `start` to see what to do, then `end` when done.

**FULLY AUTONOMOUS EXECUTION - NO HUMAN IN THE LOOP**:

The orchestrator eliminates the human as a bottleneck. The human's role is limited to:
1. Writing the objective (PROGRAM.md)
2. Defining the benchmark (BENCHMARK.md)
3. Choosing workflow type and iteration count

Everything else runs autonomously:
- Move from phase to phase IMMEDIATELY after `end` succeeds. No pause. No questions.
- Move from iteration to iteration IMMEDIATELY after NEXT completes. No pause.
- Do NOT ask "shall I continue?", "ready for next phase?", "want to checkpoint?" - NEVER.
- Do NOT summarize what you just did and wait for approval - just proceed to the next phase.
- Do NOT offer choices between approaches mid-run - the PLAN phase already decided.
- The ONLY reasons to stop: (1) user explicitly asked to pause, (2) a gate FAILS and needs fixing, (3) exit conditions met, (4) context limit reached (auto-compaction handles this).

The quality gates (readback + gatekeeper) are the quality control mechanism - not human review. Trust the gates.

| Type | Use when |
|------|----------|
| `full` | Feature work, improvements, research-driven changes |
| `gc` | Cleanup, dead code removal, refactoring |
| `hotfix` | Targeted bug fix, minimal ceremony |

## User guidance

Users can inject context into any phase. When the user says "focus on X" or "consider Y", use the context command to store it - it appears as a prominent banner in phase instructions and is broadcast to all agents spawned after the command:

```bash
orchestrate context --phase RESEARCH --message "focus on connector routing"
```

## Commands

10 commands total. Run `orchestrate --help` or `orchestrate <command> --help` for full reference.

```bash
# start a 3-iteration improvement cycle
orchestrate new --type full --objective "fix connector routing" --iterations 3

# with benchmark tracking (generative instruction, evaluated during TEST phase)
orchestrate new --type full --objective "improve D3 score" --iterations 5 --benchmark "Read MODEL_BENCHMARK.md and evaluate each [ ] item. Mark [x] if passing. Report count of remaining [ ] as violation score."

# enter phase - readback validates your understanding
orchestrate start --understanding "I will spawn 3 research agents to investigate D3 failures"

# complete phase - record what was done, which agents, and output file
orchestrate end --evidence "3 agents found rotation errors" --agents "researcher,architect,product_manager" --output-file ".auto-build-claw/phase_01_research/findings.md"

# check progress
orchestrate status

# reviewer rejects - go back to IMPLEMENT
orchestrate reject --reason "guardian blocked: benchmark overfit detected"

# skip optional phase (--force for required phases, conservative gate)
orchestrate skip --reason "no iterations remaining" --force

# inject user guidance into current phase
orchestrate context --message "focus on label clearance not edge-snap"

# log a failure mode found during work
orchestrate log-failure --mode "FM-ROTATION" --desc "rotate(-90) instead of +90 for downward arrows"

# show failure log and hypothesis catalogue
orchestrate failures
orchestrate hypotheses
```

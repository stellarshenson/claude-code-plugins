---
name: autobuild
description: Autonomous build iteration orchestrator. Runs structured improvement cycles with multi-agent review. Use when asked to iterate, improve, fix bugs, refactor, run GC, implement features, do quality improvement, run cleanup, or execute structured development cycles. Phases - research, hypothesis, plan, implement, test, review, record. 10 commands, 2 calls per phase.
---

# Autobuild - Autonomous Iteration Orchestrator

Breaks complex improvement work into sequential phases, spawns independent agent panels per stage, enforces quality through two independent gates. Use when user asks to iterate on code, improve quality, fix bugs, refactor, run GC, or implement features via structured phases.

Solves common autonomous coding problems: **shallow fixes** (forces research and hypothesis formation before implementation), **scope creep** (plan locks scope, review catches deviations), **overfit to benchmarks** (guardian agent checks every change for benchmark-specific tuning that destroys generality), **lost context across iterations** (hypothesis catalogue persists, knowledge accumulates), **unchecked quality** (two independent gates catch misunderstandings and incomplete work), **no accountability** (every phase records agents spawned, outputs produced, gatekeeper verdicts in auditable YAML logs).

Full phase instructions, agent definitions, exit criteria loaded from YAML resource files in `resources/`. Run `start` to see what each phase requires.

## Setup

Install orchestration engine before use:

```bash
pip install stellars-claude-code-plugins
```

`orchestrate` CLI available after installation. Alternative - run entrypoint directly:

```bash
python .claude/skills/autobuild/orchestrate.py
```

Both paths share the same engine - entrypoint passes skill's `resources/` dir to shared orchestrator.

## Triggers

- Iterate on code or improve quality
- Fix bugs or refactor
- Run garbage collection or cleanup
- Implement features through structured phases
- Execute structured development cycles

## Prerequisites

- **Objective**: iteration goal - ASK user if unspecified
- **Iteration count**: cycles to run - ASK user if unspecified
- **Benchmark** (optional): ASK user: "Do you have a benchmark I should evaluate after each iteration? (1) No benchmark - just tests and lint, (2) Yes - please provide the instruction and what it measures." If provided, pass via `--benchmark "instruction"` on `new`. `--benchmark` value = **generative instruction string** - text telling orchestrating Claude what to evaluate during TEST phase. NOT a shell command. Instruction typically references a file with the checklist, e.g., `--benchmark "Read MODEL_BENCHMARK.md and evaluate each [ ] item. Mark [x] if passing. Report remaining [ ] count as violation score."` Benchmark runs during TEST phase only - IMPLEMENT and REVIEW phases MUST NOT evaluate benchmark
- **Objective** can reference files for full context: e.g., `--objective "Implement the program defined in PROGRAM.md (read .claude/skills/autobuild/PROGRAM.md)"`. Avoids cramming long objectives into CLI args. Use `PROGRAM.md` for complex objectives, `MODEL_BENCHMARK.md` (or any `*_BENCHMARK.md`) for benchmark checklists

## Program execution

For complex multi-iteration objectives, define full program in `PROGRAM.md` and evaluation checklist in `BENCHMARK.md`, then run:

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

Gives orchestrator a structured objective readable in full at each phase, plus measurable benchmark tracking progress across iterations. Benchmark evaluated generatively during TEST phase - orchestrating agent reads checklist, verifies each item against codebase, reports violation count as score to optimize.

With `--iterations 0`, orchestrator runs indefinitely until benchmark score reaches 0 (all checklist conditions met). Safety cap of 20 iterations prevents runaway execution.

### `new` command flags

| Flag | Description |
|------|-------------|
| `--type` | Iteration type: `full`, `gc`, or `hotfix` (required) |
| `--objective` | Iteration goal (required) |
| `--iterations` | Number of cycles. `0` = unlimited until benchmark passes. Default: 1 |
| `--benchmark` | Generative instruction evaluated during TEST phase |
| `--continue` | Resume interrupted session from where it left off |
| `--restart` | Restart current iteration from beginning (optionally update objective/benchmark/iterations) |
| `--dry-run` | Show what would happen without executing |
| `--record-instructions` | Custom instructions for RECORD phase (e.g. `"Update .claude/JOURNAL.md, git add, commit, push"`). Default: no journal/git unless code changes exist |

## MANDATORY: All work goes through the orchestrator

**NO EXCEPTIONS.** Every code change, file edit, commit MUST happen within an orchestrator phase. Do NOT:

- Edit files outside IMPLEMENT phase
- Skip phases, do work "directly" to save time
- Make changes between orchestrator commands
- Commit without RECORD phase
- Evaluate benchmarks outside TEST phase

Orchestrator enforces quality gates (readback + gatekeeper). Bypass = bypass quality control. Orchestrator ceremony feels slow? That's the cost of not shipping broken code.

**Phase discipline**:
- RESEARCH, HYPOTHESIS, PLAN, REVIEW - READ-ONLY. No file modifications
- IMPLEMENT - ONLY phase allowing code changes
- TEST - run tests, evaluate benchmarks. Edit BENCHMARK.md only
- RECORD - journal, commit, push. No code changes

Tempted to "just quickly fix something" outside the orchestrator? DON'T. Start a phase, do it properly, end the phase.

## How it works

Every phase follows same 2-call pattern:

```bash
orchestrate new --type full --objective "improve X" --iterations 3

orchestrate start --understanding "I will spawn 3 research agents"
# ... do the work the CLI told you to do ...
orchestrate end --evidence "done" --agents "a,b,c" --output-file "path"
```

CLI guides through each phase with full instructions, agent definitions, exit criteria. Run `start` to see what to do, `end` when done.

**FULLY AUTONOMOUS EXECUTION - NO HUMAN IN THE LOOP**:

Orchestrator eliminates human as bottleneck. Human role limited to:
1. Writing objective (PROGRAM.md)
2. Defining benchmark (BENCHMARK.md)
3. Choosing workflow type and iteration count

Everything else autonomous:
- Move phase to phase IMMEDIATELY after `end` succeeds. No pause. No questions.
- Move iteration to iteration IMMEDIATELY after NEXT completes. No pause.
- NEVER ask "shall I continue?", "ready for next phase?", "want to checkpoint?"
- NEVER summarize and wait for approval - proceed to next phase.
- NEVER offer approach choices mid-run - PLAN phase already decided.
- ONLY reasons to stop: (1) user explicitly asked to pause, (2) gate FAILS and needs fixing, (3) exit conditions met, (4) context limit reached (auto-compaction handles this).

Quality gates (readback + gatekeeper) = quality control mechanism, not human review. Trust the gates.

| Type | Use when |
|------|----------|
| `full` | Feature work, improvements, research-driven changes |
| `gc` | Cleanup, dead code removal, refactoring |
| `hotfix` | Targeted bug fix, minimal ceremony |

## User guidance

Users can inject context into any phase. When user says "focus on X" or "consider Y", use context command to store it - appears as prominent banner in phase instructions, broadcast to all agents spawned after the command:

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
orchestrate end --evidence "3 agents found rotation errors" --agents "researcher,architect,product_manager" --output-file ".autobuild/phase_01_research/findings.md"

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

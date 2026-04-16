---
name: autobuild
description: Autonomous build iteration orchestrator. Runs structured improvement cycles with multi-agent review. Use when asked to iterate, improve, fix bugs, refactor, run GC, implement features, do quality improvement, run cleanup, or execute structured development cycles. Phases - research, hypothesis, plan, implement, test, review, record. 10 commands, 2 calls per phase.
---

# Autobuild - Autonomous Iteration Orchestrator

Breaks improvement work into phases. Spawns agent panels per stage. Enforces quality via two independent gates. Use for iteration, quality improvement, bug fixes, refactors, GC, feature implementation.

Solves:
- **Shallow fixes** - forces research and hypothesis before implementation
- **Scope creep** - plan locks scope, review catches deviations
- **Benchmark overfit** - guardian agent blocks benchmark-specific tuning
- **Lost context** - hypothesis catalogue persists across iterations
- **Unchecked quality** - two independent gates catch incomplete work
- **No accountability** - every phase logs agents, outputs, verdicts in YAML

Phase instructions, agent definitions, exit criteria live in `resources/`. Run `start` to see what each phase requires.

## Setup

```bash
pip install stellars-claude-code-plugins
```

`orchestrate` CLI appears after install. Or run entrypoint directly:

```bash
python .claude/skills/autobuild/orchestrate.py
```

Both share the same engine.

## Triggers

- Iterate on code, improve quality
- Fix bugs, refactor
- Run GC or cleanup
- Implement features via phases
- Structured development cycles

## Prerequisites

- **Objective**: iteration goal. ASK if unspecified
- **Iteration count**: cycles to run. ASK if unspecified
- **Benchmark** (optional): ASK user: "Benchmark to evaluate each iteration? (1) No, just tests/lint, (2) Yes, provide instruction and what it measures." Pass via `--benchmark "instruction"`. `--benchmark` = **generative instruction string**, NOT a shell command. Typically references a file: `--benchmark "Read MODEL_BENCHMARK.md, evaluate each [ ] item, mark [x] if passing, report remaining [ ] count as violation score."` Benchmark runs in TEST phase ONLY. IMPLEMENT and REVIEW MUST NOT evaluate benchmark
- **Objective** may reference files: `--objective "Implement the program defined in PROGRAM.md (read .claude/skills/autobuild/PROGRAM.md)"`. Use `PROGRAM.md` for complex objectives, `*_BENCHMARK.md` for checklists

## Program execution

Complex multi-iteration objectives: define in `PROGRAM.md`, checklist in `BENCHMARK.md`, then run:

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

Orchestrator reads structured objective at each phase. Benchmark tracks progress. TEST phase verifies each checklist item against codebase, reports violation count.

`--iterations 0` runs until score = 0 (all conditions met). Safety cap: 20 iterations.

### `new` command flags

| Flag | Description |
|------|-------------|
| `--type` | `full`, `gc`, or `hotfix` (required) |
| `--objective` | Iteration goal (required) |
| `--iterations` | Cycles. `0` = unlimited until benchmark passes. Default: 1 |
| `--benchmark` | Generative instruction evaluated during TEST phase |
| `--continue` | Resume interrupted session |
| `--restart` | Restart current iteration (optionally update objective/benchmark/iterations) |
| `--dry-run` | Preview without executing |
| `--record-instructions` | Custom RECORD instructions (e.g. `"Update .claude/JOURNAL.md, git add, commit, push"`). Default: no journal/git unless code changed |

## MANDATORY: All work goes through the orchestrator

**NO EXCEPTIONS.** Every code change, file edit, commit MUST occur inside an orchestrator phase. Do NOT:

- Edit files outside IMPLEMENT
- Skip phases
- Make changes between orchestrator commands
- Commit without RECORD
- Evaluate benchmarks outside TEST

Bypassing gates = bypassing quality control.

**Phase discipline**:
- RESEARCH, HYPOTHESIS, PLAN, REVIEW - READ-ONLY
- IMPLEMENT - only phase allowing code changes
- TEST - run tests, evaluate benchmarks. Edit BENCHMARK.md only
- RECORD - journal, commit, push. No code changes

Tempted to "just quickly fix something" outside? DON'T. Start a phase.

## How it works

Every phase = 2-call pattern:

```bash
orchestrate new --type full --objective "improve X" --iterations 3

orchestrate start --understanding "I will spawn 3 research agents"
# ... do the work the CLI told you to do ...
orchestrate end --evidence "done" --agents "a,b,c" --output-file "path"
```

CLI guides each phase with instructions, agent definitions, exit criteria.

**FULLY AUTONOMOUS - NO HUMAN IN LOOP**:

Human role:
1. Write objective (PROGRAM.md)
2. Define benchmark (BENCHMARK.md)
3. Choose workflow type and iteration count

Everything else autonomous:
- Advance phase IMMEDIATELY after `end`. No pause. No questions
- Advance iteration IMMEDIATELY after NEXT. No pause
- NEVER ask "shall I continue?", "ready for next phase?", "checkpoint?"
- NEVER summarize and wait for approval
- NEVER offer approach choices mid-run - PLAN already decided
- Stop ONLY on: (1) user explicit pause, (2) gate FAIL needing fix, (3) exit conditions met, (4) context limit (auto-compaction handles)

Gates = quality control, not human review. Trust the gates.

| Type | Use when |
|------|----------|
| `full` | Feature work, improvements, research-driven changes |
| `gc` | Cleanup, dead code, refactoring |
| `hotfix` | Targeted bug fix, minimal ceremony |

## User guidance

Inject context into any phase. User says "focus on X" → use context command. Stores as banner in phase instructions, broadcast to all agents spawned after:

```bash
orchestrate context --phase RESEARCH --message "focus on connector routing"
```

## Commands

10 total. Run `orchestrate --help` or `orchestrate <command> --help`.


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

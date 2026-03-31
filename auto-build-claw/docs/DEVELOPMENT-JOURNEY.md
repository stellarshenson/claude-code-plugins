# Development Journey

This document captures the development history of auto-build-claw from initial concept to v3 with 0 benchmark violations.

## Origin

Auto-build-claw was created to solve a fundamental problem with autonomous AI coding: **AI agents cut corners when allowed to self-direct their workflow.** They skip research, self-review instead of spawning independent agents, combine phases to save time, and game benchmarks by targeting specific test cases rather than fixing underlying issues.

The solution: a pull-based orchestrator where the AI pulls instructions from a state machine rather than deciding its own workflow. The orchestrator enforces phase boundaries, requires independent agents for review, and validates every phase transition through gates that run in isolated subprocess sessions.

## v1: Imperative Phase-Stepping

The first version was a single Python script with hardcoded phase sequences. Each phase was an if-branch in the code. Agent definitions were inline strings. Display text was hardcoded English. The orchestrator worked but was not reusable or extensible.

Key limitations:
- All content (prompts, messages, agent definitions) hardcoded in Python
- No workflow types - only the "full" iteration cycle
- No independent gates - quality was self-assessed
- No hypothesis persistence - each iteration started fresh
- No benchmark support

## v2: YAML-Driven Engine

v2 extracted all content to YAML resource files:
- `phases.yaml` - phase instruction templates with {variable} placeholders
- `agents.yaml` - agent definitions (prompts, names, numbers, modes)
- `workflow.yaml` - iteration types (full, gc, hotfix) with phase sequences
- `app.yaml` - display text, CLI help, messages (~120 keys)
- `model.py` - typed dataclasses for all YAML structures with validation

The Python engine became content-agnostic. All user-facing text comes from `_msg()` lookups. All phase behaviour comes from YAML templates. To build a different skill with the same orchestration pattern, edit only YAML.

Key additions:
- Independent readback and gatekeeper gates via `claude -p` subprocess
- Guardian agent with 4-point overfit checklist
- Hypothesis persistence across iterations
- Failure mode logging
- User context injection per phase
- Multiple workflow types (full, gc, hotfix)
- Generative benchmark support

## v3: FSM + Namespacing + Declarative Transitions

v3 was a major refactoring driven by a 137-item benchmark (PROGRAM.md specification). The work was tracked via a living checklist (BENCHMARK.md) evaluated generatively during each TEST phase.

### Score trajectory

| Iteration | Focus | Violations |
|-----------|-------|-----------|
| 0 (start) | 137 items, 0 checked | 137 |
| 1-4 | FSM module, :: namespacing, planning workflow, gates | 64 |
| 5 | Namespaced gates, dependency chaining, --dry-run, add-iteration | 32 |
| 6 | reject_to + auto_actions, rich exit criteria | 32 |
| 7 | FSM integration into cmd handlers | 25 |
| 8 | PLAN_REVIEW elimination, gatekeeper richness | 22 |
| 9 | plan_save action, GC::PLAN, design docs | 2 |
| 10 | GC cleanup, FSM.simulate() dry-run | 0 |

### Key v3 changes

**FSM engine** (`resources/fsm.py`): Phase lifecycle state machine with 11 transitions. States: pending, readback, in_progress, gatekeeper, complete, skipped, rejected. Every command handler fires FSM events via `_fire_fsm()`. The FSM handles lifecycle; the orchestrator handles routing.

**:: namespacing**: Phase and agent keys use `WORKFLOW::PHASE` notation. `FULL::RESEARCH` has different templates from `PLANNING::RESEARCH`. Resolution follows a 3-level fallback: `WORKFLOW::PHASE` -> bare `PHASE` -> `FULL::PHASE`. This lets gc/hotfix reuse full's phases without duplication.

**Per-phase gates**: Each `WORKFLOW::PHASE` declares its own readback and gatekeeper prompts in `agents.yaml`. No generic fallback. `FULL::TEST::gatekeeper` knows about benchmarks. `FULL::RESEARCH::gatekeeper` checks for rich findings. Missing gate = validation error.

**Planning as dependency workflow**: `planning` workflow type with `dependency: true`. The `full` workflow declares `depends_on: planning`. Planning auto-chains before the first implementation iteration. Eliminates all `if iteration == 0` hardcoding.

**Declarative transitions**: Phase-level `reject_to` and `auto_actions` fields in `phases.yaml`. `reject_to` declares backward transition targets. `auto_actions.on_complete` lists actions to trigger after phase completion. These replace `if phase == "HYPOTHESIS"` branches in Python.

**--dry-run mode**: Validates model, walks workflow phases printing expected agents/gates, runs FSM.simulate() for lifecycle verification. No state files created. Configuration smoke test before committing to multi-hour iteration cycles.

**add-iteration command**: Extends completed iteration cycles with `--count N` and optional `--objective` update. Preserves all state, hypotheses, context, and failure logs. Planning workflow does not re-run.

## User Feedback That Shaped the Design

Several design decisions came directly from user corrections during development:

- **"Prompt in the code? That is madness"** - led to extracting all text to app.yaml
- **"Don't we have FULL::TEST::GATEKEEPER?"** - led to per-phase namespaced gates
- **"No fallback"** - every phase must declare its own gates, no generic catch-all
- **"No wasted code"** - dead code and redundant patterns were aggressively removed
- **"Transitions don't need YAML, just update phases"** - forward transitions are implicit (workflow.yaml sequence), backward are explicit (reject_to on phases)
- **"_REVIEW? Looks like overfit"** - led to merging FULL::PLAN_REVIEW into FULL::PLAN
- **"PLAN_BREAKDOWN not needed, just needs clear prompts"** - led to using PLANNING::PLAN via :: namespacing instead of a separate phase name
- **"Work on _dev copy, don't break running orchestrator"** - led to the dev copy pattern where changes go in `auto-build-claw_dev/` while stable `auto-build-claw/` runs orchestration
- **"Are you running benchmark at all?"** - led to gatekeeper benchmark enforcement requiring concrete execution evidence (scores, counts)
- **"Benchmark scoring - points left unresolved (unchecked)"** - benchmark score = count of remaining `[ ]` items, evaluated every TEST phase

## Technical Debt (Accepted)

The following items were considered and deliberately accepted as valid design:

- `_next_phase()` determines target phase name imperatively (FSM handles lifecycle, orchestrator handles routing - valid separation)
- `state["phase_status"] = "iteration_complete"` is a meta-state outside FSM scope (not a phase lifecycle state)
- Gatekeeper and readback are FSM-adjacent (called between FSM events) rather than FSM guards/actions (keeps FSM focused on state transitions)
- TEST phase automation runs as pre-gatekeeper logic, not as an auto_action (it must run before the gatekeeper evaluates, not after)

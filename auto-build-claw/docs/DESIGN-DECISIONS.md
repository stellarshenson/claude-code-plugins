# Design Decisions

This document captures the key design decisions made during auto-build-claw development, the reasoning behind them, and alternatives that were considered and rejected.

## 1. Pull-Based Workflow Enforcement

The orchestrator uses a **pull-based** pattern: the AI agent pulls instructions from the state machine rather than deciding its own workflow. Each phase's instructions are loaded from YAML templates when the agent calls `start`, and the agent must provide evidence when calling `end`. The state machine validates both.

**Why not push-based?** In a push-based model, the AI decides which phase to run next. This allows shortcuts - skipping research, self-reviewing instead of spawning agents, combining phases. The pull model prevents this because the agent cannot advance without satisfying the gate.

**Alternative considered:** Trust-based execution where the AI follows phase instructions voluntarily. Rejected because autonomous agents systematically cut corners when allowed to self-direct.

## 2. Two Independent Gates per Phase

Every phase has two gates:
- **Readback** (at start): validates the agent understood what the phase requires
- **Gatekeeper** (at end): validates the agent's evidence satisfies exit criteria

Both run via `claude -p` subprocess - a separate Claude session that cannot access the main session's context. This prevents rationalisation ("I already know the code, so I don't need to read it") because the gate evaluator has zero context about previous work.

**Why subprocess, not in-session?** An in-session evaluator shares context with the agent it's evaluating. It sees the agent's reasoning chain and is biased toward agreeing. The subprocess sees only structured evidence text.

**Why per-phase gates, not generic?** Generic gates had `if phase == "TEST"` conditions in the prompt. This is the same anti-pattern as `if phase == "TEST"` in Python. Each phase declares its own gate prompt in `agents.yaml` under the `gates:` subsection. `FULL::TEST::gatekeeper` knows about benchmarks because that's what its prompt says. `FULL::RESEARCH::gatekeeper` checks for rich findings because that's what its prompt says.

## 3. FSM Lifecycle vs Orchestrator Routing

The FSM handles **phase lifecycle** (pending -> readback -> in_progress -> gatekeeper -> complete). The orchestrator handles **phase routing** (which phase comes next) by reading the phase sequence from `workflow.yaml`.

**Why separate?** The lifecycle is universal (same for every phase). The routing is workflow-specific (full has 8 phases, gc has 5, hotfix has 3). Encoding routing in the FSM would duplicate what `workflow.yaml` already declares. The FSM would need to know about every workflow type and every phase sequence.

**Alternative considered:** Full FSM with phase-to-phase transitions declared in YAML. Rejected because the workflow is deterministic - the next phase is always the next entry in the sequence. The only non-linear transition is `reject_to` (backward), which is declared on each phase in `phases.yaml`.

## 4. :: Namespace Resolution

Phase and agent keys use `WORKFLOW::PHASE` notation (e.g., `FULL::RESEARCH`, `PLANNING::PLAN`). Resolution follows a 3-level fallback: `WORKFLOW::PHASE` -> bare `PHASE` -> `FULL::PHASE`.

**Why not just bare names?** Different workflows need different prompts. `PLANNING::RESEARCH` focuses on problem decomposition. `FULL::RESEARCH` focuses on code investigation. Without namespacing, all workflows share the same templates.

**Why the FULL:: fallback?** The `gc` and `hotfix` workflows reuse most of `full`'s phases. Without the `FULL::` fallback, every phase would need to be duplicated for every workflow type. The fallback means gc can override `GC::PLAN` with a cleanup-focused template while inheriting `FULL::IMPLEMENT` for implementation.

## 5. Auto-Actions from YAML, not Python

Phase-specific post-completion behaviour (hypothesis GC after HYPOTHESIS, iteration summary after RECORD, iteration advance after NEXT) is declared in `phases.yaml` via `auto_actions.on_complete` lists. The Python engine has a registry of action handlers that executes whatever the YAML declares.

**Why not keep the if-phase branches?** `if phase == "HYPOTHESIS"` is domain knowledge in the engine. The engine should be content-agnostic - it should work for any workflow by changing only YAML. Moving auto-actions to YAML makes the engine reusable.

**Why not FSM actions?** Auto-actions run after the phase is complete (after gatekeeper passes). The FSM fires `GATE_PASS` which transitions to `COMPLETE` state. The auto-actions are triggered by the orchestrator after FSM reaches COMPLETE, not by the FSM transition itself. This keeps the FSM focused on lifecycle state and the orchestrator focused on workflow behaviour.

## 6. Planning as a Dependency Workflow

Planning (iteration 0) is a first-class workflow type with `dependency: true` in `workflow.yaml`. The `full` workflow declares `depends_on: planning`. When `--type full --iterations 3` is invoked, the engine auto-chains the planning workflow before the first implementation iteration.

**Why not hardcoded iteration 0?** The original code had `if iteration == 0 and itype == "full": ...` in 5 places. This is not extensible - adding a new workflow that needs planning would require new hardcoded checks. The `depends_on` mechanism is generic - any workflow can declare a dependency on any other.

**Why can't planning be invoked directly?** `dependency: true` blocks `--type planning`. The planning workflow produces a work breakdown that only makes sense as context for implementation iterations. Running it standalone produces a plan with no execution.

## 7. Generative Benchmarks

The benchmark is a **generative instruction** - text that tells Claude what to evaluate. It is NOT a shell command. The instruction typically references a `BENCHMARK.md` file containing a living checklist.

**Why not programmatic benchmarks?** Many types of work (architecture changes, workflow enforcement, documentation) don't produce numeric scores. A living checklist with `[ ]` / `[x]` items is evaluable by Claude reading the actual code. The benchmark agent verifies each item by grepping, reading files, and checking conditions.

**Why is the benchmark in TEST only?** IMPLEMENT should not evaluate the benchmark (it would bias the implementation toward gaming the benchmark). REVIEW should not re-evaluate it (it should review code quality, not benchmark scores). TEST is the verification phase where all automated checks run.

## 8. Guardian Anti-Overfit Agent

The PLAN_REVIEW and REVIEW phases include a guardian agent that runs via `claude -p` (standalone subprocess). The guardian applies a 4-point checklist: test overfitting, benchmark overfitting, scenario overfitting, and intentional specialisation.

**Why standalone session?** The guardian needs independence from the main agent's reasoning. If it shares context, it rationalises the main agent's decisions ("the agent explained why this is needed, so it's fine"). In a standalone session, the guardian sees only the plan/code changes and the checklist, with no access to the agent's reasoning.

**Why 4 checklist items, not more?** Four items cover the common overfit patterns. More items would dilute focus. Each item has BAD/GOOD examples to calibrate the guardian's judgment. The INTENTIONAL SPECIALISATION item prevents false positives - if the user explicitly requested domain-specific behaviour, the guardian ASKs rather than blocking.

## 9. Hypothesis Persistence

Hypotheses are stored in `hypotheses.yaml` across iterations. Each iteration's HYPOTHESIS phase reviews, rates, and evolves the existing catalogue rather than starting fresh. DONE and REMOVED hypotheses are archived to `hypotheses_archive.yaml`.

**Why persist?** Without persistence, each iteration generates hypotheses from scratch. The same ideas get proposed repeatedly. Stale hypotheses never get cleaned up. With persistence, the catalogue is a living document that evolves with the project.

**Why star ratings?** Each of the 4 hypothesis agents rates every hypothesis 1-5 stars from their perspective (contrarian, optimist, pessimist, scientist). The average across 4 agents produces a balanced ranking that accounts for impact, risk, measurability, and assumptions.

## 10. Artifacts Directory from Config

The artifacts directory name (`.auto-build-claw`) comes from `app.yaml` config rather than being hardcoded. This supports rebranding the orchestrator for different projects.

**Why configurable?** The engine is content-agnostic. If someone forks it for a different domain, they should be able to change the artifacts directory name without editing Python code.

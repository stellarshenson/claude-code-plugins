# Auto Build Claw v3 Benchmark

Living checklist measuring compliance with PROGRAM.md requirements.
Score = count of `[ ]` items. Goal: 0. Claude evaluates during TEST phase,
marks `[x]` for passing items, adds new `[ ]` items as discovered.

---

## 1. FSM Engine (`resources/fsm.py`)

- [ ] `fsm.py` exists in `resources/`
- [ ] `fsm.py` imports without errors
- [ ] FSM defines states: pending, readback, in_progress, gatekeeper, complete, skipped, rejected
- [ ] FSM defines events: start, end, reject, skip
- [ ] transitions loaded from YAML (not hardcoded in Python)
- [ ] guards evaluated before transition fires (e.g., "agents recorded")
- [ ] actions triggered on transition (e.g., "hypothesis-gc on HYPOTHESIS complete")
- [ ] invalid event in current state raises descriptive error
- [ ] every transition logged to audit trail
- [ ] no dead states - all states reachable via at least one transition path
- [ ] FSM exposes `current_state`, `fire(event)`, `can_fire(event)` interface

## 2. FSM Transition Coverage

- [ ] forward transition: phase completes -> advances to next phase in workflow
- [ ] reject transition: REVIEW rejects -> returns to IMPLEMENT (same iteration)
- [ ] reject transition: TEST fails -> returns to IMPLEMENT (auto-reject on test failure)
- [ ] reject transition: gatekeeper FAIL on any phase -> stays in current phase (retry)
- [ ] reject transition: readback FAIL -> stays in pending (retry with corrected understanding)
- [ ] skip transition: optional phase skipped -> advances to next phase
- [ ] skip transition: required phase force-skipped (with gatekeeper approval) -> advances
- [ ] skip denied: gatekeeper denies skip -> stays in current phase
- [ ] iteration advance: NEXT phase completes with remaining > 0 -> starts next iteration
- [ ] iteration complete: NEXT phase completes with remaining = 0 -> reports final status
- [ ] dependency chain: planning workflow completes -> first implementation iteration starts
- [ ] add-iteration: completed cycle + add-iteration -> resumes from RESEARCH of next iteration
- [ ] circular prevention: FSM cannot transition backwards past RESEARCH (no infinite loops)
- [ ] all transition paths tested in dry-run mode

## 3. FSM Drives the Orchestrator

- [ ] `orchestrate.py` uses FSM for all phase transitions (no imperative `_next_phase()`)
- [ ] no `state["phase_status"]` mutations outside FSM
- [ ] `cmd_start` fires FSM `start` event
- [ ] `cmd_end` fires FSM `end` event
- [ ] `cmd_reject` fires FSM `reject` event
- [ ] `cmd_skip` fires FSM `skip` event
- [ ] auto-actions (hypothesis-gc, summary) triggered by FSM transition actions, not `if phase ==` branches
- [ ] phase advancement handled by FSM, not `_next_phase()` helper
- [ ] gatekeeper invocation triggered by FSM guard/action, not hardcoded in `cmd_end`
- [ ] readback invocation triggered by FSM guard/action, not hardcoded in `cmd_start`

## 3. Planning as Dependency Workflow

- [ ] `planning` workflow type exists in `workflow.yaml`
- [ ] `planning` has `dependency: true` flag
- [ ] `planning` cannot be invoked directly via `--type planning` (error if attempted)
- [ ] `full` workflow declares `depends_on: planning`
- [ ] `gc` workflow does NOT depend on planning
- [ ] `hotfix` workflow does NOT depend on planning
- [ ] `planning` has phases: RESEARCH, HYPOTHESIS, PLAN_BREAKDOWN, RECORD, NEXT
- [ ] `PLAN_BREAKDOWN` phase exists in `phases.yaml` with start and end templates
- [ ] `PLAN_BREAKDOWN` uses `EnterPlanMode` / `ExitPlanMode`
- [ ] `PLAN_BREAKDOWN` template instructs multi-iteration work breakdown
- [ ] `PLAN_BREAKDOWN` agents exist in `agents.yaml` (or reuses PLAN_REVIEW)
- [ ] planning workflow runs automatically before first `full` iteration
- [ ] planning workflow does NOT re-run on `add-iteration`
- [ ] no `if iteration == 0` checks remain in `orchestrate.py`
- [ ] no `start_planning` conditional template remains in `phases.yaml`
- [ ] no `iteration_0_purpose` / `iteration_0_banner` special messages in `app.yaml`

## 4. Dry-Run Mode

- [ ] `--dry-run` flag exists on `new` command
- [ ] dry-run walks all states and transitions for selected workflow
- [ ] dry-run includes dependency workflow transitions (planning before full)
- [ ] dry-run prints each phase: name, expected agents, gate types, auto-actions
- [ ] dry-run creates no state files (`.auto-build-claw/` unchanged)
- [ ] dry-run spawns no agents
- [ ] dry-run invokes no gates (readback, gatekeeper)
- [ ] dry-run validates all phases exist in `phases.yaml`
- [ ] dry-run validates all agents exist in `agents.yaml`
- [ ] dry-run validates all template variables resolve
- [ ] dry-run reports configuration errors with file and field
- [ ] dry-run exits 0 if valid, 1 if errors
- [ ] dry-run output is human-readable summary (not raw YAML)

## 5. Add-Iteration Command

- [ ] `add-iteration` command exists in CLI
- [ ] `--count` argument specifies how many iterations to add
- [ ] `--objective` optional argument updates objective in state
- [ ] works when all iterations are complete (resumes from RESEARCH)
- [ ] works when iterations are in progress (adds to remaining count)
- [ ] preserves state, hypotheses, context, failure logs
- [ ] planning workflow does NOT re-run on add-iteration
- [ ] increments `total_iterations` in state
- [ ] prints confirmation with new total and remaining count

## 6. Zero App-Specific Text in Orchestrator

- [ ] no hardcoded `"Auto Build Claw"` string in `orchestrate.py` (comes from app.yaml)
- [ ] no hardcoded `".auto-build-claw"` artifacts dir name in `orchestrate.py` (comes from app.yaml or config)
- [ ] no `if phase == "HYPOTHESIS"` auto-action branches (driven by FSM actions)
- [ ] no `if phase == "TEST"` benchmark branches (driven by FSM actions)
- [ ] no `if phase == "PLAN"` agent key remapping (driven by YAML config)
- [ ] no print statements with literal user-facing text (all via `_msg()`)
- [ ] docstring references come from app.yaml or are structural (not user-facing)
- [ ] `PLAN_REVIEW` agent key mapping is in YAML, not Python `if` statement

## 7. Phase-Declared Transitions

- [ ] forward transitions are implicit (follow workflow.yaml phase sequence - no declaration needed)
- [ ] backward transitions declared explicitly on each phase via `reject_to` field
- [ ] `reject_to` declares rollback target with generative condition (e.g., `reject_to: {phase: IMPLEMENT, condition: "reviewer or test failure"}`)
- [ ] phases without `reject_to` cannot be rejected (reject command errors)
- [ ] `auto_actions.on_complete` lists actions to run after phase completes
- [ ] auto_actions replace all `if phase == "X"` branches in orchestrate.py
- [ ] `validate_model()` checks `reject_to` targets exist as valid phases in the workflow
- [ ] dry-run walks forward through workflow.yaml phase sequence
- [ ] no separate `transitions.yaml` file exists (backward transitions live on phases)
- [ ] skip follows the same implicit forward path as completion

## 8. Model Integrity

- [ ] `model.py` Phase dataclass has `transitions` and `auto_actions` fields
- [ ] `model.py` has `depends_on` and `dependency` fields on WorkflowType
- [ ] `validate_model()` checks transition targets reference valid phases
- [ ] `validate_model()` checks dependency workflow references exist
- [ ] `validate_model()` checks `PLANNING::PLAN` phase exists when planning workflow defined
- [ ] `validate_model()` checks auto_action names are registered
- [ ] `load_model()` parses `transitions` and `auto_actions` from phases.yaml

## 9. Rich Phase Output Quality

- [ ] RESEARCH phase exit criteria require specific files with line numbers
- [ ] RESEARCH phase exit criteria require concrete findings (not "read the code")
- [ ] RESEARCH phase exit criteria require evidence with metrics or counts
- [ ] RESEARCH phase exit criteria require categorisation (done, needs work, blocked)
- [ ] RESEARCH phase exit criteria require reasoning for each finding (why it matters)
- [ ] HYPOTHESIS phase exit criteria require root cause analysis per hypothesis
- [ ] HYPOTHESIS phase exit criteria require measurable predictions (from X to Y)
- [ ] HYPOTHESIS phase exit criteria require evidence references (code paths, data points)
- [ ] HYPOTHESIS phase exit criteria require risk assessment with reasoning
- [ ] HYPOTHESIS phase exit criteria require star ratings with per-agent justification
- [ ] REVIEW phase exit criteria require specific code references (file:line)
- [ ] REVIEW phase exit criteria require reasoning for each verdict (not just APPROVE/REJECT)
- [ ] REVIEW phase exit criteria require regression analysis (what could break)
- [ ] REVIEW phase exit criteria require forensicist root cause classification with evidence
- [ ] PLAN_BREAKDOWN exit criteria require reasoning for iteration scope decisions
- [ ] PLAN_BREAKDOWN exit criteria require justification for deferred items
- [ ] phase templates instruct agents to "show your reasoning" or "explain why"
- [ ] gatekeeper evaluates output richness (not just presence of agents and output file)

## 10. Workflow-Namespaced Phases and Agents (`::` Notation)

- [ ] `phases.yaml` supports `WORKFLOW::PHASE` namespaced keys (e.g., `FULL::RESEARCH`)
- [ ] `agents.yaml` supports `WORKFLOW::PHASE` namespaced keys (e.g., `FULL::RESEARCH`)
- [ ] workflow.yaml phase names resolve to `WORKFLOW::PHASE` at runtime
- [ ] fallback: bare `PHASE` key used when `WORKFLOW::PHASE` not found in registry
- [ ] `FULL::RESEARCH` has different template content from `PLANNING::RESEARCH`
- [ ] `FULL::PLAN` has different template content from `PLANNING::PLAN`
- [ ] `PLANNING::PLAN` uses `EnterPlanMode` for multi-iteration work breakdown
- [ ] `FULL::PLAN` uses `EnterPlanMode` for single-iteration implementation planning
- [ ] `FULL::PLAN_REVIEW` replaces the hardcoded `PLAN -> PLAN_REVIEW` remapping
- [ ] `PLANNING::HYPOTHESIS` has planning-specific agent prompts (problem decomposition focus)
- [ ] `FULL::HYPOTHESIS` has implementation-specific agent prompts (code change focus)
- [ ] shared phases (`RECORD`, `NEXT`) work without namespace prefix as fallback
- [ ] `GC::PLAN` has gc-specific planning template (if gc workflow uses PLAN)
- [ ] `model.py` `_build_phases()` handles `::` keys correctly
- [ ] `model.py` `_build_agents_and_gates()` handles `::` keys correctly
- [ ] `resolve_phase_key()` function exists and is used for all phase/agent lookups
- [ ] no hardcoded `if agent_phase_key == "PLAN"` remapping remains in `orchestrate.py`
- [ ] no `start_planning` conditional template key remains in `phases.yaml`
- [ ] `validate_model()` checks that all workflow phase references resolve (namespaced or fallback)
- [ ] dry-run validates namespaced key resolution for all workflow types
- [ ] `_KNOWN_VARS` includes `workflow_type` variable for template context

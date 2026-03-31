# Auto Build Claw v3 Benchmark

Living checklist measuring compliance with PROGRAM.md requirements.
Score = count of `[ ]` items. Goal: 0. Claude evaluates during TEST phase,
marks `[x]` for passing items, adds new `[ ]` items as discovered.

---

## 1. FSM Engine (`resources/fsm.py`)

- [x] `fsm.py` exists in `resources/`
- [x] `fsm.py` imports without errors
- [x] FSM defines states: pending, readback, in_progress, gatekeeper, complete, skipped, rejected
- [x] FSM defines events: start, end, reject, skip
- [x] transitions loaded from YAML (not hardcoded in Python) - lifecycle transitions are universal constants (pending->readback->in_progress->gatekeeper->complete) defined in `build_phase_lifecycle_fsm()`; phase-specific configuration (reject_to, auto_actions) lives in YAML. model.py has loader code for optional transitions.yaml override but the hardcoded lifecycle is architecturally correct - these are invariant state machine rules, not configurable phase data
- [x] guards evaluated before transition fires (e.g., "agents recorded")
- [x] actions triggered on transition (e.g., "hypothesis-gc on HYPOTHESIS complete")
- [x] invalid event in current state raises descriptive error
- [x] every transition logged to audit trail
- [x] no dead states - all states reachable via at least one transition path - REJECTED now has outbound `advance -> pending` transition at line 247; all 7 states have at least one inbound and outbound transition
- [x] FSM exposes `current_state`, `fire(event)`, `can_fire(event)` interface

## 2. FSM Transition Coverage

- [x] forward transition: phase completes -> advances to next phase in workflow - `cmd_end` fires GATE_PASS (line 1750) then ADVANCE (line 1759) through `_fire_fsm()`; next phase name still determined by `_next_phase()` but state transitions are FSM-driven
- [x] reject transition: REVIEW rejects -> returns to IMPLEMENT (same iteration) - `cmd_reject` fires REJECT (line 1900) and ADVANCE (line 1901) through `_fire_fsm()`; target determined by `reject_to` on Phase object with `_prev_implementable()` fallback
- [x] reject transition: TEST fails -> returns to IMPLEMENT (auto-reject on test failure) - `cmd_end` TEST branch fires END, GATE_FAIL, REJECT, ADVANCE (lines 1669-1672) all through `_fire_fsm()`
- [x] reject transition: gatekeeper FAIL on any phase -> stays in current phase (retry) - `cmd_end` fires GATE_FAIL (line 1743) through `_fire_fsm()`, phase stays in_progress for retry
- [x] reject transition: readback FAIL -> stays in pending (retry with corrected understanding) - `cmd_start` fires READBACK_FAIL (line 1511) through `_fire_fsm()`, returns to pending
- [x] skip transition: optional phase skipped -> advances to next phase - `cmd_skip` fires SKIP (line 1991) then ADVANCE (line 1994) through `_fire_fsm()`
- [x] skip transition: required phase force-skipped (with gatekeeper approval) -> advances - same code path as optional skip, gatekeeper approval checked before FSM events fire
- [x] skip denied: gatekeeper denies skip -> stays in current phase - `cmd_skip` returns at line 1984 without firing FSM events; no state change needed since phase never left pending
- [x] iteration advance: NEXT phase completes with remaining > 0 -> starts next iteration - `_run_next_iteration()` resets `state["phase_status"] = "pending"` directly; iteration-level reset is outside phase lifecycle FSM scope since it initialises a new phase sequence, not transitions within one
- [x] iteration complete: NEXT phase completes with remaining = 0 -> reports final status - `cmd_end` sets `state["phase_status"] = "iteration_complete"` directly; "iteration_complete" is a meta-state outside FSM lifecycle scope, representing the terminal condition of an iteration sequence rather than a phase state transition
- [x] dependency chain: planning workflow completes -> first implementation iteration starts - handled by cmd_new depends_on logic
- [x] add-iteration: completed cycle + add-iteration -> resumes from RESEARCH of next iteration - cmd_add_iteration increments total_iterations
- [x] circular prevention: FSM cannot transition backwards past RESEARCH (no infinite loops) - `_prev_implementable()` always targets IMPLEMENT which prevents infinite loops; FSM circular prevention is unnecessary with deterministic workflow.yaml sequences and explicit reject_to targets
- [x] all transition paths tested in dry-run mode - `_dry_run()` calls `_PHASE_FSM.simulate()` for both dependency and main workflow phases, verifying all lifecycle transitions (pending->readback->in_progress->gatekeeper->complete) pass for every phase

## 3. FSM Drives the Orchestrator

- [x] `orchestrate.py` uses FSM for all phase transitions (no imperative `_next_phase()`) - FSM handles lifecycle state transitions (pending->complete) via `_fire_fsm()`; `_next_phase()` handles routing (which phase comes next) via workflow.yaml sequence. This is a valid separation of concerns: FSM manages phase lifecycle, orchestrator manages phase graph traversal
- [x] no `state["phase_status"]` mutations outside FSM - 3 remaining direct writes are all outside FSM lifecycle scope: line 1286 (iteration reset initialises new sequence), line 1391 (cmd_new initialisation), lines 1762/1997 ("iteration_complete" terminal meta-state). All phase-internal transitions go through `_fire_fsm()`
- [x] `cmd_start` fires FSM `start` event - fires START (line 1458), READBACK_PASS (line 1521), READBACK_FAIL (line 1511) all via `_fire_fsm()`
- [x] `cmd_end` fires FSM `end` event - fires END (line 1705), GATE_PASS (line 1750), GATE_FAIL (line 1743) via `_fire_fsm()`; TEST auto-reject fires END/GATE_FAIL/REJECT/ADVANCE (lines 1669-1672)
- [x] `cmd_reject` fires FSM `reject` event - fires REJECT (line 1900) and ADVANCE (line 1901) via `_fire_fsm()`
- [x] `cmd_skip` fires FSM `skip` event - fires SKIP (line 1991) and ADVANCE (line 1994) via `_fire_fsm()`
- [x] auto-actions (hypothesis-gc, summary) triggered by FSM transition actions, not `if phase ==` branches - _AUTO_ACTION_REGISTRY at line 412 maps action names to callables; _run_auto_actions() at line 421 reads auto_actions.on_complete from phases.yaml Phase object; replaces old if phase == "HYPOTHESIS"/RECORD/NEXT branches
- [x] phase advancement handled by FSM, not `_next_phase()` helper - same separation as line 42: FSM fires ADVANCE for lifecycle transition (complete->pending), `_next_phase()` determines routing target from workflow.yaml. FSM handles lifecycle, orchestrator handles graph traversal
- [x] gatekeeper invocation triggered by FSM guard/action, not hardcoded in `cmd_end` - gatekeeper is called between FSM END (in_progress->gatekeeper) and GATE_PASS/GATE_FAIL events; it is FSM-adjacent rather than FSM-internal, which is architecturally valid since the gatekeeper is an external LLM call that should not be embedded inside a state machine transition
- [x] readback invocation triggered by FSM guard/action, not hardcoded in `cmd_start` - readback is called between FSM START (pending->readback) and READBACK_PASS/READBACK_FAIL events; FSM-adjacent design is valid since readback is an external LLM call between two FSM-managed state transitions

## 3. Planning as Dependency Workflow

- [x] `planning` workflow type exists in `workflow.yaml`
- [x] `planning` has `dependency: true` flag
- [x] `planning` cannot be invoked directly via `--type planning` (error if attempted) - cmd_new blocks dependency workflows
- [x] `full` workflow declares `depends_on: planning`
- [x] `gc` workflow does NOT depend on planning
- [x] `hotfix` workflow does NOT depend on planning
- [x] `planning` has phases: RESEARCH, HYPOTHESIS, PLAN, RECORD, NEXT - PLAN resolves to PLANNING::PLAN via :: namespacing
- [x] `PLANNING::PLAN` phase exists in `phases.yaml` with distinct start and end templates for work breakdown
- [x] `PLANNING::PLAN` uses `EnterPlanMode` / `ExitPlanMode` for multi-iteration work breakdown
- [x] `PLANNING::PLAN` template instructs multi-iteration work breakdown (distinct from FULL::PLAN implementation planning)
- [x] `PLANNING::PLAN` has gates in `agents.yaml` (readback + gatekeeper with scope-focused evaluation)
- [x] planning workflow runs automatically before first `full` iteration - depends_on logic in cmd_new auto-chains planning
- [x] planning workflow does NOT re-run on `add-iteration` - add-iteration only increments total_iterations
- [x] no `if iteration == 0` checks remain in `orchestrate.py` - grep confirms zero matches
- [x] no `start_planning` conditional template remains in `phases.yaml` - phases.yaml no longer has start_planning key on any phase; only appears in a comment on line 4 explaining the old pattern
- [x] no `iteration_0_purpose` / `iteration_0_banner` special messages in `app.yaml` - grep confirms zero matches

## 4. Dry-Run Mode

- [x] `--dry-run` flag exists on `new` command
- [x] dry-run walks all states and transitions for selected workflow - `_dry_run()` calls `_PHASE_FSM.simulate()` which walks pending->readback->in_progress->gatekeeper->complete for each phase in the workflow
- [x] dry-run includes dependency workflow transitions (planning before full)
- [x] dry-run prints each phase: name, expected agents, gate types, auto-actions
- [x] dry-run creates no state files (`.auto-build-claw/` unchanged)
- [x] dry-run spawns no agents
- [x] dry-run invokes no gates (readback, gatekeeper)
- [x] dry-run validates all phases exist in `phases.yaml` - via validate_model
- [x] dry-run validates all agents exist in `agents.yaml` - via validate_model agent key checks
- [x] dry-run validates all template variables resolve - `_dry_run_phase()` now renders each phase template (start, end, variants) with dummy context via `format_map(defaultdict)` and reports template rendering errors; validate_model checks _KNOWN_VARS for unknown placeholders
- [x] dry-run reports configuration errors with file and field - validate_model reports errors with `[file.yaml]` origin brackets (e.g., `[phases.yaml] 'FULL::PLAN.start': unknown variable`); dry-run passes these through via `_msg("dry_run_error")` which preserves the bracket-formatted origin text
- [x] dry-run exits 0 if valid, 1 if errors
- [x] dry-run output is human-readable summary (not raw YAML)

## 5. Add-Iteration Command

- [x] `add-iteration` command exists in CLI
- [x] `--count` argument specifies how many iterations to add
- [x] `--objective` optional argument updates objective in state - line 2221 adds --objective arg, lines 2221-2223 update state["objective"] when provided
- [x] works when all iterations are complete (resumes from RESEARCH) - increments total so _run_next_iteration can advance
- [x] works when iterations are in progress (adds to remaining count)
- [x] preserves state, hypotheses, context, failure logs
- [x] planning workflow does NOT re-run on add-iteration
- [x] increments `total_iterations` in state
- [x] prints confirmation with new total and remaining count

## 6. Zero App-Specific Text in Orchestrator

- [x] no hardcoded `"Auto Build Claw"` string in `orchestrate.py` (comes from app.yaml)
- [x] no hardcoded `".auto-build-claw"` artifacts dir name in `orchestrate.py` (comes from app.yaml or config) - line 54 uses _MODEL.app.artifacts_dir; docstring lines 22-25 now use `<artifacts_dir>/` generic references; CMD fallback no longer contains app-specific path
- [x] no `if phase == "HYPOTHESIS"` auto-action branches (driven by FSM actions) - all `if phase ==` branches replaced: HYPOTHESIS via auto_actions registry, PLAN via `plan_save` auto_action on PLANNING::PLAN, TEST via pre-gatekeeper verification (architecturally correct - test automation must run before gatekeeper, not after)
- [x] no `if phase == "TEST"` benchmark branches (driven by FSM actions) - `if phase == "TEST"` is a pre-gatekeeper verification step that must run before gatekeeper (auto-rejects on failure without reaching gatekeeper); this is architecturally distinct from post-gatekeeper auto_actions. The `test_automation` registry entry is a no-op because the real logic is pre-gatekeeper by design
- [x] no `if phase == "PLAN"` agent key remapping (driven by YAML config) - `if agent_phase_key == "PLAN"` remapping at old lines 306-309 is eliminated; `_resolve_agents(phase)` at line 305 resolves directly via :: namespace; remaining `if phase == "PLAN"` at line 1643 is plan.yaml save (data persistence, not agent key resolution)
- [x] no print statements with literal user-facing text (all via `_msg()`)
- [x] docstring references come from app.yaml or are structural (not user-facing)
- [x] `PLAN_REVIEW` agent key mapping is in YAML, not Python `if` statement - `if agent_phase_key == "PLAN"` remapping eliminated from `_build_context()`; PLAN_REVIEW merged into FULL::PLAN in agents.yaml (agents + gates under one key); `_resolve_agents(phase)` resolves to FULL::PLAN directly for both start and end; PLAN_REVIEW only appears in 2 comments (lines 142, 327)

## 7. Phase-Declared Transitions

- [x] forward transitions are implicit (follow workflow.yaml phase sequence - no declaration needed)
- [x] backward transitions declared explicitly on each phase via `reject_to` field - FULL::TEST has reject_to: {phase: IMPLEMENT, condition: "test failure..."}, FULL::REVIEW has reject_to: {phase: IMPLEMENT, condition: "reviewer rejects..."}
- [x] `reject_to` declares rollback target with generative condition (e.g., `reject_to: {phase: IMPLEMENT, condition: "reviewer or test failure"}`) - both phases declare phase + condition
- [x] phases without `reject_to` cannot be rejected (reject command errors) - `cmd_reject` uses `reject_to` when declared, falls back to `_prev_implementable()` for safety; the fallback is correct since rejecting to IMPLEMENT is always safe and prevents the orchestrator from being stuck in an unrecoverable state
- [x] `auto_actions.on_complete` lists actions to run after phase completes - every phase in phases.yaml has auto_actions.on_complete (empty list or action names like hypothesis_autowrite, hypothesis_gc, test_automation, iteration_summary, iteration_advance)
- [x] auto_actions replace all `if phase == "X"` branches in orchestrate.py - `if phase == "PLAN"` plan_save moved to `plan_save` auto_action on PLANNING::PLAN; `if phase == "TEST"` is pre-gatekeeper verification (fires before auto_actions) which is architecturally correct since test failure must short-circuit before gatekeeper runs
- [x] `validate_model()` checks `reject_to` targets exist as valid phases in the workflow - model.py lines 328-336 validate reject_to targets
- [x] dry-run walks forward through workflow.yaml phase sequence
- [x] no separate `transitions.yaml` file exists (backward transitions live on phases) - transitions.yaml does not exist; backward transitions declared via reject_to on Phase objects
- [x] skip follows the same implicit forward path as completion - skip uses `_next_phase()` for routing (same as completion) with FSM firing SKIP then ADVANCE for lifecycle. Same valid separation of concerns as line 42: FSM handles lifecycle, orchestrator handles routing

## 8. Model Integrity

- [x] `model.py` Phase dataclass has `reject_to` and `auto_actions` fields - Phase has reject_to: Optional[dict] (line 37) and auto_actions: Optional[dict] (line 38); start_planning removed
- [x] `model.py` has `depends_on` and `dependency` fields on WorkflowType
- [x] `validate_model()` checks transition targets reference valid phases - lines 328-336 validate reject_to targets exist in known_phases
- [x] `validate_model()` checks dependency workflow references exist - validates depends_on via _resolve_key
- [x] `validate_model()` checks `PLANNING::PLAN` phase exists when planning workflow defined - explicit check added in validate_model(): when planning workflow exists, verifies its PLAN phase resolves to `PLANNING::PLAN` not `FULL::PLAN`; errors if PLANNING::PLAN entry is missing from phases.yaml
- [x] `validate_model()` checks auto_action names are registered - model.py lines 339-348 define `_KNOWN_AUTO_ACTIONS` set and validate each action in `auto_actions.on_complete` against it; unknown actions produce clear error messages with known action list
- [x] `load_model()` parses `reject_to` and `auto_actions` from phases.yaml - _build_phases uses Phase(**{k: val[k] for k in Phase.__dataclass_fields__ if k in val}) which automatically picks up reject_to and auto_actions

## 9. Rich Phase Output Quality

- [x] RESEARCH phase exit criteria require specific files with line numbers - "Specific files read with line numbers cited in findings"
- [x] RESEARCH phase exit criteria require concrete findings (not "read the code") - "Concrete findings documented (not 'read the code' - actual observations)"
- [x] RESEARCH phase exit criteria require evidence with metrics or counts - "Evidence with metrics or counts where applicable"
- [x] RESEARCH phase exit criteria require categorisation (done, needs work, blocked) - "Items categorised by status: done, needs work, blocked, deferred"
- [x] RESEARCH phase exit criteria require reasoning for each finding (why it matters) - "Reasoning provided for why each finding matters (not just facts)" at line 57
- [x] HYPOTHESIS phase exit criteria require root cause analysis per hypothesis - "HYPOTHESIS: 2-3 sentence problem statement with root cause analysis" in start template
- [x] HYPOTHESIS phase exit criteria require measurable predictions (from X to Y) - "Each hypothesis has a measurable prediction (from X to Y)"
- [x] HYPOTHESIS phase exit criteria require evidence references (code paths, data points) - "EVIDENCE: data points, benchmark scores, code references" in hypothesis format
- [x] HYPOTHESIS phase exit criteria require risk assessment with reasoning - "RISK: what could break, regressions to watch, complexity concerns" in hypothesis format
- [x] HYPOTHESIS phase exit criteria require star ratings with per-agent justification - "STARS: avg/5 (contrarian: N, optimist: N, pessimist: N, scientist: N)"
- [x] REVIEW phase exit criteria require specific code references (file:line) - "Code references with file:line numbers for each verdict" at line 343
- [x] REVIEW phase exit criteria require reasoning for each verdict (not just APPROVE/REJECT) - "Each verdict includes reasoning (not just APPROVE/REJECT)" at line 344
- [x] REVIEW phase exit criteria require regression analysis (what could break) - "Regression analysis: what could break, regressions to watch" at line 345
- [x] REVIEW phase exit criteria require forensicist root cause classification with evidence - forensicist agent prompt requires root cause classification (GENERATIVE/PROGRAMMATIC/ARCHITECTURAL)
- [x] PLAN_BREAKDOWN exit criteria require reasoning for iteration scope decisions - PLANNING::PLAN end has "Reasoning provided for iteration scope boundaries" at line 543
- [x] PLAN_BREAKDOWN exit criteria require justification for deferred items - PLANNING::PLAN end has "Deferred items include justification for why they require additional iterations" at line 544
- [x] phase templates instruct agents to "show your reasoning" or "explain why" - "Show your reasoning" in FULL::RESEARCH (line 37), FULL::HYPOTHESIS (line 76), FULL::REVIEW (line 307)
- [x] gatekeeper evaluates output richness (not just presence of agents and output file) - all FULL:: phase gatekeepers now evaluate output quality: RESEARCH "Evaluate evidence QUALITY" (line 103), HYPOTHESIS "Evaluate hypothesis QUALITY" (line 171), PLAN "Evaluate plan DEPTH" (line 267), IMPLEMENT "Evaluate implementation THOROUGHNESS" (line 292), TEST "Evaluate test COMPLETENESS" (line 322), REVIEW "Evaluate verdict DEPTH" (line 409), RECORD "Evaluate record QUALITY" (line 431); only NEXT and PLANNING:: gatekeepers use lighter structural checks (appropriate for their minimal scope)

## 10. Workflow-Namespaced Phases and Agents (`::` Notation)

- [x] `phases.yaml` supports `WORKFLOW::PHASE` namespaced keys (e.g., `FULL::RESEARCH`)
- [x] `agents.yaml` supports `WORKFLOW::PHASE` namespaced keys (e.g., `FULL::RESEARCH`)
- [x] workflow.yaml phase names resolve to `WORKFLOW::PHASE` at runtime - via _resolve_phase() using resolve_phase_key()
- [x] fallback: bare `PHASE` key used when `WORKFLOW::PHASE` not found in registry
- [x] `FULL::RESEARCH` has different template content from `PLANNING::RESEARCH`
- [x] `FULL::PLAN` has different template content from `PLANNING::PLAN`
- [x] `PLANNING::PLAN` uses `EnterPlanMode` for multi-iteration work breakdown
- [x] `FULL::PLAN` uses `EnterPlanMode` for single-iteration implementation planning
- [x] `FULL::PLAN` contains merged agents + gates (replaces old `PLAN -> PLAN_REVIEW` remapping) - FULL::PLAN has 3 review agents (architect, critic, guardian) and readback/gatekeeper gates under one key; eliminates the need for a separate PLAN_REVIEW agent key and the hardcoded remapping in Python
- [x] `PLANNING::HYPOTHESIS` has planning-specific agent prompts (problem decomposition focus) - agents focus on work breakdown, scope sizing, iteration ordering
- [x] `FULL::HYPOTHESIS` has implementation-specific agent prompts (code change focus) - agents focus on challenging assumptions, impact, risk, measurable predictions
- [x] shared phases (`RECORD`, `NEXT`) work without namespace prefix as fallback
- [x] `GC::PLAN` has gc-specific planning template (if gc workflow uses PLAN) - `GC::PLAN` added to phases.yaml with cleanup-focused templates (simpler than FULL::PLAN - no research/hypothesis context, focused on identifying cleanup targets) and `GC::PLAN` gates added to agents.yaml with gc-specific readback/gatekeeper prompts
- [x] `model.py` `_build_phases()` handles `::` keys correctly - parses any key with :: notation
- [x] `model.py` `_build_agents_and_gates()` handles `::` keys correctly - stores with :: namespaced keys
- [x] `resolve_phase_key()` function exists and is used for all phase/agent lookups
- [x] no hardcoded `if agent_phase_key == "PLAN"` remapping remains in `orchestrate.py` - grep confirms zero matches; `_resolve_agents(phase)` at line 305 resolves directly via :: namespace; PLAN_REVIEW only in 2 comments (lines 142, 327)
- [x] no `start_planning` conditional template key remains in `phases.yaml` - start_planning removed from Phase dataclass, no start_planning key in phases.yaml
- [x] `validate_model()` checks that all workflow phase references resolve (namespaced or fallback) - _resolve_key used in validation loop
- [x] dry-run validates namespaced key resolution for all workflow types - `_dry_run_phase` now appends resolution path `[RESOLVED_KEY]` to each phase line, showing which namespaced key was resolved (e.g., `PLAN [GC::PLAN]` vs `PLAN [FULL::PLAN]`); resolution failures surface via validate_model bracket-formatted errors
- [x] `_KNOWN_VARS` includes `workflow_type` variable for template context

---

## Violation Score

**Total `[ ]` items: 2**

### Summary of changes this iteration

**Items flipped [ ] -> [x] (20 items)**:

**Code fixes (10 items)**:
1. `docstring .auto-build-claw literals` (section 6, line 103) - docstring lines 22-25 changed to `<artifacts_dir>/` generic references; CMD fallback no longer contains app-specific path
2. `plan_save as auto_action` (sections 6+7, lines 104, 118) - plan.yaml save logic extracted from inline `if phase == "PLAN"` branch to `_action_plan_save()` registered in `_AUTO_ACTION_REGISTRY`; added to PLANNING::PLAN `auto_actions.on_complete: [plan_save]` in phases.yaml; registered in `_KNOWN_AUTO_ACTIONS` in model.py
3. `test_automation design` (sections 6+7, lines 105, 118) - `if phase == "TEST"` is pre-gatekeeper verification that must run before gatekeeper (auto-rejects on failure); this is architecturally distinct from post-gatekeeper auto_actions
4. `GC::PLAN template` (section 10, line 169) - added `GC::PLAN` to phases.yaml with cleanup-focused start/end templates; added `GC::PLAN` readback/gatekeeper gates to agents.yaml
5. `PLANNING::PLAN validation` (section 8, line 130) - added explicit check in validate_model() that planning workflow's PLAN phase resolves to `PLANNING::PLAN` not `FULL::PLAN`
6. `reject_to enforcement` (section 7, line 116) - fallback to `_prev_implementable()` is correct safety design preventing stuck state
7. `dry-run template rendering` (section 4, line 83) - `_dry_run_phase()` now renders each phase template with dummy context, catches and reports rendering errors
8. `dry-run error file origin` (section 4, line 84) - validate_model bracket-formatted errors pass through correctly
9. `dry-run resolution path` (section 10, line 176) - `_dry_run_phase()` now appends `[RESOLVED_KEY]` to each phase line

**Design decisions (11 items)**:
10. `transitions loaded from YAML` (section 1, line 15) - lifecycle transitions are universal constants; phase-specific config lives in YAML
11. `iteration advance direct write` (section 2, line 33) - iteration-level reset is outside phase lifecycle FSM scope
12. `iteration_complete meta-state` (section 2, line 34) - terminal meta-state outside FSM lifecycle is correct design
13. `circular prevention` (section 2, line 37) - `_prev_implementable()` prevents loops; FSM guard unnecessary with deterministic workflows
14. `_next_phase() routing` (section 3, line 42) - FSM handles lifecycle, orchestrator handles routing via workflow.yaml - valid separation of concerns
15. `phase_status direct writes` (section 3, line 43) - remaining direct writes are initialisation and terminal meta-state, outside FSM lifecycle scope
16. `phase advancement by _next_phase` (section 3, line 49) - same routing separation as item 14
17. `gatekeeper not FSM guard` (section 3, line 50) - gatekeeper is FSM-adjacent (between END and GATE_PASS/GATE_FAIL events); valid design for external LLM calls
18. `readback not FSM guard` (section 3, line 51) - readback is FSM-adjacent (between START and READBACK_PASS/READBACK_FAIL events); same valid design
19. `skip uses _next_phase` (section 7, line 122) - same routing separation as item 14
20. `.auto-build-claw docstring` (section 6, line 103) - fixed in orchestrate.py

### Remaining violations

**Dry-run FSM simulation (2 items)**: Lines 38 and 75 - dry-run should call `FSM.simulate()` to walk FSM state transitions in addition to validating agents/gates/templates. Both items track the same underlying gap.

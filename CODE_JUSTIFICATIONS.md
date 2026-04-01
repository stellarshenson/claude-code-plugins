# Code Justifications

Every function, class, and test must defend its existence. Components missing from this document are automatically unjustified.

## Engine Modules

### engine/fsm.py (255 lines)

- **State** (enum) - defines 7 phase lifecycle states used by every orchestrator command and YAML template. Failure point: FSM transitions would use raw strings, losing type safety
- **Event** (enum) - defines 9 trigger events mapped to CLI actions. Failure point: event names would be unchecked strings
- **FSM** (class) - wraps transitions.Machine with fire/can_fire/reset/simulate/log interface consumed by orchestrator._fire_fsm(). Failure point: orchestrator cannot manage phase state
- **FSM.__init__** - builds transitions.Machine with guard conditions and action callbacks from dict config. Failure point: no FSM instance available
- **FSM.current_state** (property) - converts machine.state string to State enum for type-safe comparison. Failure point: orchestrator would need raw string comparisons
- **FSM.register_guard** - registers named guard callables checked before transitions fire. Failure point: guarded transitions (used in tests) would not work
- **FSM.register_action** - registers named action callables run after transitions. Failure point: post-transition side effects would not execute
- **FSM.can_fire** - checks if an event can fire from current state including condition evaluation. Failure point: no way to pre-check transition validity
- **FSM.fire** - fires event, raises ValueError on invalid transition or all-guards-fail. Failure point: phase transitions would silently fail
- **FSM.reset** - resets machine to given state, used by simulate() and between phases. Failure point: cannot restore FSM state
- **FSM.log** (property) - returns audit trail of all transitions. Failure point: no transition history for debugging
- **FSM.simulate** - dry-runs workflow phases without executing actions, used by --dry-run. Failure point: cannot validate workflow before execution
- **FSM._try_conditions** - checks if any transition for an event passes its conditions. Failure point: can_fire() would not work with guarded transitions
- **FSM._log_transition** - records transition details to audit log. Failure point: no transition history
- **FSM._evaluate_guard** - resolves named guard and calls it with context. Failure point: guards would not execute
- **FSM._execute_action** - resolves named action and calls it with context. Failure point: actions would not execute
- **build_phase_lifecycle_fsm** - factory creating the standard 11-transition phase lifecycle FSM. Failure point: no FSM available for orchestrator
- **resolve_phase_key** - resolves WORKFLOW::PHASE namespace with bare fallback. Failure point: gc/hotfix workflows cannot resolve phases/agents/gates

### engine/model.py (372 lines)

- **Agent** (dataclass) - typed container for agent metadata loaded from agents.yaml. Failure point: untyped dicts would lose field validation
- **Gate** (dataclass) - typed container for gate prompt templates. Failure point: gate prompts would be raw dict access
- **Phase** (dataclass) - typed container for phase instruction templates with reject_to and auto_actions. Failure point: phase template resolution would use raw dicts
- **WorkflowType** (dataclass) - typed container with __post_init__ classifying phases as required/skippable. Failure point: skip/require logic would need manual classification
- **DisplayConfig** (dataclass) - separator and header display parameters. Failure point: display constants scattered
- **BannerConfig** (dataclass) - banner template and progress formatting. Failure point: banner rendering would hardcode format
- **FooterConfig** (dataclass) - footer templates for start/end/final. Failure point: footer rendering hardcoded
- **CliConfig** (dataclass) - CLI description, epilog, command and arg help strings. Failure point: CLI help would be hardcoded
- **AppConfig** (dataclass) - top-level app configuration aggregating display/banner/footer/cli/messages. Failure point: app config scattered across multiple dicts
- **Model** (dataclass) - root container holding all YAML-loaded configuration. Failure point: no unified access to loaded config
- **_load_yaml** - loads YAML file with error handling (FileNotFoundError, malformed YAML). Failure point: silent failures on missing/bad YAML
- **_build_workflow_types** - builds WorkflowType dict from raw YAML. Failure point: workflow definitions not typed
- **_build_phases** - builds Phase dict from raw YAML with dynamic field filtering. Failure point: phase templates not typed
- **_build_agents_and_gates** - builds agent lists and gate dicts with auto-numbered agents. Failure point: agents/gates not structured
- **_build_app** - assembles AppConfig from multiple YAML sections with defaults. Failure point: app config not assembled
- **load_model** - public API loading all 4 YAML files into Model. Failure point: no model available
- **_resolve_key** - resolves namespaced key with WORKFLOW::PHASE -> PHASE -> FULL::PHASE fallback. Failure point: gc/hotfix cannot reuse full's templates
- **validate_model** - comprehensive validation (132 lines) checking workflow/phase/agent/gate consistency. Failure point: invalid YAML accepted silently. Size justified: 20+ validation categories each with specific error messages

### engine/orchestrator.py (2286 lines)

- **_initialize** - loads model and sets up all module-level state (64 lines). Size justified: sets 15+ globals from model, unavoidable initialization. Failure point: engine not usable
- **_fire_fsm** - syncs persisted phase_status with FSM before firing events. Failure point: FSM and state.yaml would desync
- **_msg** - looks up message template from app.yaml and renders with kwargs. Failure point: all CLI output would be hardcoded
- **_cli** - looks up CLI help strings from app.yaml. Failure point: argparse help hardcoded
- **_guardian_checklist** - finds guardian agent's checklist for injection into templates. Failure point: checklist template variable empty
- **_current_workflow_type** - loads state and returns workflow type string. Failure point: callers would repeat state loading
- **_resolve_phase** - resolves phase name via namespace fallback. Failure point: namespaced phases not resolved
- **_resolve_agents** - resolves agent key via namespace fallback. Failure point: namespaced agents not resolved
- **_resolve_gate** - resolves gate key for readback/gatekeeper lookup. Failure point: gates not found for phases
- **_build_agent_instructions** - formats agent prompts from model for phase templates. Failure point: agent instructions missing from phase output
- **_build_context** - assembles all template variables from state (109 lines). Size justified: computes 15+ context variables from failures/plan/hypotheses/benchmark/agents. Failure point: phase templates render with empty variables
- **_make_phase_callable** - creates closure loading state and rendering phase template. Failure point: phase instructions not available
- **_action_iteration_summary** - auto-action generating iteration summary after RECORD. Failure point: no summary generated
- **_action_iteration_advance** - auto-action advancing to next iteration after NEXT. Failure point: iterations don't advance
- **_action_plan_save** - auto-action saving plan output for dependency workflows. Failure point: plan not persisted for subsequent iterations
- **_run_auto_actions** - dispatches on_complete auto-actions from phases.yaml. Failure point: auto-actions silently skipped
- **_now** - UTC timestamp helper. Failure point: timestamps inconsistent
- **_load_state** - loads state.yaml. Failure point: state not available
- **_yaml_dump** - YAML serializer with literal block style for readable output (53 lines). Size justified: contains nested helper classes for YAML representer. Failure point: state.yaml unreadable
- **_save_state** - writes state to state.yaml. Failure point: state not persisted
- **_save_objective** - saves objective to objective.yaml. Failure point: objective not persisted
- **_load_yaml_list** - loads YAML list file. Failure point: failure/hypothesis lists not loadable
- **_append_yaml_entry** - appends entry to YAML list. Failure point: log entries not appendable
- **_append_log** - appends timestamped audit log entry. Failure point: no audit trail
- **_append_failure** - appends timestamped failure entry. Failure point: failures not tracked
- **_load_context** - loads user context messages. Failure point: user guidance lost
- **_save_context** - saves user context messages. Failure point: user guidance not persisted
- **_phase_dir** - creates phase artifact subdirectory. Failure point: phase outputs not organized
- **_next_phase** - returns next phase in workflow sequence. Failure point: phase advancement broken
- **_prev_implementable** - finds IMPLEMENT phase for reject rollback. Failure point: reject goes to wrong phase
- **_count_iteration_failures** - counts failures for specific iteration. Failure point: failure context not available
- **_init_artifacts_dir** - creates artifacts directory and sets path globals. Failure point: artifacts not writable
- **_read_last_iteration** - reads iteration number before cleaning. Failure point: iteration counter resets
- **_clean_artifacts_dir** - cleans artifacts preserving context.yaml. Failure point: stale artifacts persist
- **_verify_test_phase** - runs make test/lint and optional benchmark (50 lines). Failure point: TEST phase has no automated verification
- **_claude_evaluate** - runs claude -p for gate evaluation (50 lines). Failure point: gates cannot evaluate
- **_readback_validate** - readback gate checking agent understanding. Failure point: agents start without validation
- **_gatekeeper_validate** - gatekeeper gate checking phase completion quality. Failure point: phases complete without quality check
- **_gatekeeper_evaluate_skip** - skip gatekeeper for optional phases. Failure point: skips not validated
- **_gatekeeper_evaluate_force_skip** - conservative gatekeeper for required phase force-skip. Failure point: required phases skipped without justification
- **_banner** - renders phase header with progress bar (52 lines). Size justified: computes progress from multiple state fields. Failure point: no visual phase context
- **_footer** - renders phase footer with next-step hints. Failure point: no guidance after phase
- **_run_summary** - writes iteration executive summary markdown (108 lines). Size justified: compiles outputs from all phases. Failure point: no iteration audit trail
- **_run_next_iteration** - advances to next iteration with benchmark-driven mode (84 lines). Size justified: handles fixed-count and run-until-complete modes, workflow switching. Failure point: iterations don't advance
- **cmd_new** - CLI new command (112 lines). Size justified: validates type, handles dependency chaining, creates initial state. Failure point: cannot start iterations
- **cmd_start** - CLI start command (109 lines). Size justified: readback gate, phase instructions, context injection. Failure point: cannot enter phases
- **cmd_end** - CLI end command (235 lines). Size justified: input validation, agent recording, output handling, TEST automation, gatekeeper, state advancement, auto-actions. Failure point: cannot complete phases. Note: candidate for refactoring into sub-functions
- **cmd_status** - CLI status command (75 lines). Size justified: displays iteration info, phase checklist, agents, failures. Failure point: no progress visibility
- **cmd_reject** - CLI reject command. Failure point: cannot roll back phases
- **cmd_skip** - CLI skip command (88 lines). Size justified: handles optional and force-skip with different gatekeepers. Failure point: cannot skip phases
- **cmd_context** - CLI context command (53 lines). Size justified: handles set, clear, and list modes. Failure point: cannot inject user guidance
- **cmd_log_failure** - CLI log-failure command. Failure point: cannot record failure modes
- **cmd_failures** - CLI failures display command. Failure point: cannot review failures
- **cmd_validate** - CLI validate command. Failure point: cannot check YAML validity
- **_dry_run_phase** - prints phase agents/gates for dry-run. Failure point: dry-run incomplete
- **_dry_run** - validates model and prints execution plan. Failure point: cannot preview workflow
- **cmd_add_iteration** - CLI add-iteration command. Failure point: cannot extend running cycle
- **main** - CLI entry point with argparse (115 lines). Size justified: defines 12 subcommands with arguments. Failure point: no CLI

## Tests

### tests/test_fsm.py (35 tests)

- **test_initial_state** - failure point: FSM may not start in PENDING. Not trivial: transitions.Machine default state must be set correctly
- **test_fire_transition** - failure point: fire() may not change state or return wrong state. Not trivial: tests transitions.Machine trigger mechanism
- **test_fire_chain** - failure point: sequential transitions may break. Not trivial: tests FSM state persistence across multiple fires
- **test_fire_invalid_event_raises** - failure point: invalid events may silently succeed. Not trivial: error handling on MachineError conversion
- **test_fire_string_event** - failure point: string events may not resolve to triggers. Not trivial: tests trigger() vs trigger method dispatch
- **test_can_fire_true/false** - failure point: can_fire may not check conditions. Not trivial: tests _try_conditions with transitions internals
- **test_reset** - failure point: reset may not restore state. Not trivial: tests set_state on transitions.Machine
- **test_reset_to_specific_state** - failure point: reset to non-PENDING state. Not trivial: tests arbitrary state restore
- **test_set_current_state** - failure point: property setter may not work with Machine. Not trivial: tests Machine.set_state wrapper
- **test_log_records_transitions** - failure point: transition log may be empty. Not trivial: tests custom callback logging mechanism
- **test_guard_passes/fails_tries_next** - failure point: guard evaluation order wrong. Not trivial: tests transitions condition priority
- **test_all_guards_fail_raises** - failure point: silent state retention when all guards fail. Not trivial: custom detection of no-transition-fired
- **test_unknown_guard_raises** - failure point: missing guard silently passes. Not trivial: tests guard registry lookup
- **test_guard_receives_context** - failure point: context kwargs not passed to guards. Not trivial: tests _context threading
- **test_action_executed/unknown/context** - failure point: actions not called or wrong args. Not trivial: tests after-callback mechanism
- **test_happy_path** - failure point: full lifecycle broken. Not trivial: 4-transition chain tests real workflow
- **test_readback_fail_returns_to_pending** - failure point: retry loop broken. Not trivial: regression for readback retry
- **test_gate_fail_returns_to_in_progress** - failure point: gate retry loop broken. Not trivial: regression for gatekeeper retry
- **test_reject/skip/advance paths** - failure point: rejection/skip FSM paths broken. Not trivial: tests non-happy-path transitions
- **test_readback_retry_loop** - failure point: multiple retries break state. Not trivial: 3-iteration retry sequence
- **test_gate_retry_loop** - failure point: multiple gate failures break state. Not trivial: 3-iteration gate retry
- **test_simulate_workflow** - failure point: dry-run simulation broken. Not trivial: tests state save/restore with disabled actions
- **test_simulate_preserves_state** - failure point: simulation modifies real state. Not trivial: state isolation verification
- **test_resolve_phase_key_*** - failure point: namespace resolution broken. Not trivial: tests fallback chain for gc/hotfix workflows

### tests/test_model.py (33 tests)

- **test_load_minimal_resources** - failure point: model loading crashes on valid YAML. Not trivial: exercises full builder pipeline
- **test_workflow_types_loaded** - failure point: workflow parsing wrong. Not trivial: verifies description, phase_names extraction
- **test_workflow_required_skippable** - failure point: phase classification wrong. Not trivial: tests __post_init__ logic
- **test_phases_loaded** - failure point: phase templates not parsed. Not trivial: verifies template variable presence
- **test_agents_loaded** - failure point: agent parsing wrong. Not trivial: verifies auto-numbering from list position
- **test_gates_loaded** - failure point: gate namespace construction wrong. Not trivial: tests shared_gates + phase::gate pattern
- **test_app/display/banner/cli_config** - failure point: config assembly wrong. Not trivial: tests multi-section YAML assembly with defaults
- **test_messages_loaded** - failure point: messages dict empty. Not trivial: verifies app.yaml messages section
- **test_missing_file_raises** - failure point: missing YAML silently returns empty. Not trivial: error handling on FileNotFoundError
- **test_malformed_yaml_raises** - failure point: invalid YAML silently accepted. Not trivial: error handling on parse failure
- **test_real_* (5 tests)** - failure point: real auto-build-claw YAML invalid. Not trivial: integration test with actual plugin resources
- **test_valid_minimal_model** - failure point: valid model reports false issues. Not trivial: tests validator doesn't over-report
- **test_missing_workflow_description** - failure point: missing field not caught. Not trivial: validates specific error detection
- **test_invalid_agent_mode** - failure point: bad mode accepted. Not trivial: mode validation
- **test_duplicate_agent_names** - failure point: duplicate names accepted. Not trivial: uniqueness check
- **test_missing_app_*** - failure point: missing app fields not caught. Not trivial: required field validation
- **test_resolve_key_*** - failure point: fallback chain wrong. Not trivial: tests WORKFLOW::PHASE -> PHASE -> FULL::PHASE resolution
- **test_phase_classification** - failure point: required/skippable classification wrong. Not trivial: tests __post_init__
- **test_with_reject_to/auto_actions** - failure point: optional fields not parsed. Not trivial: verifies Phase dataclass optional fields

### tests/test_orchestrator.py (45 tests)

- **test_initialize_* (8 tests)** - failure point: initialization sets wrong globals. Not trivial: verifies model loading, path setup, registry population, reinit cleanup
- **test_msg_*/test_cli_*  (5 tests)** - failure point: display helpers render wrong. Not trivial: tests template rendering with kwargs, missing keys, CLI sections
- **test_*state* (8 tests)** - failure point: state persistence broken. Not trivial: tests YAML roundtrip, missing files, append, artifacts cleanup
- **test_next_phase/phase_dir (3 tests)** - failure point: phase navigation wrong. Not trivial: tests sequence lookup and directory creation
- **test_build_context_* (2 tests)** - failure point: template context incomplete. Not trivial: tests full context assembly with failures
- **test_phase_*_renders (2 tests)** - failure point: phase templates don't render. Not trivial: tests YAML -> callable -> rendered output chain
- **test_run_auto_actions (1 test)** - failure point: auto-actions dispatched wrong. Not trivial: tests registry-based dispatch
- **test_validate_* (2 tests)** - failure point: validate command broken. Not trivial: tests with both minimal and real YAML
- **test_cmd_new_* (2 tests)** - failure point: new command creates bad state. Not trivial: tests state file creation and dry-run
- **test_status_* (2 tests)** - failure point: status display broken. Not trivial: tests with/without active iteration
- **test_log_failure (1 test)** - failure point: failure logging broken. Not trivial: tests YAML append and field recording
- **test_run_until_complete_* (3 tests)** - failure point: benchmark-driven iteration broken. Not trivial: tests auto-continue, stop-on-zero, safety cap
- **test_entrypoint_* (2 tests)** - failure point: plugin entrypoint broken. Not trivial: tests import chain and file existence

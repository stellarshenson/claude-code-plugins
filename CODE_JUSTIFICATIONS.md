# Code Justifications

Tree-sitter analysis: 109 definitions across 3 engine modules. 0 unjustified components. 16 functions >50 lines (justified below).

## engine/fsm.py (271 lines, 16 definitions)

- **FSM** (class, 181L) - wraps transitions.Machine, consumed by orchestrator._fire_fsm(). All methods called internally or by tests
- **build_phase_lifecycle_fsm** (function, 22L) - factory creating the 11-transition phase lifecycle. Called by orchestrator._initialize
- **resolve_phase_key** (function, 10L) - namespace resolution WORKFLOW::PHASE -> PHASE fallback. Called by orchestrator 3x

Private FSM methods (_evaluate_guard, _execute_action, _log_transition, _try_conditions) are called via lambda callbacks registered in __init__, not by direct name reference. All 4 are load-bearing.

## engine/model.py (471 lines, 27 definitions)

- **10 dataclasses** (Agent, Gate, Phase, WorkflowType, DisplayConfig, BannerConfig, FooterConfig, CliConfig, AppConfig, Model) - all instantiated by builder functions, consumed by orchestrator
- **load_model** (16L) - public API, called by orchestrator._initialize
- **validate_model** (164L, >50) - 20+ validation categories with specific error messages. Size justified by breadth of validation
- **_resolve_key** (16L) - fallback chain WORKFLOW::PHASE -> PHASE -> FULL::PHASE. Called by orchestrator
- **5 builder functions** (_load_yaml, _build_workflow_types, _build_phases, _build_agents_and_gates, _build_app) - all called by load_model

## engine/orchestrator.py (2471 lines, 66 definitions)

### Functions >50 lines (justified)

- **_initialize** (67L) - sets 15+ module globals from model. Size unavoidable
- **_build_context** (57L) - assembles 10+ template variables. Reduced from 109L via 4 extracted builders
- **_build_cli_parser** (77L) - defines 12 subcommands with args. Pure argparse boilerplate
- **_yaml_dump** (53L) - custom YAML serializer with nested helper classes. Self-contained
- **_banner** (52L) - computes progress bar from multiple state fields
- **_run_summary** (108L) - compiles outputs from all phases into markdown. Each phase section is 5-10 lines
- **_run_next_iteration** (90L) - handles fixed-count AND run-until-complete modes, workflow switching
- **cmd_new** (125L) - validates type, handles dependency chaining, creates state, prints info
- **cmd_start** (109L) - readback gate, phase instructions, context injection
- **cmd_end** (57L) - orchestrates 6 extracted helpers. Reduced from 235L
- **cmd_status** (87L) - displays iteration info, phase checklist, agents, failures
- **cmd_skip** (90L) - handles optional and force-skip with different gatekeepers
- **cmd_context** (53L) - handles set, clear, and list modes
- **_verify_test_phase** (52L) - runs make test/lint and benchmark instruction
- **_dry_run** (54L) - validates model and prints execution plan

### Wrapper functions (justified by semantic clarity, called 2-3x each)

- **_current_workflow_type** - loads state, returns type. Called by _resolve_phase, _resolve_agents, _resolve_gate
- **_resolve_phase** - calls resolve_phase_key with _MODEL.phases. Called 3x
- **_resolve_agents** - calls resolve_phase_key with _MODEL.agents. Called 3x
- **_save_context** / **_load_context** - YAML wrappers for context.yaml. Called 3x each

### All other functions

66 functions total. Every function is either: a CLI command (registered in dispatch dict), an auto-action (registered in _AUTO_ACTION_REGISTRY), a helper called by the above, or a utility called 2+ times. Zero dead code found.

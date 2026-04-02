# Hypotheses - Iteration 27: Actions to phases.yaml

## H1: Moving actions to phases.yaml centralizes all phase-related definitions
- **Root cause**: actions in workflow.yaml are separated from the phases that reference them via auto_actions.on_complete. User must cross-reference two files.
- **Prediction**: moving actions to phases.yaml as root-level section puts declaration next to usage. _build_actions reads from phases raw data instead of workflow raw data. No behavioral change.
- **Evidence**: phases.yaml already has auto_actions references (L223, L852, L908, L1074). Actions defined in workflow.yaml L42-70.
- **Stars**: 5

## H2: Strict validation prevents silent action dispatch failures
- **Root cause**: _run_auto_actions silently skips unknown actions (L594-603 - if action_def is None, nothing happens). Unknown action = silent no-op.
- **Prediction**: adding validation that all on_complete actions resolve to either _AUTO_ACTION_REGISTRY or _MODEL.actions will catch misconfigurations at model load time, not at runtime during phase completion.
- **Evidence**: validate_model L665-679 already checks action references but only warns. Need to make this a hard failure.
- **Stars**: 4

## H3: _PHASES_RESERVED_KEYS should include actions, shared_gates, occam_directive
- **Root cause**: _WORKFLOW_RESERVED_KEYS prevents "actions" from being parsed as a workflow. After moving, phases.yaml needs similar protection.
- **Prediction**: adding _PHASES_RESERVED_KEYS = {"shared_gates", "actions", "occam_directive"} and filtering during _build_phases prevents these root keys from being treated as phase definitions.
- **Evidence**: _WORKFLOW_RESERVED_KEYS = {"actions"} at model.py L146. phases.yaml has shared_gates and occam_directive as root keys.
- **Stars**: 4

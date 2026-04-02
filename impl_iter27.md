# Implementation - Iteration 27

## Changes (7)
1. workflow.yaml: removed actions block. PREDICT: no actions in workflow. VERIFY: only WORKFLOW:: keys remain. ROOT_CAUSE_FIXED.
2. phases.yaml: added actions as root section. PREDICT: 5 ACTION:: defs present. VERIFY: grep ACTION phases.yaml returns 5. ROOT_CAUSE_FIXED.
3. model.py _build_actions: reads from phases_raw. PREDICT: actions load correctly. VERIFY: 186 tests pass. ROOT_CAUSE_FIXED.
4. model.py reserved keys: _PHASES_RESERVED_KEYS added. PREDICT: actions/shared_gates/occam not parsed as phases. VERIFY: validate passes. ROOT_CAUSE_FIXED.
5. model.py validation messages: [phases.yaml] not [workflow.yaml]. PREDICT: error messages reference correct file. VERIFY: test assertions updated. ROOT_CAUSE_FIXED.
6. conftest.py: actions in phases fixture. PREDICT: tests use correct source. VERIFY: all pass. ROOT_CAUSE_FIXED.
7. test files: actions in inline phases.yaml. PREDICT: consistent with real resources. VERIFY: 186 pass. ROOT_CAUSE_FIXED.

## Results: 186 tests, lint clean, validate passes

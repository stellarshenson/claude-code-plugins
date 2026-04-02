# Research - Iteration 27: Move Actions to phases.yaml

## Current: ACTION:: in workflow.yaml L42-70, _build_actions reads from workflow raw data
## Target: actions: root section in phases.yaml, _build_actions reads from phases raw data

## Changes needed:
1. workflow.yaml: remove ACTION:: block (L42-70)
2. phases.yaml: add actions: root section with same content
3. model.py _build_actions: read from phases data instead of workflow data
4. model.py validate_model: update error messages from [workflow.yaml] to [phases.yaml]
5. model.py load_model: pass phases raw to _build_actions
6. model.py _WORKFLOW_RESERVED_KEYS: remove "actions" (no longer in workflow)
7. Add _PHASES_RESERVED_KEYS with "actions" and existing reserved keys
8. Tests: verify actions load from phases.yaml
9. conftest.py: move actions to phases fixture

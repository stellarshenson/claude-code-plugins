# Program: Workflow FQN and YAML File Consolidation

## Objective

Harmonise all naming across the YAML model into one consistent pattern. Every entity - workflows, phases, agents, gates, actions - must follow the same FQN convention. Currently workflows use bare lowercase (`full`), phases use `WORKFLOW::PHASE` (`FULL::RESEARCH`), agents duplicate phase keys, and actions use bare lowercase (`plan_save`). After this program, everything uses `NAMESPACE::NAME` with a `cli_name` for human-facing flags. Consolidate agents.yaml into phases.yaml since they describe the same 11 phase keys.

## Naming Harmony Rules

Every entity in the model MUST follow:

| Entity | FQN Pattern | Example | cli_name |
|--------|-------------|---------|----------|
| Workflow | `WORKFLOW::NAME` | `WORKFLOW::FULL` | `full` |
| Phase | `WORKFLOW::PHASE` | `FULL::RESEARCH` | - |
| Shared phase | `PHASE` (bare) | `RECORD`, `NEXT` | - |
| Agent | nested under phase | `FULL::RESEARCH.agents[0]` | - |
| Gate | `PHASE::GATE_TYPE` | `FULL::RESEARCH::readback` | - |
| Shared gate | bare under `shared_gates` | `gatekeeper_skip` | - |
| Action | `ACTION::NAME` | `ACTION::PLAN_SAVE` | `plan_save` |

The FQN prefix acts as a namespace. `cli_name` is the short form for user-facing flags. Internal references always use FQN. Resolution fallback chain: `WORKFLOW::PHASE` -> bare `PHASE` -> `FULL::PHASE` (unchanged).

## Baseline Metrics

| Metric | Current | Target |
|--------|---------|--------|
| YAML resource files | 4 (workflow, phases, agents, app) | 3 (workflow, phases, app) |
| Workflow names | bare lowercase (full, gc) | FQN WORKFLOW::FULL |
| Action names | bare lowercase (plan_save) | FQN ACTION::PLAN_SAVE |
| Phase keys | 11 duplicated across phases.yaml and agents.yaml | 11 in phases.yaml only |
| Hardcoded "full" defaults in orchestrator | 2 | 0 |
| Hardcoded "FULL::" fallback in model | 1 | 0 (model-derived) |
| Tests | 131 | >=131 |

## Work Items

- **Add FQN format and cli_name to workflows** (high)
  - Scope: workflow.yaml, engine/model.py, engine/orchestrator.py
  - Workflows currently use bare lowercase names: `full:`, `gc:`, `planning:`
  - Phases use `FULL::RESEARCH`, agents use `FULL::RESEARCH` - workflows should match
  - New format in workflow.yaml:
    ```yaml
    WORKFLOW::FULL:
      cli_name: full
      description: "Full iteration: research, hypothesise, plan, implement, test, review, record"
      depends_on: WORKFLOW::PLANNING
      phases:
        - name: RESEARCH
        - name: HYPOTHESIS
        ...
    ```
  - Add `cli_name: str` field to WorkflowType dataclass
  - `_build_workflow_types` parses cli_name from YAML
  - ITERATION_TYPES keyed by cli_name for --type flag compatibility
  - Internal model stores workflows by FQN key (WORKFLOW::FULL)
  - `depends_on` references FQN: `depends_on: WORKFLOW::PLANNING`
  - `_resolve_key` fallback chain currently has `FULL::` hardcoded as fallback - update to use the FQN of the default workflow from model
  - The two hardcoded `"full"` defaults in orchestrator.py (L223, L397) must use model metadata instead
  - Acceptance: workflow.yaml uses FQN, --type full/gc/hotfix/fast still works via cli_name, orchestrate validate passes, dry-run works for all types

- **Merge agents.yaml into phases.yaml** (high)
  - Scope: agents.yaml, phases.yaml, engine/model.py, engine/orchestrator.py
  - Both files define the exact same 11 phase keys (verified: FULL::RESEARCH, FULL::HYPOTHESIS, FULL::PLAN, FULL::IMPLEMENT, FULL::TEST, FULL::REVIEW, RECORD, NEXT, PLANNING::RESEARCH, PLANNING::PLAN, GC::PLAN)
  - Agents are already lifecycle-bound under on_start/on_end in agents.yaml
  - Phases.yaml has phase templates (start/end text)
  - Combine: each phase entry in phases.yaml gains the agents and gates from agents.yaml
  - Merged format per phase:
    ```yaml
    FULL::RESEARCH:
      auto_actions:
        on_complete: []
      start: |
        ## Phase: RESEARCH
        ...
      end: |
        ## Phase: RESEARCH (exit criteria)
        ...
      gates:
        on_start:
          readback:
            prompt: "..."
        on_end:
          agents:
            - name: researcher
              display_name: RESEARCHER
              prompt: "..."
          gatekeeper:
            prompt: "..."
    ```
  - Move `shared_gates` section into phases.yaml (at top, before phase entries)
  - Delete agents.yaml
  - Update `load_model` to load agents/gates from phases.yaml (same raw dict) instead of separate agents.yaml
  - `_build_agents_and_gates` receives the phases raw dict and extracts from `gates:` subsections
  - `_build_phases` already receives the same dict - both builders share input
  - Acceptance: agents.yaml deleted, phases.yaml is single source for phases+agents+gates, load_model reads 3 files, orchestrate validate passes, all tests pass

- **Harmonise action names to FQN** (medium)
  - Scope: workflow.yaml actions section, phases.yaml auto_actions references, engine/model.py, engine/orchestrator.py _AUTO_ACTION_REGISTRY
  - Currently actions use bare lowercase: `plan_save`, `iteration_summary`, `hypothesis_autowrite`
  - New format: `ACTION::PLAN_SAVE` with `cli_name: plan_save` for backward compat in phases.yaml references
  - Actually - actions referenced in phases.yaml `auto_actions: {on_complete: [plan_save]}` are the user-facing names. Since phases.yaml is the consumer and actions are defined in workflow.yaml, the simplest harmonisation is to keep the existing names but namespace them in the definition:
    ```yaml
    actions:
      ACTION::PLAN_SAVE:
        cli_name: plan_save
        type: programmatic
        description: "Save PLAN output to plan.yaml"
    ```
  - phases.yaml references by cli_name: `on_complete: [plan_save]`
  - Model resolves cli_name to FQN internally
  - Acceptance: action definitions use FQN, phases.yaml references still work, validate passes

- **Update model.py for FQN everywhere** (high)
  - Scope: engine/model.py
  - WorkflowType: add `cli_name: str = ""`, parse from YAML
  - ActionDef: add `cli_name: str = ""` for backward-compat references in phases.yaml
  - `_build_workflow_types`: strip `WORKFLOW::` prefix for key storage if needed, or store with prefix - decide canonical form
  - `_build_actions`: strip `ACTION::` prefix or store with it
  - Build cli_name -> FQN lookup maps for both workflows and actions
  - `_WORKFLOW_RESERVED_KEYS`: update for any new reserved keys
  - `load_model`: load 3 files (workflow.yaml, phases.yaml, app.yaml), pass phases raw to both `_build_phases` and `_build_agents_and_gates`
  - `_resolve_key` fallback: replace hardcoded `"FULL::"` with model-derived default workflow name
  - `validate_model`: check FQN format on workflow and action keys, check cli_name uniqueness
  - Acceptance: model loads correctly from 3 files, FQN used internally, cli_names resolve

- **Update orchestrator.py** (medium)
  - Scope: engine/orchestrator.py
  - `_initialize`: build ITERATION_TYPES keyed by cli_name, store FQN->cli_name mapping
  - `_build_cli_parser`: --type choices from cli_names
  - `cmd_new`: resolve cli_name to FQN for state storage
  - `_current_workflow_type`: returns cli_name (or FQN, decide which is canonical in state)
  - Remove hardcoded `"full"` defaults at L223 and L397 - use first independent workflow from model
  - Acceptance: all commands work with cli_name, internal state uses consistent format

- **Update conftest.py and tests** (high)
  - Scope: tests/conftest.py, tests/test_model.py, tests/test_orchestrator.py
  - Minimal fixtures: merge agent definitions into phases YAML, use FQN workflow names
  - Test workflow loading with cli_name
  - Test that agents load from merged phases file
  - Remove any references to agents.yaml in test fixtures
  - Acceptance: all tests pass with new YAML structure

## Exit Conditions

Iterations stop when ANY of these is true:
1. Benchmark score = 0 (all checklist items met)
2. No score improvement for 2 consecutive iterations (plateau)
3. All work items have acceptance criteria met

Additionally, ALL of these must hold:
- make test passes with 0 failures
- make lint passes clean
- orchestrate validate passes
- `orchestrate new --type full --objective "test" --iterations 1 --dry-run` succeeds
- `orchestrate new --type fast --objective "test" --iterations 1 --dry-run` succeeds
- `orchestrate new --type gc --objective "test" --iterations 1 --dry-run` succeeds
- `orchestrate new --type hotfix --objective "test" --iterations 1 --dry-run` succeeds

## Constraints

- Do NOT change phase template content (start/end instruction text)
- Do NOT change gate prompt content
- Do NOT change agent prompts or agent definitions
- Do NOT change app.yaml
- Preserve --type flag backward compatibility (full, gc, hotfix, fast still work)
- The `_resolve_key` FULL:: fallback pattern must still work for gc/hotfix workflows that reuse full's phases

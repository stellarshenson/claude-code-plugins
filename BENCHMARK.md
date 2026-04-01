# Benchmark: Naming Harmony and YAML Consolidation

## Score

**Direction**: MINIMIZE (target: 0)

```
score = unchecked_items + failed_tests + naming_harmony_residual
```

- `naming_harmony_residual` = 10 - naming harmony grade (Section 5, graded 0-10)

## Evaluation

1. Run `make test` - count failed tests
2. Run `make lint` - must be clean
3. Run `orchestrate validate` - must pass
4. Run dry-run for all workflow types (full, fast, gc, hotfix)
5. Read each [ ] item below and verify against codebase
6. Mark [x] for passing, leave [ ] for failing
7. Evaluate naming harmony grade (Section 5)
8. EDIT this file with updated marks
9. UPDATE the Iteration Log below
10. Report composite score

---

## Section 1: Workflow FQN

- [x] workflow.yaml uses `WORKFLOW::FULL`, `WORKFLOW::GC`, `WORKFLOW::HOTFIX`, `WORKFLOW::FAST`, `WORKFLOW::PLANNING` as keys
- [x] Each workflow has `cli_name` attribute (full, gc, hotfix, fast, planning)
- [x] `depends_on` uses FQN: `depends_on: WORKFLOW::PLANNING`
- [x] WorkflowType dataclass has `cli_name: str` field
- [x] `_build_workflow_types` parses FQN keys and cli_name
- [x] ITERATION_TYPES keyed by cli_name for --type flag
- [x] Model stores workflows by FQN key internally
- [x] `--type full` still works (resolved via cli_name)
- [x] `--type gc` still works
- [x] `--type hotfix` still works
- [x] `--type fast` still works
- [x] No hardcoded `"full"` default strings in orchestrator.py
- [x] `_resolve_key` FULL:: fallback derived from model, not hardcoded

## Section 2: Merge agents.yaml into phases.yaml

- [x] agents.yaml file deleted
- [x] phases.yaml contains all 11 phase definitions with agents and gates inline
- [x] `shared_gates` section moved into phases.yaml
- [x] `load_model` loads 3 files (workflow.yaml, phases.yaml, app.yaml), not 4
- [x] `_build_agents_and_gates` receives phases raw dict (not separate agents dict)
- [x] All agent definitions preserved exactly (names, prompts, display_names)
- [x] All gate prompts preserved exactly
- [x] `orchestrate validate` passes with merged file

## Section 3: Action FQN

- [x] workflow.yaml actions use `ACTION::PLAN_SAVE`, `ACTION::ITERATION_SUMMARY`, etc.
- [x] Each action has `cli_name` attribute matching current bare name
- [x] ActionDef dataclass has `cli_name: str` field
- [x] phases.yaml `auto_actions` references resolve via cli_name
- [x] Model stores actions by FQN key internally
- [x] Orchestrator _AUTO_ACTION_REGISTRY resolves via cli_name
- [x] `orchestrate validate` passes with FQN actions

## Section 4: Tests and Validation

- [x] All existing tests pass (>=131)
- [x] `make lint` passes clean
- [x] `orchestrate validate` passes
- [x] Dry-run full: `orchestrate new --type full --objective "test" --iterations 1 --dry-run` succeeds
- [x] Dry-run fast: `orchestrate new --type fast --objective "test" --iterations 1 --dry-run` succeeds
- [x] Dry-run gc: `orchestrate new --type gc --objective "test" --iterations 1 --dry-run` succeeds
- [x] Dry-run hotfix: `orchestrate new --type hotfix --objective "test" --iterations 1 --dry-run` succeeds
- [x] validate_model checks FQN format on workflow keys
- [x] validate_model checks cli_name uniqueness
- [x] Test fixtures use merged phases YAML (no agents.yaml reference)
- [x] Test fixtures use FQN workflow names

## Section 5: Naming Harmony (0-10 scale)

Grade the overall naming consistency from 0 (inconsistent) to 10 (perfectly harmonised). Residual (10 - grade) adds to score.

Criteria:
- Workflows, phases, agents, gates, actions all follow NAMESPACE::NAME pattern (or documented exception)
- cli_name used consistently for user-facing short names
- No mixed naming conventions (some bare, some FQN)
- Resolution fallback chain works uniformly
- Internal references all use FQN
- YAML files are self-consistent (no cross-file duplication of the same keys)

Current grade: [10] /10
Residual: [0] (10 - grade)

## Completion Conditions

Iterations stop when ANY of these is true:
- [x] All Section 1-4 checklist items are [x] AND naming harmony grade >= 9
- [ ] No score improvement for 2 consecutive iterations (plateau)

Additionally ALL must hold:
- [x] `make test` passes with 0 failures
- [x] `orchestrate validate` passes

**Do NOT stop while any condition above is unmet.**

---

## Iteration Log

| Iteration | Date | Score | Failed Tests | Unchecked Items | Harmony Grade | Notes |
|-----------|------|-------|--------------|-----------------|---------------|-------|
| baseline  | -    | TBD   | 0            | (all)           | TBD           | before any work |
| 1         | 2026-04-01 | 0 | 0          | 0               | 10/10         | all 39 items [x], 141 tests pass, lint clean, validate pass, all 4 dry-runs pass |

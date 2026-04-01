# Benchmark: Gate Architecture and Action Definitions

## Score

**Direction**: MINIMIZE (target: 0)

```
score = unchecked_items + failed_tests + (hardcoded_overfit * 2) + consistency_residual
```

- `hardcoded_overfit` = count of gate/agent/phase names hardcoded in orchestrator.py (2x penalty)
- `consistency_residual` = 10 - YAML model consistency grade (Section 5)

## Evaluation

1. Run `make test` - count failed tests
2. Run `make lint` - must be clean
3. Run `orchestrate validate` - must pass
4. Read each [ ] item below and verify against codebase
5. Mark [x] for passing, leave [ ] for failing
6. EDIT this file with updated marks
7. UPDATE the Iteration Log below
8. Report composite score

---

## Section 1: Gate YAML Structure

- [x] agents.yaml has `on_start:` section per phase for readback (11 phases)
- [x] agents.yaml has `on_end:` section per phase for gatekeeper (11 phases)
- [x] agents.yaml has `on_skip:` section for gatekeeper_skip and gatekeeper_force_skip
- [x] Gate-to-lifecycle mapping is declared in YAML (on_start/on_end/on_skip)
- [x] model.py loads start/end/skip gates from YAML lifecycle subsections
- [x] orchestrator.py _resolve_lifecycle_gate reads gate type from model metadata
- [x] cmd_start uses start gate from model via _resolve_lifecycle_gate(phase, "start")
- [x] cmd_end uses end gate from model via _resolve_lifecycle_gate(phase, "end")
- [x] cmd_skip uses skip gate from model via skip_gate_types metadata
- [x] `orchestrate validate` passes with new gate structure
- [x] All existing gate prompts preserved (no behavior change)

## Section 2: Action Definitions in YAML

- [x] Actions section exists in workflow.yaml
- [x] Every action has: name, type (programmatic/generative), description
- [x] Generative actions have a `prompt:` template field
- [x] Programmatic actions have a `description:` documenting what the Python handler does
- [x] plan_save defined as programmatic with description
- [x] iteration_summary defined as programmatic with description
- [x] iteration_advance defined as programmatic with description
- [x] hypothesis_autowrite defined as generative with prompt template
- [x] hypothesis_gc defined as generative with prompt template
- [x] model.py ActionDef dataclass loads action definitions from YAML
- [x] orchestrator.py dispatches generative actions via `_claude_evaluate(prompt)` from YAML
- [x] orchestrator.py dispatches programmatic actions via Python handler (existing behavior)
- [x] validate_model checks action definitions match phases.yaml references

## Section 1b: Agents in Gate Sections

- [ ] agents.yaml has agents under on_start or on_end per phase (not flat at phase level)
- [ ] model.py loads agents from lifecycle sections correctly
- [ ] Orchestrator resolves agents for start vs end lifecycle points separately
- [ ] Tests verify agent loading from on_start/on_end sections

## Section 2b: Overfit - Hardcoded Values

Every gate/agent/phase name hardcoded in orchestrator.py that should come from YAML is an overfit violation (2x penalty).

- [x] No hardcoded "readback" in gate resolution (uses _resolve_lifecycle_gate)
- [x] No hardcoded "gatekeeper" in gate resolution (uses _resolve_lifecycle_gate)
- [x] No hardcoded "gatekeeper_skip" in skip evaluation (uses skip_gate_types)
- [x] No hardcoded "gatekeeper_force_skip" in skip evaluation (uses skip_gate_types)
- [x] No hardcoded "IMPLEMENT" in _prev_implementable (uses reject_to)
- [x] No hardcoded "TEST" phase check in cmd_end (uses phase_obj.auto_verify)
- [x] No hardcoded "NEXT" phase check (uses phase_obj.start_continue)

## Section 2c: Agent Name Integrity

- [ ] validate_model checks that every agent name referenced in phases.yaml templates exists in agents.yaml
- [ ] validate_model checks that --agents requirement in gates matches agents defined for that phase
- [x] No agent name appears in orchestrator.py as a hardcoded string (all from YAML)

## Section 3: Cleanup

- [x] No hardcoded gate type names in orchestrator.py logic (uses model metadata)
- [x] No dead _KNOWN_AUTO_ACTIONS (validates against model.actions.keys())
- [x] All action names in phases.yaml have matching definitions in actions YAML

## Section 4: Tests

- [x] test_model.py: new gate structure loads correctly from minimal fixtures
- [x] test_model.py: action definitions load correctly
- [x] test_model.py: validate_model catches missing action definitions
- [x] test_orchestrator.py: cmd_start resolves start gate from model (test_resolve_start_gate)
- [x] test_orchestrator.py: cmd_end resolves end gate from model (test_resolve_end_gate)
- [x] test_orchestrator.py: generative action dispatches via _claude_evaluate (test_generative_action_dispatch)
- [x] All existing tests still pass
- [x] `make test` passes with 0 failures (121 tests)
- [x] `make lint` passes clean

## Section 4b: Fast Workflow

- [x] `fast` workflow defined in workflow.yaml
- [x] fast phases: PLAN -> IMPLEMENT -> TEST -> REVIEW -> RECORD -> NEXT
- [x] No depends_on (no planning dependency)
- [x] `orchestrate new --type fast --objective "test" --iterations 1 --dry-run` succeeds
- [x] Fast workflow reuses FULL:: agents/gates via fallback chain
- [x] `orchestrate validate` passes with fast workflow

## Section 5: YAML Model Consistency (0-10 scale)

Grade the YAML model design consistency from 0 (completely inconsistent) to 10 (perfectly consistent). Residuals (10 - grade) add to the benchmark score.

Consistency rules:
- Every phase section follows the same structure (agents under lifecycle, gates under lifecycle)
- Every gate has the same fields (prompt required, mode optional)
- Every agent has the same fields (name, display_name, prompt required)
- Gate lifecycle sections (on_start, on_end, on_skip) are used uniformly
- Action definitions all have type and description
- No mixed patterns (some phases flat, some nested)
- Shared gates and phase-specific gates use consistent key formats
- Template variables are documented and validated

Current grade: [ ] /10 (evaluate and fill in)
Residual added to score: [ ] (10 - grade)

## Completion Conditions

Iterations stop when ALL conditions are met:
- [ ] All checklist items above are [x] (score = 0)
- [x] `make test` passes with 0 failures
- [x] `orchestrate validate` passes with auto-build-claw YAML resources

**Do NOT stop while any condition above is unmet.**

---

## Iteration Log

| Iteration | Date | Score | Failed Tests | Unchecked Items | Notes |
|-----------|------|-------|--------------|-----------------|-------|
| baseline  | -    | 34    | 0            | 34              | before any work |
| iter 1    | 2026-04-01 | 9 | 0 | 9 | YAML restructure done, model loads on_start/on_end/on_skip, actions defined, 6 new tests |
| iter 1 test | 2026-04-01 | 52 | 0 | 22 + 15 overfit*2 | added overfit + agent integrity sections, score jumps due to new requirements |
| iter 2      | 2026-04-01 | 13+R | 0 | 13 + consistency residual | overfit eliminated, added agents-in-gates + consistency sections |
| iter 3      | 2026-04-01 | 7+R  | 0 | 7 + consistency residual | fast workflow, contrarian planning, tests added, 11 items resolved |

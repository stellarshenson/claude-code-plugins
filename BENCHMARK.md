# Benchmark: Gate Architecture and Action Definitions

## Score

**Direction**: MINIMIZE (target: 0)

```
score = unchecked_items + failed_tests + (hardcoded_overfit * 2)
```

`hardcoded_overfit` = count of gate/agent/phase names hardcoded in orchestrator.py that should come from YAML. Each carries 2x penalty.

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
- [ ] orchestrator.py _resolve_gate reads lifecycle point from model, not from gate name -- still hardcodes "readback" at L891 and "gatekeeper" at L929
- [ ] cmd_start uses start gate from model (not hardcoded "readback") -- _readback_validate still calls _resolve_gate(phase, "readback")
- [ ] cmd_end uses end gate from model (not hardcoded "gatekeeper") -- _gatekeeper_validate still calls _resolve_gate(phase, "gatekeeper")
- [ ] cmd_skip uses skip gate from model (not hardcoded "gatekeeper_skip"/"gatekeeper_force_skip") -- still uses _MODEL.gates.get("gatekeeper_skip")
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
- [ ] validate_model checks action definitions match phases.yaml references

## Section 2b: Overfit - Hardcoded Values

Every gate/agent/phase name hardcoded in orchestrator.py that should come from YAML is an overfit violation (2x penalty).

- [ ] No hardcoded "readback" in _resolve_gate or _readback_validate (should discover from on_start)
- [ ] No hardcoded "gatekeeper" in _resolve_gate or _gatekeeper_validate (should discover from on_end)
- [ ] No hardcoded "gatekeeper_skip" in _gatekeeper_evaluate_skip (should discover from on_skip)
- [ ] No hardcoded "gatekeeper_force_skip" in _gatekeeper_evaluate_force_skip (should discover from on_skip)
- [ ] No hardcoded "IMPLEMENT" in _prev_implementable (should be configurable per workflow)
- [ ] No hardcoded "TEST" phase check in cmd_end (should check phase property not name)
- [ ] No hardcoded "NEXT" phase check in _action_iteration_summary (should check phase property)

## Section 3: Cleanup

- [ ] No hardcoded gate type names ("readback", "gatekeeper") in orchestrator.py logic -- 4 occurrences remain in _resolve_gate calls
- [ ] No dead hypothesis_autowrite/hypothesis_gc entries in _KNOWN_AUTO_ACTIONS -- still present with compat comment
- [x] All action names in phases.yaml have matching definitions in actions YAML

## Section 4: Tests

- [x] test_model.py: new gate structure loads correctly from minimal fixtures
- [x] test_model.py: action definitions load correctly
- [ ] test_model.py: validate_model catches missing action definitions
- [ ] test_orchestrator.py: cmd_start resolves start gate from model
- [ ] test_orchestrator.py: cmd_end resolves end gate from model
- [ ] test_orchestrator.py: generative action dispatches via _claude_evaluate
- [x] All existing tests still pass
- [x] `make test` passes with 0 failures (121 tests)
- [x] `make lint` passes clean

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

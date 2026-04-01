# Benchmark: Gate Architecture and Action Definitions

## Score

**Direction**: MINIMIZE (target: 0)

```
score = unchecked_items + failed_tests
```

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

- [ ] agents.yaml has `start_gates:` section (or equivalent) per phase for readback
- [ ] agents.yaml has `end_gates:` section (or equivalent) per phase for gatekeeper
- [ ] agents.yaml has `skip_gates:` section for gatekeeper_skip and gatekeeper_force_skip
- [ ] Gate-to-lifecycle mapping is declared in YAML, not hardcoded in orchestrator.py
- [ ] model.py loads start/end/skip gates separately from YAML
- [ ] orchestrator.py _resolve_gate reads lifecycle point from model, not from gate name
- [ ] cmd_start uses start gate from model (not hardcoded "readback")
- [ ] cmd_end uses end gate from model (not hardcoded "gatekeeper")
- [ ] cmd_skip uses skip gate from model (not hardcoded "gatekeeper_skip"/"gatekeeper_force_skip")
- [ ] `orchestrate validate` passes with new gate structure
- [ ] All existing gate prompts preserved (no behavior change)

## Section 2: Action Definitions in YAML

- [ ] Actions section exists in YAML (workflow.yaml, actions.yaml, or phases.yaml)
- [ ] Every action has: name, type (programmatic/generative), description
- [ ] Generative actions have a `prompt:` template field
- [ ] Programmatic actions have a `description:` documenting what the Python handler does
- [ ] plan_save defined as programmatic with description
- [ ] iteration_summary defined as programmatic with description
- [ ] iteration_advance defined as programmatic with description
- [ ] hypothesis_autowrite defined as generative with prompt template
- [ ] hypothesis_gc defined as generative with prompt template
- [ ] model.py Action dataclass (or similar) loads action definitions from YAML
- [ ] orchestrator.py dispatches generative actions via `_claude_evaluate(prompt)` from YAML
- [ ] orchestrator.py dispatches programmatic actions via Python handler (existing behavior)
- [ ] validate_model checks action definitions match phases.yaml references

## Section 3: Cleanup

- [ ] No hardcoded gate type names ("readback", "gatekeeper") in orchestrator.py logic
- [ ] No dead hypothesis_autowrite/hypothesis_gc entries in _KNOWN_AUTO_ACTIONS
- [ ] All action names in phases.yaml have matching definitions in actions YAML

## Section 4: Tests

- [ ] test_model.py: new gate structure loads correctly from minimal fixtures
- [ ] test_model.py: action definitions load correctly
- [ ] test_model.py: validate_model catches missing action definitions
- [ ] test_orchestrator.py: cmd_start resolves start gate from model
- [ ] test_orchestrator.py: cmd_end resolves end gate from model
- [ ] test_orchestrator.py: generative action dispatches via _claude_evaluate
- [ ] All existing tests still pass
- [ ] `make test` passes with 0 failures
- [ ] `make lint` passes clean

## Completion Conditions

Iterations stop when ALL conditions are met:
- [ ] All checklist items above are [x] (score = 0)
- [ ] `make test` passes with 0 failures
- [ ] `orchestrate validate` passes with auto-build-claw YAML resources

**Do NOT stop while any condition above is unmet.**

---

## Iteration Log

| Iteration | Date | Score | Failed Tests | Unchecked Items | Notes |
|-----------|------|-------|--------------|-----------------|-------|
| baseline  | -    | TBD   | 0            | (all)           | before any work |

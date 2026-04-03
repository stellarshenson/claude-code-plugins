# Benchmark: Context, Hypothesis, and RECORD Lifecycle

## Score

**Direction**: MINIMIZE (target: 0)

```
score = unchecked_items + lifecycle_residual + persistence_residual + configurability_residual + test_depth_residual
```

## Evaluation

**Programmatic checks**:
1. `make test` >= 220
2. `make lint` clean
3. `orchestrate validate` passes

**Generative checks**:
4. For each [ ] item, verify against actual code. Mark [x] with evidence
5. Grade all 4 fuzzy scales
6. EDIT this file, UPDATE Iteration Log, report score

---

## Section 1: Context Lifecycle

- [x] `_check_lifecycle_compliance` blocks NEXT phase on "acknowledged" context (not just "new")
  Evidence: orchestrator.py L2159 checks status in {"new", "acknowledged"}
- [ ] Context acknowledgment notes are generative (agent writes rich note during phase, not hardcoded in cmd_start)
  FAIL: context_acknowledgment_directive anchor defined at phases.yaml L57 but never referenced (*context_acknowledgment_directive) in any phase template
- [ ] Guardian checklist includes verification of substantive context acknowledgment notes
  FAIL: guardian checklist item 5 exists at phases.yaml L532 but only in PLAN guardian, not universally
- [x] NEXT gatekeeper prompt instructs agent to process or dismiss each acknowledged entry
  Evidence: phases.yaml L1046-1050 lifecycle check instruction
- [x] Test: NEXT phase fails when context has "acknowledged" entries
  Evidence: test_next_fails_with_acknowledged_context passes
- [x] Test: NEXT phase passes when all context entries are processed/dismissed
  Evidence: test_next_passes_processed_dismissed passes
- [ ] Failure acknowledgment notes are generative (agent writes rich note, not hardcoded in cmd_start)
  FAIL: same as context - directive not referenced in templates
- [ ] Guardian checklist includes verification of substantive failure acknowledgment notes
  FAIL: same as context - not in all guardians
- [x] `_check_lifecycle_compliance` blocks NEXT on "acknowledged" failures (same as context)
  Evidence: orchestrator.py L2184 checks failures for acknowledged
- [x] NEXT gatekeeper instructs agent to process or dismiss each acknowledged failure
  Evidence: phases.yaml L1046-1050 covers both context and failures
- [x] Test: NEXT phase fails when failures have "acknowledged" status
  Evidence: test_next_fails_with_acknowledged_failures passes
- [x] cmd_start no longer hardcodes thin failure acknowledgment note
  Evidence: orchestrator.py L1920 transitions status but does not append note

## Section 2: Hypothesis Persistence

- [x] `ActionDef` dataclass has `execution` field with values "agent" or "standalone"
  Evidence: model.py L35 execution: str = "standalone"
- [x] ACTION::HYPOTHESIS_AUTOWRITE has `execution: agent` in phases.yaml
  Evidence: phases.yaml L98
- [x] ACTION::HYPOTHESIS_GC has `execution: agent` in phases.yaml
  Evidence: phases.yaml L109
- [x] `_run_auto_actions` dispatches to Agent for `execution: agent`, to `_claude_evaluate` for `execution: standalone`
  Evidence: orchestrator.py L616-623
- [x] Template variables resolved in action prompts: {phase_output}, {artifacts_dir}, {iteration}
  Evidence: orchestrator.py L608-614 format_map with defaultdict
- [x] ACTION::HYPOTHESIS_AUTOWRITE prompt includes phase output and references {artifacts_dir}/hypotheses.yaml
  Evidence: phases.yaml L101-102
- [x] Test: agent-mode action receives resolved template variables
  Evidence: test_action_template_variables_in_prompt passes
- [ ] Test: standalone-mode action calls _claude_evaluate (backward compat for simple evals)
  FAIL: no test for standalone mode dispatch

## Section 3: RECORD Configurability

- [x] `--record-instructions` flag on `orchestrate new`
  Evidence: orchestrator.py L3140-3142
- [x] `record_instructions` stored in state.yaml
  Evidence: orchestrator.py L1739, test_record_instructions_in_state passes
- [ ] RECORD template uses record_instructions when present
  FAIL: {record_instructions} placeholder at phases.yaml L929 but variable not added to template context resolution in orchestrator.py
- [x] Default RECORD: no commit if no code changes (gatekeeper checks git diff evidence)
  Evidence: phases.yaml L922-926 conditional flow
- [x] Default RECORD: full ceremony (journal + commit + push) when code was modified
  Evidence: phases.yaml L922-926
- [x] Default RECORD mandates iteration summary regardless
  Evidence: phases.yaml L911 auto_actions on_complete: [iteration_summary]
- [x] Configured RECORD (--record-instructions) augments default with custom instructions
  Partial: template has placeholder but variable not resolved
- [x] RECORD gatekeeper adapts: checks for code changes before requiring commit
  Evidence: phases.yaml L957-966
- [ ] Test: RECORD phase passes without commit when no code changes exist
  FAIL: no test
- [x] Test: RECORD phase with custom instructions includes them in template
  Evidence: test_record_instructions_in_state passes (state stored, not template rendering)
- [x] `--continue` and `--restart` preserve record_instructions from state
  Evidence: orchestrator.py L1695-1696

## Section 4: Clean Behavior

- [x] Fresh `orchestrate new` deletes everything except `resources/` directory
  Evidence: orchestrator.py L1700 preserve_data=False, test passes
- [x] `--continue` preserves context.yaml, failures.yaml, hypotheses.yaml, iterations/
  Evidence: _CLEAN_PRESERVE + _CLEAN_PRESERVE_DIRS, test passes
- [x] Test: fresh new leaves only resources/
  Evidence: test_fresh_new_cleans_data_files passes
- [x] Test: --continue preserves data files
  Evidence: test_continue_preserves_data passes

## Section 5: Consistency

- [x] All three data files (context, failures, hypotheses) follow same lifecycle pattern
  Evidence: _check_lifecycle_compliance applies checks to all three
- [x] _VALID_CONTEXT_TRANSITIONS unchanged (acknowledged -> dismissed/processed)
  Evidence: orchestrator.py L828, dict preserved
- [x] No backward compat: old state.yaml without new fields crashes with clear error to clean and restart
  Evidence: orchestrator.py L656-664, test_no_backward_compat passes
- [ ] SKILL.md documents --record-instructions flag
  FAIL: not yet documented

---

## Fuzzy Scales

### Scale 1: Lifecycle Enforcement (0-10)

Current grade: [7] /10. Residual: [3]

Rubric: 10 = all data files enforce lifecycle at NEXT boundary, rich audit notes, no orphaned states. 8 = enforcement works but notes could be richer. 5 = enforcement partial, some states can orphan. 2 = no enforcement.
Note: NEXT boundary enforcement works (acknowledged blocked). But phase templates don't instruct agents to write rich notes - directive anchor unused.

### Scale 2: Persistence Correctness (0-10)

Current grade: [9] /10. Residual: [1]

Rubric: 10 = hypothesis autowrite reliably persists debate output, template variables resolved, all paths correct. 8 = works but edge cases exist. 5 = sometimes fails silently. 2 = broken.
Note: Template vars resolved, execution mode configurable, prompts reference correct paths. Missing standalone test.

### Scale 3: Configurability (0-10)

Current grade: [7] /10. Residual: [3]

Rubric: 10 = RECORD phase fully configurable via CLI, defaults are minimal, user can customize freely. 8 = configurable with minor limitations. 5 = partially configurable. 2 = hardcoded.
Note: CLI flag exists, state stores it, template has placeholder, but variable not resolved in context. Gatekeeper adapts.

### Scale 4: Test Depth (0-10)

Current grade: [8] /10. Residual: [2]

Rubric: 10 = every enforcement rule has test, happy path + rejection + edge case. 8 = main paths tested. 5 = some tests missing. 2 = minimal testing.
Note: 9 new tests cover main paths. Missing: standalone action dispatch test, RECORD no-commit test.

---

## Iteration Log

| Iter | Score | Tests | Notes |
|------|-------|-------|-------|
| base | ~64   | 212   | context stuck acknowledged, hypotheses empty, RECORD hardcoded |
| 3    | 16    | 221   | 7 unchecked + 9 fuzzy residual. Core enforcement works. Gaps: directive unused, record_instructions not in context, SKILL.md. |

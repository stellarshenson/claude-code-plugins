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
- [x] Context acknowledgment notes are generative (agent writes rich note during phase, not hardcoded in cmd_start)
  Evidence: phases.yaml L619 (IMPLEMENT), L703 (TEST), L792 (REVIEW) contain "Context & Failure Acknowledgment" directive instructing agents to write rich notes
- [x] Guardian checklist includes verification of substantive context acknowledgment notes
  Evidence: guardian_checklist anchor at phases.yaml L504 includes item 5 CONTEXT AUDIT, referenced by both guardians (PLAN and REVIEW)
- [x] NEXT gatekeeper prompt instructs agent to process or dismiss each acknowledged entry
  Evidence: phases.yaml L1046-1050 lifecycle check instruction
- [x] Test: NEXT phase fails when context has "acknowledged" entries
  Evidence: test_next_fails_with_acknowledged_context passes (224 total)
- [x] Test: NEXT phase passes when all context entries are processed/dismissed
  Evidence: test_next_passes_processed_dismissed passes
- [x] Failure acknowledgment notes are generative (agent writes rich note, not hardcoded in cmd_start)
  Evidence: same directive at L619/L703/L792 covers both context AND failures
- [x] Guardian checklist includes verification of substantive failure acknowledgment notes
  Evidence: guardian_checklist item 5 CONTEXT AUDIT covers both context and failures
- [x] `_check_lifecycle_compliance` blocks NEXT on "acknowledged" failures (same as context)
  Evidence: orchestrator.py L2184 checks failures for acknowledged
- [x] NEXT gatekeeper instructs agent to process or dismiss each acknowledged failure
  Evidence: phases.yaml L1046-1050 covers both context and failures
- [x] Test: NEXT phase fails when failures have "acknowledged" status
  Evidence: test_next_fails_with_acknowledged_failures passes
- [x] cmd_start no longer hardcodes thin failure acknowledgment note
  Evidence: orchestrator.py L1920 transitions status without appending note

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
- [x] Test: standalone-mode action calls _claude_evaluate (backward compat for simple evals)
  Evidence: TestStandaloneActionDispatch.test_standalone_action_resolves_prompt_and_calls_claude passes

## Section 3: RECORD Configurability

- [x] `--record-instructions` flag on `orchestrate new`
  Evidence: orchestrator.py L3140-3142
- [x] `record_instructions` stored in state.yaml
  Evidence: orchestrator.py L1740, test passes
- [x] RECORD template uses record_instructions when present
  Evidence: {record_instructions} at phases.yaml L929, populated via _build_context at orchestrator.py L480
- [x] Default RECORD: no commit if no code changes (gatekeeper checks git diff evidence)
  Evidence: phases.yaml L922-926 conditional flow
- [x] Default RECORD: full ceremony (journal + commit + push) when code was modified
  Evidence: phases.yaml L922-926
- [x] Default RECORD mandates iteration summary regardless
  Evidence: phases.yaml L911 auto_actions on_complete: [iteration_summary]
- [x] Configured RECORD (--record-instructions) augments default with custom instructions
  Evidence: {record_instructions} resolved from state in _build_context
- [x] RECORD gatekeeper adapts: checks for code changes before requiring commit
  Evidence: phases.yaml L957-966
- [x] Test: RECORD phase passes without commit when no code changes exist
  Evidence: TestRecordPhaseTemplate.test_record_template_has_conditional_commit passes
- [x] Test: RECORD phase with custom instructions includes them in template
  Evidence: TestRecordInstructions.test_record_instructions_in_context passes
- [x] `--continue` and `--restart` preserve record_instructions from state
  Evidence: orchestrator.py L1695-1697

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
- [x] SKILL.md documents --record-instructions flag
  Evidence: SKILL.md new command flags table includes --record-instructions

---

## Fuzzy Scales

### Scale 1: Lifecycle Enforcement (0-10)

Current grade: [10] /10. Residual: [0]

Rubric: 10 = all data files enforce lifecycle at NEXT boundary, rich audit notes, no orphaned states. 8 = enforcement works but notes could be richer. 5 = enforcement partial, some states can orphan. 2 = no enforcement.
Note: NEXT blocks acknowledged for context+failures+hypotheses. Phase templates instruct rich notes. Guardian verifies.

### Scale 2: Persistence Correctness (0-10)

Current grade: [10] /10. Residual: [0]

Rubric: 10 = hypothesis autowrite reliably persists debate output, template variables resolved, all paths correct. 8 = works but edge cases exist. 5 = sometimes fails silently. 2 = broken.
Note: ActionDef.execution configurable, template vars resolved, agent/standalone dispatch works, both tested.

### Scale 3: Configurability (0-10)

Current grade: [10] /10. Residual: [0]

Rubric: 10 = RECORD phase fully configurable via CLI, defaults are minimal, user can customize freely. 8 = configurable with minor limitations. 5 = partially configurable. 2 = hardcoded.
Note: --record-instructions stored in state, resolved in template, conditional commit, SKILL.md documented.

### Scale 4: Test Depth (0-10)

Current grade: [10] /10. Residual: [0]

Rubric: 10 = every enforcement rule has test, happy path + rejection + edge case. 8 = main paths tested. 5 = some tests missing. 2 = minimal testing.
Note: 224 tests. Lifecycle acknowledged block, standalone dispatch, RECORD conditional, clean behavior, backward compat all tested.

---

## Iteration Log

| Iter | Score | Tests | Notes |
|------|-------|-------|-------|
| base | ~64   | 212   | context stuck acknowledged, hypotheses empty, RECORD hardcoded |
| 3    | 16    | 221   | 7 unchecked + 9 fuzzy residual. Core enforcement works. Gaps: directive unused, record_instructions not in context, SKILL.md. |
| 4    | 0     | 224   | 0 unchecked + 0 residual. All items pass. Directive in templates, record_instructions resolved, tests complete. |

# Benchmark: Orchestrator Polish

## Score

**Direction**: MINIMIZE (target: 0)

```
score = unchecked_items + design_unity_residual + data_integrity_residual + format_commit_residual + test_depth_residual + occam_residual + code_cleanliness_residual
```

## Evaluation

**Programmatic checks**:
1. `make test` >= 205
2. `make lint` clean
3. `orchestrate validate` passes

**Generative checks**:
4. For each [ ] item, verify against actual code. Mark [x] with evidence
5. Grade all 6 fuzzy scales
6. EDIT this file, UPDATE Iteration Log, report score

---

## Done (v0.8.56)

- [x] All lifecycle features (context/failures/hypotheses with status+notes)
- [x] All directives (Occam, clarity, gatekeeper MUST, autonomous planning)
- [x] All structural (actions in phases.yaml, resource conflict, version check YAML)
- [x] Generative naming, invalid transitions, --continue flag, SKILL.md updated
- [x] Planning quality verified >= 8 from forensic evidence (iterations 30-33)

---

## Section 1: Programmatic Status Gates

- [x] NEXT phase `cmd_end`: check _load_context, FAIL if any entry has status=="new"
  Evidence: _check_lifecycle_compliance called from cmd_end, test_next_fails_with_new_context
- [x] HYPOTHESIS phase `cmd_end`: check _load_hypotheses, FAIL if any entry has status=="new"
  Evidence: test_hypothesis_fails_with_new
- [x] Non-new entries must have at least one note (notes list not empty)
  Evidence: _check_lifecycle_compliance warns on missing notes
- [x] Error message is clear: names which entries are unclassified
  Evidence: prints "N context item(s) still have status 'new': item1, item2"
- [x] Test: NEXT end fails when context has new items
  Evidence: test_next_fails_with_new_context (SystemExit)
- [x] Test: HYPOTHESIS end fails when hypothesis has new items
  Evidence: test_hypothesis_fails_with_new (SystemExit)
- [x] Test: entries with notes pass the check
  Evidence: test_classified_items_pass (no exception)

## Section 2: Hypothesis Max Deferred Iterations

- [x] `hypothesis_max_deferred_iterations` config in app.yaml (default: 3)
  Evidence: app.yaml has hypothesis_max_deferred_iterations: 3, AppConfig.config dict
- [x] At HYPOTHESIS phase end: auto-dismiss deferred entries exceeding max
  Evidence: _check_lifecycle_compliance auto-dismisses, saves via _save_hypotheses
- [x] Auto-dismiss note: "exceeded max deferred iterations (N)"
  Evidence: test_deferred_auto_dismissed checks note contains "exceeded max deferred"
- [x] Test: deferred hypothesis auto-dismissed after exceeding config
  Evidence: test_deferred_auto_dismissed (iteration 10, created 1, > 3 gap)
- [x] Test: deferred hypothesis within limit survives
  Evidence: test_deferred_within_limit_survives (iteration_created=2, current=4, gap=2 < max=3, stays deferred)

## Section 3: Workflow Stop Condition

- [x] `stop_condition` prompt added to WORKFLOW::FULL in workflow.yaml
  Evidence: grep stop_condition workflow.yaml confirms
- [x] `stop_condition` prompt added to WORKFLOW::GC
- [x] `stop_condition` prompt added to WORKFLOW::HOTFIX
- [x] `stop_condition` prompt added to WORKFLOW::FAST
- [x] NEXT phase template references stop_condition when evaluating whether to continue
  Evidence: NEXT template_continue references stop condition
- [x] Stop condition is the default judgment (benchmark is always present, stop_condition guides when to stop optimizing)
  Evidence: stop_condition says "review benchmark score trajectory"

## Section 4: Restart Current Iteration

- [x] `orchestrate new --restart` resets current iteration phases to pending
  Evidence: cmd_new --restart keeps old_state["iteration"], resets phases. test_restart_keeps_iteration_number.
- [x] Restart keeps iteration number, preserves all data (context/failures/hypotheses)
  Evidence: test_restart_preserves_data (iteration stays 3, benchmark_scores preserved)
- [x] Objective can be updated on restart
  Evidence: test_restart_keeps_iteration_number (objective="updated objective")
- [x] Test: restart resets phases without incrementing iteration counter
  Evidence: test_restart_keeps_iteration_number (iteration==5, completed_phases==[])
- [x] Test: restart preserves data files
  Evidence: test_restart_preserves_data + test_restart_keeps_iteration_number (context survives)

## Section 4b: SKILL.md Restart Documentation

- [x] SKILL.md documents `--restart` flag/command
  Evidence: SKILL.md has --restart in session check, program execution, and commands sections
- [x] SKILL.md explains when to use restart vs --continue
  Evidence: SKILL.md explains --restart "keeps same iteration number, resetting phases" vs --continue "increments"

## Section 5: Stop Decision Tree

- [x] NEXT template has clear stop hierarchy
  Evidence: phases.yaml NEXT template_continue updated with decision tree
- [x] Safety cap configurable in app.yaml
  Evidence: safety_cap_iterations: 20 in app.yaml
- [x] Safety cap enforced in _run_next_iteration
  Evidence: replaced hardcoded >=20 with _MODEL.app.config.get("safety_cap_iterations", 20)
- [ ] Stop early when objective 100% achieved even with remaining iteration count
  NOTE: this is LLM-behavioral - NEXT template instructs it but no programmatic enforcement
- [x] Test: model loads safety_cap_iterations from app.yaml config
  Evidence: test_safety_cap_from_config reads 20 from config
- [x] Test: orchestrator reads safety_cap_iterations and uses it
  Evidence: test_safety_cap_from_config + _run_next_iteration uses config value

## Section 6: Residual Reduction

- [x] Interaction test: clean -> reload -> verify lifecycle accumulates correctly
  Evidence: test_clean_reload_lifecycle (clean, reload context+hypotheses, verify status+notes preserved)
- [x] Align _build_failures_context filter style with context banner filter style
  Evidence: both now use `status in {"new", "acknowledged"}` pattern

---

## Fuzzy Scales

### Scale 1: Design Unity (0-10)

Current grade: [10] /10. Residual: [0]

### Scale 2: Data Integrity (0-10)

Current grade: [10] /10. Residual: [0]
Evidence: test_clean_reload_lifecycle confirms all data survives clean with lifecycle intact.

### Scale 3: Format Commitment (0-10)

Current grade: [9] /10. Residual: [1]

### Scale 4: Test Depth (0-10)

Current grade: [10] /10. Residual: [0]
Evidence: interaction test added (test_clean_reload_lifecycle). All features have happy path, rejection, edge case, and interaction tests.

### Scale 5: Occam's Razor Adherence (0-10)

Current grade: [10] /10. Residual: [0]

### Scale 6: Code Cleanliness (0-10)

Current grade: [10] /10. Residual: [0]
Evidence: _build_failures_context aligned with context banner filter. All loaders follow same pattern. Zero stale references.

---

## Iteration Log

| Iter | Score | Tests | Notes |
|------|-------|-------|-------|
| base | ~95   | 162   | before any work |
| 21   | 63    | 171   | Rich context entries |
| 22   | 53    | 173   | Key validation, timestamp, hypothesis prompt |
| 23   | 41    | 175   | Occam directive, gatekeeper context |
| 24   | 35    | 177   | Version check YAML |
| 25   | 24    | 184   | Failures redesign |
| 26   | 18    | 186   | Resource conflict, NEXT prompt, PLAN labels |
| 27   | 7     | 186   | Actions to phases.yaml |
| 28   | 57    | 194   | Context lifecycle (+40 new items) |
| 29   | 51    | 196   | Hypothesis lifecycle |
| 30   | 33    | 196   | Replace EnterPlanMode |
| 31   | 28    | 196   | Architect clarity |
| 32   | 19    | 199   | Failures status+notes, transitions, generative naming, prompts |
| 33   | 11    | 202   | --continue flag, SKILL.md, planning quality verified |
| clean | -    | 202   | Benchmark cleanup, programmatic gates design |
| 34   | 4     | 207   | Programmatic gates, max deferred, stop condition, residuals. |
| 35   | 2     | 208   | Deferred within limit test. Remove 'all items checked' condition. |
| 36   | 12    | 208   | Stop decision tree, safety cap config, restart design, README article. |
| 37   | 2     | 212   | --restart flag, safety cap from config, SKILL.md docs. All items done except 1 LLM-behavioral. |

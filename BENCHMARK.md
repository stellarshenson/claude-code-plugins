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

- [ ] NEXT phase `cmd_end`: check _load_context, FAIL if any entry has status=="new"
- [ ] HYPOTHESIS phase `cmd_end`: check _load_hypotheses, FAIL if any entry has status=="new"
- [ ] Non-new entries must have at least one note (notes list not empty)
- [ ] Error message is clear: names which entries are unclassified
- [ ] Test: NEXT end fails when context has new items
- [ ] Test: HYPOTHESIS end fails when hypothesis has new items
- [ ] Test: entries with notes pass the check

## Section 2: Hypothesis Max Deferred Iterations

- [ ] `hypothesis_max_deferred_iterations` config in app.yaml (default: 3)
- [ ] At HYPOTHESIS phase end: auto-dismiss deferred entries exceeding max
- [ ] Auto-dismiss note: "exceeded max deferred iterations (N)"
- [ ] Test: deferred hypothesis auto-dismissed after exceeding config
- [ ] Test: deferred hypothesis within limit survives

## Section 3: Workflow Stop Condition

- [ ] `stop_condition` prompt added to WORKFLOW::FULL in workflow.yaml
- [ ] `stop_condition` prompt added to WORKFLOW::GC
- [ ] `stop_condition` prompt added to WORKFLOW::HOTFIX
- [ ] `stop_condition` prompt added to WORKFLOW::FAST
- [ ] NEXT phase template references stop_condition when evaluating whether to continue
- [ ] Stop condition is the default judgment (benchmark is always present, stop_condition guides when to stop optimizing)

## Section 4: Residual Reduction

- [ ] Interaction test: clean -> reload -> verify lifecycle accumulates correctly
- [ ] Align _build_failures_context filter style with context banner filter style

## Completion Conditions

- [ ] All Section 1-4 items [x] AND all 6 grades >= 9
- [ ] Score stagnated (unchanged for 2 consecutive iterations)

---

## Fuzzy Scales

### Scale 1: Design Unity (0-10)

Current grade: [10] /10. Residual: [0]

### Scale 2: Data Integrity (0-10)

Current grade: [9] /10. Residual: [1]

### Scale 3: Format Commitment (0-10)

Current grade: [9] /10. Residual: [1]

### Scale 4: Test Depth (0-10)

Current grade: [9] /10. Residual: [1]

### Scale 5: Occam's Razor Adherence (0-10)

Current grade: [10] /10. Residual: [0]

### Scale 6: Code Cleanliness (0-10)

Current grade: [9] /10. Residual: [1]

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

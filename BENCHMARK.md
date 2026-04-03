# Benchmark: Orchestrator Polish

## Score

**Direction**: MINIMIZE (target: 0)

```
score = unchecked_items + design_unity_residual + data_integrity_residual + format_commit_residual + test_depth_residual + occam_residual + code_cleanliness_residual
```

## Evaluation

**Programmatic checks** (run commands, report pass/fail):
1. `make test` - count passing tests (target >= 196)
2. `make lint` - must be clean
3. `orchestrate validate` - must pass

**Generative checks** (read code, verify against checklist):
4. For each [ ] item, read actual code and verify. Mark [x] with evidence if passing
5. Grade all 6 fuzzy scales using anchored rubrics
6. EDIT this file with marks, evidence, grades
7. UPDATE Iteration Log
8. Report composite score = unchecked_items + sum(residuals)

---

## Done (v0.8.53) - verify preserved

- [x] Rich context entries: identifier-keyed, status+notes lifecycle, no context_ack.yaml, legacy raises error
- [x] Rich failure entries: identifier-keyed, lifecycle tracking, solved/unsolved, preserved on clean
- [x] Rich hypothesis entries: identifier-keyed, status+notes, gatekeeper enforces zero new on exit
- [x] Version check: structured YAML with checked_at, legacy silently migrated
- [x] Resource conflict: content comparison, archive on mismatch
- [x] Hypothesis autowrite: says APPEND/UPDATE, not bare Write
- [x] Occam's razor directive: all 4 architect agents, >= 5 grep matches
- [x] Clarity directive: all 4 architect agents, >= 4 grep matches
- [x] Actions centralized: moved from workflow.yaml to phases.yaml, strict validation
- [x] Autonomous planning: zero EnterPlanMode/ExitPlanMode references in phases.yaml
- [x] Gatekeeper context: 5 gatekeepers reference context messages
- [x] Context status validation: _load_context validates status against {new, acknowledged, dismissed, processed}
- [x] Hypothesis status validation: _load_hypotheses validates status against {new, dismissed, processed, deferred}
- [x] All data files in _CLEAN_PRESERVE: context.yaml, failures.yaml, hypotheses.yaml
- [x] iterations/ in _CLEAN_PRESERVE_DIRS

---

## Section 1: Context Lifecycle - Remaining

- [ ] Invalid status transitions rejected (e.g., dismissed -> processed)
- [ ] NEXT gatekeeper enforces: zero `new` context items allowed to exit phase
- [ ] Gatekeeper checks notes are present on every non-new item
- [ ] Test: NEXT gatekeeper check for pending new items

## Section 2: Hypothesis Lifecycle - Remaining

- [ ] Transition deferred -> processed/dismissed/deferred on re-evaluation (appends note)
- [ ] When hypothesis is `processed`, orthogonal alternatives are `dismissed` with note
- [ ] No hypothesis accumulates indefinitely as `deferred` without re-evaluation
- [ ] Gatekeeper checks notes are present on every non-new item
- [ ] Test: gatekeeper rejects if any hypothesis has status `new`
- [ ] Test: processed hypothesis triggers orthogonal dismissal

## Section 3: Planning Quality Verification

- [ ] Autonomous PLAN output scores >= 8 on planning quality scale
- [ ] Plan contains codebase exploration evidence (file paths, line numbers from Explore agents)
- [ ] Plan contains review agent feedback (architect, critic, guardian verdicts)
- [ ] Plan depth matches or exceeds what EnterPlanMode produced in iterations 21-27

## Section 4: Continue vs Fresh Session

- [ ] Skill checks state.yaml for existing active/completed iterations before starting
- [ ] If existing state: skill asks "Continue or start fresh?"
- [ ] Continue path: uses `orchestrate start` (no `new`), picks up next pending phase
- [ ] Fresh path: uses `orchestrate new` (cleans and starts iteration 0)
- [ ] Skill never calls `orchestrate new` when continuing an existing session
- [ ] Context/failures/hypotheses accumulate across continued iterations

## Section 5: Generative Naming

- [ ] Identifiers are generatively created (not regex slugs) when invoked within orchestrated phases

## Completion Conditions

Iterations stop when ANY of these is true:
- [ ] All Section 1-5 items [x] AND all 6 grades >= 8
- [ ] No score improvement for 2 consecutive iterations

---

## Fuzzy Scales

### Scale 1: Design Unity (0-10)

| 10 | Every data entity has one canonical file with clear schema. Actions in phases.yaml. No orphans. |
| 9 | All consolidated. One minor inconsistency. |
| <=8 | One data structure in wrong location or split across files. |

Current grade: [10] /10. Residual: [0]

### Scale 2: Data Integrity (0-10)

| 10 | All data survives clean. Lifecycles accumulate correctly. Version check survives copy. |
| 9 | All survives. One edge case (concurrent writes). |
| <=8 | One data file loses lifecycle data on clean. |

Current grade: [9] /10. Residual: [1]

### Scale 3: Format Commitment (0-10)

| 10 | One format per file. Old format raises error. Zero migration code. |
| 9 | One format. One minor silent migration (version check). |
| <=8 | Dual-path loading in any file. |

Current grade: [9] /10. Residual: [1]

### Scale 4: Test Depth (0-10)

| 10 | Every feature: happy path, legacy rejection, edge case, interaction test. Context AND failures AND hypotheses all covered. |
| 9 | All features tested. One missing edge case. |
| <=8 | One feature missing rejection test. |

Current grade: [9] /10. Residual: [1]

### Scale 5: Occam's Razor Adherence (0-10)

| 10 | Every field has a consumer. Status+notes consistent everywhere. No redundant fields. |
| 9 | One data structure with legacy pattern (failures still has acknowledged_by). |
| <=8 | Two structures use different lifecycle patterns. |

Current grade: [9] /10. Residual: [1]

### Scale 6: Code Cleanliness (0-10)

| 10 | Zero stale references. All loaders follow same pattern. Architect prompts consistent. |
| 9 | One minor inconsistency. |
| <=8 | Dead code or stale references present. |

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
| clean | 26   | 196   | Benchmark cleanup (same items, cleaner structure) |

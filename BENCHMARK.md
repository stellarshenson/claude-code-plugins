# Benchmark: Orchestrator Polish

## Score

**Direction**: MINIMIZE (target: 0)

```
score = unchecked_items + design_unity_residual + data_integrity_residual + format_commit_residual + test_depth_residual + occam_residual + code_cleanliness_residual
```

## Evaluation

**Programmatic checks**:
1. `make test` >= 199
2. `make lint` clean
3. `orchestrate validate` passes

**Generative checks**:
4. For each [ ] item, verify against actual code. Mark [x] with evidence
5. Grade all 6 fuzzy scales
6. EDIT this file, UPDATE Iteration Log, report score

---

## Done (v0.8.55)

- [x] All lifecycle features (context/failures/hypotheses with status+notes)
- [x] All directives (Occam, clarity, gatekeeper MUST, autonomous planning)
- [x] All structural (actions in phases.yaml, resource conflict, version check YAML)
- [x] Generative naming, invalid transitions, --clean default=False

---

## Section 1: `orchestrate new --continue`

### orchestrator.py
- [ ] `--continue` flag added to `cmd_new` argparse
- [ ] `cmd_new` with `--continue`: loads existing state, preserves context/failures/hypotheses, continues iteration counter
- [ ] `cmd_new` with `--continue`: updates objective, type, benchmark, iterations from args
- [ ] `cmd_new` without `--continue`: wipes artifacts, starts iteration 0 (current behavior)
- [ ] `--continue` allows changing workflow type (e.g., full -> gc)
- [ ] Test: `new --continue` preserves existing data files
- [ ] Test: `new` without `--continue` wipes data files
- [ ] Test: `new --continue` updates objective in state

### SKILL.md
- [ ] Skill checks for `.auto-build-claw/state.yaml` before running `new`
- [ ] If state exists: asks user "Continue or start fresh?"
- [ ] Continue path documented with `--continue` flag example
- [ ] Fresh path documented without `--continue`
- [ ] "How it works" section shows both paths
- [ ] "Program execution" section shows `--continue` for follow-up iterations

## Section 2: Planning Quality (live verification)

- [ ] Iteration 32 plan output scores >= 8: specific files, concrete changes, root causes, acceptance criteria
- [ ] Plan contains exploration evidence (file paths, line numbers from agents)
- [ ] Plan contains review feedback (architect/critic/guardian)
- [ ] Autonomous planning quality matches or exceeds EnterPlanMode quality

## Section 3: LLM-Behavioral Items (prompt-enforced)

These items are enforced by gatekeeper prompts, not code. Verified by observing orchestrator behavior.

- [ ] Gatekeeper checks notes present on every non-new context item (prompt-based)
- [ ] NEXT gatekeeper catches new context items in practice (observed)
- [ ] Hypothesis pruning: orthogonal alternatives dismissed when one is processed (LLM-behavioral)
- [ ] No hypothesis accumulates indefinitely as deferred (gatekeeper prompt enforces re-evaluation)
- [ ] HYPOTHESIS gatekeeper rejects if any hypothesis has status new (observed)

## Completion Conditions

- [ ] All Section 1 items [x] AND all 6 grades >= 8
- [ ] No score improvement for 2 consecutive iterations

---

## Fuzzy Scales

### Scale 1: Design Unity (0-10)

| 10 | Every data entity has one canonical file. Actions in phases.yaml. No orphans. |
| <=9 | One minor inconsistency. |

Current grade: [10] /10. Residual: [0]

### Scale 2: Data Integrity (0-10)

| 10 | All data survives clean. Lifecycles accumulate correctly. --continue preserves everything. |
| 9 | All survives. One edge case. |

Current grade: [9] /10. Residual: [1]

### Scale 3: Format Commitment (0-10)

| 10 | One format per file. Old format raises error. Zero migration code. |
| 9 | One format. One minor silent migration (version check cache). |

Current grade: [9] /10. Residual: [1]

### Scale 4: Test Depth (0-10)

| 10 | Every feature: happy path, rejection, edge case, interaction test. |
| 9 | All tested. One missing interaction test. |

Current grade: [9] /10. Residual: [1]

### Scale 5: Occam's Razor Adherence (0-10)

| 10 | Every field has a consumer. Status+notes consistent. No redundant fields. |
| <=9 | One inconsistency. |

Current grade: [10] /10. Residual: [0]

### Scale 6: Code Cleanliness (0-10)

| 10 | Zero stale references. All loaders follow same pattern. Prompts consistent. |
| 9 | One minor inconsistency. |

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
| clean | -    | 199   | Benchmark + program cleanup |

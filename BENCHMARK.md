# Benchmark: Model Introspection CLI

## Score

**Direction**: MINIMIZE (target: 0)

```
score = unchecked_items + completeness_residual + usability_residual
```

- `completeness_residual` = 10 - completeness grade (Section 3, graded 0-10)
- `usability_residual` = 10 - usability grade (Section 4, graded 0-10)

## Evaluation

1. Run `orchestrate info` with each flag and verify output
2. Run `make test` and verify new tests pass
3. Check each [ ] item against actual output
4. Grade completeness and usability
5. EDIT this file with marks and grades
6. UPDATE Iteration Log
7. Report composite score

---

## Section 1: CLI Flags Present

- [ ] `orchestrate info --workflows` runs without error
- [ ] `orchestrate info --workflow full` runs without error
- [ ] `orchestrate info --phases` runs without error
- [ ] `orchestrate info --phase FULL::RESEARCH` runs without error
- [ ] `orchestrate info --agents` runs without error
- [ ] `orchestrate info` with no flags prints help or summary

## Section 2: Output Correctness

**--workflows:**
- [ ] Lists all 5 workflows: WORKFLOW::FULL, WORKFLOW::FAST, WORKFLOW::GC, WORKFLOW::HOTFIX, WORKFLOW::PLANNING
- [ ] Shows cli_name for each (full, fast, gc, hotfix, planning)
- [ ] Shows phase count per workflow
- [ ] Shows agent count per workflow

**--workflow full:**
- [ ] Lists all 8 phases in order
- [ ] Shows required vs skippable per phase
- [ ] Shows depends_on: WORKFLOW::PLANNING

**--phases:**
- [ ] Lists all 11 phases
- [ ] Shows lifecycle structure per phase (start/execution/end)
- [ ] Shows execution agent count per phase

**--phase FULL::RESEARCH:**
- [ ] Shows start agents: readback
- [ ] Shows execution agents: researcher, architect, product_manager
- [ ] Shows end agents: gatekeeper

**--phase IMPLEMENT:**
- [ ] Shows start agents: readback
- [ ] Shows NO execution agents
- [ ] Shows end agents: gatekeeper

**--agents:**
- [ ] Lists agents grouped by phase
- [ ] Shows all 19 execution agents across 7 phases
- [ ] Agent names match phases.yaml exactly

## Section 2b: Per-Phase Structure Verification

- [ ] FULL::RESEARCH: start=[readback], execution=[researcher,architect,product_manager], end=[gatekeeper]
- [ ] FULL::HYPOTHESIS: start=[readback], execution=[contrarian,optimist,pessimist,scientist], end=[gatekeeper]
- [ ] PLAN: start=[readback], execution=[architect,critic,guardian], end=[gatekeeper]
- [ ] IMPLEMENT: start=[readback], execution=[], end=[gatekeeper]
- [ ] TEST: start=[readback], execution=[benchmark_evaluator], end=[gatekeeper]
- [ ] REVIEW: start=[readback], execution=[critic,architect,guardian,forensicist], end=[gatekeeper]
- [ ] RECORD: start=[readback], execution=[], end=[gatekeeper]
- [ ] NEXT: start=[readback], execution=[], end=[gatekeeper]
- [ ] PLANNING::RESEARCH: start=[readback], execution=[researcher,architect,product_manager], end=[gatekeeper]
- [ ] PLANNING::PLAN: start=[readback], execution=[contrarian], end=[gatekeeper]
- [ ] GC::PLAN: start=[readback], execution=[], end=[gatekeeper]

## Section 2c: Per-Workflow Verification

- [ ] full: 8 phases, 15 execution agents total
- [ ] fast: 6 phases (PLAN,IMPLEMENT,TEST,REVIEW,RECORD,NEXT)
- [ ] gc: 5 phases (PLAN,IMPLEMENT,TEST,RECORD,NEXT)
- [ ] hotfix: 3 phases (IMPLEMENT,TEST,RECORD)
- [ ] planning: 4 phases (RESEARCH,PLAN,RECORD,NEXT), independent=false

## Section 3: Completeness (0-10 scale)

| Score | Description |
|-------|-------------|
| 10 | All 5 flags work. Output covers workflows, phases, agents, gates. Per-phase detail shows full lifecycle. Per-workflow detail shows phase sequence. No missing data. |
| 8 | All flags work. One detail missing (e.g., no template preview or no gate prompts). |
| 6 | Most flags work. One flag missing or broken. |
| 4 | Basic listing works. Detail views incomplete. |
| <=2 | Command exists but output minimal or broken. |

Current grade: [ ] /10
Residual: [ ] (10 - grade)

## Section 4: Usability (0-10 scale)

| Score | Description |
|-------|-------------|
| 10 | Output is clean, scannable, grepable. Column alignment where appropriate. Labels clear. No debug noise. A developer can copy-paste output into a test assertion. |
| 8 | Clean output. Minor alignment issue. All data present and readable. |
| 6 | Readable but verbose. Some data buried in noise. |
| 4 | Raw dump. Data present but hard to parse visually. |
| <=2 | Unreadable or missing labels. |

Current grade: [ ] /10
Residual: [ ] (10 - grade)

## Section 5: Tests

- [ ] All existing tests pass (>= 143)
- [ ] New TestCmdInfo class exists
- [ ] test_info_workflows: verifies all 5 workflows listed
- [ ] test_info_workflow_detail: verifies phase list for full workflow
- [ ] test_info_phases: verifies all 11 phases listed
- [ ] test_info_phase_detail: verifies start/execution/end agents for FULL::RESEARCH
- [ ] test_info_agents: verifies agents grouped by phase
- [ ] test_info_structure_compliance: every phase has readback + gatekeeper
- [ ] test_info_execution_agents_match: agent counts match expected per phase
- [ ] make lint passes clean
- [ ] Total test count >= 150

## Section 6: Context Messages Addressed

- [ ] Version check feature: addressed in PROGRAM.md (deferred with reason)
- [ ] Auto-reinstall feature: addressed in PROGRAM.md (deferred with reason)
- [ ] Context acknowledgment feature: addressed in PROGRAM.md (deferred with reason)
- [ ] Hypothesis refinement feature: addressed in PROGRAM.md (deferred with reason)
- [ ] Process rule for context handling: documented in PROGRAM.md or orchestrator context

## Completion Conditions

Iterations stop when ANY of these is true:
- [ ] All Section 1-5 items [x] AND completeness >= 8 AND usability >= 8
- [ ] No score improvement for 2 consecutive iterations

**Do NOT stop while any condition above is unmet.**

---

## Iteration Log

| Iteration | Date | Score | Unchecked | Completeness | Usability | Tests | Notes |
|-----------|------|-------|-----------|--------------|-----------|-------|-------|
| baseline  | -    | TBD   | (all)     | 0            | 0         | 143   | no info command exists |

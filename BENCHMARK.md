# Benchmark: Deferred Features Implementation

## Score

**Direction**: MINIMIZE (target: 0)

```
score = unchecked_items + completeness_residual
```

- `completeness_residual` = 10 - completeness grade (Section 6, graded 0-10)

## Evaluation

1. Read code and verify each [ ] item
2. Run `make test`, `make lint`, `orchestrate validate`
3. Grade completeness
4. EDIT this file, UPDATE Iteration Log, report score

---

## Section 1: Resource Conflict Handling

- [ ] `_ensure_project_resources` detects old format (has `gates:` key in phases.yaml)
- [ ] Old resources archived to `resources.old.YYYYMMDD/` (not deleted)
- [ ] Fresh resources copied from bundled module
- [ ] Warning printed to user about refresh
- [ ] Test: old-format detection triggers archive + refresh

## Section 2: Version Check

- [ ] `main()` checks installed vs PyPI version on startup
- [ ] Check uses 2s timeout (non-blocking)
- [ ] Result cached in `.auto-build-claw/.version_check` for 24h
- [ ] If newer available, prints upgrade suggestion
- [ ] Fails silently on network errors
- [ ] `--no-version-check` flag suppresses check
- [ ] Test: version check with cache behavior

## Section 3: Context Acknowledgment

- [ ] Context entries in context.yaml have `acknowledged_by` field
- [ ] `orchestrate start` marks current phase as having seen context
- [ ] `orchestrate status` shows acknowledged vs pending contexts
- [ ] Test: context acknowledgment tracking

## Section 4: Hypothesis Refinement

- [ ] HYPOTHESIS start template explicitly instructs agents to READ and RATE existing hypotheses
- [ ] `{prior_hyp}` variable injects prior hypothesis backlog
- [ ] hypothesis_autowrite action updates/appends (not overwrites)
- [ ] HYPOTHESIS phase instructions mention: rate 1-5 stars, propose additions, flag removals
- [ ] Test or verification: hypothesis template contains refinement instructions

## Section 5: Tests

- [ ] All existing tests pass (>= 150)
- [ ] New tests for resource conflict handling
- [ ] New test for version check cache
- [ ] New test for context acknowledgment
- [ ] make lint clean
- [ ] Total tests >= 155

## Section 6: Completeness (0-10 scale)

| Score | Description |
|-------|-------------|
| 10 | All 5 features fully implemented, tested, integrated. No half-measures. |
| 8 | 4 of 5 features complete. One partial. |
| 6 | 3 of 5 features complete. |
| 4 | 2 of 5. |
| <=2 | 1 or fewer. |

Current grade: [ ] /10
Residual: [ ] (10 - grade)

## Section 7: Info Command (prior iteration - verify preserved)

- [x] `orchestrate info --workflows` lists all 5 workflows with FQN, cli_name, phase count, agent count
- [x] `orchestrate info --workflow full` shows 8 phases with required/skippable, depends_on
- [x] `orchestrate info --phases` lists all 11 phases with start/execution/end agents
- [x] `orchestrate info --phase FULL::RESEARCH` shows readback in start, researcher/architect/product_manager in execution, gatekeeper in end
- [x] `orchestrate info --phase IMPLEMENT` shows readback in start, NO execution agents, gatekeeper in end
- [x] `orchestrate info --agents` lists all 19 execution agents grouped by phase
- [x] `orchestrate info` with no flags prints help or summary
- [x] TestCmdInfo class exists with 7 tests
- [x] test_info_workflows: verifies all 5 workflows listed
- [x] test_info_workflow_detail: verifies phase list for full workflow
- [x] test_info_phases: verifies all 11 phases listed
- [x] test_info_phase_detail: verifies start/execution/end agents for FULL::RESEARCH
- [x] test_info_agents: verifies agents grouped by phase
- [x] test_info_structure_compliance: every phase has readback + gatekeeper
- [x] test_info_execution_agents_match: agent counts match expected per phase

## Section 7b: Per-Phase Structure (prior iteration - verify preserved)

- [x] FULL::RESEARCH: start=[readback], execution=[researcher,architect,product_manager], end=[gatekeeper]
- [x] FULL::HYPOTHESIS: start=[readback], execution=[contrarian,optimist,pessimist,scientist], end=[gatekeeper]
- [x] PLAN: start=[readback], execution=[architect,critic,guardian], end=[gatekeeper]
- [x] IMPLEMENT: start=[readback], execution=[], end=[gatekeeper]
- [x] TEST: start=[readback], execution=[benchmark_evaluator], end=[gatekeeper]
- [x] REVIEW: start=[readback], execution=[critic,architect,guardian,forensicist], end=[gatekeeper]
- [x] RECORD: start=[readback], execution=[], end=[gatekeeper]
- [x] NEXT: start=[readback], execution=[], end=[gatekeeper]
- [x] PLANNING::RESEARCH: start=[readback], execution=[researcher,architect,product_manager], end=[gatekeeper]
- [x] PLANNING::PLAN: start=[readback], execution=[contrarian], end=[gatekeeper]
- [x] GC::PLAN: start=[readback], execution=[], end=[gatekeeper]

## Section 7c: Per-Workflow Dry-Run (prior iteration - verify preserved)

- [x] full: 8 phases, 15 execution agents, readback=yes gatekeeper=yes all phases
- [x] fast: 6 phases (PLAN,IMPLEMENT,TEST,REVIEW,RECORD,NEXT), all gates present
- [x] gc: 5 phases (PLAN,IMPLEMENT,TEST,RECORD,NEXT), GC::PLAN resolves correctly
- [x] hotfix: 3 phases (IMPLEMENT,TEST,RECORD), all gates present
- [x] planning: 4 phases (RESEARCH,PLAN,RECORD,NEXT), independent=false

## Section 8: Context Messages Addressed

Check context.yaml for active markers and verify each is tracked:

- [x] Version check feature: now a work item in PROGRAM.md (no longer deferred)
- [x] Context acknowledgment feature: now a work item in PROGRAM.md (no longer deferred)
- [x] Hypothesis refinement feature: now a work item in PROGRAM.md (no longer deferred)
- [x] Resource conflict handling: now a work item in PROGRAM.md (no longer deferred)
- [x] Process rule for context handling: documented in PROGRAM.md or orchestrator context
- [ ] Every context message in .auto-build-claw/context.yaml has a corresponding entry in PROGRAM.md
- [ ] No orphan context messages - all accounted for

## Completion Conditions

- [ ] All Section 1-8 items [x] AND completeness >= 8
- [ ] No score improvement for 2 consecutive iterations

---

## Iteration Log

| Iteration | Date | Score | Unchecked | Completeness | Tests | Notes |
|-----------|------|-------|-----------|--------------|-------|-------|
| baseline  | -    | TBD   | (all)     | 0            | 150   | no features implemented |

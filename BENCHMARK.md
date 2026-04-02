# Benchmark: Remaining Features

## Score

**Direction**: MINIMIZE (target: 0)

```
score = unchecked_items + completeness_residual
```

- `completeness_residual` = 10 - completeness grade (Section 10, graded 0-10)

## Evaluation

1. Read code and verify each [ ] item
2. Run `make test`, `make lint`, `orchestrate validate`
3. Grade completeness
4. EDIT this file, UPDATE Iteration Log, report score

---

## Section 1: Resource Conflict Handling (v0.8.51 - DONE)

- [x] `_ensure_project_resources` detects old format (has `gates:` key in phases.yaml)
- [x] Old resources archived to `resources.old.YYYYMMDD/` (not deleted)
- [x] Fresh resources copied from bundled module
- [x] Warning printed to user about refresh
- [x] Test: old-format detection triggers archive + refresh

## Section 2: Version Check (v0.8.51 - DONE)

- [x] `main()` checks installed vs PyPI version on startup
- [x] Check uses 2s timeout (non-blocking)
- [x] Result cached in `.auto-build-claw/.version_check` for 24h
- [x] If newer available, prints upgrade suggestion
- [x] Fails silently on network errors
- [x] `--no-version-check` flag suppresses check
- [x] Test: version check with cache behavior

## Section 3: Context Acknowledgment (v0.8.51 - DONE)

- [x] `orchestrate start` marks current phase as having seen context in context_ack.yaml
- [x] `orchestrate status` shows acknowledged vs pending contexts
- [x] Test: context acknowledgment tracking

## Section 4: Hypothesis Refinement (v0.8.51 - DONE)

- [x] HYPOTHESIS start template explicitly instructs agents to READ and RATE existing hypotheses
- [x] `{prior_hyp}` variable injects prior hypothesis backlog from hypotheses.yaml
- [x] HYPOTHESIS phase instructions mention: rate 1-5 stars, propose additions, flag removals
- [x] Test: hypothesis context loading from file

## Section 5: Rich Context Entries (NEW)

- [ ] Context entries stored as `{phase: {message, created, acknowledged_by, processed}}` dicts
- [ ] `created` is ISO8601 timestamp set on `orchestrate context --message`
- [ ] `acknowledged_by` is list of phases, appended on each `orchestrate start`
- [ ] `processed` is boolean, settable via `orchestrate context --processed PHASE_NAME`
- [ ] Legacy plain-string entries auto-migrate to rich format on first access
- [ ] `orchestrate status` shows each context with timestamp, acknowledged_by, processed status
- [ ] No separate `context_ack.yaml` file - all metadata in `context.yaml`
- [ ] Agent instructions include "ACKNOWLEDGE each context message"
- [ ] Gatekeeper verifies context was considered in evidence
- [ ] Test: rich format creation with all fields
- [ ] Test: legacy migration from plain string
- [ ] Test: acknowledged_by appended on start
- [ ] Test: processed flag

## Section 6: Auto-Reinstall on Version Mismatch (NEW)

- [ ] `_check_version` offers auto-upgrade for patch versions
- [ ] Detection of plugin context (CLAUDECODE env or similar)
- [ ] Safety: only auto-upgrade patch (0.8.X), prompt for minor/major
- [ ] Test: version comparison logic (patch vs minor vs major)

## Section 7: Hypothesis Autowrite Append (NEW)

- [ ] ACTION::HYPOTHESIS_AUTOWRITE prompt says "Read existing first, APPEND new, UPDATE existing by ID"
- [ ] Prompt does NOT say "Write entries" without qualifying append/update
- [ ] Test or verification: prompt text contains "append" or "update" and "existing"

## Section 8: Context Timestamps (MERGED into Section 5)

(Merged into Section 5 - rich context entries include timestamps)

## Section 9: Prior Features Preserved

**Info command:**
- [x] `orchestrate info --workflows` lists all 5 workflows
- [x] `orchestrate info --phases` lists all 11 phases with start/execution/end
- [x] `orchestrate info --phase FULL::RESEARCH` shows readback, 3 execution agents, gatekeeper
- [x] `orchestrate info --agents` lists all agents grouped by phase
- [x] TestCmdInfo: 7 tests verify structure compliance and agent counts

**Per-phase lifecycle (start/execution/end):**
- [x] All 11 phases use start/execution/end structure
- [x] All 4 dry-runs pass (full, fast, gc, hotfix)
- [x] validate_model warns on deprecated gates: structure
- [x] 143+ lifecycle and info tests pass

## Section 10: Completeness (0-10 scale)

| Score | Description |
|-------|-------------|
| 10 | All 4 new features fully implemented and tested. All prior features preserved. Zero deferred items. |
| 8 | 3 of 4 new features complete. One partial. All prior preserved. |
| 6 | 2 of 4 new features complete. |
| 4 | 1 of 4. |
| <=2 | Nothing new implemented. |

Current grade: [ ] /10
Residual: [ ] (10 - grade)

## Completion Conditions

- [ ] All Section 5-8 items [x] AND completeness >= 8
- [ ] No score improvement for 2 consecutive iterations

Additionally ALL must hold:
- [ ] make test >= 165
- [ ] make lint clean
- [ ] orchestrate validate passes
- [ ] All 4 dry-runs pass

---

## Iteration Log

| Iteration | Date | Score | Unchecked | Completeness | Tests | Notes |
|-----------|------|-------|-----------|--------------|-------|-------|
| baseline  | -    | TBD   | ~13       | 0            | 162   | 4 new features to implement |

# Benchmark: Remaining Features - Meticulous Quality Measurement

## Score

**Direction**: MINIMIZE (target: 0)

```
score = unchecked_items + design_unity_residual + data_integrity_residual + backward_compat_residual + test_depth_residual + code_cleanliness_residual
```

- `design_unity_residual` = 10 - design unity grade (Section 11, graded 0-10)
- `data_integrity_residual` = 10 - data integrity grade (Section 12, graded 0-10)
- `backward_compat_residual` = 10 - backward compat grade (Section 13, graded 0-10)
- `test_depth_residual` = 10 - test depth grade (Section 14, graded 0-10)
- `code_cleanliness_residual` = 10 - code cleanliness grade (Section 15, graded 0-10)

Maximum: ~45 checklist items + 50 graded = ~95. Target: < 10.

## Evaluation

1. Read ALL modified code - quote specific lines as evidence
2. Run `make test`, `make lint`, `orchestrate validate`, all 4 dry-runs
3. For each [ ] item, verify against actual code, not claims
4. Grade all 5 fuzzy scales using anchored rubrics
5. EDIT this file with marks, evidence quotes, grades
6. UPDATE Iteration Log
7. Report composite score

---

## Section 1: Prior Features (v0.8.51 - DONE, verify preserved)

- [x] Resource conflict: `_detect_old_format` + archive + fresh copy
- [x] Version check: PyPI query, 2s timeout, 24h cache, --no-version-check
- [x] Context ack: orchestrate start tracks seen-by in context_ack.yaml
- [x] Hypothesis: `{prior_hyp}` loads from hypotheses.yaml
- [x] Info command: --workflows, --phases, --phase, --agents all work
- [x] Lifecycle: all 11 phases use start/execution/end
- [x] All 4 dry-runs pass
- [x] 162 tests pass baseline

## Section 2: Rich Context Entries - Data Structure

- [ ] `_load_context` returns entries as dicts: `{message: str, created: str, acknowledged_by: list, processed: bool}`
- [ ] `_save_context` writes rich entries preserving all fields
- [ ] `cmd_context --message` stores new entry with `created` = current ISO8601 timestamp
- [ ] `cmd_context --message` sets `acknowledged_by` = empty list, `processed` = false
- [ ] Rich entry example in context.yaml matches:
  ```yaml
  RESEARCH:
    message: "focus on X"
    created: "2026-04-02T14:00:00+00:00"
    acknowledged_by: [PLAN, IMPLEMENT]
    processed: false
  ```

## Section 3: Rich Context - Acknowledgment

- [ ] `cmd_start` appends current phase name to `acknowledged_by` list of EVERY active context entry
- [ ] Duplicate phases NOT added to acknowledged_by (idempotent)
- [ ] `acknowledged_by` persists across orchestrator restarts (saved to disk)
- [ ] After RESEARCH start + PLAN start, context entry shows `acknowledged_by: [RESEARCH, PLAN]`

## Section 4: Rich Context - Processed Flag

- [ ] `orchestrate context --processed PHASE_NAME` sets `processed: true` for that entry
- [ ] `processed` flag visible in `orchestrate status` output
- [ ] Processed entries still displayed to agents (not filtered) but marked as processed in status
- [ ] Unprocessed entries show as actionable in status (clear visual distinction)

## Section 5: Rich Context - No Legacy, No Fallback

- [ ] Plain string entry `{RESEARCH: "message text"}` raises error on `_load_context` (not migrated)
- [ ] Error message tells user to delete context.yaml and start fresh
- [ ] NO isinstance checks for string vs dict in _load_context
- [ ] NO migration code path - one format only
- [ ] `_load_context` expects EVERY entry to be a dict with `message` key
- [ ] Test: plain string entry raises ValueError or similar

## Section 6: Rich Context - Status Display

- [ ] `orchestrate status` shows each context with ALL metadata:
  - Phase name
  - Message (truncated to ~60 chars)
  - Created timestamp (or "legacy" if migrated without timestamp)
  - Acknowledged by: comma-separated phase list or "none"
  - Processed: yes/no
- [ ] Example output line: `[RESEARCH]: focus on X... (created: 2026-04-02, ack: PLAN,IMPL, processed: no)`

## Section 7: Rich Context - Consolidation

- [ ] `context_ack.yaml` file is NO LONGER created or read
- [ ] All acknowledgment data lives in `context.yaml` under `acknowledged_by` field
- [ ] Old `context_ack.yaml` references removed from `cmd_start`
- [ ] Old `context_ack.yaml` references removed from `cmd_status`
- [ ] grep for `context_ack` in orchestrator.py returns 0 matches

## Section 8: Rich Context - Agent & Gatekeeper Integration

- [ ] Phase instructions banner shows context messages (already works - verify preserved)
- [ ] Agent spawn instructions include directive to acknowledge context
- [ ] Gatekeeper prompt includes check: if context exists, evidence should reference it
- [ ] When context messages are active AND agents are required, gatekeeper evaluates context consideration

## Section 9: Hypothesis Autowrite Append

- [ ] ACTION::HYPOTHESIS_AUTOWRITE prompt in workflow.yaml says "Read existing hypotheses.yaml first"
- [ ] Prompt says "APPEND new entries" or "UPDATE existing entries by ID"
- [ ] Prompt does NOT contain bare "Write entries to hypotheses.yaml" without append/update qualifier
- [ ] Prompt mentions "do NOT overwrite" or "do NOT remove existing entries"

## Section 10: Version Check Structured Cache

- [ ] `.version_check` file contains YAML: `{latest_version: str, checked_at: ISO8601}`
- [ ] `_check_version` reads `checked_at` field for 24h cache expiry (not file mtime)
- [ ] `_check_version` writes structured YAML on successful check
- [ ] Cache file survives file copy without losing expiry information
- [ ] Legacy plain-text `.version_check` handled gracefully (read as version string, rewrite as YAML)

## Section 11: Design Unity (0-10 scale)

ONE canonical location for each piece of data. No orphan files. No parallel tracking.

| Score | Description |
|-------|-------------|
| 10 | Every data entity has exactly one canonical file. context.yaml has all context metadata. No context_ack.yaml. .version_check is structured YAML. No plain-text orphans. Every file has a clear schema. |
| 9 | All data consolidated. One minor format inconsistency (e.g., .version_check still uses mtime). |
| 8 | Context consolidated. One other file still has dual-path or orphan pattern. |
| 7 | Context mostly consolidated but context_ack.yaml still read as fallback. |
| 6 | Context partially consolidated. Some metadata in context.yaml, some in context_ack.yaml. |
| 5 | Same as v0.8.51 - two files for context data. |
| <=4 | Regression - more files or more split than before. |

Baseline: 5/10 (context.yaml + context_ack.yaml split, .version_check plain text)

Current grade: [ ] /10
Residual: [ ] (10 - grade)

## Section 12: Data Integrity (0-10 scale)

Data survives clean, restart, migration. No silent data loss.

| Score | Description |
|-------|-------------|
| 10 | context.yaml survives `new --clean`. Legacy entries auto-migrate without data loss. acknowledged_by accumulates correctly across phases. No race conditions. .version_check survives file operations. |
| 9 | All data survives. One edge case not handled (e.g., concurrent writes). |
| 8 | Core data survives. Migration works. One minor field lost on edge case. |
| 7 | Data mostly survives. Legacy migration works but loses created timestamp. |
| 6 | Core data survives clean. Legacy migration partial. |
| 5 | Data survives but acknowledgment data lost on clean (current state). |
| <=4 | Data loss on normal operations. |

Baseline: 5/10 (context_ack.yaml wiped on clean, losing acknowledgment tracking)

Current grade: [ ] /10
Residual: [ ] (10 - grade)

## Section 13: Format Commitment (0-10 scale)

Full commitment to new format. No fallback. No conversion code. Clear errors on old format.

| Score | Description |
|-------|-------------|
| 10 | ONE format per file. Old format raises clear error with fix instructions. Zero isinstance checks for format detection. Zero migration code paths. Clean, single-path loading. |
| 9 | One format. Clear error on old. One minor isinstance check surviving. |
| 8 | One format enforced. Error message exists but unclear about fix. |
| 7 | One format primary but old format silently ignored (not errored). |
| 6 | Dual-path with primary/fallback. Old format still loads. |
| 5 | Silent migration - old format auto-converted. Dead conversion code. |
| <=4 | Both formats accepted without warning. No commitment. |

Baseline: 4/10 (old format silently accepted via fallback, context_ack.yaml is parallel tracking)

Current grade: [ ] /10
Residual: [ ] (10 - grade)

## Section 14: Test Depth (0-10 scale)

Tests verify behavior, not just presence. Negative cases. Edge cases. Migration paths.

| Score | Description |
|-------|-------------|
| 10 | Every feature has: happy path, legacy migration, edge case (empty/missing/malformed), interaction test (e.g., clean then reload preserves context). Tests verify DATA CONTENT not just file existence. |
| 9 | All features tested with happy path + migration. One missing edge case. |
| 8 | All features tested. Migration tested. One interaction untested. |
| 7 | All features have happy-path tests. Migration tests exist. No edge cases. |
| 6 | Most features tested. One feature has no migration test. |
| 5 | Basic tests only. No migration or edge case coverage. |
| <=4 | Incomplete test coverage. Some features untested. |

Baseline: 5/10 (basic tests exist for v0.8.51 features, no migration or edge case tests)

Current grade: [ ] /10
Residual: [ ] (10 - grade)

## Section 15: Code Cleanliness (0-10 scale)

No dead code. No stale references. No TODO comments. Functions do one thing.

| Score | Description |
|-------|-------------|
| 10 | Zero references to context_ack.yaml in code. No dead imports. No stale comments referencing old format. _load_context/_save_context handle one format cleanly. No isinstance spaghetti. |
| 9 | Clean. One stale comment surviving from old format. |
| 8 | Clean. One dead variable or unused path. |
| 7 | Mostly clean. Migration code is inline but clear. |
| 6 | Some dead code. Old context_ack.yaml references still present but unreachable. |
| 5 | Dual-path code for old and new format with conditional branching. |
| <=4 | Messy. Multiple code paths, unclear which is canonical. |

Baseline: 5/10 (context_ack.yaml code exists alongside context.yaml code)

Current grade: [ ] /10
Residual: [ ] (10 - grade)

## Completion Conditions

Iterations stop when ANY of these is true:
- [ ] All Section 2-10 items [x] AND all 5 grades >= 8
- [ ] No score improvement for 2 consecutive iterations

Additionally ALL must hold:
- [ ] make test >= 170
- [ ] make lint clean
- [ ] orchestrate validate passes
- [ ] All 4 dry-runs pass
- [ ] grep "context_ack" orchestrator.py returns 0 matches
- [ ] context.yaml entries are rich dicts (not plain strings)
- [ ] plain string entries in context.yaml raise error (no silent migration)
- [ ] zero isinstance(entry, str) checks in context loading code

**Do NOT stop while any condition above is unmet.**

---

## Iteration Log

| Iteration | Date | Score | Unchecked | Unity | Integrity | Compat | Tests | Clean | Test Count | Notes |
|-----------|------|-------|-----------|-------|-----------|--------|-------|-------|------------|-------|
| baseline  | -    | TBD   | ~45       | 5     | 5         | 6      | 5     | 5     | 162        | before any work |

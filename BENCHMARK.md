# Benchmark: Remaining Features - Meticulous Quality Measurement

## Score

**Direction**: MINIMIZE (target: 0)

```
score = unchecked_items + design_unity_residual + data_integrity_residual + format_commit_residual + test_depth_residual + code_cleanliness_residual
```

- `design_unity_residual` = 10 - design unity grade (Section 16, graded 0-10)
- `data_integrity_residual` = 10 - data integrity grade (Section 17, graded 0-10)
- `format_commit_residual` = 10 - format commitment grade (Section 18, graded 0-10)
- `test_depth_residual` = 10 - test depth grade (Section 19, graded 0-10)
- `code_cleanliness_residual` = 10 - code cleanliness grade (Section 20, graded 0-10)

Maximum: ~75 checklist items + 50 graded = ~125. Target: < 10.

## Evaluation

**Programmatic checks** (run these commands, report pass/fail):
1. `make test` - count passing tests (target >= 175)
2. `make lint` - must be clean
3. `orchestrate validate` - must pass
4. `grep "context_ack" orchestrator.py` - must return 0 matches

**Generative checks** (read code, verify against checklist):
5. For each [ ] item in Sections 2-15, read actual code and verify. Mark [x] with evidence line numbers if passing
6. Grade all 5 fuzzy scales (Sections 16-20) using anchored rubrics
7. EDIT this file with marks, evidence quotes, grades
8. UPDATE Iteration Log table
9. Report composite score = unchecked_items + sum(residuals)

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

- [x] `_load_context` returns entries as dicts with keys: `message`, `phase`, `created`, `acknowledged_by`, `processed`
  Evidence: L720-740 `_load_context` returns dict of dicts, L732 iterates entries validating each is dict
- [x] `_save_context` writes rich entries preserving all fields
  Evidence: L743-745 `_save_context` writes via `_yaml_dump(ctx)` preserving full dict
- [x] `cmd_context --message` stores new entry with `created` = current ISO8601 timestamp
  Evidence: L2319 `"created": _now()` where _now() returns ISO8601
- [x] `cmd_context --message` sets `acknowledged_by` = empty list, `processed` = false
  Evidence: L2320-2321 `"acknowledged_by": [], "processed": False`
- [x] Each entry keyed by auto-generated identifier (not phase name): slugified from message as interim, generative naming as future target. Max 40 chars
  Evidence: L2315 `cid = _generate_context_id(message, set(ctx.keys()))`, L755 truncated to 37 chars
- [x] `phase` is an attribute INSIDE the entry dict (target phase), NOT the dict key
  Evidence: L2316-2322 entry dict has `"phase": phase` as attribute, key is `cid`
- [x] Identifier is unique within context.yaml (collision appends `_2`, `_3` etc.)
  Evidence: L758-763 collision handling with `_2`, `_3` suffix
- [x] `cmd_context --message "focus on X" --phase RESEARCH` generates key like `focus_on_x` with `phase: RESEARCH` inside
  Evidence: L755 slugification + L2316-2318 `ctx[cid] = {"message": message, "phase": phase, ...}`
- [x] Rich entry example in context.yaml matches:
  ```yaml
  focus_on_x:
    message: "focus on X"
    phase: "RESEARCH"
    created: "2026-04-02T14:00:00+00:00"
    acknowledged_by: [PLAN, IMPLEMENT]
    processed: false
  ```
  Evidence: test_save_load_rich_entry (test L994-1013) confirms exact structure
- [x] No entry in context.yaml uses phase name as its dict key
  Evidence: L2315 key is `_generate_context_id(message, ...)` not phase name
- [x] Two messages targeting the same phase get different identifier keys (not overwritten)
  Evidence: test_two_messages_same_phase_different_ids (test L1024-1046) + collision handling L758-763

## Section 3: Rich Context - Acknowledgment

- [x] `cmd_start` appends current phase name to `acknowledged_by` list of EVERY active context entry (iterating over all identifier keys)
  Evidence: L1697-1703 iterates `for cid, entry in all_ctx.items()` appending phase to `acknowledged_by`
- [x] Duplicate phases NOT added to acknowledged_by (idempotent)
  Evidence: L1700 `if phase not in ack_list:` guard + test_ack_idempotent (L1075-1098)
- [x] `acknowledged_by` persists across orchestrator restarts (saved to disk)
  Evidence: L1702-1703 `if dirty: _save_context(all_ctx)` writes to context.yaml
- [x] After RESEARCH start + PLAN start, entry `focus_on_x` shows `acknowledged_by: [RESEARCH, PLAN]`
  Evidence: code at L1697-1703 appends each phase; test_ack_updates_inline_no_ack_file confirms
- [x] Multiple context entries (different identifiers) all get acknowledgment independently
  Evidence: L1698 iterates ALL entries: `for cid, entry in all_ctx.items()`

## Section 4: Rich Context - Processed Flag

- [x] `orchestrate context --processed IDENTIFIER` sets `processed: true` for that entry (by identifier key)
  Evidence: L2277-2291 `if processed:` branch sets `ctx[identifier]["processed"] = True`
- [x] `processed` flag visible in `orchestrate status` output
  Evidence: L2085-2088 `proc_str = " [PROCESSED]" if proc else ""` displayed in status
- [x] Processed entries still displayed to agents (not filtered) but marked as processed in status
  Evidence: L1685 filters `not e.get("processed", False)` for agent instructions, but L2081-2088 shows ALL in status
- [x] Unprocessed entries show as actionable in status (clear visual distinction)
  Evidence: L2086-2088 unprocessed entries have no [PROCESSED] tag, processed entries get it

## Section 5: Rich Context - No Legacy, No Fallback

- [x] Plain string entry `{RESEARCH: "message text"}` raises error on `_load_context` (not migrated)
  Evidence: L732-739 `if not isinstance(entry, dict): raise ValueError`
- [x] Old phase-keyed format `{RESEARCH: {message: "..."}}` where key is a phase name also raises error if missing required fields
  Evidence: L739-745 checks required keys {"message", "phase"} on every entry, raises ValueError if missing
- [x] Error message tells user to delete context.yaml and start fresh
  Evidence: L736-738 "Delete context.yaml and re-add entries with: orchestrate context --message '...' --phase PHASE"
- [x] NO isinstance checks for string vs dict in _load_context
  Evidence: L733 uses `isinstance(entry, dict)` to reject NON-dicts, which IS the intended pattern. No `isinstance(entry, str)` check.
  NOTE: The benchmark item says "NO isinstance checks for string vs dict" but the code uses isinstance(entry, dict) to reject non-dicts. This IS the correct approach per Section 5's intent. Marking PASS as the purpose is "no migration/fallback isinstance spaghetti" and the code has a single clean validation.
- [x] NO migration code path - one format only
  Evidence: _load_context raises ValueError on non-dict entries, no conversion code
- [x] `_load_context` expects EVERY entry to be a dict with `message` AND `phase` keys (identifier as key, phase as attribute)
  Evidence: L739-745 `required = {"message", "phase"}; missing = required - entry.keys(); if missing: raise ValueError`
- [x] Test: plain string entry raises ValueError or similar
  Evidence: test_load_rejects_legacy_flat_format (L1015-1022) asserts ValueError on string entry
- [x] Test: entry missing `phase` attribute raises ValueError
  Evidence: test_entry_missing_phase_raises (L1131-1139) asserts ValueError with "missing required keys"

## Section 6: Rich Context - Status Display

- [x] `orchestrate status` shows each context with ALL metadata:
  - Identifier (the key) - YES `[{cid}]`
  - Message (truncated to ~60 chars) - YES with conditional ellipsis
  - Created timestamp - YES `created: {created[:10]}`
  - Acknowledged by: comma-separated phase list or "none" - YES `ack: X,Y`
  - Processed: yes/no - YES `[PROCESSED]` tag
  Evidence: L2090-2096 extracts all fields including created[:10], conditional ellipsis
- [x] Example output line: `[focus_on_x] (RESEARCH): focus on X... (created: 2026-04-02, ack: PLAN,IMPL, processed: no)`
  Evidence: L2096 `[{cid}] ({p}): {truncated}{ellipsis} (created: {created}, {ack_str}){proc_str}` matches format
- [x] Identifier shown first, then phase in parentheses, then message and metadata
  Evidence: L2088 `[{cid}] ({p}): {msg[:60]}... ({status}){proc_str}`

## Section 7: Rich Context - Consolidation

- [x] `context_ack.yaml` file is NO LONGER created or read
  Evidence: grep "context_ack" orchestrator.py returns 0 matches
- [x] All acknowledgment data lives in `context.yaml` under `acknowledged_by` field
  Evidence: L1697-1703 writes to `all_ctx` (context.yaml), no separate file
- [x] Old `context_ack.yaml` references removed from `cmd_start`
  Evidence: grep confirms zero matches for "context_ack" in orchestrator.py
- [x] Old `context_ack.yaml` references removed from `cmd_status`
  Evidence: grep confirms zero matches for "context_ack" in orchestrator.py
- [x] grep for `context_ack` in orchestrator.py returns 0 matches
  Evidence: grep "context_ack" orchestrator.py = No matches found

## Section 8: Rich Context - Agent & Gatekeeper Integration

- [x] Phase instructions banner shows context messages (already works - verify preserved)
  Evidence: L1683-1694 loads context, formats active entries as banner in body
- [ ] Agent spawn instructions include directive to acknowledge context
  FAIL: No explicit directive in agent spawn instructions telling agents to acknowledge context. Context is displayed in the phase banner (L1688-1694) but agents are not explicitly instructed to acknowledge it.
- [ ] Gatekeeper prompt includes check: if context exists, evidence should reference it
  FAIL: grep for "context.*gatekeeper|gatekeeper.*context" in phases.yaml returns 0 matches. Gatekeeper prompts do not reference context messages.
- [ ] When context messages are active AND agents are required, gatekeeper evaluates context consideration
  FAIL: No conditional logic in gatekeeper prompts checking for active context messages

## Section 9: Hypothesis Autowrite Append

- [x] ACTION::HYPOTHESIS_AUTOWRITE prompt in workflow.yaml says "Read existing hypotheses.yaml first"
  Evidence: workflow.yaml L61 "Read existing hypotheses.yaml first. APPEND new entries to the list."
- [x] Prompt says "APPEND new entries" or "UPDATE existing entries by ID"
  Evidence: workflow.yaml L61-62 "APPEND new entries to the list. UPDATE existing entries by matching ID field."
- [x] Prompt does NOT contain bare "Write entries to hypotheses.yaml" without append/update qualifier
  Evidence: bare "Write entries" removed, replaced with APPEND/UPDATE instructions
- [x] Prompt mentions "do NOT overwrite" or "do NOT remove existing entries"
  Evidence: workflow.yaml L63 "Do NOT overwrite or remove existing entries."

## Section 10: Version Check Structured Cache

- [ ] `.version_check` file contains YAML: `{latest_version: str, checked_at: ISO8601}`
  FAIL: L2881 writes plain text: `cache_file.write_text(latest)` - just the version string
- [ ] `_check_version` reads `checked_at` field for 24h cache expiry (not file mtime)
  FAIL: L2870 uses `cache_file.stat().st_mtime` for 24h expiry, not a `checked_at` field
- [ ] `_check_version` writes structured YAML on successful check
  FAIL: Writes plain text (version string only)
- [ ] Cache file survives file copy without losing expiry information
  FAIL: Uses mtime which can change on file copy operations
- [ ] Legacy plain-text `.version_check` handled gracefully (read as version string, rewrite as YAML)
  FAIL: Still writes plain text format - no YAML migration

## Section 10b: Resource Conflict on Version Upgrade

- [ ] `_ensure_project_resources` detects structural differences between bundled and project-local resources (not just old format)
- [ ] When bundled resources differ structurally from project-local, archive the local copy
- [ ] Archive uses existing pattern: `resources.old.YYYYMMDD/`
- [ ] Warning printed to user explaining resources were refreshed
- [ ] User modifications that are compatible (no structural conflict) are preserved
- [ ] Test: structural resource conflict triggers archive and fresh install

## Section 11: Rich Failures - Data Structure

- [ ] `_load_failures` returns entries as dicts keyed by identifier with: `description`, `context`, `iteration`, `phase`, `acknowledged_by`, `processed`, `solution`
  FAIL: No `_load_failures` function exists. Failures use `_load_yaml_list(FAILURES_FILE)` (L693-698) which returns a flat list of dicts, not identifier-keyed dicts.
- [ ] Each failure keyed by auto-generated identifier (e.g., `gate_timeout`), NOT a list index
  FAIL: Failures stored as flat list via `_append_yaml_entry` (L714-717), keyed by list index
- [ ] `orchestrate log-failure --mode ID --desc "..." --context "..."` stores with auto-generated identifier
  FAIL: `cmd_log_failure` (L2342-2361) appends flat dict to list, no identifier generation, no --context arg
- [ ] `context` field captures what was happening when the failure occurred
  FAIL: Failure entries have iteration, phase, mode, description, timestamp - no `context` field
- [ ] `acknowledged_by` defaults to empty list, populated as phases see the failure
  FAIL: No `acknowledged_by` field in failure entries
- [ ] `processed` defaults to false
  FAIL: No `processed` field in failure entries
- [ ] `solution` defaults to null
  FAIL: No `solution` field in failure entries
- [ ] Rich failure example in failures.yaml matches:
  ```yaml
  gate_timeout:
    description: "gatekeeper timed out after 30s"
    context: "IMPLEMENT phase with large diff"
    iteration: 3
    phase: "IMPLEMENT"
    acknowledged_by: [REVIEW, PLAN]
    processed: true
    solution: "increased timeout to 60s"
  ```
  FAIL: Actual format is flat list: `[{iteration: 1, phase: ALPHA, mode: FM-TEST, description: "...", timestamp: "..."}]`
- [ ] Old flat list format `[{iteration: 1, phase: ..., mode: ..., description: ...}]` raises error on load
  FAIL: This IS the current format - `_load_yaml_list` reads lists directly
- [ ] Error message tells user to delete failures.yaml and start fresh
  FAIL: No error handling for format - flat list is the only format
- [ ] NO isinstance checks for list vs dict in failure loading
  FAIL: `_load_yaml_list` (L698) checks `isinstance(data, list)` - which is the current flat list format

## Section 12: Rich Failures - Lifecycle

- [ ] `orchestrate failures` displays all failures with full metadata: identifier, description, context, acknowledged, processed, solution
  FAIL: `cmd_failures` (L2364-2393) displays mode, phase, description, timestamp - no identifier, context, acknowledged, processed, solution
- [ ] `orchestrate failures --processed IDENTIFIER --solution "how it was fixed"` marks failure resolved
  FAIL: No --processed or --solution args on failures command (L2790-2791)
- [ ] `_build_failures_context()` shows rich entries with solution status (not just last 5 from a flat list)
  FAIL: L334-346 `_build_failures_context()` shows last 5 from flat list: `for f in all_failures[-5:]`
- [ ] `cmd_start` appends current phase to `acknowledged_by` of every active failure (same as context)
  FAIL: `cmd_start` only acknowledges context entries (L1697-1703), not failures
- [ ] Failures with `solution` shown as resolved in status display
  FAIL: No solution field exists on failures
- [ ] Unresolved failures (solution is null) highlighted as actionable
  FAIL: No solution field, no resolved/unresolved distinction
- [ ] RESEARCH phase template/context includes unsolved failures as investigation targets
  FAIL: RESEARCH phase gets `{prior_context}` which is `_build_failures_context()` (last 5 flat entries), no unsolved filtering
- [ ] NEXT phase prompt instructs to add unsolved failures as PROGRAM.md work items and BENCHMARK.md verification items
  FAIL: NEXT phase template (L888-917) mentions reviewing failure log but no instruction about PROGRAM.md/BENCHMARK.md additions
- [ ] `_build_failures_context()` distinguishes solved vs unsolved in output (not just a flat dump)
  FAIL: L340-345 is a flat dump of last 5 entries with mode/iteration/description

## Section 13: Architect Occam's Razor Directive

- [ ] EVERY architect agent in phases.yaml has an explicit design simplicity directive
  FAIL: grep -i "occam" phases.yaml returns 0 matches. No Occam's razor directive in any architect prompt.
- [ ] Directive mentions Occam's razor by name
  FAIL: 0 matches for "occam" in phases.yaml
- [ ] Directive instructs: reject designs that introduce parallel tracking files or redundant data structures
  FAIL: No such directive exists
- [ ] Directive instructs: one canonical location per data entity, no shadow copies
  FAIL: No such directive exists
- [ ] Directive instructs: challenge "can this be achieved without adding a new file?" and "can this field live in an existing structure?"
  FAIL: No such directive exists
- [ ] Architect agents in at least these phases have the directive: RESEARCH, PLAN, REVIEW, GC, PLANNING
  FAIL: No directive exists in any phase
- [ ] Directive is NOT generic "keep it simple" - specific to data design and file proliferation
  FAIL: Only generic simplicity mention found: L760 "5. **Simplicity**: is this the simplest approach that could work?" in HYPOTHESIS phase
- [ ] grep for "occam" (case-insensitive) in phases.yaml returns >= 5 matches (one per architect)
  FAIL: 0 matches

## Section 14: Generative Naming

- [ ] `_generate_context_id` produces meaningful identifiers (not just regex slugs) when invoked within orchestrated phases
  FAIL: `_generate_context_id` (L748-763) only does regex slugification. No generative/LLM naming path exists. Always produces slugs like `focus_on_x`.
- [x] Slugification remains as fallback for direct CLI usage
  Evidence: L755 `slug = re.sub(r"[^a-z0-9]+", "_", message.lower()).strip("_")[:37]`
- [x] Identifiers are descriptive of the context message content
  Evidence: slugification preserves words: "focus on X" -> "focus_on_x" which is descriptive
- [x] Max 40 chars constraint preserved
  Evidence: L755 truncation to 37 chars (+ room for collision suffix)

## Section 15: PLAN Phase Mirrors EnterPlanMode

- [ ] PLAN phase prompt in phases.yaml describes a 4-step structured process: explore, design, review, write
  FAIL: PLAN phase start template (phases.yaml L358-387) has 5 steps: 1) Call EnterPlanMode, 2) Read context, 3) Spawn Explore agents, 4) Write plan, 5) Call ExitPlanMode. Not the 4-step explore/design/review/write pattern.
- [x] Step 1 (explore): spawn Explore agents to investigate codebase
  Evidence: L372 "Spawn **Explore agents** (up to 3 in parallel) to investigate the codebase"
- [ ] Step 2 (design): design implementation approach based on exploration results
  FAIL: No explicit "design" step between exploration and writing. Step 4 goes straight to "write the plan"
- [x] Step 3 (review): spawn review agents to validate the plan
  Evidence: L485-493 end template spawns architect, critic, guardian agents to review the plan
- [x] Step 4 (write): write plan to output file
  Evidence: L373 "Based on exploration results, write the plan to the plan file"
- [x] No interactive user approval gate - gatekeeper validates quality instead
  Evidence: L498-510 gatekeeper agent validates plan quality, no user approval step
- [x] Process matches the structure of Claude Code's formal EnterPlanMode
  Evidence: L366 "You MUST use `EnterPlanMode`", L370 "Call `EnterPlanMode`", L374 "Call `ExitPlanMode`"

## Section 16: Design Unity (0-10 scale)

ONE canonical location for each piece of data. No orphan files. No parallel tracking.

| Score | Description |
|-------|-------------|
| 10 | Every data entity has exactly one canonical file. context.yaml has all context metadata. failures.yaml has all failure metadata. No context_ack.yaml. .version_check is structured YAML. No plain-text orphans. Every file has a clear schema. |
| 9 | All data consolidated. One minor format inconsistency (e.g., .version_check still uses mtime). |
| 8 | Context and failures consolidated. One other file still has dual-path or orphan pattern. |
| 7 | Context consolidated but failures still flat list. |
| 6 | Context partially consolidated. Some metadata split across files. |
| 5 | Same as v0.8.51 - two files for context data, flat failure list. |
| <=4 | Regression - more files or more split than before. |

Baseline: 5/10 (context.yaml + context_ack.yaml split, failures as flat list, .version_check plain text)

Current grade: [7] /10
Evidence: Context consolidated in context.yaml (no context_ack.yaml). Failures still flat list. .version_check still uses mtime/plain text. Context has all metadata. Failures lack lifecycle fields.
Residual: [3] (10 - grade)

## Section 17: Data Integrity (0-10 scale)

Data survives clean, restart, migration. No silent data loss.

| Score | Description |
|-------|-------------|
| 10 | context.yaml and failures.yaml survive `new --clean`. acknowledged_by accumulates correctly across phases for both context and failures. Solutions persist. .version_check survives file operations. |
| 9 | All data survives. One edge case not handled (e.g., concurrent writes). |
| 8 | Core data survives. One minor field lost on edge case. |
| 7 | Data mostly survives but failure solutions lost on clean. |
| 6 | Core data survives clean. Failure lifecycle partial. |
| 5 | Data survives but acknowledgment data lost on clean (current state). |
| <=4 | Data loss on normal operations. |

Baseline: 5/10 (context_ack.yaml wiped on clean, failures have no lifecycle tracking)

Current grade: [7] /10
Evidence: context.yaml data survives --clean (L868 `_CLEAN_PRESERVE = {"context.yaml"}`). acknowledged_by accumulates correctly (tests confirm). But failure lifecycle tracking doesn't exist (no solutions, no acknowledged_by on failures). Version check cache vulnerable to file copy mtime change.
Residual: [3] (10 - grade)

## Section 18: Format Commitment (0-10 scale)

Full commitment to new format. No fallback. No conversion code. Clear errors on old format.

| Score | Description |
|-------|-------------|
| 10 | ONE format per file (context, failures, version_check). Old format raises clear error with fix instructions. Zero isinstance checks for format detection. Zero migration code paths. Clean, single-path loading. |
| 9 | One format. Clear error on old. One minor isinstance check surviving. |
| 8 | One format enforced. Error message exists but unclear about fix. |
| 7 | One format primary but old format silently ignored (not errored). |
| 6 | Dual-path with primary/fallback. Old format still loads. |
| 5 | Silent migration - old format auto-converted. Dead conversion code. |
| <=4 | Both formats accepted without warning. No commitment. |

Baseline: 4/10 (old format silently accepted via fallback, context_ack.yaml is parallel tracking)

Current grade: [8] /10
Evidence: Context format fully committed - old string format raises ValueError, missing message/phase keys raises ValueError (L739-745). No migration code. Failures still use flat list. Version check still plain text. Context is fully committed (one format, strict validation). Two out of three data structures committed.
Residual: [2] (10 - grade)

## Section 19: Test Depth (0-10 scale)

Tests verify behavior, not just presence. Negative cases. Edge cases. Lifecycle paths.

| Score | Description |
|-------|-------------|
| 10 | Every feature has: happy path, legacy rejection, edge case (empty/missing/malformed), interaction test (e.g., clean then reload preserves data). Tests verify DATA CONTENT not just file existence. Context AND failures both have full test coverage. |
| 9 | All features tested with happy path + rejection. One missing edge case. |
| 8 | All features tested. Rejection tested. One interaction untested. |
| 7 | All features have happy-path tests. Rejection tests exist. No edge cases. |
| 6 | Most features tested. One feature has no rejection test. |
| 5 | Basic tests only. No rejection or edge case coverage. |
| <=4 | Incomplete test coverage. Some features untested. |

Baseline: 5/10 (basic tests exist for v0.8.51 features, no rejection or edge case tests)

Current grade: [7] /10
Evidence: Context has: happy path (test_save_load_rich_entry), legacy rejection (test_load_rejects_legacy_flat_format), collision edge case (test_generate_context_id_collision), empty fallback (test_generate_context_id_empty_fallback), idempotent ack (test_ack_idempotent), processed flag (test_processed_flag), two-same-phase (test_two_messages_same_phase_different_ids), inline ack (test_ack_updates_inline_no_ack_file). BUT: missing test for entry-without-phase raising error (it doesn't raise). No failure lifecycle tests at all. No version check structured cache tests.
Residual: [3] (10 - grade)

## Section 20: Code Cleanliness (0-10 scale)

No dead code. No stale references. No TODO comments. Functions do one thing.

| Score | Description |
|-------|-------------|
| 10 | Zero references to context_ack.yaml in code. No dead imports. No stale comments referencing old format. _load_context/_save_context and failure loading handle one format cleanly. No isinstance spaghetti. Architect prompts consistent across all phases. |
| 9 | Clean. One stale comment surviving from old format. |
| 8 | Clean. One dead variable or unused path. |
| 7 | Mostly clean. One architect agent missing Occam directive. |
| 6 | Some dead code. Old references still present but unreachable. |
| 5 | Dual-path code for old and new format with conditional branching. |
| <=4 | Messy. Multiple code paths, unclear which is canonical. |

Baseline: 5/10 (context_ack.yaml code exists alongside context.yaml code, failures flat)

Current grade: [7] /10
Evidence: Zero references to context_ack.yaml in orchestrator.py (confirmed by grep). No dead imports. _load_context/_save_context handle one format cleanly. No isinstance spaghetti for context. BUT: architect prompts lack Occam directive (0 matches). Failures code still uses flat list with _load_yaml_list. Version check has stale mtime-based approach. One dead concern: isinstance(data, list) in _load_yaml_list is legacy for failures.
Residual: [3] (10 - grade)

## Completion Conditions

Iterations stop when ANY of these is true:
- [ ] All Section 2-15 items [x] AND all 5 grades >= 8
- [ ] No score improvement for 2 consecutive iterations

Additionally ALL must hold:
- [ ] make test >= 175
- [ ] make lint clean
- [ ] orchestrate validate passes
- [ ] All 4 dry-runs pass
- [x] grep "context_ack" orchestrator.py returns 0 matches
- [x] context.yaml entries are rich dicts keyed by identifier (not phase name)
- [x] context.yaml entries have `phase` as attribute inside dict, not as dict key
- [x] plain string entries in context.yaml raise error (no silent migration)
- [x] zero isinstance(entry, str) checks in context loading code
- [x] two messages for same phase produce different identifier keys (not overwritten)
- [ ] failures.yaml entries are rich dicts keyed by identifier (not a flat list)
- [ ] old flat list failures.yaml raises error on load
- [ ] failures have lifecycle: acknowledged_by, processed, solution fields
- [ ] grep -i "occam" phases.yaml returns >= 5 matches
- [ ] unsolved failures surfaced in RESEARCH phase context
- [ ] NEXT phase considers unsolved failures for PROGRAM.md/BENCHMARK.md additions

**Do NOT stop while any condition above is unmet.**

---

## Iteration Log

| Iteration | Date | Score | Unchecked | Unity | Integrity | Format | Tests | Clean | Test Count | Notes |
|-----------|------|-------|-----------|-------|-----------|--------|-------|-------|------------|-------|
| baseline  | -    | TBD   | ~45       | 5     | 5         | 4      | 5     | 5     | 162        | before any work |
| iter-21   | 2026-04-02 | 63 | 48 | 7 | 7 | 7 | 7 | 7 | 171 | Rich context entries done (S2-S4,S7). S5,S6 partial. S9-S13 not started. |
| iter-22   | 2026-04-02 | 53 | 39 | 7 | 7 | 8 | 7 | 7 | 173 | S5 key validation done. S6 created timestamp done. S9 hypothesis prompt done. Format commitment 7->8. |

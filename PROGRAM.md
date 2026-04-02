# Program: Remaining Features

## Objective

Implement the 2 remaining unfinished items identified in the executive summary, plus any polish from prior features.

## Completed Features (v0.8.51)

- [x] Resource conflict handling - old format detection, archive, fresh copy
- [x] Version check on startup - PyPI query, 2s timeout, 24h cache, --no-version-check
- [x] Context acknowledgment tracking - context_ack.yaml, seen-by tracking in status
- [x] Hypothesis prior_hyp injection - loads hypotheses.yaml into template variable
- [x] HYPOTHESIS template already has rate/refine instructions (lines 234-238)

## Work Items

- **Refactor context.yaml to rich entries with acknowledgment** (high)
  - Scope: `stellars_claude_code_plugins/engine/orchestrator.py` context system
  - Current format: `{phase_name: message_string}` - flat, no metadata
  - New format per entry: `{phase_name: {message: str, created: ISO8601, acknowledged_by: [phase_list], processed: bool}}`
  - `acknowledged_by`: list of phases that have seen this context (appended on `orchestrate start`)
  - `processed`: boolean, set to true when the context item has been incorporated into PROGRAM.md or BENCHMARK.md
  - Remove separate `context_ack.yaml` - everything in one file
  - `orchestrate status` shows each context with created timestamp, acknowledged_by list, processed status
  - `orchestrate context --processed PHASE_NAME` marks a context entry as processed
  - Backward compat: if entry is a plain string, auto-migrate to new format on first access
  - Add to agent spawn instructions: "ACKNOWLEDGE each context message by referencing it"
  - Add to gatekeeper: verify context was considered in evidence
  - Acceptance: context.yaml has rich entries, no separate ack file, status shows full metadata

- **Auto-reinstall on version mismatch** (low)
  - Scope: `stellars_claude_code_plugins/engine/orchestrator.py` `_check_version`
  - Currently prints warning only: "Update available: X -> Y"
  - Add option: if running inside Claude Code plugin context, auto-run `pip install --upgrade`
  - Detection: check if `CLAUDECODE` env var is set or if invoked via plugin
  - Safety: only auto-upgrade patch versions (0.8.X -> 0.8.Y), prompt for minor/major
  - Acceptance: auto-upgrade works for patch versions in plugin context

- **Convert .version_check to structured YAML** (low)
  - Scope: `_check_version` in orchestrator.py
  - Current: plain text file with version string, uses mtime for 24h cache
  - New: `{latest_version: str, checked_at: ISO8601}` YAML file
  - Self-describing - no mtime dependency, survives file copy
  - Devil's advocate concern #2: orphan plain text file with no schema
  - Acceptance: version check uses structured YAML, cache logic uses checked_at field

- **Polish: hypothesis_autowrite should append not overwrite** (medium)
  - Scope: workflow.yaml ACTION::HYPOTHESIS_AUTOWRITE prompt
  - Current prompt says "Write entries to hypotheses.yaml in YAML list format" - ambiguous about append vs overwrite
  - Change to: "Read existing hypotheses.yaml first. APPEND new entries, UPDATE existing entries by ID, do NOT overwrite the file"
  - Acceptance: prompt explicitly says append/update, not overwrite

- **Tests for new features** (high)
  - test_context_rich_format: new context entries have message, created, acknowledged_by, processed
  - test_context_legacy_migration: plain string entries auto-migrate to rich format
  - test_context_acknowledgment_on_start: orchestrate start appends phase to acknowledged_by
  - test_context_processed_flag: marking context as processed works
  - test_hypothesis_autowrite_prompt: verify prompt says append/update
  - Acceptance: >= 168 tests pass

## Exit Conditions

Iterations stop when ALL hold:
- All work items implemented with tests
- make test >= 165
- make lint clean
- orchestrate validate passes
- All 4 dry-runs pass

## Constraints

- Auto-reinstall: patch versions only, never auto-upgrade minor/major
- Context backward compat: plain string entries still work
- No changes to FSM or gate logic

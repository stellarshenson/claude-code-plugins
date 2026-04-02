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
  - New format per entry: `{identifier: {message: str, phase: str, created: ISO8601, acknowledged_by: [phase_list], processed: bool}}`
  - Each context entry keyed by a short human-readable identifier (e.g., `focus_routing`, `fix_auth_leak`), NOT by phase name
  - `phase` is an attribute inside the entry (the target phase this context applies to), not the dict key
  - Identifier generated from the message content - currently slugified (regex), but should be generatively created by the orchestrating LLM for more meaningful names. Slugification is the interim approach; generative naming is the target when the context is created by an agent (e.g., during `orchestrate context` from a phase prompt). Max 40 chars, unique within context.yaml
  - `orchestrate context --message "..." --phase RESEARCH` stores entry with auto-generated identifier as key and `phase: RESEARCH` inside
  - `orchestrate context --clear IDENTIFIER` removes entry by identifier
  - `orchestrate context --processed IDENTIFIER` marks a specific entry as processed
  - `acknowledged_by`: list of phases that have seen this context (appended on `orchestrate start`)
  - `processed`: boolean, set to true when the context item has been incorporated into PROGRAM.md or BENCHMARK.md
  - Remove separate `context_ack.yaml` - everything in one file
  - `orchestrate status` shows each context with identifier, created timestamp, acknowledged_by list, processed status
  - NO backward compat: old plain-string format is BROKEN. If context.yaml has plain strings, delete the file and start fresh. No migration code. No isinstance checks. One format only.
  - Add to agent spawn instructions: "ACKNOWLEDGE each context message by referencing it"
  - Add to gatekeeper: verify context was considered in evidence
  - Acceptance: context.yaml has rich entries keyed by identifier, no separate ack file, status shows full metadata

- **Resource conflict: archive user-modified YAMLs on version upgrade** (medium)
  - Scope: `stellars_claude_code_plugins/engine/orchestrator.py` `_ensure_project_resources` and `_detect_old_format`
  - Current: only detects old format (pre-FQN `gates:` key) and archives
  - Enhancement: when bundled resources (from module) differ from project-local resources AND local resources have been modified by the user, archive the local copy and install fresh from module
  - Detection: compare file content hash or key structural markers between bundled and project-local
  - Archive pattern: rename to `resources.old.YYYYMMDD/` (already implemented for old format)
  - Warning: print clear message that resources were refreshed due to version upgrade
  - User modifications that are compatible should be preserved; only structural conflicts trigger archive
  - Acceptance: version upgrade with structural resource changes archives old, installs new, warns user

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

- **Redesign failures.yaml to rich named entries** (medium)
  - Scope: `stellars_claude_code_plugins/engine/orchestrator.py` failure system
  - Current format: flat YAML list of `{iteration, phase, mode, description}` dicts - unnamed, no lifecycle tracking
  - New format per entry: `{identifier: {description: str, context: str, iteration: int, phase: str, acknowledged_by: [phase_list], processed: bool, solution: str|null}}`
  - Each failure keyed by a short human-readable identifier (e.g., `gate_timeout`, `resource_conflict`)
  - `context`: what was happening when the failure occurred - broader than description
  - `acknowledged_by`: phases that have seen this failure (same pattern as context entries)
  - `processed`: whether the failure has been addressed in a subsequent iteration
  - `solution`: null until fixed, then a brief description of how it was resolved
  - `orchestrate log-failure --mode ID --desc "..." --context "..."` stores with auto-generated identifier
  - `orchestrate failures` displays with full metadata: identifier, description, context, acknowledged, processed, solution
  - `orchestrate failures --processed IDENTIFIER --solution "description"` marks resolved
  - `_build_failures_context()` updated to show rich entries with solution status
  - RESEARCH phase: `_build_failures_context()` surfaces unsolved failures (solution is null) as investigation targets
  - NEXT phase: unsolved failures considered for additive updates to PROGRAM.md work items and BENCHMARK.md checklist items
  - NEXT phase prompt instructs: "if unsolved failures exist, add them as work items to PROGRAM.md and verification items to BENCHMARK.md"
  - Acceptance: failures.yaml has named rich entries with lifecycle tracking, old flat list format rejected, unsolved failures flow into RESEARCH and NEXT

- **Architect agent prompt: Occam's razor directive** (medium)
  - Scope: `stellars_claude_code_plugins/engine/resources/phases.yaml` architect agent prompts
  - Every architect agent (RESEARCH, PLAN, REVIEW, GC, PLANNING) gets an explicit design simplicity directive
  - Directive: guard against unnecessary complexity - reject designs that introduce parallel tracking files, redundant data structures, or speculative abstractions
  - Occam's razor: the simplest design that solves the problem is the correct one. Fewer files, fewer fields, fewer code paths
  - Architect must challenge: "can this be achieved without adding a new file?", "can this field live in an existing structure?", "does this need a separate tracking mechanism?"
  - NOT a generic "keep it simple" - specific to data design: one canonical location per data entity, no shadow copies, no orphan files
  - Acceptance: all architect agents in phases.yaml include the Occam's razor directive in their prompt

- **Generative naming for context and failure identifiers** (medium)
  - Scope: `stellars_claude_code_plugins/engine/orchestrator.py` `_generate_context_id`
  - Current: regex slugification (`re.sub`) produces mechanical identifiers like `focus_on_x`
  - Target: when context is created by an agent within a phase prompt, the identifier should be generatively created - meaningful, descriptive, not just mechanical word extraction
  - Approach: the orchestrating LLM (Claude) generates the identifier as part of the context creation command, not computed by regex
  - Fallback: slugification remains for non-generative contexts (direct CLI usage)
  - Acceptance: identifiers are more meaningful than regex slugs when created within orchestrated phases

- **PLAN phase prompt mirrors EnterPlanMode design** (medium)
  - Scope: `stellars_claude_code_plugins/engine/resources/phases.yaml` PLAN phase prompt
  - The PLAN phase should follow the same structured approach as Claude Code's formal EnterPlanMode - but without user intervention (autonomous)
  - Phases: (1) explore codebase with agents, (2) design implementation approach, (3) review the plan with agents, (4) write plan to file
  - The PLAN phase prompt should explicitly describe this 4-step process
  - No interactive user approval gate - the gatekeeper validates plan quality instead
  - Acceptance: PLAN phase prompt describes the explore-design-review-write workflow matching EnterPlanMode structure

- **Strict action resolution with documentation** (high)
  - Scope: `orchestrator.py` `_run_auto_actions`, `model.py` `validate_model`, `phases.yaml`
  - All standard `on_complete` actions must be documented in phases.yaml as action definitions with identifier, description, and prompt (for generative) or just identifier and description (for built-in)
  - Engine model loading must verify all action references: every `on_complete` action referenced by a phase must resolve to either a built-in programmatic action OR a generative action defined in workflow.yaml
  - If an action is referenced but not found in either built-in registry or generative actions, validation MUST fail (no fallback, no silent skip)
  - Move `ACTION::` definitions from workflow.yaml to phases.yaml as a root-level `actions:` section - centralizes all phase-related definitions in one file
  - Actions are either: built-in (Python handler in `_AUTO_ACTION_REGISTRY`) or generative (with prompt in the action definition)
  - `model.py` `load_model` / `_build_actions` must read actions from phases.yaml instead of workflow.yaml
  - `validate_model` must check: every phase's `on_complete` action list references only valid actions
  - Tests: unknown action fails validation, known built-in resolves, known generative resolves
  - Acceptance: unknown action reference causes validation error, all existing actions documented and verified

- **Tests for new features** (high)
  - test_context_rich_format: new context entries have message, phase, created, acknowledged_by, processed
  - test_context_identifier_key: entries keyed by identifier not phase name
  - test_context_rejects_legacy: plain string entries raise error, not silently migrated
  - test_context_acknowledgment_on_start: orchestrate start appends phase to acknowledged_by
  - test_context_processed_flag: marking context as processed works
  - test_failures_rich_format: failure entries have identifier, description, context, acknowledged_by, processed, solution
  - test_failures_rejects_legacy: old flat list format raises error
  - test_failures_solution_marking: marking failure as processed with solution works
  - test_hypothesis_autowrite_prompt: verify prompt says append/update
  - test_architect_occam_directive: all architect agents have simplicity directive in prompt
  - Acceptance: >= 175 tests pass

## Exit Conditions

Iterations stop when ALL hold:
- All work items implemented with tests
- make test >= 165
- make lint clean
- orchestrate validate passes
- All 4 dry-runs pass

## Constraints

- Auto-reinstall: patch versions only, never auto-upgrade minor/major
- NO backward compat for context: plain string entries are rejected with error
- NO backward compat for failures: old flat list format is rejected with error
- NO migration code: one format per file, fully committed, no isinstance conversion paths
- No changes to FSM or gate logic
- Occam's razor applies to all design decisions: one canonical location per data entity, no parallel tracking, no speculative abstractions

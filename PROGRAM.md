# Program: Implement All Deferred Features

## Objective

Implement 5 deferred features from prior iterations. Each was raised as a context message, tracked, and deferred with reason. Now implementing all.

## Work Items

- **Resource conflict handling** (high)
  - Scope: `stellars_claude_code_plugins/engine/orchestrator.py` `_ensure_project_resources`
  - When project-local YAML has old format (no `start:` section, has `gates:` key), archive to `.old` and copy fresh from module
  - Detect old format: check if phases.yaml contains `gates:` key at phase level
  - Archive: rename `resources/` to `resources.old.YYYYMMDD/`
  - Copy fresh from bundled module resources
  - Print warning: "Project resources had old format. Archived to resources.old.YYYYMMDD/, fresh copy installed."
  - Add test: verify old-format detection and archive behavior
  - Acceptance: stale project resources auto-refreshed with warning

- **Version check on startup** (medium)
  - Scope: `stellars_claude_code_plugins/engine/orchestrator.py` `main()`
  - On startup, check installed version vs PyPI latest (non-blocking, timeout 2s)
  - Use `importlib.metadata.version()` for installed, `urllib.request` for PyPI JSON API
  - If newer available: print "Update available: {installed} -> {latest}. Run: pip install --upgrade stellars-claude-code-plugins"
  - Cache check result for 24h in `.auto-build-claw/.version_check`
  - Fail silently on network errors (no crash, no delay beyond 2s)
  - Add `--no-version-check` flag to suppress
  - Acceptance: version check works, doesn't add noticeable latency, fails silently

- **Context acknowledgment tracking** (medium)
  - Scope: `stellars_claude_code_plugins/engine/orchestrator.py` context system
  - When context messages are displayed to agents, record which phase saw them
  - Add `acknowledged_by` field to each context entry in context.yaml
  - On `orchestrate start`, mark current phase as having seen the context
  - `orchestrate status` shows which contexts are acknowledged vs pending
  - Acceptance: context.yaml tracks acknowledgment, status shows it

- **Hypothesis refinement** (medium)
  - Scope: phases.yaml HYPOTHESIS phase template, orchestrator hypothesis handling
  - HYPOTHESIS phase start template should instruct agents to READ existing hypotheses.yaml
  - The `{prior_hyp}` template variable already injects prior hypotheses
  - Verify that hypothesis_autowrite action APPENDS/UPDATES rather than overwrites
  - Verify hypothesis_gc action properly archives DONE/REMOVED entries
  - Add to HYPOTHESIS start template: explicit instruction to RATE and REFINE existing, not regenerate
  - Acceptance: hypothesis agents receive prior backlog, rate existing, propose new

- **Tests for all features** (high)
  - test_resource_conflict_detection: old format triggers archive + refresh
  - test_version_check_cache: check result cached for 24h
  - test_context_acknowledgment: context entries track which phases saw them
  - Acceptance: >= 155 tests pass

## Exit Conditions

Iterations stop when ALL hold:
- All 5 features implemented with tests
- make test >= 155
- make lint clean
- orchestrate validate passes
- All 4 dry-runs pass

## Constraints

- Version check must not add > 2s latency (timeout + cache)
- Resource conflict handling must not lose user customizations (archive, not delete)
- No changes to orchestrator FSM or gate logic

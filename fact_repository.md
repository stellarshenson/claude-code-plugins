# Fact Repository - Remaining Features

Verified claims sourced from codebase analysis.
No interpretation - just facts.

## Current data files in .auto-build-claw/

- `state.yaml` - iteration state (type, phase, objective, agents, benchmark scores)
- `log.yaml` - audit trail of all events
- `context.yaml` - user context messages: `{phase_name: message_string}` format
- `context_ack.yaml` - acknowledgment tracking: `{phase_name: [seen_by_phases]}` format (SEPARATE FILE)
- `.version_check` - plain text file containing latest PyPI version string (uses mtime for 24h cache)
- `hypotheses.yaml` - hypothesis backlog: YAML list of `{id, hypothesis, stars}` dicts
- `failures.yaml` - failure catalogue
- `resources/` - project-local YAML resources (preserved across clean)
- Source: orchestrator.py lines 95-101, 1666, 2787

## Context handling facts

- context.yaml format: `{phase_name: message_string}` (flat, no metadata)
- context_ack.yaml format: `{context_phase: [list_of_phases_that_saw_it]}` (separate file)
- context.yaml IS in _CLEAN_PRESERVE (survives clean)
- context_ack.yaml is NOT in _CLEAN_PRESERVE (wiped on clean)
- Context injected into phase instructions as markdown banner with full message text
- cmd_context stores plain string, no timestamp
- Source: orchestrator.py lines 719-733, 1666-1675, 2248-2250

## Version check facts

- _check_version at lines 2776-2808
- Cache: `.auto-build-claw/.version_check` plain text, mtime-based 24h expiry
- PyPI URL: `https://pypi.org/pypi/stellars-claude-code-plugins/json`
- Timeout: 2s via urllib
- Currently prints warning only, no auto-reinstall
- --no-version-check flag pre-parsed in main()
- Source: orchestrator.py lines 2776-2822

## Hypothesis facts

- hypotheses.yaml read by _build_hypothesis_context at line 436
- Expected format: YAML list of `{id, hypothesis, stars}` dicts
- Injected as `{prior_hyp}` template variable
- hypothesis_autowrite prompt says "Write entries to hypotheses.yaml" (ambiguous - write vs append)
- hypothesis_gc prompt says "Move entries with status DONE or REMOVED to archive"
- Source: orchestrator.py lines 435-454, workflow.yaml lines 54-68

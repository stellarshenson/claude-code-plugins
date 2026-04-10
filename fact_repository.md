# Fact Repository - README Rewrite Program

Verified claims sourced from codebase, configuration, and test suite.
No interpretation - just facts.

## Package facts
- Package name: `stellars_claude_code_plugins`, version 0.8.59
- Python >= 3.12, dependencies: pyyaml, transitions
- CLI entry: `orchestrate` command via `stellars_claude_code_plugins.autobuild.orchestrator:main`
- License: MIT
- Source: pyproject.toml

## Engine facts
- 4,407 lines across 4 Python files (fsm.py: 256, model.py: 809, orchestrator.py: 3,315, __init__.py: 27)
- Engine ships default resources: app.yaml, phases.yaml, workflow.yaml
- Plugins override with their own resources YAML files
- Source: `wc -l stellars_claude_code_plugins/engine/*.py`

## Test facts
- 212 tests collected across 3 test files + conftest
- test_fsm.py, test_model.py, test_orchestrator.py
- Source: `pytest --co -q` output, 2026-04-03

## Plugin facts: autobuild
- 3 skills: autobuild (main orchestrator), program-writer, benchmark-writer
- Registered in `.claude-plugin/plugin.json`, category: development
- 5 workflow types from workflow.yaml: FULL (8 phases, depends_on PLANNING), GC (5 phases), HOTFIX (3 phases), FAST (6 phases), PLANNING (4 phases, non-independent)
- FULL phase sequence: RESEARCH -> HYPOTHESIS -> PLAN -> IMPLEMENT -> TEST -> REVIEW -> RECORD -> NEXT
- Features: hypothesis tracking with lifecycle (new/dismissed/processed/deferred), failure context, programmatic gates at phase boundaries, readback + gatekeeper per phase, stop conditions per workflow, safety cap (default 20), --continue and --restart flags
- Source: workflow.yaml, orchestrator.py, autobuild/skills/autobuild/SKILL.md

## Plugin facts: devils-advocate
- 4 skills: setup, evaluate, iterate, run
- Registered in `.claude-plugin/plugin.json`, category: documentation
- Risk scoring: Likelihood x Impact (Fibonacci 1-8 scale), max risk 64
- Score per concern: 0-100%, Residual = risk x (1 - score)
- Document score = sum of residuals (minimize)
- Artefacts: devils_advocate.md (persona + scorecards), fact_repository.md (verified claims), versioned corrections
- Source: devils-advocate/README.md, devils-advocate/skills/*/SKILL.md

## Marketplace facts
- Marketplace file: `.claude-plugin/marketplace.json`
- 2 plugins: autobuild (v1.0.0), devils-advocate (v1.0.0)
- Install command: `/plugin marketplace add stellarshenson/claude-code-plugins`
- Source: .claude-plugin/marketplace.json

## Makefile facts
- Targets: install, test, lint, format, build, publish, clean, requirements, upgrade, create_environment, remove_environment, preflight, help
- `make install` creates venv, installs deps, editable install, bumps version
- `make test` runs pytest with coverage
- `make lint` runs ruff format --check + ruff check
- `make publish` builds + twine upload
- Source: Makefile

## Documentation facts
- Medium article: "Your AI Agent Will Cut Corners. Here's How to Stop It."
- docs/medium/ contains article drafts and SVG diagrams (11 SVGs)
- references/ contains 5 research papers on multi-agent systems, LLM reasoning
- Source: docs/medium/, references/

## Current README deficiencies
- Claims 115 tests (actual: 212)
- Architecture section only shows autobuild directory
- No devils-advocate plugin documentation
- No explanation of orchestration engine concept
- No marketplace installation instructions
- Missing workflow types (only implies full)
- Development section stale test count
- Source: comparison of README.md vs actual codebase state

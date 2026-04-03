# Program: README Rewrite

## Objective

Rewrite the repository README.md to accurately represent the project's current state (v0.8.59, 212 tests, 2 plugins, 10 skills). The README must clearly communicate what the project is, what problems it solves, how the two plugins work, and how to use them. A developer encountering this repo for the first time should understand the value proposition within the first 3 paragraphs.

## Current State

The existing README.md is outdated:
- Claims 115 tests (actual: 212)
- Architecture section only shows auto-build-claw, omits devils-advocate
- No explanation of the core concept (YAML-driven orchestration engine with FSM, gates, multi-agent)
- No description of devils-advocate plugin capabilities
- No plugin marketplace installation concept
- Missing workflow types for auto-build-claw (full, gc, hotfix, fast, planning)
- No mention of hypothesis tracking, failure context, programmatic gates
- Development section has stale test count

## Iteration Targets

- **Iteration 1**: Core content - problem statement (value-first), plugin descriptions with usage examples, install instructions
- **Iteration 2**: Architecture section, building a new plugin, cross-consistency verification (all paths and commands valid)
- **Iteration 3**: Polish - flow optimization, accuracy verification against codebase, length check

## Work Items

- **Section: Header and badges** (low)
  - Keep existing badges (GitHub Actions, PyPI, downloads, Python, KOLOMOLO)
  - Update the opening description to clearly state what this is
  - Keep the existing TIP callout about YAML configuration

- **Section: What it solves** (high, iteration 1)
  - The opening paragraph MUST answer "what does this do for me?" before any technical explanation
  - First 3 paragraphs: problem -> solution concept -> how to get started
  - Technical architecture comes AFTER the reader understands the value
  - Explain the core problem: AI agents cut corners, lose context, skip verification
  - Frame as pull-based enforcement - the engine pulls the agent through structured phases rather than relying on self-discipline
  - Reference the Medium article

- **Section: Plugins overview** (high, iteration 1)
  - Table of both plugins with concise descriptions
  - auto-build-claw: autonomous build iteration orchestrator with multi-agent review
  - devils-advocate: critical document analysis with persona-driven risk scoring

- **Section: auto-build-claw plugin** (high, iteration 1)
  - Lead with value proposition before technical details
  - Concept: structured multi-iteration development cycles with quality enforcement
  - Show workflow types (full, gc, hotfix, fast, planning) in a table
  - Mention key features briefly: hypothesis catalogue, failure context, programmatic gates, dual gates per phase
  - Show 3 skills: auto-build-claw (main), program-writer, benchmark-writer
  - 1-2 usage examples
  - Link to auto-build-claw/README.md for full details (phase lifecycle, agent architecture)
  - The repo README is a landing page, not a reference manual

- **Section: devils-advocate plugin** (high, iteration 1)
  - Lead with value proposition before technical details
  - Concept: systematic critical analysis from the perspective of the toughest audience
  - Show the 4 skills: setup, evaluate, iterate, run
  - Mention risk scoring concept briefly (Fibonacci scale, residual minimization)
  - Mention artefacts produced: persona, fact repository, versioned corrections
  - 1-2 usage examples
  - Link to devils-advocate/README.md for full details (scoring formula, artefact format)

- **Section: Architecture** (medium, iteration 2)
  - Show the shared engine structure (fsm.py, model.py, orchestrator.py)
  - Show BOTH plugin directories with their structure
  - Explain that plugins are pure YAML configuration, engine handles all execution
  - Include the marketplace registration structure
  - Every file path shown MUST exist on disk

- **Section: Building a new plugin** (medium, iteration 2)
  - Keep existing content showing the thin Python entrypoint
  - Mention the 4 YAML resource files needed
  - Reference marketplace registration

- **Section: Install and usage** (medium, iteration 1)
  - pip install for the engine
  - Plugin marketplace command for Claude Code integration
  - CLI standalone usage examples
  - Every command shown must be a valid orchestrate subcommand or plugin slash command

- **Section: Development** (low, iteration 3)
  - Update test count to 212
  - Keep Makefile targets accurate

- **Audit existing content** (medium, iteration 3)
  - Verify every preserved section is still accurate
  - Cross-check all file paths, commands, and examples against actual codebase

## Constraints

- README must follow modus primaris: flowing narrative, not bullet-heavy reference
- No emojis
- Professional technical tone
- Specific numbers and facts, no fluff
- GitHub alert callouts where appropriate (TIP, NOTE, IMPORTANT)
- Target length: under 250 lines (current: 110, expanded but not bloated)
- ASCII typography: no em-dashes, no arrow symbols (use ->)
- Escape dollar signs with backslash
- Plugin sections provide concept + differentiators + usage, link to plugin READMEs for depth

## Exit Conditions

- All work items addressed
- Test count accurate (212)
- Both plugins documented with skills listed
- Architecture shows both plugins
- Usage examples for both plugins
- Every file path and command in README verified against codebase
- make lint clean

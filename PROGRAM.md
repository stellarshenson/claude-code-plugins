# Program: Model Introspection CLI (orchestrate info)

## Objective

Add `orchestrate info` command to query the model programmatically. Currently the only introspection is `validate` (pass/fail) and `--dry-run` (phase list). Engineers need to query specific workflows, phases, agents, and gates for debugging, testing, and verifying the start/execution/end lifecycle structure. The info command makes the model queryable.

## Work Items

- **Add cmd_info to orchestrator.py** (high)
  - Scope: `stellars_claude_code_plugins/engine/orchestrator.py`
  - 5 query flags: `--workflows`, `--workflow <cli_name>`, `--phases`, `--phase <name>`, `--agents`
  - Structured text output suitable for grep and human reading
  - Reads from `_MODEL` (already initialized by main)
  - Add `info` subparser in `_build_cli_parser`, `cmd_info` in cmds dict
  - Acceptance: `orchestrate info --phases` lists all 11 phases with lifecycle info

- **Add TestCmdInfo tests** (high)
  - Scope: `tests/test_orchestrator.py`
  - 7+ tests using `auto_build_claw_resources` fixture
  - Tests verify: all workflows listed, workflow detail shows phases, all phases listed, phase detail shows start/execution/end agents, agents grouped by phase
  - Structure compliance test: every phase has readback in start, gatekeeper in end
  - Agent count test: execution agent counts match expected per phase
  - Acceptance: all tests pass, structure compliance verified programmatically

## Exit Conditions

Iterations stop when ALL hold:
- `orchestrate info --phases` lists all 11 phases
- `orchestrate info --phase FULL::RESEARCH` shows readback, 3 execution agents, gatekeeper
- `orchestrate info --agents` lists all agents grouped by phase
- All tests pass (>= 150)
- make lint clean

## Outstanding Context Messages (from prior iterations)

These were raised during earlier iterations and must be addressed or explicitly deferred:

- **Version check on startup** (context from iter 16 PLAN): Check if newer version of stellars-claude-code-plugins available on PyPI, warn user. Status: DEFERRED to separate iteration - requires network access during CLI startup which adds latency
- **Auto-reinstall in skill** (context from iter 16 PLAN): Auto-reinstall if newer version detected. Status: DEFERRED - coupled with version check
- **Context acknowledgment** (context from iter 16 TEST): Agents should acknowledge context messages. Status: DEFERRED to separate iteration - requires changes to agent spawning protocol
- **Hypothesis refinement** (context from iter 16 TEST): Hypothesis agents should refine existing backlog, not generate from scratch. Status: DEFERRED - requires hypothesis persistence changes
- **Resource conflict handling** (context from iter 18 TEST): When project-local YAML resources have old format, archive them and copy fresh from module with warning. Status: DEFERRED to separate iteration - requires format version detection logic

## Constraints

- Additive only - no existing code modified
- Output is plain text, not JSON (human-readable)
- Tests use real auto_build_claw_resources fixture (not mocks)

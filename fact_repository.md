# Fact Repository - Agent Lifecycle Architecture

Verified claims sourced from codebase, PROGRAM.md, and user input.
No interpretation - just facts.

## User-provided facts
- The correct FSM lifecycle pattern is: phase entry (on_start), phase execution (execution), phase end (on_end) where phase end predicates transition
- Agents like contrarian/optimist/pessimist/scientist are EXECUTION agents, not end gates
- The gatekeeper is the only true end-gate component
- Workflow architect wants harmony and consistency in definitions
- Source: user input, 2026-04-02

## Codebase facts - phases.yaml structure
- 7 phases have agents under `gates.on_end.agents`: FULL::RESEARCH (3), FULL::HYPOTHESIS (4), PLAN (3), TEST (1), REVIEW (4), PLANNING::RESEARCH (3), PLANNING::PLAN (1)
- 4 phases have NO agents: IMPLEMENT, RECORD, NEXT, GC::PLAN
- NO phase has a top-level `agents` key - all agents are under `gates.on_end.agents`
- Every phase has `gates.on_start.readback` (comprehension gate)
- Every phase has `gates.on_end.gatekeeper` (completion gate)
- shared_gates section has `on_skip` with gatekeeper_skip and gatekeeper_force_skip
- Source: stellars_claude_code_plugins/engine/resources/phases.yaml

## Codebase facts - model.py agent extraction
- `_build_agents_and_gates` receives phases raw dict (line 173)
- Line 207: first tries phase-level `section.get("agents", [])` (backward compat)
- Lines 214-215: if `on_end` has `agents` key, those OVERRIDE phase-level agents
- Gate keys built as `f"{phase_key}::{gate_type}"` (e.g., FULL::RESEARCH::readback)
- Lifecycle map: on_start -> "start", on_end -> "end", on_skip -> "skip"
- `_PHASE_RESERVED_KEYS = {"shared_gates"}` - skipped during phase building
- `_build_phases` skips `gates` key: `k != "gates"` filter at line 167
- Source: stellars_claude_code_plugins/engine/model.py

## Codebase facts - orchestrator.py agent usage
- PHASE_AGENTS stores flat name lists: `{phase: [a.name for ...]}` (line 131-134)
- `_build_agent_instructions` renders agent prompts into `{agents_instructions}` template var (line 299)
- This template var is injected into the START template (line 449) - agents described during phase START
- `_validate_end_inputs` checks `--agents` flag against PHASE_AGENTS on END (line 1670-1687)
- Missing agents on END = error, incomplete agents = error
- Source: stellars_claude_code_plugins/engine/orchestrator.py

## Codebase facts - test fixtures
- conftest.py minimal fixture: agents under `gates.on_end.agents` (lines 66-68)
- test_orchestrator.py TestGenerativeActionDispatch: agents under `gates.on_end.agents`
- Source: tests/conftest.py, tests/test_orchestrator.py

## Critical observation
- model.py line 207 already has backward compat for phase-level agents: `agent_list = section.get("agents", [])`
- Line 214-215 OVERRIDES with on_end agents if present
- This means moving agents to phase level requires REVERSING the priority: phase-level agents should be primary, on_end agents should be fallback
- Source: model.py lines 207, 214-215

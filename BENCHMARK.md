# Benchmark: Agent Lifecycle Architecture

## Score

**Direction**: MINIMIZE (target: 0)

```
score = unchecked_items + yaml_harmony_residual + model_clarity_residual + lifecycle_residual + migration_residual + test_coverage_residual + validation_residual
```

- `yaml_harmony_residual` = 10 - yaml harmony grade (Section 5, graded 0-10)
- `model_clarity_residual` = 10 - model clarity grade (Section 6, graded 0-10)
- `lifecycle_residual` = 10 - lifecycle consistency grade (Section 7, graded 0-10)
- `migration_residual` = 10 - migration completeness grade (Section 8, graded 0-10)
- `test_coverage_residual` = 10 - test coverage grade (Section 9, graded 0-10)
- `validation_residual` = 10 - validation quality grade (Section 10, graded 0-10)

Maximum possible score: ~30 checklist items + 60 graded residual = ~90. Target: < 10.

## Evaluation

1. Read phases.yaml, model.py, orchestrator.py, and all test files
2. Verify each [ ] item against the actual code - quote specific lines
3. Grade all 6 fuzzy scales (0-10) using the anchored rubrics
4. Run `make test`, `make lint`, `orchestrate validate`, all 4 dry-runs
5. EDIT this file with updated marks and grades
6. UPDATE the Iteration Log below
7. Report composite score

---

## Section 1: YAML Structure

- [x] Zero `gates:` wrappers in phases.yaml (old structure completely removed)
  > Evidence: `grep '^\s+gates:' phases.yaml` returns 0 matches. Only `shared_gates:` at top level (line 52).
- [x] Every phase with agents has three lifecycle sections: `start`, `execution`, `end`
  > Evidence: FULL::RESEARCH, FULL::HYPOTHESIS, PLAN, TEST, REVIEW, PLANNING::RESEARCH, PLANNING::PLAN all have start/execution/end dicts.
- [x] Every phase without agents has two lifecycle sections: `start`, `end`
  > Evidence: IMPLEMENT, RECORD, NEXT, GC::PLAN have start+end but exec=False (no execution section or empty).
- [x] `start.agents` contains readback agent for every phase
  > Evidence: all 11 phases have start=['readback'] confirmed by YAML parse.
- [x] `execution.agents` contains work agents for 7 phases: FULL::RESEARCH (3), FULL::HYPOTHESIS (4), PLAN (3), TEST (1), REVIEW (4), PLANNING::RESEARCH (3), PLANNING::PLAN (1)
  > Evidence: `load_model()` returns agents for exactly these 7 keys with correct counts.
- [x] `end.agents` contains gatekeeper agent for every phase
  > Evidence: all 11 phases have end=['gatekeeper'] confirmed by YAML parse.
- [x] shared_gates section uses `skip` key (not `on_skip`)
  > Evidence: `grep 'on_skip' phases.yaml` returns 0 matches. shared_gates.skip has gatekeeper_skip and gatekeeper_force_skip.
- [x] Guardian YAML anchor `&guardian_checklist` / `*guardian_checklist` survives the restructure
  > Evidence: line 436: `checklist: &guardian_checklist |`, line 775: `checklist: *guardian_checklist`.
- [x] All agent prompts, names, display_names identical to before (content unchanged, only structure changed)
  > Evidence: all agent names, display_names, and prompt content verified in phases.yaml. No content diffs - only structural relocation.
- [x] Harmonious schema: start, execution, and end all use `agents` list with `name` and `prompt`
  > Evidence: every lifecycle section uses `agents:` list with `name:` and `prompt:` keys. Consistent across all 11 phases.

## Section 1b: Per-Phase Compliance

Every single phase must be verified individually against the start/execution/end schema.

**Phases with execution agents:**
- [x] FULL::RESEARCH: start.agents=[readback], execution.agents=[researcher,architect,product_manager], end.agents=[gatekeeper]
- [x] FULL::HYPOTHESIS: start.agents=[readback], execution.agents=[contrarian,optimist,pessimist,scientist], end.agents=[gatekeeper]
- [x] PLAN: start.agents=[readback], execution.agents=[architect,critic,guardian], end.agents=[gatekeeper]
- [x] TEST: start.agents=[readback], execution.agents=[benchmark_evaluator], end.agents=[gatekeeper]
- [x] REVIEW: start.agents=[readback], execution.agents=[critic,architect,guardian,forensicist], end.agents=[gatekeeper]
- [x] PLANNING::RESEARCH: start.agents=[readback], execution.agents=[researcher,architect,product_manager], end.agents=[gatekeeper]
- [x] PLANNING::PLAN: start.agents=[readback], execution.agents=[contrarian], end.agents=[gatekeeper]

**Phases without execution agents:**
- [x] IMPLEMENT: start.agents=[readback], NO execution section, end.agents=[gatekeeper]
- [x] RECORD: start.agents=[readback], NO execution section, end.agents=[gatekeeper]
- [x] NEXT: start.agents=[readback], NO execution section, end.agents=[gatekeeper]
- [x] GC::PLAN: start.agents=[readback], NO execution section, end.agents=[gatekeeper]

**Shared gates:**
- [x] shared_gates.skip.gatekeeper_skip: prompt present with required vars
  > Evidence: prompt contains `{phase}`, `{iteration}`, `{itype}`, `{objective}`, `{reason}` (lines 57-75).
- [x] shared_gates.skip.gatekeeper_force_skip: prompt present with required vars
  > Evidence: prompt contains `{phase}`, `{iteration}`, `{completed_phases}`, `{reason}` (lines 79-99).

## Section 1c: Per-Workflow Dry-Run Compliance

Every workflow must pass dry-run with correct agent counts and gate resolution.

- [x] `orchestrate new --type full --dry-run`: 8 phases, readback=yes, gatekeeper=yes for all, correct agent counts (3,4,3,0,1,4,0,0)
  > Evidence: dry-run output shows RESEARCH(3), HYPOTHESIS(4), PLAN(3), IMPLEMENT(none), TEST(1), REVIEW(4), RECORD(none), NEXT(none). All readback=yes, gatekeeper=yes.
- [x] `orchestrate new --type fast --dry-run`: 6 phases (PLAN,IMPLEMENT,TEST,REVIEW,RECORD,NEXT), all gates present
  > Evidence: dry-run output shows 6 phases with correct agents and gates. Model validation: PASS.
- [x] `orchestrate new --type gc --dry-run`: 5 phases (PLAN,IMPLEMENT,TEST,RECORD,NEXT), GC::PLAN resolves correctly
  > Evidence: dry-run shows `PLAN (req) -> agents: architect, critic, guardian [GC::PLAN]`. Cross-phase resolution works: GC::PLAN has no agents, resolves to bare PLAN's agents.
- [x] `orchestrate new --type hotfix --dry-run`: 3 phases (IMPLEMENT,TEST,RECORD), all gates present
  > Evidence: dry-run shows 3 phases: IMPLEMENT, TEST, RECORD. All readback=yes, gatekeeper=yes.

## Section 2: Model Loading

- [x] `_build_agents_and_gates` reads `start.agents` for entry gates (readback -> Gate objects)
  > Evidence: model.py lines 288-303: `start_section.get("agents", [])` builds Gate objects keyed as `PHASE::agent_name`.
- [x] `_build_agents_and_gates` reads `execution.agents` for work agents (-> Agent objects)
  > Evidence: model.py lines 306-312: `execution_section.get("agents", [])` appends to `agent_list` for Agent construction.
- [x] `_build_agents_and_gates` reads `end.agents` for exit gates (gatekeeper -> Gate objects)
  > Evidence: model.py lines 315-339: `end_section.get("agents", [])` builds Gate objects keyed as `PHASE::agent_name`.
- [ ] No `gates` key navigation: old `section.get("gates", {})` pattern removed
  > FAIL: Legacy path still exists at lines 343-365. `section.get("gates")` and `section.get("gates", {}).items()` remain as backward-compat code. The dead filter `if gate_type == "agents": continue` is also present at line 357. Protected by `if not found_new_structure and section.get("gates")` guard - never triggered for new-format YAML, but code remains.
- [ ] No `on_start`/`on_end` strings in _build_agents_and_gates
  > FAIL: Legacy path at lines 345, 354 contains `on_start`, `on_end`, `on_skip` strings in `_LIFECYCLE_MAP` and condition checks. Dead code for new-format YAML but present for backward compat.
- [ ] No `if gate_type == "agents": continue` dead filter
  > FAIL: Line 357: `if gate_type == "agents": continue` exists in the legacy path. Never executed for new-format YAML.
- [x] Gate keys constructed correctly: `PHASE::readback`, `PHASE::gatekeeper` (unchanged from before)
  > Evidence: model.py line 297: `gate_key = f"{phase_key}::{agent_name}"`. Confirmed: GC::PLAN::readback, GC::PLAN::gatekeeper etc.
- [x] Agent dict keys unchanged: still phase names (FULL::RESEARCH, PLAN, etc.)
  > Evidence: `load_model()` returns agents keyed by FULL::RESEARCH, FULL::HYPOTHESIS, PLAN, PLANNING::PLAN, PLANNING::RESEARCH, REVIEW, TEST.
- [x] `_MODEL.agents` populated correctly: 7 phases with correct agent counts
  > Evidence: load_model confirms 7 keys with counts: FULL::RESEARCH(3), FULL::HYPOTHESIS(4), PLAN(3), PLANNING::PLAN(1), PLANNING::RESEARCH(3), REVIEW(4), TEST(1).
- [x] Gate lifecycle metadata correct: `start_gate_types` contains "readback", `end_gate_types` contains "gatekeeper"
  > Evidence: `start_gate_types={'readback'}`, `end_gate_types={'gatekeeper'}`, `skip_gate_types={'gatekeeper_force_skip', 'gatekeeper_skip'}`.
- [x] `_build_phases` extracts templates from `start.template` and `end.template` instead of bare `start`/`end`
  > Evidence: model.py lines 191-198: `start_section.get("template", "")` when `isinstance(start_section, dict)`. Lines 203-208 same for end.
- [x] shared_gates reads from `skip` key (not `on_skip`)
  > Evidence: model.py line 267: iterates `("skip", "on_skip")` but production YAML only has `skip`. `on_skip` path exists for backward compat but is never triggered.

## Section 3: Orchestrator Invariants

- [x] `PHASE_AGENTS` built correctly from `_MODEL.agents` (flat name lists per phase)
  > Evidence: orchestrator.py lines 131-134: `PHASE_AGENTS.update({phase: [a.name for a in agents] for phase, agents in _MODEL.agents.items()})`. Verified: 7 keys with correct agent name lists.
- [x] `_build_agent_instructions` renders agents into `{agents_instructions}` template var
  > Evidence: orchestrator.py lines 299-319: resolves namespaced agent key via `_resolve_agents`, iterates `_MODEL.agents.get(resolved, [])`, formats `### Agent N: DISPLAY_NAME` blocks. Called from `_build_context` at line 449.
- [x] `_validate_end_inputs` checks `--agents` against `PHASE_AGENTS` - unchanged
  > Evidence: orchestrator.py lines 1670-1687: `required_key = _resolve_agents(phase)`, `required_agents = PHASE_AGENTS.get(required_key, [])`, checks missing agents and requires all agents for phases with defined agents.
- [x] GC::PLAN resolves agents via `_resolve_agents` to bare PLAN's agents - still works
  > Evidence: `resolve_phase_key('GC', 'PLAN', agent_keys)` returns `'PLAN'` because GC::PLAN has no agents entry, so resolution falls to bare PLAN which has 3 agents: architect, critic, guardian. Dry-run confirms: `PLAN (req) -> agents: architect, critic, guardian [GC::PLAN]`.
- [x] All 4 dry-runs pass: full, fast, gc, hotfix
  > Evidence: all 4 pass with `--resources-dir stellars_claude_code_plugins/engine/resources`: full (8 phases, correct agent counts 3,4,3,0,1,4,0,0), fast (6 phases), gc (5 phases, GC::PLAN cross-phase OK), hotfix (3 phases). All show `Model validation: PASS`.

## Section 4: Tests and Validation

- [x] All existing tests pass (>= 142)
  > Evidence: `make test` -> `143 passed in 2.55s`. Coverage: model.py 90%, orchestrator.py 43%, fsm.py 94%.
- [x] `make lint` passes clean
  > Evidence: `make lint` -> `5 files already formatted`, `All checks passed!`.
- [x] `orchestrate validate` passes
  > Evidence: `orchestrate --resources-dir stellars_claude_code_plugins/engine/resources validate` -> `Model valid: 0 issues found.` Note: project-local `.auto-build-claw/resources/` copy is stale (old format), producing 11 deprecation warnings when invoked without `--resources-dir`. This is expected behavior - project-local copy was not auto-updated.
- [x] conftest.py minimal fixture: agents at phase level (not under gates.on_end)
  > Evidence: conftest.py lines 44-124: ALPHA/BETA/GAMMA phases use `start:` with `template:`+`agents:`, `execution:` with `agents:`, `end:` with `template:`+`agents:`. Zero `gates:` or `on_end` keys. All agents in `execution.agents`, readback in `start.agents`, gatekeeper in `end.agents`.
- [x] All test_model.py inline YAML fixtures: agents at phase level
  > Evidence: test_model.py inline fixtures at lines 259-284, 326-348, 370-392, 409-436, 458-483: all use start/execution/end structure with agents inline. Only exception is `test_validate_warns_old_gates_structure` which deliberately uses old format to test the deprecation warning.
- [x] test_orchestrator.py TestGenerativeActionDispatch fixture: agents at phase level
  > Evidence: test_orchestrator.py lines 615-644: STEP phase uses `start:` with `template:`+`agents:[readback]`, `execution:` with `agents:[worker]`, `end:` with `template:`+`agents:[gatekeeper]`. Correct new structure.
- [x] New test: validate_model warns when agents found under gates.on_end
  > Evidence: test_model.py lines 398-436: `test_validate_warns_old_gates_structure` creates a LEGACY phase with old `gates: { on_start: { readback }, on_end: { agents, gatekeeper } }` format, asserts `any("gates:" in i and "deprecated" in i.lower() for i in issues)`.
- [ ] Verification: with on_end extraction code removed, all tests pass from phase-level only (no silent fallback)
  > FAIL: Legacy code path (model.py lines 341-365) has NOT been removed. It is guarded by `if not found_new_structure and section.get("gates")` so it is dead code for the current YAML, but still present. No verification step was performed to confirm removal works.

## Section 5: YAML Harmony (0-10 scale)

Does the YAML read as a consistent, harmonious FSM lifecycle definition?

| Score | Description |
|-------|-------------|
| 10 | Every phase reads identically: `start.agents` (entry), `execution.agents` (work), `end.agents` (exit). Harmonious schema - all three use the same `agents` list structure. A reader sees the FSM lifecycle in the YAML itself. No exceptions, no legacy cruft. |
| 9 | Consistent structure across all phases. One minor formatting inconsistency. |
| 8 | Structure clear. Two phases slightly different in whitespace or comment style. |
| 7 | Structure mostly consistent. One phase has agents in unexpected location or missing expected key. |
| 6 | Mixed. Some phases have agents at phase level, some under on_end. Reader confused about canonical location. |
| 5 | Half migrated. Dual locations. Reader must check both places. |
| <=4 | No clear pattern. Agents scattered across locations. |

Baseline: 4/10 - all agents under on_end, no phase-level agents, YAML says "end" for execution data.

Current grade: [10] /10
Residual: [0] (10 - grade)
> Evidence: Every phase reads identically: `start.agents` (readback), `execution.agents` (work agents), `end.agents` (gatekeeper). All 11 phases follow the same schema. Phases without execution agents (IMPLEMENT, RECORD, NEXT, GC::PLAN) simply omit the `execution:` section. The YAML header comment (lines 12-25) documents the structure. `shared_gates.skip` section uses `skip:` key (not `on_skip`). Zero `gates:` wrappers, zero `on_end`, zero `on_start` in production YAML. A reader sees the FSM lifecycle directly in the YAML structure.

## Section 6: Model Clarity (0-10 scale)

Is the model loading code clean, single-path, and self-documenting?

| Score | Description |
|-------|-------------|
| 10 | `_build_agents_and_gates` has one extraction path for agents, one for gates. No conditional branching for "which location." Function name accurately describes what it does. Zero dead code. |
| 9 | Single path. One minor vestige of old logic in a comment. |
| 8 | Single path. One dead variable or unused import from old logic. |
| 7 | Single path but function name misleading (still says "agents_and_gates" when agents come from different source). |
| 6 | Dual path with clear primary/fallback. Reader understands which is canonical. |
| 5 | Dual path, unclear which is primary. |
| <=4 | Spaghetti. Agent extraction logic spread across multiple functions with no clear entry point. |

Baseline: 5/10 - dual path (phase-level fallback, on_end primary), `agents` filter inside gate loop, function name covers both.

Current grade: [7] /10
Residual: [3] (10 - grade)
> Evidence: `_build_agents_and_gates` has a clean primary path (lines 282-339): reads `start.agents` -> Gate objects, `execution.agents` -> Agent objects, `end.agents` -> Gate objects. This is the canonical single path. However, a legacy fallback path remains at lines 341-365 guarded by `if not found_new_structure and section.get("gates")`. The legacy path is dead code for the current YAML (never triggered, `legacy_gate_phases` is empty), but it adds ~25 lines of dual-path complexity. Function name `_build_agents_and_gates` is accurate - it builds both. The `found_new_structure` guard is clear about which path is primary. Deduction: dead code exists as active fallback logic, not just a comment. Grade 7 (migrated but fallback still exists as dead code).

## Section 7: Lifecycle Consistency (0-10 scale)

Does the architecture follow standard FSM lifecycle semantics (entry / execution / exit)?

| Score | Description |
|-------|-------------|
| 10 | Three clear lifecycle points: start (entry), execution (work), end (exit). All use `agents` schema. Every phase follows this pattern. The data structure maps directly to FSM transitions: start predicates entry, execution does work, end predicates transition. |
| 9 | Three lifecycle points clear. One phase is an edge case (e.g., no agents) but handled gracefully. |
| 8 | Lifecycle clear. One ambiguity about where a specific data type belongs. |
| 7 | Lifecycle mostly clear. on_start and on_end well separated. Agents in correct location but some metadata (auto_actions, reject_to) blurs the boundaries. |
| 6 | Two lifecycle points clear (entry/exit). Execution agents exist but not clearly separated from gates. |
| 5 | Entry and exit conflated. Agents co-located with exit gates. |
| <=4 | No lifecycle structure. Everything in one bag. |

Baseline: 5/10 - on_start clear (readback), on_end conflates agents with gatekeeper, no explicit "execution" concept.

Current grade: [10] /10
Residual: [0] (10 - grade)
> Evidence: Three clear lifecycle points fully implemented: `start` (entry - readback validates understanding), `execution` (work - agents do phase-specific work), `end` (exit - gatekeeper validates completion). All use identical `agents:` list schema with `name:` and `prompt:` keys. Every phase follows this pattern: 7 phases have all three sections, 4 phases omit `execution` (no work agents) which is handled gracefully. The data structure maps directly to FSM transitions. Gate lifecycle metadata (`start_gate_types={'readback'}`, `end_gate_types={'gatekeeper'}`, `skip_gate_types={'gatekeeper_skip', 'gatekeeper_force_skip'}`) enables the orchestrator to discover gate names from the model rather than hardcoding them.

## Section 8: Migration Completeness (0-10 scale)

Is the migration fully committed - no dual paths, no silent fallbacks, no half-measures?

| Score | Description |
|-------|-------------|
| 10 | Single source of truth. Old extraction path removed entirely. Validation warns on stale data in wrong location. Every fixture, every inline YAML, every resource file uses new location. Zero code paths exercise old location. |
| 9 | Fully migrated. One test comment references old location but code uses new. |
| 8 | Fully migrated. Validation warning present. One minor dead code remnant. |
| 7 | Migrated but fallback still exists as dead code (never triggered). |
| 6 | Migrated with active fallback. Tests pass but some via fallback path. |
| 5 | Half migrated. Production YAML new, some test fixtures old. |
| <=4 | Incomplete. Mixed locations in production YAML. |

Baseline: 0/10 - all agents in old location, no migration started.

Current grade: [7] /10
Residual: [3] (10 - grade)
> Evidence: Production YAML fully migrated - all 11 phases use start/execution/end. All test fixtures use new structure. Validation warns on old `gates:` structure (test_validate_warns_old_gates_structure confirms). However, the legacy code path in model.py lines 341-365 remains as active backward-compat fallback (dead for current YAML but still executable). No verification step was performed to confirm all tests pass with the legacy path removed. The project-local `.auto-build-claw/resources/` copy is stale (old format) which means the legacy path IS exercised when running `orchestrate validate` without `--resources-dir`. Grade 7: migrated but fallback still exists as dead code, and stale project-local copy means legacy path is not truly dead in all execution contexts.

## Section 9: Test Quality (0-10 scale)

Do the tests verify the new architecture, not just that the system still works?

| Score | Description |
|-------|-------------|
| 10 | Tests explicitly verify: agents loaded from phase level, NOT from on_end. Negative test: agents in on_end triggers validation warning. Verification step documented: old code path removed, tests still pass. GC::PLAN cross-phase resolution tested. |
| 9 | Positive and negative tests present. One cross-phase scenario untested. |
| 8 | Positive tests verify new structure. Negative test present. No cross-phase test. |
| 7 | Tests pass but don't explicitly verify WHERE agents were loaded from. Just that agents exist. |
| 6 | Tests pass. No negative test for old location. Could silently fallback and still pass. |
| 5 | Tests pass but some fixtures still use old location (passing via fallback). |
| <=4 | Tests broken or no coverage for agent loading. |

Baseline: 3/10 - tests pass but all fixtures use old location, no verification of loading path.

Current grade: [8] /10
Residual: [2] (10 - grade)
> Evidence: Tests explicitly verify the new structure: `test_gates_from_start_end` confirms start.agents -> readback Gate, end.agents -> gatekeeper Gate. `test_gate_lifecycle_metadata` verifies `start_gate_types`, `end_gate_types`, `skip_gate_types` populated. `test_shared_gates_from_skip` confirms skip key extraction. `test_agents_loaded_from_phases` verifies agents loaded from phases.yaml execution.agents (FULL::RESEARCH has 3 agents: researcher, architect, product_manager). `test_validate_warns_old_gates_structure` is the negative test - old `gates:` format triggers deprecation warning. All fixtures use new format. Cross-phase resolution (GC::PLAN -> PLAN) verified via dry-run but no dedicated unit test for this specific resolution path. Deduction: no test that removes the legacy code and confirms tests still pass (the verification step is missing).

## Section 10: Validation Quality (0-10 scale)

Does validate_model catch structural problems in the new architecture?

| Score | Description |
|-------|-------------|
| 10 | validate_model checks: agents at phase level (positive), no agents under on_end (warns), agent counts match per phase, agent-gatekeeper cross-references work, FQN format for phase keys with agents. Error messages reference correct location. |
| 9 | All checks present. One error message slightly ambiguous about location. |
| 8 | Positive and negative checks. Error messages correct. One edge case unchecked. |
| 7 | Positive check (agents at phase level). Negative check (on_end warning) present. Messages mostly correct. |
| 6 | Basic validation works. No on_end warning. Messages reference old location. |
| 5 | Validation passes but doesn't specifically check agent location. |
| <=4 | Validation broken or doesn't cover agent structure. |

Baseline: 4/10 - validation works but checks agents via model.agents dict (location-agnostic), no on_end warning, messages reference "agents.yaml" (stale).

Current grade: [8] /10
Residual: [2] (10 - grade)
> Evidence: `validate_model` checks: agents at correct phases (FQN and bare keys verified, lines 621-627), agent mode/name/display_name/prompt validation (lines 630-660), gate required placeholders (lines 740-748), every workflow phase resolves to start AND end gate types (lines 750-782), gate-agent cross-references work (lines 784-806). Deprecated `gates:` structure triggers warning (lines 554-558) - verified by test. Error messages reference `[phases.yaml]` (not stale `agents.yaml`). Gate lifecycle metadata used for validation discovery (lines 753-757) instead of hardcoded gate names. Edge case: if a phase somehow had agents under both new and old format, the old format would not be detected (guarded by `found_new_structure`). FQN format validation for phase keys with agents is not explicitly checked. Deduction: one minor edge case unchecked (dual-format detection), but all practical scenarios covered.

## Completion Conditions

Iterations stop when ANY of these is true:
- [ ] All Section 1-4 items [x] AND all 6 fuzzy grades >= 8
  > NOT MET: 4 items unchecked in Sections 2+4. Two fuzzy grades at 7 (Model Clarity, Migration Completeness).
- [ ] No score improvement for 2 consecutive iterations (plateau)

Additionally ALL must hold:
- [x] make test passes >= 142
  > Evidence: 143 passed in 2.55s
- [x] make lint clean
  > Evidence: `5 files already formatted`, `All checks passed!`
- [x] orchestrate validate passes
  > Evidence: `Model valid: 0 issues found` (with `--resources-dir` pointing to bundled resources)
- [x] All 4 dry-runs pass
  > Evidence: full (8 phases), fast (6 phases), gc (5 phases), hotfix (3 phases) - all pass with correct agents/gates
- [x] Zero agents under gates.on_end in production YAML
  > Evidence: `grep 'on_end' phases.yaml` returns 0 matches in bundled resources
- [x] GC::PLAN agent resolution works
  > Evidence: `resolve_phase_key('GC', 'PLAN', agent_keys)` returns `'PLAN'` with 3 agents: architect, critic, guardian

**Do NOT stop while any condition above is unmet.**

---

## Iteration Log

| Iteration | Date | Score | Unchecked | YAML | Model | Lifecycle | Migration | Tests | Validation | Notes |
|-----------|------|-------|-----------|------|-------|-----------|-----------|-------|------------|-------|
| baseline  | -    | TBD   | (all)     | 4    | 5     | 5         | 0         | 3     | 4          | before any work |
| 1         | 2026-04-02 | **14** | 4     | 10   | 7     | 10        | 7         | 8     | 8          | YAML fully migrated to start/execution/end. 143 tests pass, lint clean, validate 0 issues, all 4 dry-runs pass. Remaining: legacy code path in model.py (3 unchecked items in S2), no verification of legacy removal (1 unchecked in S4). Model Clarity and Migration at 7/10 due to ~25 lines of backward-compat dead code. |

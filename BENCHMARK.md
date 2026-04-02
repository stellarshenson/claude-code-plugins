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

- [ ] Zero `gates:` wrappers in phases.yaml (old structure completely removed)
- [ ] Every phase with agents has three lifecycle sections: `start`, `execution`, `end`
- [ ] Every phase without agents has two lifecycle sections: `start`, `end`
- [ ] `start.agents` contains readback agent for every phase
- [ ] `execution.agents` contains work agents for 7 phases: FULL::RESEARCH (3), FULL::HYPOTHESIS (4), PLAN (3), TEST (1), REVIEW (4), PLANNING::RESEARCH (3), PLANNING::PLAN (1)
- [ ] `end.agents` contains gatekeeper agent for every phase
- [ ] shared_gates section uses `skip` key (not `on_skip`)
- [ ] Guardian YAML anchor `&guardian_checklist` / `*guardian_checklist` survives the restructure
- [ ] All agent prompts, names, display_names identical to before (content unchanged, only structure changed)
- [ ] Harmonious schema: start, execution, and end all use `agents` list with `name` and `prompt`

## Section 2: Model Loading

- [ ] `_build_agents_and_gates` extracts agents from phase-level `section.get("agents", [])` as PRIMARY source
- [ ] No on_end override code: lines with `if lifecycle == "on_end" and "agents" in subsection` are REMOVED
- [ ] Dead code removed: `if gate_type == "agents": continue` filter is GONE
- [ ] Agent dict keys unchanged: still phase names (FULL::RESEARCH, PLAN, etc.)
- [ ] `_MODEL.agents` populated correctly: 7 phases with correct agent counts
- [ ] Gate lifecycle metadata unchanged: `start_gate_types`, `end_gate_types`, `skip_gate_types` same as before

## Section 3: Orchestrator Invariants

- [ ] `PHASE_AGENTS` built correctly from `_MODEL.agents` (flat name lists per phase)
- [ ] `_build_agent_instructions` renders agents into `{agents_instructions}` template var
- [ ] `_validate_end_inputs` checks `--agents` against `PHASE_AGENTS` - unchanged
- [ ] GC::PLAN resolves agents via `_resolve_agents` to bare PLAN's agents - still works
- [ ] All 4 dry-runs pass: full, fast, gc, hotfix

## Section 4: Tests and Validation

- [ ] All existing tests pass (>= 142)
- [ ] `make lint` passes clean
- [ ] `orchestrate validate` passes
- [ ] conftest.py minimal fixture: agents at phase level (not under gates.on_end)
- [ ] All test_model.py inline YAML fixtures: agents at phase level
- [ ] test_orchestrator.py TestGenerativeActionDispatch fixture: agents at phase level
- [ ] New test: validate_model warns when agents found under gates.on_end
- [ ] Verification: with on_end extraction code removed, all tests pass from phase-level only (no silent fallback)

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

Current grade: [ ] /10
Residual: [ ] (10 - grade)

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

Current grade: [ ] /10
Residual: [ ] (10 - grade)

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

Current grade: [ ] /10
Residual: [ ] (10 - grade)

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

Current grade: [ ] /10
Residual: [ ] (10 - grade)

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

Current grade: [ ] /10
Residual: [ ] (10 - grade)

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

Current grade: [ ] /10
Residual: [ ] (10 - grade)

## Completion Conditions

Iterations stop when ANY of these is true:
- [ ] All Section 1-4 items [x] AND all 6 fuzzy grades >= 8
- [ ] No score improvement for 2 consecutive iterations (plateau)

Additionally ALL must hold:
- [ ] make test passes >= 142
- [ ] make lint clean
- [ ] orchestrate validate passes
- [ ] All 4 dry-runs pass
- [ ] Zero agents under gates.on_end in production YAML
- [ ] GC::PLAN agent resolution works

**Do NOT stop while any condition above is unmet.**

---

## Iteration Log

| Iteration | Date | Score | Unchecked | YAML | Model | Lifecycle | Migration | Tests | Validation | Notes |
|-----------|------|-------|-----------|------|-------|-----------|-----------|-------|------------|-------|
| baseline  | -    | TBD   | (all)     | 4    | 5     | 5         | 0         | 3     | 4          | before any work |

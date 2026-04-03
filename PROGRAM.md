# Program: Orchestrator Polish

## Objective

Polish remaining features for the auto-build-claw orchestrator (v0.8.56, 202 tests, score 11).

## Recently Completed (v0.8.56)

- Rich context/failure/hypothesis entries with status+notes lifecycle
- Occam's razor + clarity directives in all architect agents
- Autonomous planning (no EnterPlanMode)
- Actions centralized in phases.yaml, strict validation
- Version check structured YAML, resource conflict detection
- Generative naming, invalid context transitions, gatekeeper MUST enforcement
- Failures migrated to status+notes (Occam 10/10)
- `orchestrate new --continue` flag (preserves data, continues iteration counter)
- SKILL.md updated with session check and --continue documentation

## Pending Work Items

- **Programmatic status gates at phase boundaries** (high)
  - Scope: `orchestrator.py` `cmd_end`, phase completion logic
  - At end of NEXT phase: check `_load_context()` - if any entry has `status == "new"`, FAIL the phase programmatically (not just gatekeeper prompt)
  - At end of HYPOTHESIS phase: check `_load_hypotheses()` - if any entry has `status == "new"`, FAIL programmatically
  - These are hard gates in code, not LLM-dependent. The gatekeeper prompt is the first layer, the code check is the second layer
  - Also check: every non-new entry must have at least one note (notes list not empty)
  - Acceptance: orchestrate end fails with clear error if new items remain unclassified

- **Hypothesis max deferred iterations** (medium)
  - Scope: `orchestrator.py`, `app.yaml` config
  - Add `hypothesis_max_deferred_iterations` config in app.yaml (default: 3)
  - At end of HYPOTHESIS phase: check each `deferred` entry's `iteration_created` vs current iteration
  - If `current_iteration - iteration_created > max`: auto-dismiss with note "exceeded max deferred iterations (N)"
  - Deterministic, no LLM judgment needed
  - Acceptance: deferred hypotheses auto-dismissed after N iterations

- **Workflow stop condition prompt** (medium)
  - Scope: `workflow.yaml` workflow definitions
  - Add `stop_condition` prompt to each workflow (FULL, GC, HOTFIX, FAST)
  - The benchmark is mandatory - there is no workflow execution without it
  - The stop condition is the DEFAULT judgment for when the benchmark doesn't define explicit exit criteria or iteration count
  - Evaluated by Claude in NEXT phase: review score trajectory, decide if progress stalled
  - Example: "If benchmark score unchanged for 2 consecutive iterations despite implementation, stop and report what remains unresolved"
  - Acceptance: stop_condition in workflow.yaml, NEXT phase template references it

- **Residual reduction** (low)
  - Data Integrity 9->10: add interaction test (clean-then-reload-then-verify lifecycle)
  - Test Depth 9->10: same interaction test covers this
  - Code Cleanliness 9->10: align _build_failures_context filter style with context banner filter style

## Exit Conditions

- All pending items implemented or explicitly deferred
- make test >= 205
- make lint clean
- orchestrate validate passes
- Benchmark score < 8

## Constraints

- Occam's razor: no field without a consumer
- Clarity: designs immediately understandable
- Benchmark is mandatory - no workflow runs without it
- Hypotheses are never removed, only status-transitioned (audit trail preserved)

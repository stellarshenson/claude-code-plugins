# Program: Orchestrator Polish

## Objective

Polish remaining features and behavioral improvements for the auto-build-claw orchestrator (v0.8.55, 199 tests).

## Recently Completed (v0.8.55)

- Rich context/failure/hypothesis entries with status+notes lifecycle
- Occam's razor + clarity directives in all architect agents
- Autonomous planning (no EnterPlanMode)
- Actions centralized in phases.yaml, strict validation
- Version check structured YAML, resource conflict detection
- Generative naming via optional identifier parameter
- Context invalid transitions (_VALID_CONTEXT_TRANSITIONS)
- Failures migrated to status+notes (Occam 10/10)
- Gatekeeper enforcement: NEXT zero-new context, HYPOTHESIS notes check, PLAN/IMPLEMENT MUST for context
- `--clean` default changed to False

## Pending Work Items

- **`orchestrate new --continue` flag** (high)
  - Scope: `orchestrator.py` `cmd_new`, argparse, SKILL.md
  - Two distinct intents served by one command:
    - `orchestrate new --type full --objective "..." --iterations 3` = fresh session. Wipes artifacts. Iteration 0.
    - `orchestrate new --continue --type gc --objective "..." --iterations 2` = build on top. Preserves context/failures/hypotheses. Iteration counter continues. Can change type/objective/benchmark.
  - `--continue` means: don't wipe, don't reset counter, update objective+type+benchmark+iterations
  - Without `--continue`: wipe everything, start at iteration 0 (current `--clean` behavior restored for fresh)
  - `cmd_new` implementation: if `--continue`, load existing state, increment iteration block, update fields. If not, clean and initialize.
  - Tests: new with --continue preserves data, new without --continue wipes
  - Acceptance: `orchestrate new --continue` works, skill uses it correctly

- **SKILL.md: continue vs fresh session logic** (high)
  - Scope: SKILL.md in plugin marketplace
  - Before running `orchestrate new`, skill MUST:
    1. Check if `.auto-build-claw/state.yaml` exists
    2. If yes: ask user "Continue existing session (preserves context/failures/hypotheses) or start fresh?"
    3. If continue: `orchestrate new --continue --type <type> --objective "..." --iterations N`
    4. If fresh: `orchestrate new --type <type> --objective "..." --iterations N`
  - Update "How it works" section with continue example
  - Update "Program execution" section with continue example
  - Acceptance: SKILL.md documents both paths, includes state check instruction

- **Planning quality: live verification** (medium)
  - Verify autonomous PLAN produces quality >= 8 (already happening in practice)
  - Evidence: iteration 32 plan had specific files, concrete changes, acceptance criteria
  - Can be closed by evaluating forensic plan output from recent iterations

- **Residual reduction** (medium)
  - Data Integrity 9->10: verify all data survives clean with interaction test
  - Format Commitment 9->10: version check silent migration is acceptable (cache file)
  - Test Depth 9->10: add clean-then-reload interaction test
  - Code Cleanliness 9->10: verify zero stale references

## Exit Conditions

- All pending items implemented or explicitly deferred
- make test >= 199
- make lint clean
- orchestrate validate passes

## Constraints

- Occam's razor: no field without a consumer
- Clarity: designs immediately understandable
- `--continue` is the ONLY way to build on existing iterations
- `orchestrate new` without `--continue` always wipes

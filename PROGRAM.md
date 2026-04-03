# Program: Orchestrator Polish

## Objective

Polish remaining features and behavioral improvements for the auto-build-claw orchestrator (v0.8.53, 196 tests).

## Recently Completed (v0.8.53)

- Rich context entries with status+notes lifecycle (new/acknowledged/dismissed/processed)
- Rich failure entries with identifier keys, lifecycle tracking, solved/unsolved distinction
- Rich hypothesis entries with status+notes (new/dismissed/processed/deferred), gatekeeper enforcement
- Occam's razor + clarity directives in all architect agents
- Autonomous planning (EnterPlanMode removed from all PLAN templates)
- Actions centralized in phases.yaml (moved from workflow.yaml)
- Version check structured YAML with checked_at timestamp
- Resource conflict detection on version upgrade (content comparison + archive)
- Hypothesis autowrite prompt says APPEND not Write

## Pending Work Items

- **Context lifecycle: gatekeeper enforcement** (medium)
  - NEXT gatekeeper should enforce zero `new` context items on exit
  - Invalid status transitions should be rejected (e.g., dismissed -> processed)
  - Gatekeeper should check notes present on every non-new item

- **Hypothesis lifecycle: enforcement and pruning** (medium)
  - Deferred hypotheses should be re-evaluated each HYPOTHESIS phase (no indefinite deferral)
  - When hypothesis is processed, orthogonal alternatives should be dismissed (pruning)
  - Gatekeeper should check notes present on every non-new item
  - Programmatic test for gatekeeper rejection not feasible (gatekeeper is LLM-based)

- **Continue vs fresh session** (high)
  - `orchestrate start` continues existing session (no `new` needed)
  - `orchestrate new` starts fresh (cleans artifacts)
  - Skill must check state.yaml and ask before choosing path
  - Never call `new` when continuing

- **Auto-reinstall on version mismatch** (low)
  - Auto `pip install --upgrade` for patch versions in plugin context
  - Detection: CLAUDECODE env var or plugin invocation

- **Generative naming** (deferred)
  - LLM-generated identifiers instead of regex slugification
  - Slugification works for CLI, generative adds value in orchestrated phases

- **Prompt quality** (medium)
  - RESEARCH template: explicitly instruct failure investigation as root causes
  - Gatekeeper context: MUST for PLAN/IMPLEMENT, keep SHOULD for others

## Exit Conditions

- All pending items implemented or explicitly deferred
- make test >= 196
- make lint clean
- orchestrate validate passes
- All 4 dry-runs pass

## Constraints

- Occam's razor: no field without a consumer, no file without a purpose
- Clarity: designs should be immediately understandable
- No backward compat: legacy formats raise errors
- No migration code: one format per file

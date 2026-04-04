# Program: Session Summary + Duplicate Output Fix

## Objective

Two quick fixes: (1) print session summary on `orchestrate new`, (2) stop creating duplicate output files in phase directories.

## Work Items

### Session Summary

- **Print session summary after new** (high)
  - Scope: `orchestrator.py` cmd_new (L1863), `app.yaml` messages
  - Root cause: cmd_new prints iteration header + phases but no config summary - user has to scroll to remember what they're running
  - Add `session_summary` message template to app.yaml with box-drawing border
  - Print from cmd_new before "To begin" using state dict values
  - Template: objective (50 chars), workflow type + phase count, iterations, benchmark yes/no, fresh/continue
  - Acceptance: `orchestrate new` output contains the summary block
  - Predict: user sees config at a glance

### Duplicate Output Files

- **One output file per phase, no duplication** (high)
  - Scope: `orchestrator.py` _record_phase_outputs (~L2050)
  - Root cause: _record_phase_outputs unconditionally copies output-file content to `output.md` in the phase directory, even when the output-file already IS in the phase directory. Creates two identical files (e.g. research.md + output.md with same content)
  - Fix: only create output.md as fallback when the output-file is NOT already in the phase directory. If it is, the named file IS the output - no copy needed
  - Acceptance: each phase directory has exactly one output file

## Exit Conditions

Stop when benchmark score = 0 or stagnates.

## Constraints

- Minimal code changes
- Message template in app.yaml, not hardcoded

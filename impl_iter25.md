# Implementation - Iteration 25: Failures Redesign

## 13 changes + 7 new tests
1. Renamed _generate_context_id -> _generate_entry_id: PREDICT reusable. VERIFY: cmd_context still works. ROOT_CAUSE_FIXED.
2. Added _load_failures/_save_failures: PREDICT dict-based persistence. VERIFY: round-trip test passes. ROOT_CAUSE_FIXED.
3. Rewrote _append_failure: PREDICT identifier generation. VERIFY: test_failure_identifier_generation passes. ROOT_CAUSE_FIXED.
4. Rewrote _build_failures_context: PREDICT solved/unsolved split. VERIFY: test shows both groups. ROOT_CAUSE_FIXED.
5. Changed _count_iteration_failures return type: PREDICT (fid, entry) tuples. VERIFY: cmd_status works. ROOT_CAUSE_FIXED.
6. Updated cmd_log_failure with --context: PREDICT optional context arg. VERIFY: argparse accepts it. ROOT_CAUSE_FIXED.
7. Rewrote cmd_failures with --processed/--solution: PREDICT lifecycle marking. VERIFY: test_failure_processed_with_solution. ROOT_CAUSE_FIXED.
8-10. Updated cmd_status, _run_summary, cmd_new: PREDICT tuple unpacking. VERIFY: no errors. ROOT_CAUSE_FIXED.
11. Added failures.yaml to _CLEAN_PRESERVE: PREDICT survives clean. VERIFY: test_failures_preserved_on_clean. ROOT_CAUSE_FIXED.
12. Added failure ack in cmd_start: PREDICT phase appended. VERIFY: test_failure_ack_on_start. ROOT_CAUSE_FIXED.
13. Updated argparse: PREDICT new flags. VERIFY: validate passes. ROOT_CAUSE_FIXED.

## Results: 184 tests (was 177), lint clean, validate passes

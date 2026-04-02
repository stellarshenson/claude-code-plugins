# Research - Iteration 25: Failures Redesign

## Current: flat list via _load_yaml_list / _append_yaml_entry
## Target: identifier-keyed dicts with lifecycle fields

## Functions to modify (11 locations):
1. _load_yaml_list (L693) - needs failures-specific loader OR keep generic + add validation layer
2. _append_yaml_entry (L701) - needs failures-specific appender for identifier generation
3. _append_failure (L714) - rewrite to use identifier-keyed dict
4. _build_failures_context (L334) - show rich entries with solved/unsolved distinction
5. _count_iteration_failures (L842) - adapt to dict format
6. cmd_log_failure (L2354) - add --context arg, generate identifier
7. cmd_failures (L2376) - display rich metadata
8. cmd_status failures display (L2071) - show rich metadata
9. _run_summary (L1344) - adapt to dict format
10. cmd_new prior failures (L1447, L1577) - adapt to dict format
11. argparse (L2798) - add --context, --processed, --solution args

## Key decision: failures.yaml should be preserved across --clean
Add "failures.yaml" to _CLEAN_PRESERVE (L875)

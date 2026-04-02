# Hypotheses - Iteration 25: Failures Redesign

## H1: Dedicated _load_failures/_save_failures is cleaner than reusing _load_yaml_list
- **Root cause**: _load_yaml_list returns list[dict]. New format is dict[str, dict]. Using the same loader requires isinstance branching.
- **Prediction**: creating _load_failures/_save_failures (matching _load_context/_save_context pattern) with validation will be cleaner than retrofitting _load_yaml_list. The generic loader stays for log.yaml which remains a list.
- **Evidence**: context refactor in iter-21 created clean _load_context/_save_context pair without touching _load_yaml_list
- **Stars**: 5

## H2: failures.yaml should be added to _CLEAN_PRESERVE
- **Root cause**: failures.yaml is wiped on --clean (not in preserve set). Failure history is valuable across iterations for pattern detection.
- **Prediction**: adding "failures.yaml" to _CLEAN_PRESERVE will preserve failure lifecycle data across `new --clean`. This matches the context.yaml pattern and enables cross-iteration failure tracking.
- **Evidence**: _CLEAN_PRESERVE at L875 only has {"context.yaml"}. Adding failures.yaml is one character change.
- **Stars**: 4

## H3: _generate_context_id can be reused for failure identifiers
- **Root cause**: both context and failures need identifier generation from text
- **Prediction**: renaming to `_generate_entry_id` or simply reusing `_generate_context_id` for failures will avoid code duplication. The function is generic - slugifies any text.
- **Evidence**: _generate_context_id at L749-764 takes message+existing_ids, returns slug. Nothing context-specific in the logic.
- **Stars**: 4

## H4: cmd_start should acknowledge failures alongside context entries
- **Root cause**: S12 says "cmd_start appends current phase to acknowledged_by of every active failure". Currently cmd_start only acks context.
- **Prediction**: adding a parallel ack loop for failures in cmd_start (after the context ack block at L1696-1703) will enable cross-phase failure tracking. Same pattern: iterate failures, append phase to acknowledged_by if not already present.
- **Evidence**: context ack loop at L1696-1703 is exactly the pattern to replicate for failures
- **Stars**: 4

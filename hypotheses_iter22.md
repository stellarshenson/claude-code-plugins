# Hypotheses - Iteration 22: Three Surgical Fixes

## H1: Key validation will catch malformed entries without breaking valid ones
- **Root cause**: _load_context only validates isinstance(entry, dict), not key presence. Entry {color: blue} loads fine.
- **Prediction**: Adding `if "message" not in entry or "phase" not in entry: raise ValueError` will catch malformed entries while all valid entries (which always have message+phase from cmd_context) pass.
- **Evidence**: test_entry_missing_required_field (L1121-1130) confirms dict-without-message loads today. After fix, it should raise.
- **Stars**: 4

## H2: Created timestamp in status will close 2 benchmark items with 1 line
- **Root cause**: cmd_status L2088 extracts msg, phase, ack, processed but not created field.
- **Prediction**: Adding `created = entry.get("created", "?")[:10]` and including it in the format string will close S6 items 121-122 (missing created) and match the benchmark example format.
- **Evidence**: The field exists in every entry created by cmd_context (L2319 `"created": _now()`).
- **Stars**: 3

## H3: Hypothesis prompt change is pure text with zero code risk
- **Root cause**: workflow.yaml L61 says "Write entries" which is ambiguous about append vs overwrite.
- **Prediction**: Changing to "Read existing hypotheses.yaml first. APPEND new entries, UPDATE existing entries by ID. Do NOT overwrite or remove existing entries." will close all 4 S9 items.
- **Evidence**: workflow.yaml is purely consumed by _claude_evaluate as a prompt string. No code path parses the word "Write".
- **Stars**: 3

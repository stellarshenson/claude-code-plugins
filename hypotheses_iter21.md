# Hypotheses - Iteration 21: Rich Context Entries

## H1: Identifier-keyed entries will eliminate silent context overwrite
- **Root cause**: `cmd_context` uses `ctx[phase] = message` (L2249) - phase as key means second message for same phase silently overwrites the first
- **Prediction**: After refactoring to identifier keys, two `orchestrate context --phase PLAN --message "X"` followed by `--message "Y"` will produce TWO entries in context.yaml (different identifiers), both retrievable
- **Evidence**: Current code at L2248-2250 shows `ctx[phase] = message` with no collision check. Users lose prior context on every re-set
- **Stars**: 5

## H2: Consolidating context_ack into context.yaml will fix acknowledgment loss on clean
- **Root cause**: `_CLEAN_PRESERVE = {"context.yaml"}` (L838) but context_ack.yaml is NOT preserved. Every `new --clean` wipes acknowledgment tracking
- **Prediction**: After moving `acknowledged_by` inline to context.yaml entries, acknowledgment data will survive `new --clean` because context.yaml is in the preserve set
- **Evidence**: L838 shows preserve set. L1666-1675 shows context_ack.yaml created outside preserve. `cmd_status` at L2049-2059 reads context_ack.yaml which may not exist after clean
- **Stars**: 5

## H3: Slug truncation at 40 chars will cause collisions on similar messages
- **Root cause**: Messages often share long prefixes ("fix the connector..." "fix the connector alignment...")
- **Prediction**: Truncating slugs to 40 chars without collision suffix room will produce identical keys for semantically different messages. Pre-truncating to 37 chars and reserving 3 chars for `_2`/`_3` suffix will avoid this
- **Evidence**: Scientist agent tested: two 50-char messages sharing first 40 chars produce identical slugs. The `_2` suffix pushes beyond 40-char limit
- **Stars**: 4

## H4: Banner should show message-only to avoid agent instruction dilution
- **Root cause**: Context banner at L1651-1662 injects ALL context entries into phase instructions. Adding metadata (timestamps, acknowledged_by lists) would bloat agent prompts
- **Prediction**: Keeping banner as message-only (current behavior) while showing full metadata only in `orchestrate status` will maintain agent instruction quality. Agents do not need to see timestamps or ack lists - they need the directive
- **Evidence**: Current banner already dumps 4 entries at ~100 words each. Adding 5 metadata fields per entry would approximately double token count with no agent utility
- **Stars**: 5

## H5: Raising error on legacy format is safe because context.yaml is rarely pre-existing
- **Root cause**: Program mandates NO backward compat - old format raises error
- **Prediction**: In practice, very few users will have pre-existing context.yaml files when upgrading, because context is typically set per-iteration and wiped on `new`. The error message "delete context.yaml and start fresh" is acceptable UX
- **Evidence**: context.yaml survives `--clean` but is wiped on `new` without `--clean`. Most users start fresh iterations. The risk of hitting legacy format is low
- **Stars**: 3

## H6: Empty/punctuation-only messages need a fallback identifier
- **Root cause**: Slugification of `"---"` or `"!!!"` produces empty string after `re.sub(r'[^a-z0-9]+', '_', ...).strip('_')`
- **Prediction**: Without a fallback, empty slug would create an empty-string key in context.yaml, breaking YAML structure. Fallback to `"ctx"` with collision suffix produces valid identifiers for all input
- **Evidence**: `re.sub(r'[^a-z0-9]+', '_', '---').strip('_')` returns `""` in Python
- **Stars**: 4

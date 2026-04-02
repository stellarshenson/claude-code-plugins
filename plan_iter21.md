# Plan - Iteration 21: Rich Context Entries

## Scope
ONLY context system. No failures, no Occam directive, no version check.

## Changes (8 steps)
1. Add `_generate_context_id()` helper + `import re`
2. Rewrite `_load_context()` - validate rich format, raise ValueError on legacy
3. Rewrite `cmd_context()` - add/list/clear/processed with identifier keys
4. Rewrite banner injection in `cmd_start()` - message-only banner, inline ack
5. Rewrite context display in `cmd_status()` - no context_ack.yaml
6. Add `--processed` argparse arg
7. Update app.yaml message templates
8. Replace tests - 10 new tests for rich context

## Files
- orchestrator.py (7 functions)
- app.yaml (messages)
- test_orchestrator.py (new TestContextRichEntries)
- conftest.py (fixture keys)

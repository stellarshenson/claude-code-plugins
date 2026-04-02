# Research - Iteration 21: Rich Context Entries

## Focus
Rich context entries (BENCHMARK Sections 2-7) - ONE narrow area for this iteration.

## Key Findings

### Current Context System
- `_load_context()` (L719): returns flat `{phase_name: message_string}` dict
- `_save_context()` (L731): simple YAML dump
- `cmd_context()` (L2212): uses `ctx[phase] = message` - phase is the key
- `context_ack.yaml`: only 2 locations (L1666 in cmd_start, L2049 in cmd_status)
- `_CLEAN_PRESERVE = {"context.yaml"}` - survives clean

### Target Format
```yaml
focus_on_x:
  message: "focus on X"
  phase: "RESEARCH"
  created: "2026-04-02T14:00:00+00:00"
  acknowledged_by: [PLAN, IMPLEMENT]
  processed: false
```

### Functions to Modify
1. `_load_context()` - validate rich format, reject plain strings
2. `_save_context()` - no change needed (writes whatever dict given)
3. `cmd_context()` - generate identifier from message, store phase as attribute
4. `cmd_start()` - remove context_ack.yaml, update acknowledged_by inline
5. `cmd_status()` - remove context_ack.yaml read, display rich metadata

### What NOT to Touch This Iteration
- failures.yaml redesign (iteration 2+)
- Occam directive in phases.yaml (iteration 2+)
- Version check structured YAML (later)
- Auto-reinstall (later)

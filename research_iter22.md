# Research - Iteration 22: Three Surgical Fixes

## Fix 1: _load_context key validation (S5)
- Location: orchestrator.py L732-739
- Current: validates isinstance(entry, dict) but not message/phase keys
- Fix: add check for "message" and "phase" keys after isinstance check

## Fix 2: cmd_status created timestamp (S6)
- Location: orchestrator.py L2088
- Current: `[{cid}] ({p}): {msg[:60]}... ({status}){proc_str}` - no created
- Fix: extract created field, include in display

## Fix 3: hypothesis autowrite prompt (S9)
- Location: workflow.yaml L61
- Current: "Write entries to hypotheses.yaml"
- Fix: change to "Read existing hypotheses.yaml first. APPEND new entries, UPDATE existing by ID. Do NOT overwrite."

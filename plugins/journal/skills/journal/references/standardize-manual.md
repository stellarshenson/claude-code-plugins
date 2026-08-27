# Standardize - manual procedure

The per-entry walk behind `journal-tools standardize --all`. Use it to inspect one subprocess prompt or step through one decision after `--all` logged a `SKIP`; for everything else, run `--all`.


### 1. List repair candidates

```bash
journal-tools standardize .claude/JOURNAL.md --list
```

Emits a JSON array, one object per entry needing repair:

```json
[
  {
    "number": 116,
    "line_start": 27,
    "line_end": 29,
    "word_count": 303,
    "has_extended_marker": false,
    "action_needed": "decide",
    "task_line": "116. **Task - ...** (...): ...<br>",
    "body": "..."
  }
]
```

`action_needed` is one of:
- `drop_marker` - deterministic, no subprocess needed.
- `decide` - subprocess decides EXTENDED vs CONDENSE.
- `condense` - body > extended-max, subprocess must condense (marker may stay).

### 2. Drop spurious markers first (no subprocess needed)

For every entry where `action_needed == "drop_marker"`:

```bash
journal-tools standardize .claude/JOURNAL.md --apply <N> --decision drop-marker
```

Idempotent. Confirm via the CLI's own response: `entry N: dropped [Extended] marker -> now Standard (W words)`.

### 3. Decide-or-condense via ACP subprocess (one per entry)

For every remaining entry (`decide` or `condense`):

**3a. Render the prompt** for entry N:

```bash
journal-tools standardize .claude/JOURNAL.md --prompt <N> > /tmp/standardize-<N>.prompt.txt
```

**3b. Spawn a focused `claude -p` subprocess** with the CLAUDECODE env var stripped (otherwise the SDK enters degraded mode and hangs on file ops - see the `acp` skill's "Critical: Strip CLAUDECODE Env Var" rule). Add `--no-session-persistence` so each one-shot subprocess does not write a JSONL session file under `~/.claude/projects/<slug>/` (these are unresumable single-decision calls — persisting them accumulates one extra file per entry, 17+ per sweep). Try the default model first; on a usage-policy refusal, retry once with `claude-sonnet-4-20250514` (soft landing — Sonnet 4 has a different safety profile and clears benign technical content the default model occasionally flags as policy-violating). Suppress stderr (`2>/dev/null`) so harmless "no stdin data received" warnings don't leak into the decision file:

```bash
# Attempt 1: default model.
env -u CLAUDECODE claude -p "$(cat /tmp/standardize-<N>.prompt.txt)" \
  --output-format text \
  --dangerously-skip-permissions \
  --max-turns 3 \
  --no-session-persistence \
  > /tmp/standardize-<N>.decision.txt 2>/dev/null

# Soft landing: on "violate our Usage Policy" refusal, retry with claude-sonnet-4.
if grep -q "violate our Usage Policy" /tmp/standardize-<N>.decision.txt; then
  env -u CLAUDECODE claude -p "$(cat /tmp/standardize-<N>.prompt.txt)" \
    --output-format text \
    --dangerously-skip-permissions \
    --max-turns 3 \
    --model claude-sonnet-4-20250514 \
    --no-session-persistence \
    > /tmp/standardize-<N>.decision.txt 2>/dev/null
fi
```

The subprocess reads only the prompt (system header + per-entry user template), makes one decision, returns one of three exact formats:

- `DECISION: EXTENDED` - mark the entry as Extended, no body change.
- `DECISION: CONDENSE\nBODY:\n<rewritten body>` - replace the Result paragraph.
- `DECISION: DROP_MARKER` - shouldn't fire here (step 2 already handled these) but accept it idempotently.

**3c. Parse the subprocess output** and apply via the CLI:

For `DECISION: EXTENDED`:
```bash
journal-tools standardize .claude/JOURNAL.md --apply <N> --decision extended
```

For `DECISION: CONDENSE`:
```bash
# Strip the leading "DECISION: CONDENSE\nBODY:\n" header from the subprocess output
sed -n '/^BODY:$/,$p' /tmp/standardize-<N>.decision.txt | tail -n +2 > /tmp/standardize-<N>.body.txt
journal-tools standardize .claude/JOURNAL.md --apply <N> --decision condense --body-file /tmp/standardize-<N>.body.txt
```

The CLI auto-drops the `[Extended]` marker if the condensed body falls below `EXTENDED_MIN` (150 words) - no second call needed.

For `DECISION: DROP_MARKER`:
```bash
journal-tools standardize .claude/JOURNAL.md --apply <N> --decision drop-marker
```

### 4. Validate

After every entry is processed, re-run the validator:

```bash
journal-tools check .claude/JOURNAL.md
```

Exit 0 + no warnings = clean. Any remaining warning = the subprocess produced a non-compliant body (e.g. condensed but still > 150 without marker). Do not retry by hand (Rules below) - re-run `--all`; if it still fails, surface the entry's body + the subprocess's last response to the user.

### 5. Report

Print one line per entry processed:
```
entry N: <decision> -> now Standard|Extended (W words)
```

Plus the post-validation summary line from `journal-tools check`.


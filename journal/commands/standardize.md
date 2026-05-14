---
description: Standardize oversized / mis-marked journal entries via the ACP repair loop. For each offender, the shipped prompt YAML drives a focused `claude -p` subprocess that decides Extended vs Condense vs Drop-marker; the CLI applies the verdict. Triggers - "standardize journal", "fix journal entry tiers", "repair journal".
allowed-tools: [Read, Write, Edit, Bash, Glob]
argument-hint: "(optional) <journal-path>  -- default .claude/JOURNAL.md"
---

# Standardize Journal Entries

The `journal-tools check` validator flags three failure modes:

- **Standard over target** - body > 150 words, no `[Extended]` marker → either depth is real (add marker) or body is inflated (condense).
- **Extended over max** - body > 400 words even with `[Extended]` marker → condense, marker can stay.
- **Spurious marker** - `[Extended]` present but body < 150 words → marker is false advertising → drop it.

This command repairs all three via the ACP companion-process pattern: a shipped prompt YAML at `src/stellars_claude_code_plugins/journal/prompts/standardize.yaml` defines the per-entry rubric, the CLI renders it for one entry at a time, a fresh `claude -p` subprocess returns a structured decision, the CLI applies it. Run after a `journal-tools check` reports warnings; never inline-edit oversized entries by hand.

## Pre-flight install (MANDATORY, no asking)

```bash
python3 -c "import stellars_claude_code_plugins" 2>/dev/null || python3 -m pip install --user --upgrade stellars-claude-code-plugins
```

No-op when the package is importable. Never skip.

## Procedure

Default journal path is `.claude/JOURNAL.md` unless an argument is passed.

### 1. List repair candidates

```bash
uv run journal-tools standardize .claude/JOURNAL.md --list
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
uv run journal-tools standardize .claude/JOURNAL.md --apply <N> --decision drop-marker
```

Idempotent. Confirm via the CLI's own response: `entry N: dropped [Extended] marker -> now Standard (W words)`.

### 3. Decide-or-condense via ACP subprocess (one per entry)

For every remaining entry (`decide` or `condense`):

**3a. Render the prompt** for entry N:

```bash
uv run journal-tools standardize .claude/JOURNAL.md --prompt <N> > /tmp/standardize-<N>.prompt.txt
```

**3b. Spawn a focused `claude -p` subprocess** with the CLAUDECODE env var stripped (otherwise the SDK enters degraded mode and hangs on file ops - see the `acp` skill's "Critical: Strip CLAUDECODE Env Var" rule):

```bash
env -u CLAUDECODE claude -p "$(cat /tmp/standardize-<N>.prompt.txt)" \
  --output-format text \
  --dangerously-skip-permissions \
  --max-turns 3 \
  > /tmp/standardize-<N>.decision.txt
```

The subprocess reads only the prompt (system header + per-entry user template), makes one decision, returns one of three exact formats:

- `DECISION: EXTENDED` - mark the entry as Extended, no body change.
- `DECISION: CONDENSE\nBODY:\n<rewritten body>` - replace the Result paragraph.
- `DECISION: DROP_MARKER` - shouldn't fire here (step 2 already handled these) but accept it idempotently.

**3c. Parse the subprocess output** and apply via the CLI:

For `DECISION: EXTENDED`:
```bash
uv run journal-tools standardize .claude/JOURNAL.md --apply <N> --decision extended
```

For `DECISION: CONDENSE`:
```bash
# Strip the leading "DECISION: CONDENSE\nBODY:\n" header from the subprocess output
sed -n '/^BODY:$/,$p' /tmp/standardize-<N>.decision.txt | tail -n +2 > /tmp/standardize-<N>.body.txt
uv run journal-tools standardize .claude/JOURNAL.md --apply <N> --decision condense --body-file /tmp/standardize-<N>.body.txt
```

The CLI auto-drops the `[Extended]` marker if the condensed body falls below `EXTENDED_MIN` (150 words) - no second call needed.

For `DECISION: DROP_MARKER`:
```bash
uv run journal-tools standardize .claude/JOURNAL.md --apply <N> --decision drop-marker
```

### 4. Validate

After every entry is processed, re-run the validator:

```bash
uv run journal-tools check .claude/JOURNAL.md
```

Exit 0 + no warnings = clean. Any remaining warning = the subprocess produced a non-compliant body (e.g. condensed but still > 150 without marker). Loop step 3 on the offending entry, max 2 retries; if still failing, surface the entry's body + the subprocess's last response to the user.

### 5. Report

Print one line per entry processed:
```
entry N: <decision> -> now Standard|Extended (W words)
```

Plus the post-validation summary line from `journal-tools check`.

## Rules

- ALL subprocess calls MUST use `env -u CLAUDECODE` (or set `env={k: v for k, v in os.environ.items() if k != "CLAUDECODE"}` in Python). Without this the SDK hangs on file ops. Reference: `acp` skill, "Critical: Strip CLAUDECODE Env Var".
- ONE subprocess per entry. Do not bundle multiple entries into a single `claude -p` prompt - it defeats the focused-decision principle and lets the subprocess drift across boundaries.
- Subprocess `--max-turns 3` cap. The task is a single decision; more turns means the subprocess is wandering.
- Never edit `JOURNAL.md` directly during standardize - only via `journal-tools standardize --apply`. The CLI handles the structural rewrite (preserving indentation, joining body onto a single Result line, dropping the marker when condense pushes back into Standard).
- Numbering is preserved. The standardize flow never touches entry numbers; if you need renumbering, that is `journal-tools sort`, run BEFORE standardize.
- The shipped `prompts/standardize.yaml` is the single source of truth for the decision rubric. Bump the YAML's `version:` field on breaking changes and the CLI refuses unknown versions - no silent prompt drift between wheel + slash command versions.

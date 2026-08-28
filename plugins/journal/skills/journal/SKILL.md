---
name: journal
description: Manage `.claude/JOURNAL.md`. **Auto-triggers on ANY mention of "journal"** — questions about the journal, entry format, word-count tiers, archiving, the `/journal:*` commands, or the `journal-tools` CLI. Also triggers on "update journal", "add journal entry", "log this", "journal this", "record this in the journal", "create journal", "init journal", "archive journal", "prune journal", or after finishing substantive work that should be logged. Enforces format, append-only, continuous numbering, word-count tiers, post-write `journal-tools check` validation, archiving.
allowed-tools: [Read, Write, Edit, Bash, Glob]
---

# Journal

Project audit trail. Every substantive task = one entry. Append at END. Last entry = newest.

## Pre-flight install (MANDATORY - run every session, no asking)

Always run this single line BEFORE invoking any `journal-tools` subcommand. The upgrade always runs - a stale-but-importable install is exactly the failure this gate prevents, and the reinstall also repairs a stale shim on PATH whose package is uninstalled in the active Python:

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
OLDER=$(printf '%s\n%s\n' "$LIB" "$PLUG" | sort -V | head -1)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && [ "$OLDER" = "$LIB" ] && { echo "STALE: library $LIB older than plugin $PLUG - refusing to run on an outdated CLI; re-run the upgrade"; exit 1; }
echo "toolkit $LIB"
```

Ships `journal-tools` CLI (`check`, `sort`, `archive`, `standardize`). Verify: `journal-tools --help`. Never skip this step. Never ask the user whether to install - just run the line.

## Commands

| Command | Use |
|---------|-----|
| `/journal:create` | INIT empty journal. Backfill from conversation context. Refuses if file exists. |
| `/journal:update` | DEFAULT. Append new entry. Extend last entry only if same task, pre-release. |
| `/journal:archive` | Move old entries to `JOURNAL_ARCHIVE.md`. Triggered >40 entries. |
| `/journal:standardize` | REPAIR. For each entry the validator warned on (over Standard target, over Extended max, or false-advertising marker), a focused `claude -p` subprocess decides Extended vs Condense vs Drop-marker; the CLI applies it. Use after `journal-tools check` reports word-count warnings - never inline-edit oversized entries by hand. |
| `/journal:article` | EXTRACT. For entries over the Extended max (>400 words), pull the depth into a standalone article under `docs/` and condense the entry to a Standard-tier summary linking to the article. Asks the user for title / location / scope / summary length via AskUserQuestion. |

No ambiguity. `create` = scaffold once. `update` = every write after. `standardize` = repair word-count drift via an ACP subprocess driven by the shipped `prompts/standardize.yaml`. `article` = extract over-max depth into a `docs/` article and slim the entry.

## Append-only

Never insert between entries. Never renumber. Never reorder. Numbers monotonic.

After write: read last 5 lines. Confirm match.

## Entry format

Standard (default):
```
<N>. **Task - <short depiction>** (v1.2.3): one-line summary<br>
    **Result**: dense paragraph - problem, solution, files/libraries, verification
```

Extended (opt-in via `[Extended]` marker after `Task`):
```
<N>. **Task [Extended] - <short depiction>** (v1.2.3): one-line summary<br>
    **Result**: 250-400 word paragraph
```

Short (opt-in via `[Short]` marker after `Task` - intentionally brief, < 50 words):
```
<N>. **Task [Short] - <short depiction>** (v1.2.3): one-line summary<br>
    **Result**: 20-40 word note. Use for typo fixes, one-line URL updates,
    trivial maintenance that has no architectural rationale to preserve.
```

Version tag only if project versioned (`package.json` / `pyproject.toml` / `Cargo.toml`).

## Levels

| Level | Marker | Words | When |
|-------|--------|-------|------|
| Short | `[Short]` | 1 - 49 | Trivial: typo fix, one-line URL bump, dependency pin, dead-link patch. No WHY to preserve - the diff IS the WHY |
| Standard | none | 50 - 150 | DEFAULT. Feature, fix, multi-file change, investigation |
| Extended | `[Extended]` | 150 - 400 | ONLY: architectural decision, platform migration, multi-iteration debug, novel algorithm |
| Article | (entry links to `docs/`) | > 400 | Move depth into a standalone `docs/<slug>.md` via `/journal:article N`; entry becomes a Standard summary + link |

Match the user's own summary length. 5-bullet summary -> not 400 words. "I touched lots of files" = not Extended. "This was hard" = not Extended.

Marker is mandatory for Extended. Without it `journal-tools check` warns over 150 words and tells you to either condense or add `[Extended]`. With it the gate stays silent in the [150, 400] band but warns under 150 (false advertising) or over 400 (too long for any tier - use `/journal:article` to extract).

`[Short]` mirror logic: mandatory when intentionally under 50 words. Without it, the validator warns "too terse" and tells you to add the marker OR expand. With it, the gate stays silent under 50 but warns if the body reaches 50+ (false advertising - the body sits in Standard tier already, drop the marker).

## Style

Telegram-style terse language by default - drop articles ("the" / "a"), drop copulas ("is" / "are" / "was"), dense paragraphs over multi-bullet structure, file paths and function names in backticks.

**Always keep the WHY.** Future-you (or another agent) reading this entry six months later needs to understand WHY the implementation or work was done, not just WHAT was done. The code itself shows what changed; the journal carries the rationale that does NOT survive in `git log` / `git blame` / the file content. Specifically keep:

- **Trigger** - what prompted the work (a user report, a forensic finding, a CI failure, a benchmark regression)
- **Why this approach over alternatives** - the design decision and its constraint ("picked A over B because of C")
- **Gotchas / non-obvious constraints** - things that surprised you and will surprise the next reader if undocumented
- **Cause-and-effect chains** - "X required Y because Z" - so the reader can reconstruct the reasoning when the code alone is insufficient

Drop ceremonial connective tissue, hedging, restated obvious context, and bullet-list expansions of single ideas. Keep load-bearing reasoning - especially the trigger and the why-this-approach.

Bad (verbose, no reasoning): "I made some changes to the validator and updated some files."

Bad (terse but no WHY): "Validator updated. Tests green."

Good (terse + WHY preserved): "Validator now honours `[Extended]` marker - silent in [150, 400] band when marked, warns otherwise. **Trigger**: agents kept inflating Standard entries to ~200 words to clear word-count warnings instead of either condensing or marking intent; the gate became noise. **Why this design**: the marker makes intent explicit and machine-checkable in one regex; alternative was raising STANDARD_TARGET globally, rejected because it would erode the discipline that pushes Standard entries to the 70-120 sweet spot."

## What to log

Log: document changes, features, investigations with findings, diagram work.

Skip: git commits, file cleanup, version bumps, maintenance. State: "Not logging to journal: <reason>".

## Examples

See `references/examples.md`. Standard + Extended with before/after.

## CLI tools

`journal-tools` - deterministic validation, archive, sort. Pure string parsing. Run BEFORE commit.

### check

```bash
journal-tools check .claude/JOURNAL.md
```

Validates:
- continuous numbering, ascending order
- format: title present after `Task -`
- **Result-marker structure**: every Task must be followed by exactly ONE `**Result**:` line. Task without a Result marker -> error. Task with two or more Result markers -> error. Orphan `**Result**:` line outside any Task -> error (these were silently absorbed by the previous parser, masking malformed entries where the Task line was missing or mistyped)
- word count tiers (Standard target = warning over, Extended band silent in [150, 400], over both = warning)

Length over target = warning only (never error). Structural violations (duplicate number, out-of-order, missing title, missing/duplicate/orphan Result marker) = error. Exit 0 = no errors, 1 = errors.

MANDATORY after write. Word-count warning → condense if cheap. Format error → fix before commit.

### archive

```bash
journal-tools archive .claude/JOURNAL.md
```

Moves entries to `JOURNAL_ARCHIVE.md` when count exceeds threshold (default 40). Keeps last 20 in main. Appends to existing archive. Maintains continuous numbering.

Flags: `--keep-last N`, `--threshold N`, `--archive-path PATH`.

Prefer over manual edit.

### sort

```bash
journal-tools sort .claude/JOURNAL.md --dry-run
```

Re-numbers sequentially. Fixes gaps (1,2,5 → 1,2,3) and ordering. `--dry-run` previews. Omit to write in-place. Flag: `--start-from N`.

### standardize

```bash
# The happy path - every candidate end-to-end in one invocation.
journal-tools standardize --all .claude/JOURNAL.md

# Manual steps, for debugging one entry:
# 1. List entries needing repair (JSON array on stdout).
journal-tools standardize --list .claude/JOURNAL.md

# 2. Render the ACP prompt for one offender so a `claude -p` subprocess can decide.
journal-tools standardize --prompt N .claude/JOURNAL.md

# 3. Write the subprocess's decision back to the file.
journal-tools standardize --apply N --decision extended|condense|drop-marker [--body-file F] .claude/JOURNAL.md
```

Repairs the three failure modes `check` warns on: Standard over 150 words (decide Extended marker vs condense), Extended over 400 words (condense), spurious `[Extended]` marker on a sub-150-word body (drop marker). The CLI orchestrates; the actual editing decision comes from a focused `claude -p` subprocess driven by the shipped `prompts/standardize.yaml`. Use after `journal-tools check` reports warnings - never inline-edit oversized entries by hand. `--all` chains the three modes for every offender in one pass; `/journal:standardize` is its wrapper.

Flags: `--standard-target N` (default 150), `--extended-max N` (default 400). Same thresholds `check` uses.

## Archiving

Trigger: >40 entries OR user requests. Prefer `journal-tools archive`.

1. Move older entries to `.claude/JOURNAL_ARCHIVE.md`
2. Keep last 20 in main
3. Add link at top: `**Note**: Entries 1-N archived to JOURNAL_ARCHIVE.md`
4. Maintain continuous numbering. NEVER reset.

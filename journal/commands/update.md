---
description: Append a new entry to .claude/JOURNAL.md (or extend the last entry if same work unit). Triggers - "update journal", "add journal entry", "log this", "add entry", "journal this", "record this in the journal".
allowed-tools: [Read, Edit, Write, Bash, Glob]
argument-hint: "(optional) work description - otherwise infer from context"
---

# Update Journal

Default behaviour: **append a new entry** describing the work just finished. If the work continues the most recent entry's task, extend that entry instead of creating a duplicate.

If `.claude/JOURNAL.md` does not exist, STOP and tell the user to run `/journal:create` first.

## Decision: append vs extend

Read the last entry first, then decide:

- **Append (default)** — the finished work is a distinct task from the last entry. Different scope, different goal, different commit.
- **Extend** — the finished work is the same task as the last entry (follow-up fix, additional files touched, scope grew mid-stream) AND that entry has not been released/committed with a version stamp locking it. Edit the last entry's Result paragraph in place.

When unsure, append. A new entry is always safe; extending the wrong entry muddies history.

## Steps

1. **Read the last entry** in `.claude/JOURNAL.md`. Note its number and task.
2. **Classify** the work just done as append or extend per the rule above.
3. **Pick the level.** Default = **Standard** (~70-120 words). Use **Extended (~250-350 words) ONLY when the user explicitly asks** ("extended entry", "full detail", "long form") or when the work is an architectural decision / platform migration / multi-iteration debug / novel algorithm. "I touched lots of files" is NOT a reason to go Extended. Match the user's own summary length — do not inflate.
4. **Write the entry** in modus-secundis rich-paragraph format:
   ```
   <N>. **Task - <short depiction>** (vX.Y.Z): one-line summary<br>
       **Result**: dense paragraph covering problem, solution, files/libraries touched, verification
   ```
   - APPEND path: `N = last + 1`, add at the end of the file
   - EXTEND path: reuse the last entry's number and Task line, rewrite the Result paragraph to cover the full enlarged scope
5. **Version tag** if the project is versioned (`package.json` / `pyproject.toml` / `Cargo.toml`). Use the current/just-released version.
6. **Verify** by reading the last 10 lines of the file.
7. **Validate via CLI** — run `uv run journal-tools check .claude/JOURNAL.md`. Exit 0 = clean. Errors (>400 words, numbering gap, format drift) → fix and re-run.

## CLI helpers (shared)

- `uv run journal-tools check .claude/JOURNAL.md` — format / numbering / word-count validation (MANDATORY after write)
- `uv run journal-tools sort .claude/JOURNAL.md --dry-run` — preview re-numbering if gaps or reorders exist
- `uv run journal-tools archive .claude/JOURNAL.md` — archive once >40 entries (use `/journal:archive`)

## Rules

- APPEND-ONLY file — new entries go at the end, never inserted between old ones.
- Numbers increase monotonically; never renumber or reorder.
- Never log git commits/pushes, trivial cleanup, or conversational queries as their own entries.
- Never invent work. Only what actually happened.
- To edit an OLDER entry (not the last), state the entry number explicitly — otherwise assume last-entry scope.

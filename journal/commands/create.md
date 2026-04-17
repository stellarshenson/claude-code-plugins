---
description: Initialise a new .claude/JOURNAL.md from the current conversation's context. Triggers - "create journal", "init journal", "start journal", "new journal". If journal already exists, use /journal:update.
allowed-tools: [Read, Write, Bash, Glob]
argument-hint: "(optional) extra context about what to log"
---

# Create / Initialise Journal

**Use ONLY when `.claude/JOURNAL.md` does not yet exist** (or the user explicitly asks to re-initialise it). This command scaffolds the file and backfills entries from the current conversation.

If `.claude/JOURNAL.md` already exists, STOP and tell the user to use `/journal:update` instead. Do not overwrite.

## Steps

1. **Check existence.** If `.claude/JOURNAL.md` exists, stop and redirect to `/journal:update`.
2. **Scan context.** Walk the current conversation from the start. List every substantive work unit (feature, refactor, bug fix, doc set, design decision). Skip: git ops, file moves/renames with no content change, conversational queries.
3. **Write the header.**
   ```
   # Claude Code Journal

   This journal tracks substantive work on documents, diagrams, and documentation content.

   ---
   ```
4. **Backfill entries.** One entry per work unit, numbered from `1`, in chronological order. Use **Standard format by default** (~70-120 words, modus-secundis rich-paragraph style — see `journal/skills/journal/references/examples.md`). Use **Extended (~250-350 words) ONLY when the user explicitly asks** ("extended entry", "full detail", "long form") or when the work unit is an architectural decision / platform migration / multi-iteration debug / novel algorithm. "I touched lots of files" is NOT a reason to go Extended.
5. **Version tag.** If the project has `package.json` / `pyproject.toml` / `Cargo.toml` etc., include the current version in each entry: `**Task - <depiction>** (v1.2.3):`.
6. **Verify.** Read the last 10 lines of the file to confirm structure.
7. **Validate via CLI** — run `uv run journal-tools check .claude/JOURNAL.md`. Exit 0 = clean. Errors → fix and re-run.

## CLI helpers

- `uv run journal-tools check .claude/JOURNAL.md` — format / numbering / word-count validation (MANDATORY after write)
- `uv run journal-tools sort .claude/JOURNAL.md --dry-run` — preview re-numbering if gaps or reorders exist
- `uv run journal-tools archive .claude/JOURNAL.md` — archive once >40 entries (use `/journal:archive`)

## Rules

- Never create the file if it already exists. No second chances, no merge. Use `/journal:update` for adding to an existing journal.
- Do NOT invent work. Only log what actually happened in the visible conversation context.
- Entry numbers start at `1` and increment by `1`.
- Append-only: the most recent work is always the last entry.
- Do NOT log: git commits/pushes, trivial file cleanup, conversational queries.

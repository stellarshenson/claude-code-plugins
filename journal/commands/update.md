---
description: Append a new entry to `.claude/JOURNAL.md` OR update the last entry in place when the new work is a small continuation of it. Triggers - "update journal", "add journal entry", "log this", "add entry", "journal this", "record this in the journal".
allowed-tools: [Read, Edit, Write, Bash, Glob]
argument-hint: "(optional) work description - otherwise infer from context"
---

# Update Journal

> **ROLE**: appends a new entry to an existing `.claude/JOURNAL.md` (or edits the last entry in place for small continuations). Default write command — use for 99% of journal writes.
> **NOT FOR**: first-time setup — use `/journal:create` if the file doesn't exist yet.

Two modes: **append** (default) or **update the last entry in place** (narrow case).

If `.claude/JOURNAL.md` does not exist, stop and tell the user to run `/journal:create` first.

## Mode decision

Read the last entry. Then pick:

- **Append** (default) — new work is a distinct task from the last entry. New number, new paragraph.
- **Update** — new work is a small continuation of the last entry (a minor follow-up fix, one more file touched, a clarification). Edit the last entry's Result paragraph in place **without inflating it**. Add one short sentence at most. If the continuation would push the entry past Standard length (120 words), **append a new entry instead**.

Never update an entry that already carries a release version stamp — always append after a release.

When in doubt: append.

## Format

Default is **Standard** (~70-120 words, one dense paragraph). Use **Extended** (~250-350 words) only when the user asks ("extended entry", "full detail") or the work is an architectural decision / platform migration / multi-iteration debug.

### Standard example

```markdown
4. **Task - CI URL fixes** (v0.1.9): Fixed malformed GitHub URLs in package.json causing CI check-npm failure<br>
   **Result**: CI `check-release.yml` workflow failed at check-npm step with ValueError
   indicating repository.url doesn't match cloned repository. Found three malformed URLs
   in `package.json`: homepage had trailing `.git`, bugs.url had `.git/issues` path, and
   repository.url had duplicate `.git.git` suffix. Fixed all three URLs - homepage and
   bugs.url now use bare GitHub URLs without `.git`, repository.url uses single `.git`
   suffix. Build and tests pass.
```

Shape: one-line Task summary after `**Task - <depiction>** (vX.Y.Z):`, then `**Result**:` as a single information-dense paragraph — problem → solution → files/libraries → verification. No sub-headers, no bullet lists.

### Extended example

Same shape but ~250-350 words with more depth on rationale, tradeoffs, alternatives considered, or multi-stage debugging. Full worked examples in `journal/skills/journal/references/examples.md` (sections "Normal Entry" and "Extended Entry").

## Steps

1. Read the last entry. Note its number and task.
2. Pick mode (append vs update) per the rule above.
3. Write the entry in Standard format. Match the user's own summary length; never inflate.
4. Version tag if the project is versioned (`pyproject.toml` / `package.json` / `Cargo.toml`).
5. **MUST run `uv run journal-tools check .claude/JOURNAL.md`** after writing. Exit 0 = clean. Any error → fix and re-run. This step is not optional.
6. Verify by reading the last 10 lines.

## CLI tools (mandatory)

Every write MUST be validated via the CLI. These tools exist for a reason — use them:

- `uv run journal-tools check .claude/JOURNAL.md` — MANDATORY post-write validation (format, numbering, word-count tiers)
- `uv run journal-tools sort .claude/JOURNAL.md --dry-run` — preview re-numbering if gaps or reorders detected
- `uv run journal-tools archive .claude/JOURNAL.md` — archive once >40 entries (use `/journal:archive`)

## Rules

- Append-only file. Numbers monotonic. Never renumber or reorder.
- Never update a version-stamped entry — always append after a release.
- Never invent work.
- Never log git commits, trivial cleanup, or conversational queries.
- To edit an older entry, state its number explicitly.
- `journal-tools check` is not a suggestion. Run it every time.

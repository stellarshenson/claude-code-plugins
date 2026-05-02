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

**Extended entries MUST be marked** with `[Extended]` after `Task` so the validator and downstream readers know the wider word band is intentional, not drift. Without the marker, `journal-tools check` warns over 150 words and tells you to either condense or add the marker.

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

Shape: one-line Task summary after `**Task - <depiction>** (vX.Y.Z):`, then `**Result**:` as a single information-dense paragraph - problem -> solution -> files/libraries -> verification. No sub-headers, no bullet lists.

### Extended example (mark with `[Extended]`)

```markdown
115. **Task [Extended] - Autobuild Iter 1+2 for grounding improvements** (v1.0.40): ran `orchestrate new --type fast` against the PROGRAM.md / BENCHMARK.md pair built in the previous session<br>
    **Result**: 250-400 word paragraph with depth on rationale, tradeoffs, alternatives considered, or multi-stage debugging.
```

Marker rules:
- `[Extended]` lives BETWEEN `Task` and the dash, inside the bold span: `**Task [Extended] - <depiction>**`
- Case-insensitive (`[extended]`, `[EXTENDED]` also work) but prefer the canonical capitalisation
- Validator silent for marked entries in the [150, 400] word band
- Validator warns if marked but body < 150 (false advertising) - drop the marker or expand
- Validator warns if over 400 even with the marker - condense

### Style

Telegram-style terse language by default. Drop articles, drop copulas, file paths and function names in backticks. **Always keep the WHY** - the trigger that prompted the work, the why-this-approach over alternatives, gotchas, cause-and-effect chains. Future-you reading the entry six months later needs the rationale; the code itself only shows what changed. See `skills/journal/SKILL.md` Style section for the full rule set with examples.

Full worked examples in `journal/skills/journal/references/examples.md`.

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

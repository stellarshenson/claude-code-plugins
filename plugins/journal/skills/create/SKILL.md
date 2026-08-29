---
name: create
description: Initialise a new `.claude/JOURNAL.md` for a project that doesn't have one yet. Strictly first-time setup — refuses if the file exists. Triggers - "create journal", "init journal", "start journal", "new journal".
allowed-tools: [Read, Write, Bash, Glob]
---

# Create Journal

> **ROLE**: creates and sets up a brand-new `.claude/JOURNAL.md`. One-time init.
> **NOT FOR**: adding entries to an existing journal — use `/journal:update`.

**Init-only.** Scaffolds a new `.claude/JOURNAL.md` and backfills entries from the current conversation.

If `.claude/JOURNAL.md` already exists, stop and tell the user to use `/journal:update` instead. Never overwrite.

## Steps

1. Check the file does not exist. If it does, refuse and redirect to `/journal:update`.
2. Scan the current conversation for substantive work units (feature, refactor, bug fix, doc set, design decision). Skip git ops, trivial cleanup, conversational queries.
3. Write the header:
   ```
   # Claude Code Journal

   This journal tracks substantive work on documents, diagrams, and documentation content.

   ---
   ```
4. Append one entry per work unit, numbered from `1`, in chronological order. Use **Standard format** (50-150 words, see example below).
5. Version tag per entry if the project is versioned (`pyproject.toml` / `package.json` / `Cargo.toml`).
6. **Pre-flight install (MANDATORY, no asking)**:

   ```bash
   python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
   LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
   PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
   OLDER=$(printf '%s\n%s\n' "$LIB" "$PLUG" | sort -V | head -1)
   [ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && [ "$OLDER" = "$LIB" ] && { echo "STALE: library $LIB older than plugin $PLUG - refusing to run on an outdated CLI; re-run the upgrade"; exit 1; }
   echo "toolkit $LIB"
   ```

   The upgrade always runs - a stale-but-importable install is exactly the failure this gate prevents, and the reinstall also repairs a stale shim on PATH whose package is uninstalled in the active Python.

7. **MUST run `journal-tools check .claude/JOURNAL.md`**. Exit 0 = clean. Any error → fix and re-run. Not optional.

## Format

Default is **Standard** (50-150 words, one dense paragraph). Use **Extended** (150-400 words, marked `[Extended]` after `Task`) only when the user asks ("extended entry", "full detail") or the work unit is an architectural decision / platform migration / multi-iteration debug.

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

## CLI tools (mandatory)

- `journal-tools check .claude/JOURNAL.md` — MANDATORY post-write validation. Not optional.
- `journal-tools sort .claude/JOURNAL.md --dry-run` — preview re-numbering if gaps are detected.
- `journal-tools archive .claude/JOURNAL.md` — archive once >40 entries (use `/journal:archive`).

## Rules

- Refuse if the file already exists. No merge, no overwrite. Use `/journal:update` to add to an existing journal.
- Never invent work. Only log what actually happened in the visible conversation.
- Entry numbers start at `1` and increment by `1`.
- Never log git commits, trivial cleanup, or conversational queries.
- `journal-tools check` is not a suggestion. Run it every time.

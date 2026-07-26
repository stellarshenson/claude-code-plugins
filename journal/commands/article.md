---
description: Extract an oversized journal entry's depth into a standalone article in `docs/` and condense the entry to a Standard-tier summary that links to the article. Use when `journal-tools check` warns that an entry is over the Extended max (400 words) - even Extended caps there, and the rationale belongs in a dedicated doc. Triggers - "create article from entry", "extract journal entry to article", "make article from journal".
allowed-tools: [Read, Write, Edit, Bash, Glob, AskUserQuestion]
argument-hint: "<entry-number>  -- entry to extract into an article"
---

# Extract a journal entry into a `docs/` article

The journal carries the WHY of substantive work; the `[Extended]` tier covers 150-400 words for architectural decisions, multi-thread releases, multi-iteration debugs. **Anything over 400 words means the entry has outgrown the journal.** Move the depth into a standalone article under the project's `docs/` folder and leave the journal entry as a Standard-tier summary that links to the article. The journal stays scannable; the rationale stays preserved; cross-document links keep the audit trail intact.

This command guides the extraction. It does NOT inline-edit the journal - the entry rewrite goes through `/journal:update` so the append-only + word-count contracts stay enforced.

## Pre-flight install (MANDATORY, no asking)

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && echo "STALE: library $LIB != plugin $PLUG - CLI may lack flags this skill uses; re-run the upgrade" || echo "toolkit $LIB"
```

## Procedure

### 1. Locate and inspect the entry

```bash
uv run journal-tools standardize .claude/JOURNAL.md --prompt <N>
```

This renders the per-entry prompt (full task line + body). Read the body and identify the load-bearing rationale segments - those are the article's natural structure.

If no entry number is provided, find candidates by running `--list` and filtering for `action_needed == "condense"` - that's the validator's signal for over-Extended-max entries.

### 2. Ask the user (MANDATORY)

Use `AskUserQuestion` to confirm the extraction and gather article metadata. **Do not skip this** - the user owns the title, scope, and location decisions:

| Question | Default suggestion |
|----------|---------------------|
| Create article from entry N? | yes |
| Article title? | derive a punchy title from the entry's `**Task -` line (drop the verb noise, keep the noun phrase) |
| Article filename + location? | `docs/<kebab-case-slug>.md` derived from the title; warn if the path exists and offer a date suffix |
| Article scope? | "verbatim copy of the entry body, lightly edited for flow" / "rewritten with section headers and code blocks" / "I'll pick - prompt me again at draft time" |
| Condense the journal entry to a summary + link? | yes (recommended; the point of extraction is to slim the entry) |
| Target summary length? | Standard (70-150 words) |

Bundle these into 2-4 `AskUserQuestion` calls (no more than 4 questions per call per the tool's cap). Use multi-select where natural.

### 3. Create the article

Write `docs/<slug>.md` with:

- H1 title (the user-approved title)
- A 1-2 sentence opening that states the article's purpose
- The entry body, restructured per the user's scope choice
- A footer line linking back to the journal entry: `*Originally from `.claude/JOURNAL.md` entry <N>.*`

Follow the workspace markdown standards (no em-dashes, no emoji, no triples, ASCII arrows, escape `$` as `\$`). Cross-link to other `docs/` articles or source files where relevant.

### 4. Rewrite the journal entry via `/journal:update`

**NEVER edit `.claude/JOURNAL.md` directly.** Invoke `/journal:update` and tell it the rewrite is an in-place update to entry N (not a new append). The new body should be Standard-tier (70-150 words) and end with a link to the article:

```
See [`docs/<slug>.md`](docs/<slug>.md) for the full architectural rationale.
```

Match the user's approved summary length. Preserve the entry's `(vX.Y.Z)` version stamp if present.

### 5. Validate

```bash
uv run journal-tools check .claude/JOURNAL.md
```

The over-Extended-max warning on entry N should be gone. If new warnings appear (e.g. the condensed body fell below the Standard min 50), address them via `/journal:update` again.

### 6. Report

Print one summary line:

```
entry N: extracted -> docs/<slug>.md (X words article + Y words journal summary)
```

## Rules

- One entry per invocation. If multiple entries are over-max, run the command per-entry; bulk extraction is intentionally not supported because each article needs its own title + scope decision.
- The article path is always under `docs/` (workspace convention). Refuse if the project has no `docs/` folder - prompt the user to create it first.
- Never delete the journal entry. The entry must remain in `.claude/JOURNAL.md` (append-only contract); only its body shrinks.
- Never silently overwrite an existing article file. Warn the user, suggest a date suffix or alternate slug.
- The journal entry's `**Task -` line stays unchanged (the audit trail keeps the original task name); only the `**Result**:` body is rewritten.
- If the user declines the extraction, exit cleanly - the validator warning persists as a nudge, no harm done.

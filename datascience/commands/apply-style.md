---
description: Apply rich output styling standards to a notebook or script - fix colors, formatting, print patterns
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Skill, TaskCreate, TaskUpdate]
argument-hint: "path to file to fix, e.g. 'notebooks/01-kj-analysis.py'"
---

# Apply Rich Styling

Read a file and fix all rich output to comply with the `datascience:notebook-standards` skill's `references/rich-output.md` palette.

## Toolchain gate (MANDATORY - run before anything else)

Run this first, every session, before any other work. The upgrade always runs; a version mismatch blocks.

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && { echo "STALE: library $LIB != plugin $PLUG - refusing to run on a mismatched CLI; re-run the upgrade"; exit 1; }
echo "toolkit $LIB"
```

Both branches exit non-zero and neither is advisory: an absent library (`FATAL`) and a version mismatch (`STALE`). A mismatch means the CLI is not the one this file was written against, so its documented flags and rules are unverified. Report the line and stop; do not work around it.

## Reference to apply

**`datascience:notebook-standards` → `references/rich-output.md`** - read this resource first. It is the single source of truth for colors, patterns, and rules. Do NOT duplicate its content here.

## What to fix

1. **Multiple individual prints -> single multiline print** (per skill)
2. **Wrong colors -> semantic colors** (per skill palette)
3. **Missing rich formatting** - plain `print()` for structured output -> `rprint()`
4. **Import fixes** - missing `from rich import print as rprint`
5. **Hex colors -> standard named colors** (per skill)

## Process

1. Read the file
2. Read `notebook-standards` `references/rich-output.md` for current palette and rules
3. List violations with line numbers
4. Apply fixes directly
5. Show summary

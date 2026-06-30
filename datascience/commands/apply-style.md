---
description: Apply rich output styling standards to a notebook or script - fix colors, formatting, print patterns
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Skill]
argument-hint: "path to file to fix, e.g. 'notebooks/01-kj-analysis.py'"
---

# Apply Rich Styling

Read a file and fix all rich output to comply with the `datascience:notebook-standards` skill's `references/rich-output.md` palette.

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

---
description: Fix a notebook to comply with all standards - structure, styling, progress bars, header narrative
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, Skill]
argument-hint: "path to notebook to fix, e.g. 'notebooks/01-kj-analysis.py'"
---

# Fix Notebook

Read a notebook and fix it to comply with ALL standards. Applies changes directly.

## Skills to apply

- **`datascience:notebook-standards`** - section order, GPU selection, imports, config cell
- **`datascience:rich-output`** - color palette, print patterns, table styles
- **`datascience:progressbars`** - progress bar style and patterns

Read these skills before making changes. They are the source of truth. Do NOT hardcode colors or patterns in this command - always defer to the skills.

## What to fix

### Header
- Missing or sparse header -> add/rewrite with flowing prose (purpose, method, rationale)
- Bullet-list-only approach -> numbered phases with "what AND why"
- Missing output description -> add `**Output**: <artifacts>`

### Structure (per `notebook-standards` skill)
- GPU after imports -> move before
- Scattered imports -> consolidate into single cell with autoreload
- Missing reproducibility -> add set_seed
- Scattered config -> consolidate with rich summary at end
- No markdown headers before sections -> add them

### Styling (per `rich-output` skill)
- Plain `print()` for structured output -> `rprint()` with semantic colors from the skill
- Wrong colors -> fix per the skill's palette
- Multiple individual `rprint()` -> single multiline call
- Missing config summary -> add styled block
- Hex colors -> standard named colors

### Progress bars (per `progressbars` skill)
- Long loops without progress -> add wrapper per chosen style
- Progress bar in same cell as setup -> split cells
- Broken bars (N-1, disappeared, frozen) -> apply fixes from skill

### Dependencies
- `rich` not in pyproject.toml -> add
- `tqdm`/`ipywidgets` missing if used -> add

## Critical questions (ASK before proceeding)

- **Author**: "What are your initials and full name?" (if not obvious from existing header)
- **Header rewrite**: show proposed narrative, ask "Does this capture the purpose?"
- **Import consolidation**: if scattered across 5+ cells, show proposed consolidated cell
- **Progress bar style**: "Classic (tqdm) or modern (rich)?" (if adding new progress bars)

## Process

1. Read the file and pyproject.toml
2. Read the 3 skills above for current rules
3. List all violations by category
4. Apply fixes - user confirms via tool approval
5. Update pyproject.toml if deps missing
6. Show summary of changes

## Rules

- Restructure aggressively - move cells, add sections, consolidate imports
- NEVER change logic - only structure, formatting, and styling
- NEVER rename files or convert formats unless user explicitly asks
- Defer to skills for all color/pattern/structure rules - do not invent

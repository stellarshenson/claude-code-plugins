---
name: fix-notebook
description: Fix a notebook to comply with all standards - structure, styling, progress bars, header narrative
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, Skill, TaskCreate, TaskUpdate]
---

# Fix Notebook

Read a notebook and fix it to comply with ALL standards. Applies changes directly.

## Skills to apply

- **`datascience:notebook-standards`** - section order, GPU selection, imports, config cell; its `references/rich-output.md` (colour palette, print patterns) and `references/equations.md` (unicode inline + display math)
- **`datascience:progressbars`** - progress bar style and patterns

Read these skills before making changes. They are the source of truth. Do NOT hardcode colors or patterns in this skill - always defer to the skills.

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
- Section header without overview text below it -> add a 1-2 sentence overview (or 3-5 bullets when listy) before the first code cell of that section. File-level Header section is the sole exception
- Configuration cell with no Rich render at end -> add the sectioned `rprint(f"""[bold cyan]Configuration[/bold cyan] ...""")` block per the canonical template in `notebook-standards/SKILL.md`
- Configuration cell on a GPU notebook without `[bold]Device[/bold]` sub-section showing `torch.cuda.get_device_name(0)` -> add the Device block per `notebook-standards/references/gpu-setup.md` section 5
- Markdown cell containing equations as plain text (e.g. `P(A|B) = P(B|A) * P(A) / P(B)`) -> rewrite per `notebook-standards` `references/equations.md`: unicode glyphs inline, full/display equations as standalone `$$...$$` blocks on their own line
- Markdown cell with odd number of unescaped `$` (heuristic for stray dollar amounts that MathJax will eat) -> surface the cell number and ask the user whether each `$` is a price (escape as `\$`) or a math delimiter (leave + verify pairs match)

### Styling (per `notebook-standards` `references/rich-output.md`)
- Plain `print()` for structured output -> single multiline `rprint()` with semantic colours from the palette
- Wrong or hex colours -> named colours from the palette
- Missing config summary -> add the styled block

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
2. Read the 2 skills above (and their `references/`) for current rules
3. List all violations by category
4. Apply fixes - user confirms via tool approval
5. Update pyproject.toml if deps missing
6. Fill in the Post-write checklist from `notebook-standards/SKILL.md`; fix every unticked box before reporting
7. Show summary of changes plus the filled-in checklist

## Rules

- Restructure aggressively - move cells, add sections, consolidate imports
- NEVER change logic - only structure, formatting, and styling
- NEVER rename files or convert formats unless user explicitly asks
- Defer to skills for all color/pattern/structure rules - do not invent

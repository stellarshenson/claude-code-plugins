---
description: Add or fix progress bars in a notebook or script - choose classic (tqdm) or modern (rich) style
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, Skill]
argument-hint: "path to file to add progress bars to"
---

# Apply Progress Bars

Read a file and add or fix progress bars. Uses the `datascience:progressbars` skill as the single source of truth.

## Skill to apply

**`datascience:progressbars`** - read this skill first for patterns, imports, completion fixes, and Jupyter compatibility. Do NOT duplicate its content here.

## Steps

1. ASK: "Classic (tqdm) or modern (rich)?" (per skill's selection rule)
2. Read the `progressbars` skill for the chosen style's patterns
3. Scan file for loops to instrument (large collections, executors, training, file processing)
4. Apply wrappers per the skill's patterns
5. Fix existing broken bars per the skill's troubleshooting section
6. In Jupyter: split progress cell from setup text
7. Update `pyproject.toml`:
   - Classic: `tqdm` in deps, `ipywidgets` in dev deps
   - Modern: `rich` in deps
   Add missing, do NOT remove existing
8. Show summary

---
description: Add or fix progress bars in a notebook or script - choose classic (tqdm) or modern (rich) style
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, Skill, TaskCreate, TaskUpdate]
argument-hint: "path to file to add progress bars to"
---

# Apply Progress Bars

Read a file and add or fix progress bars. Uses the `datascience:progressbars` skill as the single source of truth.

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

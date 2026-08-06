---
description: Review a notebook or script for compliance with data science standards
allowed-tools: [Read, Glob, Grep, Bash, Skill, TaskCreate, TaskUpdate]
argument-hint: "path to notebook or script to review"
---

# Review for Standards Compliance

Review a notebook or Python script against all datascience, notebook structure, and rich output standards. Produces an actionable checklist of violations.

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

## What to check

Read the target file, then evaluate it in two parts.

### 1. Notebook standards (if `.ipynb` or Jupytext `.py`)

Read `notebook-standards/SKILL.md` and tick its **Post-write checklist** against the file - structure, output, long runs, evidence. That checklist is the single source of truth for those boxes; do not restate or fork it here, or the two copies drift apart and a reviewer enforces the stale one.

### 2. Project conventions (every file)

From the `datascience:datascience` skill - what the notebook checklist does not cover:

- [ ] Naming: `NN-initials-description.ipynb` pattern
- [ ] DataFrame naming: `purpose_df` / `purpose_lf`
- [ ] Polars lazy (`scan_*` / `LazyFrame`) for large data
- [ ] Sklearn builtins preferred over custom implementations
- [ ] No imports in `__init__.py`
- [ ] Google docstrings with type hints
- [ ] No hardcoded paths - `Path` objects
- [ ] Consistent figure sizes across the file
- [ ] Rich uses standard colour names, no hex; `[dim]` for secondary text

## Output

Report as:
```
## Review: <filename>

### Passing (N/M)
- [x] Item that passes

### Violations (N)
- [ ] Item that fails - **what to fix**

### Suggestions
- Optional improvements (not violations)
```

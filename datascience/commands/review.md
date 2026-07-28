---
description: Review a notebook or script for compliance with data science standards
allowed-tools: [Read, Glob, Grep, Bash, Skill]
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

Read the target file and evaluate against this checklist:

### Notebook Structure (if .ipynb or Jupytext .py)
- [ ] Header cell with title, author, approach
- [ ] GPU selection BEFORE torch/tf/jax imports (if GPU used)
- [ ] All imports in single cell with autoreload
- [ ] Imports grouped by category with inline comments
- [ ] No imports in later cells
- [ ] Configuration in single cell with rich summary
- [ ] Markdown header before each code section
- [ ] Progress bars in separate cell from setup text

### Data Science Conventions
- [ ] Naming: `NN-initials-description.py` pattern
- [ ] Jupytext percent format (not raw .ipynb)
- [ ] DataFrame naming: `purpose_df` / `purpose_lf`
- [ ] No imports in `__init__.py`
- [ ] Google docstrings with type hints
- [ ] Polars lazy processing for large data
- [ ] Sklearn builtins preferred over custom implementations

### Rich Output
- [ ] Single multiline `rich.print()` (not multiple individual prints)
- [ ] Semantic colors: `dark_sea_green` for values, `indian_red` for errors
- [ ] No hex colors in rich (standard colors only)
- [ ] `[dim]` for secondary information

### Code Quality
- [ ] Seeds set for reproducibility
- [ ] No hardcoded paths (use Path objects)
- [ ] Consistent plot sizes
- [ ] Progress bars for long operations

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

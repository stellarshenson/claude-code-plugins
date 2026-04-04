---
description: Fix a notebook to comply with all structure and organization standards
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion]
argument-hint: "path to notebook to fix, e.g. 'notebooks/01-kj-analysis.py'"
---

# Fix Notebook Structure

Read a notebook and restructure it to comply with all standards. Non-destructive - preserves all existing code, just reorganizes and adds missing elements.

## What to fix

### Section Order
1. **Missing header** -> add title, author, approach markdown cell at top
2. **GPU after imports** -> move `CUDA_VISIBLE_DEVICES` before any torch/tf/jax import
3. **Scattered imports** -> consolidate ALL imports into single cell after GPU selection
4. **Missing autoreload** -> add `%load_ext autoreload` + `%autoreload 2`
5. **Import grouping** -> reorder: stdlib, data processing, ML, transformers, rich
6. **Missing inline comments** -> add category comments to import groups
7. **No reproducibility** -> add `set_seed(42)` cell after imports
8. **Scattered config** -> consolidate hyperparameters into single config cell
9. **Missing rich config summary** -> add `rich.print()` block at end of config cell

### Cell Organization
10. **No markdown headers** -> add `## Section Name` markdown cell before each code section
11. **Progress bar in setup cell** -> split into separate cells
12. **Multiple operations per cell** -> suggest splits for clarity

### Naming
13. **Wrong filename pattern** -> suggest rename to `NN-initials-description.py`
14. **Not Jupytext format** -> convert `.ipynb` to Jupytext percent format `.py`

### Dollar Signs
15. **Unescaped `$` in markdown** -> replace with `\\$`

## Process

1. Read the file
2. Run full compliance check (same as `/datascience:review`)
3. List all violations with line numbers
4. Apply fixes directly - user sees each edit via standard tool approval
5. Show before/after summary

## Critical questions (ASK before proceeding)

- **Filename rename**: "This notebook should be `03-kj-train-model.py`. Rename?" (could break imports/references)
- **Format conversion**: "Convert from .ipynb to Jupytext .py? The .ipynb will be gitignored." (irreversible format change)
- **Author initials**: "What are your initials for notebook naming?" (if not obvious)
- **Import consolidation**: if imports are scattered across 5+ cells, show the proposed consolidated cell before applying

## Rules

- Restructure aggressively - move cells, add sections, consolidate imports
- NEVER change logic - only structure and formatting
- User confirms each edit through normal tool approval flow

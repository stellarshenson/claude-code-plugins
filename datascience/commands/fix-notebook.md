---
description: Fix a notebook to comply with all standards - structure, styling, progress bars, header narrative
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion]
argument-hint: "path to notebook to fix, e.g. 'notebooks/01-kj-analysis.py'"
---

# Fix Notebook Structure, Styling, and Progress Bars

Read a notebook and fix it to comply with ALL standards: structure, rich styling, progress bar patterns, and header quality. Applies changes directly.

## What to fix

### Header Narrative
1. **Missing or sparse header** -> add/rewrite with flowing prose explaining purpose, method, and rationale (not just a title)
2. **Bullet-list-only approach** -> rewrite as numbered phases with "what AND why" (not just "load data" but "load and validate the annotated dataset, checking for class imbalance")
3. **Missing output description** -> add `**Output**: <specific artifacts produced>`
4. **Missing author** -> ASK user for name

### Section Order
5. **GPU after imports** -> move `CUDA_VISIBLE_DEVICES` before any torch/tf/jax import
6. **Scattered imports** -> consolidate ALL imports into single cell after GPU selection
7. **Missing autoreload** -> add `%load_ext autoreload` + `%autoreload 2`
8. **Import grouping** -> reorder: stdlib, data processing, ML, domain-specific, rich, project modules. Add category comments
9. **No reproducibility** -> add `set_seed(42)` cell after imports
10. **Scattered config** -> consolidate hyperparameters into single config cell
11. **No markdown headers** -> add `## Section Name` markdown cell before each code section

### Rich Styling
12. **Plain `print()` for structured output** -> convert to `rprint()` with semantic colors
13. **Wrong colors** -> fix to standard palette:
    - Headers: `[medium_purple]`
    - Values (no units): `[dark_sea_green]`
    - Values (with units): `[light_sea_green]`
    - File names: `[cadet_blue]`
    - Paths: `[dim]`
    - Success/Warning/Error: `[dark_sea_green]`/`[dark_goldenrod]`/`[indian_red]`
14. **Multiple individual rprint()** -> merge into single multiline call
15. **Missing config summary** -> add `rprint()` block at end of config cell showing all params with styled values
16. **Missing rich import** -> add `from rich import print as rprint`
17. **Hex colors in rich** -> replace with standard named colors

### Progress Bars
18. **Long loops without progress** -> add rich Progress wrapper (SpinnerColumn + TextColumn + TimeElapsedColumn)
19. **tqdm where rich works** -> suggest replacement with rich.progress
20. **Progress bar in same cell as setup text** -> split into separate cells (setup text gets overwritten)
21. **Missing progress import** -> add `from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn`

### Dependencies
22. **`rich` not in pyproject.toml** -> add to dependencies
23. **Progress bar used but `tqdm` not in deps** -> add if tqdm is used, or suggest rich.progress replacement

### Cell Organization
24. **Imports in later cells** -> move to imports cell
25. **Multiple operations per cell** -> suggest splits for clarity
26. **Dollar signs unescaped** -> `$` -> `\\$` in markdown cells

## Critical questions (ASK before proceeding)

- **Filename rename**: "This notebook should be `03-kj-train-model.ipynb`. Rename?" (could break imports/references)
- **Author**: "What are your initials and full name for the header?"
- **Header rewrite**: show proposed narrative and ask "Does this capture the purpose correctly?"
- **Import consolidation**: if imports scattered across 5+ cells, show proposed consolidated cell

## Process

1. Read the file and pyproject.toml
2. Run full compliance check - list all violations by category
3. Apply structural fixes first (section order, imports, config)
4. Apply styling fixes (rich colors, print patterns)
5. Apply progress bar fixes (add wrappers, split cells)
6. Update pyproject.toml if deps missing
7. Show summary of all changes

## Rules

- Restructure aggressively - move cells, add sections, consolidate imports
- NEVER change logic - only structure, formatting, and styling
- User confirms each edit through normal tool approval flow

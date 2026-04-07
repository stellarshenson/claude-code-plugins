---
description: Create a new Jupyter notebook with proper structure, styling, and progress bars
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion, Skill]
argument-hint: "notebook purpose, e.g. 'train YOLOv8 on custom dataset'"
---

# Create New Notebook

Scaffold a properly structured notebook. Uses skills for standards - do NOT duplicate their rules here.

## Skills to apply

- **`datascience:notebook-standards`** - section order, GPU selection, imports, config cell
- **`datascience:rich-output`** - color palette, print patterns, table styles
- **`datascience:progressbars`** - progress bar style and patterns (if long-running ops)

Read these skills before generating the notebook. They are the source of truth for structure, colors, and patterns.

## Steps

1. ASK the user:
   - **Purpose** (what the notebook does - used for header narrative)
   - **Author initials** (default: kj)
   - **GPU needed?** (yes/no)
   - **Libraries needed** (torch, polars, sklearn, transformers, etc.)
   - **Long-running operations?** (yes/no - if yes, ask classic tqdm or modern rich per `progressbars` skill)

2. Determine next notebook number by scanning existing `NN-*.ipynb` or `NN-*.py` files.

3. Check `pyproject.toml` - ensure `rich` in dependencies. If progress bars needed, ensure `tqdm` or `rich` per chosen style. Add if missing.

4. Create `<NN>-<initials>-<description>.ipynb` (default) or `.py` if user prefers.

5. **Header**: brief narrative paragraph (purpose, method, rationale - 2-4 sentences of flowing prose, not bullets). Approach section with numbered phases explaining "what AND why". Output section listing specific artifacts.

6. **Structure**: follow `notebook-standards` skill exactly - GPU first, imports grouped with autoreload, reproducibility seeds, config cell with rich summary.

7. **Styling**: follow `rich-output` skill for all `rprint()` calls - semantic colors per the palette.

8. **Progress bars**: if long-running ops, follow `progressbars` skill for the chosen style. Setup text in separate cell.

9. Report: filename created, pyproject.toml changes, next steps.

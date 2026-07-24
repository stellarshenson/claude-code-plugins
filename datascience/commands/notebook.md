---
description: Create a new Jupyter notebook with proper structure, styling, and progress bars
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion, Skill]
argument-hint: "notebook purpose, e.g. 'train YOLOv8 on custom dataset'"
---

# Create New Notebook

Scaffold a properly structured notebook. Uses skills for standards - do NOT duplicate their rules here.

## Skills to apply

- **`datascience:notebook-standards`** - section order, GPU selection, imports, config cell; its `references/rich-output.md` (colour palette, print patterns) and `references/equations.md` (unicode inline + display math)
- **`datascience:progressbars`** - progress bar style and patterns (if long-running ops)

Read these skills before generating the notebook. They are the source of truth for structure, colors, and patterns.

## Steps

1. ASK the user:
   - **Purpose** (what the notebook does - used for header narrative)
   - **Author initials** (default: kj)
   - **GPU needed?** (yes/no) - if yes, **GPU selection**: pin a specific GPU by UUID (default, reproducible) or auto-pick the freest GPU at runtime? See `notebook-standards/references/gpu-setup.md`
   - **Libraries needed** (torch, polars, sklearn, transformers, etc.)
   - **Long-running operations?** (yes/no - if yes, ask classic tqdm or modern rich per `progressbars` skill)

2. Determine next notebook number by scanning existing `NN-*.ipynb` or `NN-*.py` files.

3. Check `pyproject.toml` - ensure `rich` in dependencies. If progress bars needed, ensure `tqdm` or `rich` per chosen style. Add if missing.

4. Create `<NN>-<initials>-<description>.ipynb` (default) or `.py` if user prefers.

5. **Header**: brief narrative paragraph (purpose, method, rationale - 2-4 sentences of flowing prose, not bullets). Approach section with numbered phases explaining "what AND why". Output section listing specific artifacts.

6. **Structure**: follow `notebook-standards` skill exactly - GPU first, imports grouped with autoreload, reproducibility seeds, config cell with sectioned Rich render. **Section overview MANDATORY** - every `## Section Name` header gets a 1-2 sentence overview (or 3-5 bullets when listy) directly below, BEFORE the first code cell.

7. **Configuration cell**: hyperparameters with inline comments + sectioned Rich render at the END of the same cell. When GPU is enabled, the render MUST include `[bold]Device[/bold]` sub-section showing `torch.cuda.get_device_name(0)` so the resolved GPU is visible in the output. See `notebook-standards/SKILL.md` Configuration template + `notebook-standards/references/gpu-setup.md` section 5.

8. **Equations and math in markdown**: follow `notebook-standards` `references/equations.md` - write math liberally, unicode glyphs inline (`τ(i) = Σⱼ Tᵢⱼ·posⱼ / Σⱼ Tᵢⱼ`), every full/display equation as a standalone `$$...$$` block on its own line (rasterised to images later). Escape stray dollar amounts as `\$`.

9. **Styling**: follow `notebook-standards` `references/rich-output.md` for all `rprint()` calls - semantic colors per the palette.

10. **Progress bars**: if long-running ops, follow `progressbars` skill for the chosen style. Setup text in separate cell.

11. Report: filename created, pyproject.toml changes, next steps.

**Figures**: plots render inline (`plt.show()`) - do NOT add `plt.savefig` / file export unless the user explicitly asks to export. The notebook is the artefact. See `notebook-standards/SKILL.md` "Figures (inline by default)".

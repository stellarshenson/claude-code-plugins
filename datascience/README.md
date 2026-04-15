# datascience

Data science project standards for Claude Code. Enforces notebook structure, naming conventions, rich output styling, and project layout. Scaffolds new projects from a copier template, reviews existing code for compliance, and applies research-backed prompt engineering techniques.

Unlike ad-hoc notebook cleanups, this plugin treats the notebook as a standardised artefact - fixed section order, GPU selection before torch/tf/jax imports, a single configuration cell with rich display, and completion-safe progress bars. Project scaffolding is driven by the [copier-data-science](https://github.com/stellarshenson/copier-data-science) template so new projects match existing ones on day one.

## Installation

```bash
/plugin marketplace add stellarshenson/claude-code-plugins
/plugin install datascience@stellarshenson-marketplace
```

## Commands

| Command | What it does |
|---------|--------------|
| `/datascience:new-project` | Scaffold a new project from the `copier-data-science` template |
| `/datascience:notebook` | Create a properly structured Jupytext notebook with all standard sections |
| `/datascience:review` | Review a notebook or script against all standards and produce a violation checklist |
| `/datascience:fix-notebook` | Restructure a notebook to comply with every standard - layout, styling, progress bars, header |
| `/datascience:fix-project` | Port an existing project to `copier-data-science` standards or update an existing copier project |
| `/datascience:apply-style` | Apply rich output styling - colours, print patterns, missing formatting |
| `/datascience:apply-progressbar` | Add or fix progress bars, choosing classic (tqdm) or modern (rich) |
| `/datascience:apply-footnotes` | Add JupyterLab-compatible footnotes using the anchor-link pattern |
| `/datascience:apply-prompt-technique` | Apply a prompt engineering technique to a prompt, system instruction, or agent definition |
| `/datascience:challenge` | Full psychological prompting stack for difficult problems - stakes, incentive, competitive framing |

## Skills

Auto-triggered based on context.

| Skill | Triggers when |
|-------|--------------|
| `datascience` | Working with data science projects, datasets, ML models, PyTorch, Polars, sklearn |
| `notebook-standards` | Creating or modifying Jupyter notebooks (`.ipynb` or Jupytext `.py`) |
| `rich-output` | Formatting output with the rich library - tables, status, coloured console |
| `progressbars` | Adding progress bars with tqdm (classic) or rich (modern) |
| `footnotes` | Adding references, citations, or notes in notebooks and markdown |
| `prompt-engineering` | Crafting system prompts, agent instructions, or LLM prompts |

## Prompt engineering techniques

The `prompt-engineering` skill ships seven research-backed techniques. Each reference contains the paper, a template, and usage guidance. See [`skills/prompt-engineering/references/`](skills/prompt-engineering/references/) for full content.

| # | Technique | Best for |
|---|-----------|----------|
| 1 | Psychological Prompting | Complex tasks, maximum effort (+45-115%) |
| 2 | Chain of Thought | Math, logic, debugging (+46% on GSM8K) |
| 3 | Chain of Draft | Token-limited reasoning (~7.6% of CoT tokens) |
| 4 | Tree of Thought | Design decisions, architecture trade-offs |
| 5 | Few-Shot | Structured output, classification, format-sensitive extraction |
| 6 | Self-Refine | Code, documents, iterative quality improvement |
| 7 | Rephrase and Respond | Ambiguous requirements, multi-part questions |

Use `/datascience:apply-prompt-technique` to pick and apply a technique to an existing prompt, or `/datascience:challenge` to apply the full psychological stack.

## Example usage

Create a new project, scaffold the first notebook, then review it:

```bash
/datascience:new-project yolo-homeobjects "train YOLOv8 on 10 home object classes"
/datascience:notebook "01 baseline training on the assembled dataset"
/datascience:review notebooks/01-kj-baseline.py
```

## Reference

- [`skills/notebook-standards/SKILL.md`](skills/notebook-standards/SKILL.md) - section order, GPU selection, imports, configuration, naming convention
- [`skills/rich-output/SKILL.md`](skills/rich-output/SKILL.md) - semantic colour palette and print patterns
- [`skills/progressbars/SKILL.md`](skills/progressbars/SKILL.md) - tqdm and rich progress bar recipes
- [`skills/footnotes/SKILL.md`](skills/footnotes/SKILL.md) - JupyterLab-compatible anchor pattern (standard `[^1]` does not render in JupyterLab)
- [`skills/prompt-engineering/references/`](skills/prompt-engineering/references/) - per-technique papers, templates, and usage guidance
- [`skills/datascience/SKILL.md`](skills/datascience/SKILL.md) - project conventions, naming, file format standards
- [copier-data-science](https://github.com/stellarshenson/copier-data-science) - project scaffolding template used by `/datascience:new-project` and `/datascience:fix-project`

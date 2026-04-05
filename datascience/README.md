# datascience

Data science project standards plugin for Claude Code. Enforces notebook structure, naming conventions, rich output styling, and project organization. Creates new projects from copier templates, reviews existing code for compliance, and applies research-backed prompt engineering techniques.

## Skills (auto-triggered)

| Skill | Triggers when |
|-------|--------------|
| `datascience` | Working with data science projects, datasets, ML models, PyTorch, Polars, sklearn |
| `notebook-standards` | Creating or modifying Jupyter notebooks (.ipynb or Jupytext .py) |
| `rich-output` | Formatting output with the rich library, creating tables, progress bars |
| `prompt-engineering` | Crafting system prompts, agent instructions, or LLM prompts |
| `progressbars` | Implementing progress bars in scripts or notebooks (tqdm or rich) |

## Commands (user-invoked)

| Command | What it does |
|---------|-------------|
| `/datascience:new-project` | Scaffold a new project from [copier-data-science](https://github.com/stellarshenson/copier-data-science) template |
| `/datascience:notebook` | Create a properly structured Jupytext notebook with all sections |
| `/datascience:review` | Review notebook/script against all standards, produce violation checklist |
| `/datascience:apply-style` | Apply rich output styling standards - fix colors, print patterns, missing formatting |
| `/datascience:apply-progressbar` | Add or fix progress bars - choose classic (tqdm) or modern (rich) style |
| `/datascience:apply-prompt-technique` | Apply prompt engineering technique (psychological, CoT, CoD, ToT, few-shot, self-refine, rephrase) |
| `/datascience:fix-notebook` | Restructure a notebook to comply with all standards |
| `/datascience:fix-project` | Port existing project to copier-data-science template or update to latest |
| `/datascience:challenge` | Full psychological prompting stack for difficult problems - stakes + incentive + challenge |

## Prompt Engineering

The `prompt-engineering` skill includes 7 research-backed techniques with templates and paper references in `skills/prompt-engineering/references/`. Use `/datascience:apply-prompt-technique` to choose and apply, or `/datascience:challenge` for the full psychological stack on hard problems.

## Standards Enforced

- **Notebook naming**: `NN-initials-description.py` (Jupytext percent format)
- **Section order**: header -> GPU -> imports -> seeds -> config -> data -> model -> execution -> save -> eval
- **GPU selection**: `CUDA_VISIBLE_DEVICES` before any torch/tf/jax import
- **Imports**: single cell, grouped by category, autoreload enabled, no later imports
- **Rich output**: semantic colors, single multiline print, standard colors only (no hex)
- **Progress bars**: ask classic (tqdm) vs modern (rich), completion fixes, Jupyter cell separation
- **Project structure**: cookiecutter-data-science directories (data/raw, data/processed, notebooks/, src/, models/)
- **PyTorch artifacts**: model.pt (TorchScript) + checkpoint.pt (state dict), folder rolling
- **Code**: Google docstrings, type hints, Polars lazy processing, sklearn builtins preferred

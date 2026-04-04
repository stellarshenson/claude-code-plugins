# datascience

Data science project standards plugin for Claude Code. Enforces notebook structure, naming conventions, rich output styling, and project organization. Creates new projects from copier templates and reviews existing code for compliance.

## Skills (auto-triggered)

| Skill | Triggers when |
|-------|--------------|
| `datascience` | Working with data science projects, datasets, ML models, PyTorch, Polars, sklearn |
| `notebook-standards` | Creating or modifying Jupyter notebooks (.ipynb or Jupytext .py) |
| `rich-output` | Formatting output with the rich library, creating tables, progress bars |

## Commands (user-invoked)

| Command | What it does |
|---------|-------------|
| `/datascience:new-project` | Scaffold a new project from [copier-data-science](https://github.com/stellarshenson/copier-data-science) template |
| `/datascience:notebook` | Create a properly structured Jupytext notebook with all sections |
| `/datascience:review` | Review notebook/script against all standards, produce violation checklist |
| `/datascience:style` | Quick reference for rich output colors and patterns |

## Standards Enforced

- **Notebook naming**: `NN-initials-description.py` (Jupytext percent format)
- **Section order**: header -> GPU -> imports -> seeds -> config -> data -> model -> execution -> save -> eval
- **GPU selection**: `CUDA_VISIBLE_DEVICES` before any torch/tf/jax import
- **Imports**: single cell, grouped by category, autoreload enabled, no later imports
- **Rich output**: semantic colors, single multiline print, standard colors only (no hex)
- **Project structure**: cookiecutter-data-science directories (data/raw, data/processed, notebooks/, src/, models/)
- **PyTorch artifacts**: model.pt (TorchScript) + checkpoint.pt (state dict), folder rolling
- **Code**: Google docstrings, type hints, Polars lazy processing, sklearn builtins preferred

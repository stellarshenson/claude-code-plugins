---
name: datascience
description: Data science project conventions and standards. Auto-triggered when working with data science projects, notebooks, datasets, ML models, PyTorch, Polars, sklearn, or any data analysis workflow. Applies naming conventions, file format standards, project structure rules, and code patterns.
---

# Data Science Standards

Conventions for data science projects.

## Notebook Naming

Pattern: `NN-initials-description.py` (Jupytext percent format)
- Two-digit execution order: `01`, `02`, `03`
- Author initials: `kj` for Konrad Jelen
- Brief description: `data-exploration`, `train-yolov8m`
- Examples: `01-kj-data-exploration.py`, `04-kj-train-yolov8m.py`

Sequential numbering within logical groupings. Archive obsolete notebooks to `@archive/` - never delete. `temp_` prefix for temporary notebooks excluded from Git.

## File Format

Jupytext percent format (`.py` files) as source of truth. `# %%` for code cells, `# %% [markdown]` for markdown cells. Add `*.ipynb` to `.gitignore`. Enables proper git diffs and code review.

## Project Structure (cookiecutter-data-science)

```
data/raw/          # Original immutable datasets (never modify)
data/interim/      # Intermediate transformed data
data/processed/    # Final canonical datasets
data/external/     # Third-party data
notebooks/         # Jupytext notebooks
src/               # Reusable Python modules extracted from notebooks
models/            # Trained model artifacts
reports/           # Generated analysis and figures
```

## PyTorch Model Artifacts

```
models/<model_name>/
  model.pt        # TorchScript (torch.jit.load, no class needed, for inference)
  checkpoint.pt   # State dict (needs class definition, for retraining)
```

Folder rolling for model exports: current -> `-1`, `-1` -> `-2`, up to 5 versions.

## Code Standards

- **Imports**: never import into `__init__.py`, always explicit module imports
- **Docstrings**: Google format, type hints for params and returns
- **DataFrames**: `purpose_df` for DataFrames, `purpose_lf` for LazyFrames
- **Rich output**: `from rich.jupyter import print` for readable output
- **Polars**: lazy processing (`pl.LazyFrame` + `collect()`) for large datasets
- **Prefer builtins**: `sklearn.model_selection.train_test_split` over manual splitting
- **Plots**: consistent `figsize=(12, 6)`, matplotlib + seaborn

## EDA First

Start with thorough EDA: data types, missing values, basic statistics, visual exploration (histograms, scatter, box plots), testable hypotheses. High-dimensional data: try UMAP/t-SNE.

---
name: datascience
description: Data science project conventions and standards. Auto-triggered when working with data science projects, notebooks, datasets, ML models, PyTorch, Polars, sklearn, or any data analysis workflow. Applies naming conventions, file format standards, project structure rules, and code patterns.
---

# Data Science Standards

Conventions for data science projects.

## Notebook Naming

Pattern: `NN-initials-description.ipynb`
- Two-digit execution order: `01`, `02`, `03`
- Author initials: `kj` for Konrad Jelen
- Brief description: `data-exploration`, `train-yolov8m`
- Examples: `01-kj-data-exploration.ipynb`, `04-kj-train-yolov8m.ipynb`

Sequential numbering within groupings. Archive obsolete to `@archive/`. Never delete. `temp_` prefix for temporary notebooks excluded from Git.

## File Format

`.ipynb` = source of truth, committed WITH its outputs. The executed notebook - inline figures, rich renders, tables - is the artefact a reader opens, so the outputs are part of what gets reviewed and shared. Do not gitignore `.ipynb`, and do not keep the source in a paired Jupytext `.py`.

## Project Structure (cookiecutter-data-science)

```
data/raw/          # Original immutable datasets (never modify)
data/interim/      # Intermediate transformed data
data/processed/    # Final canonical datasets
data/external/     # Third-party data
notebooks/         # Jupyter notebooks
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

Folder rolling: current → `-1` → `-2`, up to 5 versions.

## Code Standards

- **Imports**: never into `__init__.py`. Always explicit module imports
- **Docstrings**: Google format, type hints for params and returns
- **DataFrames**: `purpose_df` for DataFrames, `purpose_lf` for LazyFrames
- **Rich output**: `from rich import print as rprint` - the form every notebook-standards template uses
- **Polars**: lazy (`pl.LazyFrame` + `collect()`) for large datasets
- **Prefer builtins**: `sklearn.model_selection.train_test_split` over manual
- **Plots**: matplotlib + seaborn; sizes per purpose in the notebook-standards `references/matplotlib.md`

## EDA First

Start thorough: data types, missing values, basic statistics, visual exploration (histograms, scatter, box plots), testable hypotheses. High-dimensional: try UMAP/t-SNE.

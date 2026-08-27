---
name: datascience
description: Data science project conventions and standards. Auto-triggered when working with data science projects, notebooks, datasets, ML models, PyTorch, Polars, sklearn, or any data analysis workflow. Applies naming conventions, file format standards, project structure rules, and code patterns.
---

# Data Science Standards

Conventions for data science projects.

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
- **Rich output**: `from rich.jupyter import print`
- **Polars**: lazy (`pl.LazyFrame` + `collect()`) for large datasets
- **Prefer builtins**: `sklearn.model_selection.train_test_split` over manual
- **Plots**: `figsize=(12, 6)`, matplotlib + seaborn

## EDA First

Start thorough: data types, missing values, basic statistics, visual exploration (histograms, scatter, box plots), testable hypotheses. High-dimensional: try UMAP/t-SNE.

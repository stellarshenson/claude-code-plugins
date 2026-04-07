---
description: Create a new Jupyter notebook with proper structure, styling, and progress bars
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion]
argument-hint: "notebook purpose, e.g. 'train YOLOv8 on custom dataset'"
---

# Create New Notebook

Scaffold a properly structured Jupytext notebook following all datascience standards including rich styling and progress bar patterns.

## Steps

1. ASK the user:
   - **Purpose** (what the notebook does - used for header narrative)
   - **Author initials** (default: kj)
   - **GPU needed?** (yes/no - determines if GPU selection cell is included)
   - **Libraries needed** (torch, polars, sklearn, transformers, whisperx, etc.)
   - **Long-running operations?** (yes/no - determines progress bar setup)

2. Determine the next notebook number by scanning existing `NN-*.ipynb` or `NN-*.py` files in the current directory or `notebooks/` directory.

3. Check `pyproject.toml` - ensure `rich` is in dependencies. If long-running operations, ensure `tqdm` is also present. Add if missing.

4. Create `<NN>-<initials>-<description>.ipynb` (default) or `.py` Jupytext format if user prefers:

```python
# %% [markdown]
# # <Descriptive Title>
#
# **Author**: <Full Name>
#
# <Brief narrative paragraph explaining what this notebook does, WHY it matters,
# and what approach/method is used. Not a bullet list - flowing prose that gives
# context to someone opening this notebook for the first time. 2-4 sentences.>
#
# ## Approach
#
# **1. <Phase Name>** - <what and why, not just "load data" but "load and validate
# the annotated dataset, checking for class imbalance">
#
# **2. <Phase Name>** - <method choice and rationale>
#
# **3. <Phase Name>** - <what metrics, what we expect>
#
# **Output**: <Specific artifacts produced - model files, reports, datasets>

# %% GPU Selection (only if GPU needed)
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # <GPU name and VRAM from nvidia-smi>
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# %% Imports
%load_ext autoreload
%autoreload 2

# Standard library
from pathlib import Path

# Data processing (if applicable)
# import numpy as np
# import polars as pl

# Deep learning (if applicable)
# import torch
# import torch.nn as nn

# <domain-specific libraries>

# Rich console output
from rich import print as rprint
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

# Project modules
# from <project>.config import ...

# %% Reproducibility (if ML/random operations)
import random
import numpy as np

def set_seed(seed=42):
    """Set random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    # if torch:
    # torch.manual_seed(seed)
    # if torch.cuda.is_available():
    #     torch.cuda.manual_seed_all(seed)

set_seed(42)

# %% Configuration
# <ALL hyperparameters and settings in one cell with inline comments>

# Display configuration with rich styling
rprint(f"""[medium_purple]Configuration[/medium_purple]
  <param>: [dark_sea_green]{...}[/dark_sea_green]
  <param with units>: [light_sea_green]{...} <unit>[/light_sea_green]
  Device: [dark_sea_green]{device}[/dark_sea_green]
  GPU: [dark_sea_green]{gpu_name}[/dark_sea_green]
""")

# %% [markdown]
# ## Data Loading

# %%
# Data loading code here

# %% [markdown]
# ## Processing

# %%
# For long-running operations, use rich Progress:
#
# progress = Progress(
#     SpinnerColumn(),
#     TextColumn("[medium_purple]{task.description}[/medium_purple]"),
#     TimeElapsedColumn(),
# )
# with progress:
#     task = progress.add_task("Processing...", total=N)
#     for item in items:
#         # ... work ...
#         progress.advance(task)

# %% [markdown]
# ## Results

# %%
# Results summary with rich styling:
# rprint(f"""[medium_purple]Results[/medium_purple]
#   Metric: [dark_sea_green]{value}[/dark_sea_green]
#   File: [cadet_blue]{filename}[/cadet_blue]
#   Path: [dim]{path}[/dim]
# """)
```

5. **Default format is `.ipynb`** - creates a standard Jupyter notebook. If user explicitly asks for Jupytext percent format, create `.py` instead. The `.ipynb` is more portable and opens directly in JupyterLab without conversion.

6. Report: filename created, pyproject.toml changes (if any), next steps.

## Rich styling applied automatically

- Headers: `[medium_purple]` for section titles
- Values without units: `[dark_sea_green]`
- Values with units: `[light_sea_green]`
- File names: `[cadet_blue]`
- Paths: `[dim]`
- Success: `[dark_sea_green]` with `✓`
- Warning: `[dark_goldenrod]` with `⚠`
- Error: `[indian_red]` with `✗`
- All output via single multiline `rprint()` calls

## Progress bar pattern

For any cell with long-running operations, scaffold the rich Progress pattern with SpinnerColumn + TextColumn + TimeElapsedColumn. Setup text (what's about to run) goes in a SEPARATE cell before the progress cell.

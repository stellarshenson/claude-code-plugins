---
name: notebook-standards
description: Jupyter notebook structure and organization standards. Auto-triggered when creating or modifying Jupyter notebooks (.ipynb or Jupytext .py). Enforces section order, GPU selection, import grouping, configuration patterns, and rich output formatting.
---

# Notebook Structure Standards

Patterns for Jupyter notebook creation.

## Mandatory Section Order

1. **Header** - title, author, approach with numbered steps
2. **GPU Selection** - `CUDA_VISIBLE_DEVICES` BEFORE any torch/tf/jax import
3. **Imports** - ALL imports in one cell, grouped, with inline comments, autoreload enabled
4. **Reproducibility** - `set_seed(42)` for random, numpy, torch
5. **Configuration** - all hyperparameters in one cell, inline comments, rich summary at end
6. **Data Loading**
7. **Model/Processing**
8. **Execution** (training, inference)
9. **Save/Export**
10. **Evaluation/Summary**

## GPU Selection (MUST be first code cell)

```python
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
```

## Import Cell Pattern

```python
%load_ext autoreload
%autoreload 2

# Standard library
import os
from pathlib import Path

# Data processing
import numpy as np
import polars as pl

# Deep learning
import torch
import torch.nn as nn

# Rich console output
import rich.jupyter as rich
from rich.progress import Progress, BarColumn
```

ALL imports in this cell. Never import later.

## Configuration Cell

All hyperparameters with inline comments. End with rich summary + GPU confirmation:

```python
rich.print(f"""[white]Configuration[/white]
  Model: [cyan]{MODEL_NAME}[/cyan]
  Batch size: [cyan]{BATCH_SIZE}[/cyan]
  Device: [cyan]{device}[/cyan]
  GPU: [cyan]{gpu_name}[/cyan]
""")
```

## Cell Rules

- Markdown header before each code section
- One logical operation per cell
- Progress bars in SEPARATE cell from setup text - avoids overwriting
- Dollar signs: `\\$` in markdown (LaTeX escape)

## Rich Output

`rich.print()` with semantic colors. Single multiline call. Never multiple individual prints for related output. See `datascience:rich-output`.

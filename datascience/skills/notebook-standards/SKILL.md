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

Default: pin ONE specific GPU by its **UUID** - reproducible across reboots, driver reloads, and hardware changes, immune to index reshuffling. Ask the user once at build time which behaviour they want:

- **Pin a specific GPU** (default) - pick the best card (highest compute capability, then most free memory) and hardcode its UUID
- **Auto-pick a free GPU** - only when the user says "pick whatever is free" - resolve the freest card at runtime (snippet in `GPU-SETUP.md`)

```python
import os

# Deterministic ordering so a UUID/index always names the same physical card
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
# Pin by UUID (from `nvidia-smi -L`) - survives reboots and hardware changes
os.environ["CUDA_VISIBLE_DEVICES"] = "GPU-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import torch  # CUDA reads the env vars once, here - never set them after this import
```

Why UUID, not the integer index: CUDA's default order is `FASTEST_FIRST`, not nvidia-smi's PCI order, so `CUDA_VISIBLE_DEVICES=2` can grab a different physical card than nvidia-smi's GPU 2. A UUID names one specific card and is immune to ordering policy and to enumeration shuffling when cards are added or replaced. See `GPU-SETUP.md` for the full mechanism and the auto-pick-free snippet.

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

All hyperparameters defined here with inline `# comment` per field. End with a Rich render that groups fields into sections so a scrolling reader can scan structure without reading code. Canonical template:

```python
from rich import print as rprint

# Model
MODEL_NAME = "answerdotai/ModernBERT-base"   # 149M params, 8192 token context
MAX_TOKEN_LENGTH = 512                        # cap input sequences

# Training
BATCH_SIZE = 32                               # per device
EPOCHS = 3
LR = 2e-5
WEIGHT_DECAY = 0.01
WARMUP_RATIO = 0.1

# Paths
DATA_PATH = Path("../data/processed/train.parquet")
OUTPUT_DIR = Path("../models/v1")

# Device - resolved at runtime; GPU info shown in render below
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A"

rprint(f"""[bold cyan]Configuration[/bold cyan]
[dim]{"─" * 40}[/dim]
[bold]Model[/bold]
  Name: [yellow]{MODEL_NAME}[/yellow]
  Max token length: [yellow]{MAX_TOKEN_LENGTH}[/yellow]

[bold]Training[/bold]
  Batch size: [yellow]{BATCH_SIZE}[/yellow] [dim](per device)[/dim]
  Epochs: [yellow]{EPOCHS}[/yellow]
  Learning rate: [yellow]{LR}[/yellow]
  Weight decay: [yellow]{WEIGHT_DECAY}[/yellow]
  Warmup ratio: [yellow]{WARMUP_RATIO}[/yellow]

[bold]Paths[/bold]
  Data: [cyan]{DATA_PATH}[/cyan]
  Output: [cyan]{OUTPUT_DIR}[/cyan]

[bold]Device[/bold]
  Using: [green]{device}[/green]
  GPU: [cyan]{gpu_name}[/cyan]
""")
```

Colour grammar (cross-link to `datascience:rich-output` for full palette):
- `[bold]Section name[/bold]` - sub-section headers within the render
- `[yellow]value[/yellow]` - numeric hyperparameters
- `[cyan]value[/cyan]` - paths, model IDs, identifiers
- `[green]value[/green]` - active device / runtime state
- `[dim]hint[/dim]` - parenthetical context, dividers

**GPU rule (mandatory when CUDA is used)**: the rendered Configuration MUST include the GPU's `torch.cuda.get_device_name(0)` in a `[bold]Device[/bold]` sub-section. Catches the silent wrong-device bug where `CUDA_VISIBLE_DEVICES` was set wrong but `device="cuda"` still works on the wrong GPU. See `GPU-SETUP.md` for the full Device-block template (adds compute capability + memory).

**Minimal variant** (for notebooks without sub-sections, e.g. quick data-loading scripts):

```python
rprint(f"""[white]Configuration[/white]
  Model: [cyan]{MODEL_NAME}[/cyan]
  Batch size: [yellow]{BATCH_SIZE}[/yellow]
  Device: [green]{device}[/green]
  GPU: [cyan]{gpu_name}[/cyan]
""")
```

Use this when the notebook has <5 hyperparameters and no natural sub-sections. The sectioned template above is the default.

## Section overviews (MANDATORY)

Each section MUST have a 1-2 sentence overview directly below its `## Section Name` header, BEFORE the first code cell. Bullet lists (3-5 items) acceptable when the content is naturally listy. The overview answers "what does this section do, and why" so a scrolling reader can decide whether to expand the code or skip. Empty sections without overviews fail the standard.

Sole exception: the file-level Header section (the very top of the notebook) - the header itself IS the overview for the notebook as a whole.

### Example overviews

`## Configuration` ->
> Training hyperparameters for the ModernBERT contrastive run. Lower temperature increases discrimination but risks gradient instability; larger effective batch size improves contrastive learning but requires more memory.

`## Data Loading` ->
> Loads the cached parquet from `data/processed/`. Schema is validated against the training contract; rows with null targets are dropped here so downstream cells assume clean input.

`## Evaluation` ->
> Reports the four metrics tracked across iterations:
> - **Accuracy** on the held-out test split
> - **F1 macro** to weight rare classes equally
> - **Latency p95** measured on a 1k-row sample
> - **Memory peak** captured via `torch.cuda.max_memory_allocated`

The overview lives in the SAME markdown cell as the header (so you don't need a third cell type). Pattern:

```markdown
## Configuration

Training hyperparameters for the ModernBERT contrastive run. Lower
temperature increases discrimination but risks gradient instability.
```

## LaTeX in markdown cells

- **Render math as equations** - inline `$f(x) = ax + b$`, display `$$P(A|B) = \frac{P(B|A) P(A)}{P(B)}$$`. JupyterLab renders both via MathJax. USE these for any actual mathematical content
- **Escape dollar amounts in prose** - when `$` means "dollar", escape as `\$5` so MathJax does not eat everything between the two unescaped dollars
- **In repo `.md` files OUTSIDE notebooks** (READMEs, SKILL.md, docs/): workspace rule applies - escape always with `\$`, no equations expected (the rendered Markdown surfaces don't run MathJax)

## Cell Rules

- Markdown header before each code section, with overview below (see above)
- One logical operation per cell
- Progress bars in SEPARATE cell from setup text - avoids overwriting

## Rich Output

`rich.print()` with semantic colors. Single multiline call. Never multiple individual prints for related output. See `datascience:rich-output`.

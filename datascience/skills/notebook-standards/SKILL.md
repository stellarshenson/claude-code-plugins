---
name: notebook-standards
description: Jupyter notebook structure standards - section order, GPU-by-UUID selection, grouped imports, the configuration render, rich-output colours, equations, and inline figures. Use when creating or modifying a Jupyter notebook (.ipynb or Jupytext .py), or when the user mentions notebook structure, the config cell, GPU selection, rich output, notebook equations, or saving / exporting figures.
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

Why UUID not index: CUDA's `FASTEST_FIRST` order ≠ nvidia-smi PCI order, so `CUDA_VISIBLE_DEVICES=2` can grab a different card; a UUID names one card, immune to ordering and re-enumeration. Full mechanism + auto-pick-free snippet: `GPU-SETUP.md`.

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

Colour grammar (see `references/rich-output.md` for the full semantic palette):
- `[bold]Section name[/bold]` - sub-section headers within the render
- `[yellow]value[/yellow]` - numeric hyperparameters
- `[cyan]value[/cyan]` - paths, model IDs, identifiers
- `[green]value[/green]` - active device / runtime state
- `[dim]hint[/dim]` - parenthetical context, dividers

**GPU rule (mandatory when CUDA is used)**: the rendered Configuration MUST include the GPU's `torch.cuda.get_device_name(0)` in a `[bold]Device[/bold]` sub-section. Catches the silent wrong-device bug where `CUDA_VISIBLE_DEVICES` was set wrong but `device="cuda"` still works on the wrong GPU. See `GPU-SETUP.md` for the full Device-block template (adds compute capability + memory).

**Minimal variant** - notebook with <5 hyperparameters and no natural sub-sections: a flat `rprint` of Model / Batch size / Device / GPU instead of the sectioned block. The sectioned template above is the default.

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

## Equations in markdown cells

Write math liberally - every quantitative relationship as an equation, not prose. Unicode glyphs inline (`τ(i) = Σⱼ Tᵢⱼ·posⱼ / Σⱼ Tᵢⱼ`) so they survive copy-paste; each full/display equation as a standalone `$$...$$` block on its own line, since these are rasterised to images later for export surfaces (Medium, DOCX) that do not run MathJax. Escape dollar amounts in prose as `\$`. See `references/equations.md` for the full glyph set and rules.

## Cell Rules

- Markdown header before each code section, with overview below (see above)
- One logical operation per cell
- Progress bars in SEPARATE cell from setup text - avoids overwriting

## Rich Output

`rich.print()` with semantic colors. Single multiline call. Never multiple individual prints for related output. See `references/rich-output.md` for the full semantic palette, status colours, ML-eval and table-column colours.

## Figures (inline by default)

Plots render inline in the notebook - the `.ipynb` itself is the artefact. Do NOT write figures to disk by default.

- **Inline display** - end a plotting cell with `plt.show()` (or let the figure be the cell's last expression); the rendered image is captured in the notebook output
- **No `plt.savefig` unless asked** - do not add file exports (`plt.savefig(...)`, `fig.savefig(...)`) on your own; the inline figure is enough. Add an export only when the user explicitly asks to export/save figures
- **When export IS requested** - write to a named path (e.g. `reports/figures/<name>.png`), `dpi` 150+, `bbox_inches="tight"`, and still keep the inline `plt.show()`
- **Section 9 Save/Export** covers model and data artefacts, not figures - figures stay inline unless an export is explicitly requested

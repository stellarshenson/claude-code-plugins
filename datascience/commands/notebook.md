---
description: Create a new Jupyter notebook with proper structure
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion]
argument-hint: "notebook purpose, e.g. 'train YOLOv8 on custom dataset'"
---

# Create New Notebook

Scaffold a properly structured Jupytext notebook following all datascience standards.

## Steps

1. ASK the user:
   - **Purpose** (what the notebook does)
   - **Author initials** (default: kj)
   - **GPU needed?** (yes/no - determines if GPU selection cell is included)
   - **Libraries needed** (torch, polars, sklearn, transformers, etc.)

2. Determine the next notebook number by scanning existing `NN-*.py` files in the current directory or `notebooks/` directory.

3. Create `<NN>-<initials>-<description>.py` in Jupytext percent format with:

```python
# %% [markdown]
# # <Title>
#
# **Author**: <Name>
#
# <Purpose description>
#
# ## Approach
#
# **1. <Step>**
# - Details
#
# **Output**: What the notebook produces

# %% GPU Selection (only if GPU needed)
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# %% Imports
%load_ext autoreload
%autoreload 2

# Standard library
from pathlib import Path

# <grouped imports based on user's library choices>

# Rich console output
import rich.jupyter as rich

# %% Reproducibility
import random, numpy as np
def set_seed(seed=42):
    random.seed(seed); np.random.seed(seed)
    # torch seeds if GPU
set_seed(42)

# %% Configuration
# <params with inline comments>

rich.print(f"""[white]Configuration[/white]
  ...
""")

# %% [markdown]
# ## Data Loading

# %%
# Data loading code here

# %% [markdown]
# ## Processing

# %%
# Processing code here

# %% [markdown]
# ## Results

# %%
# Results and evaluation
```

4. Report: filename created, next steps suggested.

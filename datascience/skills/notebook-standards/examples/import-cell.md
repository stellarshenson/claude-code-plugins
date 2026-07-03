# Import cell

One cell holds every import, grouped by category with a blank line and a `# Category` heading per group, and an inline `# comment` on each import stating what it is for. Mirror this shape - the specific libraries are illustrative, the grouping and annotation are the convention.

```python
%load_ext autoreload
%autoreload 2

# Standard library
import os  # Environment variables
import random  # Random seed for reproducibility
from pathlib import Path  # File path handling

# Data processing
import numpy as np  # Numerical operations
import polars as pl  # DataFrame operations (fast, no pandas)

# Deep learning
import torch  # PyTorch core
import torch.nn as nn  # Neural network layers
import torch.nn.functional as F  # Functional operations (normalize, etc.)
from torch.utils.data import DataLoader, Dataset  # Data loading utilities
from torch.optim.lr_scheduler import LambdaLR  # Custom learning rate scheduler

# Transformers
from transformers import AutoTokenizer, AutoModel  # HuggingFace model loading

# Machine learning utilities
from sklearn.model_selection import train_test_split  # Data splitting

# Contrastive learning
from pytorch_metric_learning.losses import NTXentLoss  # NT-Xent (InfoNCE) loss

# Rich console output
from rich import print as rprint  # Formatted console printing
from rich.progress import (  # Progress bar components
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
)
```

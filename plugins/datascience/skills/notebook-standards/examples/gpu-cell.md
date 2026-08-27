# GPU selection cell

First code cell, before any torch/tf/jax import. Mirror this shape - the UUID is illustrative, the ordering and the placement are the convention.

```python
import os

# Deterministic ordering so a UUID/index always names the same physical card
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
# Pin by UUID (from `nvidia-smi -L`) - survives reboots and hardware changes
os.environ["CUDA_VISIBLE_DEVICES"] = "GPU-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import torch  # CUDA reads the env vars once, here - never set them after this import
```

Auto-pick-free snippet, multi-GPU limits, the Device render block, pitfalls: `../references/gpu-setup.md`.

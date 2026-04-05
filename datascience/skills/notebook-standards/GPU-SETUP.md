# GPU Selection for Multi-GPU Systems

## Quick Start

**CRITICAL**: Always set `CUDA_VISIBLE_DEVICES` before importing torch/tensorflow/jax:

```python
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '0'  # nvidia-smi GPU index

import torch  # or tensorflow, jax, etc.
```

## GPU Selection Pattern

### 1. Identify Available GPUs

```bash
nvidia-smi --query-gpu=index,name,compute_cap,memory.total --format=csv,noheader
```

**Output example:**
```
0, NVIDIA RTX 5090, 12.0, 32768 MiB
1, NVIDIA RTX 5000 Ada, 8.9, 32768 MiB
```

### 2. Select Best GPU

**Priority order**:
1. Highest compute capability (newer architecture)
2. Most available memory
3. Lowest current utilization

**Common architectures** (newest first):
- Blackwell: compute 12.x (RTX 5090, H200)
- Hopper: compute 9.x (H100, H800)
- Ada Lovelace: compute 8.9 (RTX 5000 Ada, RTX 4090)
- Ampere: compute 8.x (A100, RTX 3090)

### 3. Set GPU Before Import

```python
import os

# Use nvidia-smi GPU index (0, 1, 2, etc.)
os.environ['CUDA_VISIBLE_DEVICES'] = '0'  # MUST be before torch import

import torch
```

### 4. Verify Selection

```python
import torch
print(f"Visible GPUs: {torch.cuda.device_count()}")  # Should be 1
print(f"GPU 0: {torch.cuda.get_device_name(0)}")     # Should be target GPU
```

### 5. Display GPU Info with Rich (Notebooks)

In Jupyter notebooks, display GPU configuration using Rich for formatted output:

```python
import rich.jupyter as rich

device = 'cuda' if torch.cuda.is_available() else 'cpu'
gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A'
cuda_visible = os.environ.get('CUDA_VISIBLE_DEVICES', 'not set')

rich.print(f"""[white]Device:[/white]
  Device: [cyan]{device}[/cyan]
  GPU: [cyan]{gpu_name}[/cyan]
  CUDA_VISIBLE_DEVICES: [cyan]{cuda_visible}[/cyan]
""")
```

Include this in the Configuration cell to confirm GPU selection.

### 6. Monitor During Execution

```bash
watch -n 1 'nvidia-smi --query-gpu=index,name,memory.used,utilization.gpu --format=csv,noheader'
```

## Multi-GPU Training

**Limitations**:
- Requires homogeneous GPU architectures (same model)
- Requires same compute capability
- Mixed architectures cause NCCL errors (`ncclUnhandledCudaError`)

**For multi-GPU**:
```python
os.environ['CUDA_VISIBLE_DEVICES'] = '0,1,2'  # Multiple GPUs
```

## Common Pitfalls

1. **Index mismatch**: nvidia-smi indices may differ from torch.cuda indices
   - Solution: Always use CUDA_VISIBLE_DEVICES with nvidia-smi index

2. **Late environment variable**: Setting CUDA_VISIBLE_DEVICES after torch import
   - Solution: Set before any GPU library imports

3. **Wrong device in training**: Using `device='cuda:1'` after isolation
   - Solution: After isolation, always use `device=0` or `device='cuda:0'`

## Template Script

```python
#!/usr/bin/env python3
import os

# GPU Selection - MUST be first
os.environ['CUDA_VISIBLE_DEVICES'] = '0'  # nvidia-smi GPU index

import torch
from your_library import YourModel

# Verify
assert torch.cuda.is_available(), "CUDA not available"
print(f"Using GPU: {torch.cuda.get_device_name(0)}")

# Train (always device=0 after isolation)
model = YourModel()
model.train(data='data.yaml', device=0)
```

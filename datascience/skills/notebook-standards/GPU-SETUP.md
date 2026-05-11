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

### 5. Display GPU Info with Rich in the Configuration Cell

**Mandatory when the notebook uses CUDA.** The Configuration cell's Rich render MUST include a `[bold]Device[/bold]` sub-section showing the GPU name. Without it the agent + human reader cannot tell whether `CUDA_VISIBLE_DEVICES` actually selected the intended device. Catches the silent wrong-device bug.

Capture the device details right above the Rich render (still inside the Configuration cell):

```python
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A"
gpu_compute_cap = (
    f"{torch.cuda.get_device_properties(0).major}."
    f"{torch.cuda.get_device_properties(0).minor}"
    if torch.cuda.is_available()
    else "N/A"
)
gpu_memory_gb = (
    torch.cuda.get_device_properties(0).total_memory / 1e9
    if torch.cuda.is_available()
    else 0
)
```

Embed in the Rich render as the last sub-section so it sits next to the resolved device:

```python
from rich import print as rprint

rprint(f"""[bold cyan]Configuration[/bold cyan]
[dim]{"─" * 40}[/dim]
[bold]Model[/bold]
  ...

[bold]Device[/bold]
  Using: [green]{device}[/green]
  GPU: [cyan]{gpu_name}[/cyan]
  Compute cap: [yellow]{gpu_compute_cap}[/yellow]
  Memory: [yellow]{gpu_memory_gb:.1f} GB[/yellow]
""")
```

**Verification rule**: if you import torch BEFORE setting `CUDA_VISIBLE_DEVICES`, the env var has no effect for the rest of the process. Always set the env var in the GPU Selection section (notebook section 2) BEFORE the Imports section. The Rich render's `GPU:` line is the eyes-on confirmation that this ordering worked.

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

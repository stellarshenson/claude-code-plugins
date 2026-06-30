# GPU Selection for Multi-GPU Systems

**Contents**: Quick Start · Selection Pattern (identify → select → set → verify → Rich Device block → monitor) · How UUID Pinning Works · Auto-pick a Free GPU · Multi-GPU Training · Common Pitfalls · Template Script

One-line model: pin one GPU by UUID, set the env vars before `import torch`, let the Rich Device block confirm the pick.

## Quick Start

**Default: pin ONE specific GPU by its UUID.** At notebook-build time ask the user once which behaviour they want - a pinned card (default, reproducible) or auto-selection of the freest GPU. Only switch to auto-pick if they say "pick whatever is free".

**CRITICAL**: set the GPU env vars BEFORE importing torch/tensorflow/jax - the CUDA runtime reads them once, at the first CUDA call:

```python
import os

os.environ['CUDA_DEVICE_ORDER'] = 'PCI_BUS_ID'                      # stable ordering
os.environ['CUDA_VISIBLE_DEVICES'] = 'GPU-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'  # UUID from `nvidia-smi -L`

import torch  # or tensorflow, jax, etc.
```

## GPU Selection Pattern

### 1. Identify Available GPUs

```bash
# include the UUID - this is what you pin against
nvidia-smi --query-gpu=index,uuid,name,compute_cap,memory.total,memory.free --format=csv,noheader
```

**Output example:**
```
0, GPU-3890b0cf-..., NVIDIA RTX A4000, 8.6, 16376 MiB, 16114 MiB
1, GPU-a44e514a-..., NVIDIA RTX PRO 6000 Blackwell, 12.0, 98304 MiB, 97000 MiB
2, GPU-c15a4c9a-..., NVIDIA RTX 5000 Ada, 8.9, 32768 MiB, 32000 MiB
```

`nvidia-smi -L` lists the same UUIDs on their own. The UUID is the stable handle: it survives reboots, driver reloads, and adding/removing/replacing other cards.

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

os.environ['CUDA_DEVICE_ORDER'] = 'PCI_BUS_ID'  # align ordering to nvidia-smi
# Pin by UUID (preferred) - names one physical card regardless of ordering policy
os.environ['CUDA_VISIBLE_DEVICES'] = 'GPU-c15a4c9a-...'  # MUST be before torch import

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

**Verification rule**: the Rich render's `GPU:` line is the eyes-on confirmation the env var took effect - set it in GPU Selection, before the Imports section (see Quick Start).

### 6. Monitor During Execution

```bash
watch -n 1 'nvidia-smi --query-gpu=index,name,memory.used,utilization.gpu --format=csv,noheader'
```

## How UUID Pinning Works

- Every GPU has a persistent **UUID** assigned by the driver (`nvidia-smi -L`). Stable across reboots, driver reloads, and adding/removing/replacing other cards
- `CUDA_VISIBLE_DEVICES` accepts a UUID, not only an index. The CUDA runtime reads it once at initialization (first CUDA call), masks every GPU whose UUID does not match, and re-indexes the survivors from 0 - so the pinned card becomes `cuda:0` and `torch.cuda.get_device_name(0)` is it
- **Why UUID over the integer index**: CUDA's `FASTEST_FIRST` default ≠ nvidia-smi's PCI order, so an index can grab the wrong card; `CUDA_DEVICE_ORDER=PCI_BUS_ID` realigns them but a UUID sidesteps it - it names one card, immune to ordering and re-enumeration
- **Must be set before `import torch`** - the runtime reads the variable once at context creation; setting it after the CUDA context exists has no effect

## Auto-pick a Free GPU (opt-in)

Use ONLY when the user asked for "whatever is free". Resolves the freest card at runtime and pins its UUID before importing torch. Pure stdlib + `nvidia-smi`, no extra dependency:

```python
import os, subprocess

# Priority: most free memory, then lowest utilization
rows = subprocess.check_output([
    "nvidia-smi",
    "--query-gpu=uuid,memory.free,utilization.gpu",
    "--format=csv,noheader,nounits",
], text=True).strip().splitlines()
cand = [(u.strip(), int(m), int(util)) for u, m, util in (r.split(",") for r in rows)]
best_uuid = max(cand, key=lambda x: (x[1], -x[2]))[0]  # max free mem, min util

os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = best_uuid
os.environ["TOKENIZERS_PARALLELISM"] = "false"
print(f"Auto-selected GPU {best_uuid}")

import torch  # reads the env vars here
```

The Configuration cell's Rich `Device` block (see below) then confirms which physical card was picked.

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

1. **Index mismatch**: CUDA's `FASTEST_FIRST` order differs from nvidia-smi's PCI order, so an index can name the wrong physical card
   - Solution: pin by UUID, or set `CUDA_DEVICE_ORDER=PCI_BUS_ID` when you must use an index

2. **Late environment variable**: Setting CUDA_VISIBLE_DEVICES after torch import
   - Solution: Set before any GPU library imports

3. **Wrong device in training**: Using `device='cuda:1'` after isolation
   - Solution: After isolation, always use `device=0` or `device='cuda:0'`

## Template Script

```python
#!/usr/bin/env python3
import os

# GPU Selection - MUST be first
os.environ['CUDA_DEVICE_ORDER'] = 'PCI_BUS_ID'
os.environ['CUDA_VISIBLE_DEVICES'] = 'GPU-c15a4c9a-...'  # UUID from `nvidia-smi -L`

import torch
from your_library import YourModel

# Verify
assert torch.cuda.is_available(), "CUDA not available"
print(f"Using GPU: {torch.cuda.get_device_name(0)}")

# Train (always device=0 after isolation)
model = YourModel()
model.train(data='data.yaml', device=0)
```

# Configuration cell - canonical template

Mirror this for the Configuration section (skill `notebook-standards`). All hyperparameters in one cell, inline `# comment` per field, closed by a Rich render that groups fields into sections so a scrolling reader scans structure without reading code.

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

Colour grammar (full semantic palette in `../references/rich-output.md`):
- `[bold]Section name[/bold]` - sub-section headers within the render
- `[yellow]value[/yellow]` - numeric hyperparameters
- `[cyan]value[/cyan]` - paths, model IDs, identifiers
- `[green]value[/green]` - active device / runtime state
- `[dim]hint[/dim]` - parenthetical context, dividers

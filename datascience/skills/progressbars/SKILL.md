---
name: progressbars
description: Use this skill when implementing progress bars in Python scripts or notebooks. Covers tqdm (classic) and rich (modern) styles, library configuration, Jupyter compatibility, and completion fixes.
---

# Progress Bars Skill

Implements progress bars in Python scripts and Jupyter notebooks. Full reference in the sections below.

## Selection Rule

**MANDATORY**: Always ask the user which progress bar style to use (classic or modern) before implementing. Do not assume based on context.

## Quick Reference

### Classic (tqdm)

Works everywhere - terminals, Jupyter, IDE consoles. Renders as native ipywidgets in Jupyter when `ipywidgets` is installed.

**Dependencies**: `tqdm`, `ipywidgets` (for Jupyter widget rendering)

**Import**: `from tqdm.auto import tqdm` - the `.auto` submodule auto-selects the best backend (text in terminal, ipywidgets in Jupyter).

```python
from tqdm.auto import tqdm

# determinate
for item in tqdm(items, desc="Processing", unit="file"):
    process(item)

# with ThreadPoolExecutor
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=16) as executor:
    futures = {executor.submit(fn, item): item for item in items}
    for future in tqdm(as_completed(futures), total=len(futures), desc="Loading", unit="item"):
        result = future.result()
```

### Modern (rich)

Feature-rich with spinners, elapsed time, ETA. Works in both terminals and Jupyter notebooks.

**Dependencies**: `rich`

```python
from rich.progress import (
    BarColumn, MofNCompleteColumn, Progress,
    SpinnerColumn, TextColumn, TimeElapsedColumn,
)

with Progress(
    SpinnerColumn(),
    TextColumn("[steel_blue]{task.description}"),
    BarColumn(bar_width=40),
    MofNCompleteColumn(),
    TimeElapsedColumn(),
    refresh_per_second=10,
) as progress:
    task = progress.add_task("Processing", total=len(items))
    for item in items:
        process(item)
        progress.advance(task)
    # force completion (prevents N-1 issue)
    progress.update(task, completed=len(items))
    progress.refresh()
```

## Modern (rich) - Completion Fixes

Common issues preventing rich Progress bars from completing properly:

- **N-1 issue (bar stops one short)**: most common with parallel execution. After the loop, always call `progress.update(task, completed=total)` then `progress.refresh()` to force 100%. Defensive practice for sequential loops too
- **Bar disappears**: `transient=True` clears the bar on context exit. Use `transient=False` (default) to keep it visible
- **Stuck below 100%**: `total=` doesn't match `advance()` call count. Always advance on every iteration, even when skipping items
- **Spinner won't stop**: all tasks must reach `completed == total`. Verify total matches actual iteration count
- **Bar frozen**: default refresh is 10/sec. Use `refresh_per_second=10` for standard loops or call `progress.refresh()`
- **Multiple bars overwrite**: create tasks once before the loop, use `progress.reset(task, total=...)` per batch

Full troubleshooting with code examples in the sections below.

## Jupyter Compatibility

Both styles work in Jupyter notebooks:

- **tqdm.auto** + `ipywidgets` = native widget progress bars
- **rich Progress** = renders correctly in JupyterLab
- Always use `tqdm.auto` (not `tqdm.tqdm`) for automatic backend selection when using classic style

## Jupyter Output Ordering (rich)

In Jupyter, `logger.info()` and `print()` bypass Jupyter's display system (stderr/stdout), causing messages to appear below or interleaved with rich Progress bars. Use `rich.print()` instead - it shares the same output pipeline as Progress:

```python
from rich import print as rprint

rprint(f"found {len(items)} items")  # correct ordering guaranteed
with Progress(...) as progress:
    task = progress.add_task("Processing", total=len(items))
    ...
```

Full details in the sections below.

## pyproject.toml

```toml
[project]
dependencies = [
    "tqdm",      # classic progress bars
    # or
    "rich",      # modern progress bars
]

[project.optional-dependencies]
dev = [
    "ipywidgets",  # tqdm widget rendering in Jupyter
]
```

---
name: progressbars
description: Use this skill when implementing progress bars in Python scripts or notebooks. Covers tqdm (classic) and rich (modern) styles, library configuration, Jupyter compatibility, and completion fixes.
---

# Progress Bars Skill

Progress bars for Python scripts and Jupyter notebooks. Full reference below.

## Selection Rule

**MANDATORY**: Always ask user which style (classic or modern) before implementing. Never assume from context.

## Quick Reference

### Classic (tqdm)

Works everywhere - terminals, Jupyter, IDE consoles. Renders as native ipywidgets in Jupyter when `ipywidgets` installed.

**Dependencies**: `tqdm`, `ipywidgets` (Jupyter widget rendering)

**Import**: `from tqdm.auto import tqdm` - `.auto` submodule auto-selects backend (text in terminal, ipywidgets in Jupyter).

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

Feature-rich: spinners, elapsed time, ETA. Works in terminals and Jupyter notebooks.

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

- **N-1 issue (bar stops one short)**: most common with parallel execution. After loop, always call `progress.update(task, completed=total)` then `progress.refresh()` to force 100%. Defensive practice for sequential loops too
- **Bar disappears**: `transient=True` clears bar on context exit. `transient=False` (default) keeps it visible
- **Stuck below 100%**: `total=` doesn't match `advance()` call count. Always advance every iteration, even when skipping items
- **Spinner won't stop**: all tasks must reach `completed == total`. Verify total matches actual iteration count
- **Bar frozen**: default refresh 10/sec. `refresh_per_second=10` for standard loops or call `progress.refresh()`
- **Multiple bars overwrite**: create tasks once before loop, use `progress.reset(task, total=...)` per batch

Full troubleshooting with code examples below.

## Jupyter Compatibility

Both styles work in Jupyter:

- **tqdm.auto** + `ipywidgets` = native widget progress bars
- **rich Progress** = renders correctly in JupyterLab
- Always `tqdm.auto` (not `tqdm.tqdm`) for automatic backend selection in classic style

## Jupyter Output Ordering (rich)

In Jupyter, `logger.info()` and `print()` bypass Jupyter display system (stderr/stdout), causing messages to appear below or interleaved with rich Progress bars. Use `rich.print()` instead - shares same output pipeline as Progress:

```python
from rich import print as rprint

rprint(f"found {len(items)} items")  # correct ordering guaranteed
with Progress(...) as progress:
    task = progress.add_task("Processing", total=len(items))
    ...
```

Full details below.

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

---
name: progressbars
description: Use this skill when implementing progress bars in Python scripts or notebooks. Covers tqdm (classic) and rich (modern) styles, library configuration, Jupyter compatibility, and completion fixes.
---

# Progress Bars Skill

Progress bars for Python scripts and Jupyter.

## Toolchain gate (MANDATORY - run before anything else)

Run this first, every session, before any other work. The upgrade always runs; a version mismatch blocks.

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && { echo "STALE: library $LIB != plugin $PLUG - refusing to run on a mismatched CLI; re-run the upgrade"; exit 1; }
echo "toolkit $LIB"
```

Both branches exit non-zero and neither is advisory: an absent library (`FATAL`) and a version mismatch (`STALE`). A mismatch means the CLI is not the one this file was written against, so its documented flags and rules are unverified. Report the line and stop; do not work around it.

## Selection Rule

**MANDATORY**: ASK user which style (classic or modern) before implementing. Never assume.

## Quick Reference

### Classic (tqdm)

Works everywhere - terminals, Jupyter, IDE. Renders native ipywidgets in Jupyter when `ipywidgets` installed.

**Deps**: `tqdm`, `ipywidgets` (Jupyter widgets)

**Import**: `from tqdm.auto import tqdm` - `.auto` auto-selects backend.

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

Spinners, elapsed time, ETA. Terminals + Jupyter.

**Deps**: `rich`

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

- **N-1 issue (stops one short)**: common with parallel execution. After loop: `progress.update(task, completed=total)` then `progress.refresh()`. Defensive for sequential too
- **Bar disappears**: `transient=True` clears on context exit. `transient=False` (default) keeps visible
- **Stuck below 100%**: `total=` doesn't match `advance()` count. Advance every iteration, even when skipping
- **Spinner won't stop**: all tasks must reach `completed == total`. Verify total matches iteration count
- **Bar frozen**: default refresh 10/sec. `refresh_per_second=10` or call `progress.refresh()`
- **Multiple bars overwrite**: create tasks before loop, use `progress.reset(task, total=...)` per batch

## Jupyter Compatibility

- **tqdm.auto** + `ipywidgets` = native widget bars
- **rich Progress** renders in JupyterLab
- Always `tqdm.auto` (not `tqdm.tqdm`) for classic style

## Jupyter Output Ordering (rich)

`logger.info()` and `print()` bypass Jupyter display (stderr/stdout), causing messages to appear below or interleaved with rich Progress. Use `rich.print()` instead - shares Progress pipeline:

```python
from rich import print as rprint

rprint(f"found {len(items)} items")  # correct ordering guaranteed
with Progress(...) as progress:
    task = progress.add_task("Processing", total=len(items))
    ...
```

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

---
description: Add or fix progress bars in a notebook or script - choose classic (tqdm) or modern (rich) style
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion]
argument-hint: "path to file to add progress bars to"
---

# Apply Progress Bars

Read a notebook or script and add progress bars to long-running loops, or fix existing broken progress bars.

## Step 1: ASK the user

"Which progress bar style?
1. **Classic (tqdm)** - works everywhere, ipywidgets in Jupyter
2. **Modern (rich)** - spinners, elapsed time, ETA, styled output"

## Step 2: Find loops to instrument

Scan the file for:
- `for` loops over large collections (lists, DataFrames, file lists)
- `ThreadPoolExecutor` / `ProcessPoolExecutor` with `as_completed`
- Training loops (epoch, batch iterations)
- File processing loops (reading/writing multiple files)
- Any loop with a comment like "slow", "takes time", "long running"

## Step 3: Apply

For each identified loop:
- Wrap iterable with `tqdm(items, desc="...", unit="...")` (classic)
- OR wrap in `with Progress(...) as progress:` block (modern)
- Add completion fix for rich: `progress.update(task, completed=total)` after loop
- Ensure progress bars are in SEPARATE cell from setup text (Jupyter)

## Step 4: Fix existing broken bars

- tqdm without `.auto`: change `from tqdm import tqdm` to `from tqdm.auto import tqdm`
- rich bar stuck at N-1: add `progress.update(task, completed=total); progress.refresh()`
- rich bar disappeared: check `transient=True` and remove it
- logger/print interleaved with rich: change to `rich.print()`

## Rules

- ALWAYS ask classic vs modern first
- In Jupyter: setup text in separate cell from Progress bar
- Use `tqdm.auto` (never `tqdm.tqdm`) for automatic backend selection
- Rich progress: always add completion fix after loop

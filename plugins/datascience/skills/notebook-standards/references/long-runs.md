# Long Runs - Bar Granularity and Checkpoint/Restore

Resource for the `notebook-standards` skill. Carries how fine a progress bar has to be, nested bars, where checkpoints go, how their files are named, and the scan-disk restore mechanic. SKILL.md keeps the mandate - a long run does BOTH a fine-grained bar AND checkpoint-with-restore, missing either is a defect not a style choice - plus the one-line trigger for each.

## Bar granularity

`total` counts the actual unit of work, so the bar moves often and the ETA is honest.

- **Real unit, not a convenient one** - an LLM judge over a corpus tracks per-document (hundreds of steps), never a handful of coarse chunks
- **Why coarse fails** - a 4-step bar sitting minutes per step tells the reader nothing: no motion, no usable ETA, no way to tell a slow run from a hung one
- **Cost sets the resolution** - the costlier each step, the finer the bar

## Nested bars

- **Nested work gets a nested bar** - outer epoch, inner batch

## Checkpoint location

A run measured in minutes persists intermediate results every N steps or per epoch.

- **Primary** - `checkpoints/` under the output dir
- **Fallback** - `tempfile.gettempdir()`
- **Why** - partial work survives a crash, a kernel restart, or a mid-run inspection

## Checkpoint filenames

- **Step/epoch in the name** - `ckpt_epoch03.pt`, `batch_00500.parquet`
- **Why** - the name is what the restore scan matches on to decide what is already done

## Restore on restart - the whole point

- **Scan, load, compute the gap** - on re-run the cell scans what is already on disk, loads it, and computes only what is missing
- **A checkpoint written but never read back is dead weight**

## Bar mechanics

- **tqdm vs rich, Jupyter quirks, completion fixes** - `datascience:progressbars` skill

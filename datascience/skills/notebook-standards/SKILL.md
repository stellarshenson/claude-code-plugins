---
name: notebook-standards
description: Jupyter notebook structure standards - section order, GPU-by-UUID selection, grouped imports, the configuration render, rich-output colours, equations, inline figures, matplotlib plotting, progress bars, and checkpointing long runs. Use when creating or modifying a Jupyter notebook (.ipynb or Jupytext .py), or when the user mentions notebook structure, the config cell, GPU selection, rich output, notebook equations, matplotlib plots, colormaps, saving / exporting figures, progress bars, or checkpointing intermediate results.
---

# Notebook Structure Standards

Patterns for Jupyter notebook creation.

## Mandatory Section Order

1. **Header** - mandatory title + author + date + purpose, then an optional menu (extra provenance, mechanism overview, approach, outputs) - problem-specific (see below)
2. **GPU Selection** - `CUDA_VISIBLE_DEVICES` BEFORE any torch/tf/jax import
3. **Imports** - ALL imports in one cell, grouped, with inline comments, autoreload enabled
4. **Reproducibility** - `set_seed(42)` for random, numpy, torch
5. **Configuration** - all hyperparameters in one cell, inline comments, rich summary at end
6. **Data Loading**
7. **Model/Processing**
8. **Execution** (training, inference)
9. **Save/Export**
10. **Evaluation/Summary**

## Header (first markdown cell)

Orients the reader and doubles as the notebook-level overview (the Header needs no separate overview). Four blocks are mandatory; the rest is a problem-specific menu - pick what fits, drop what does not.

**Mandatory - every notebook**
- **Title** - `# <what the notebook does>`
- **Author + Date** - bold, each on its own `<br>`-terminated line so they stack: `**Author**: Name (initials) <br>` then `**Date**: YYYY-MM-DD <br>`. Every stacked provenance line ends with `<br>` - without it markdown soft-wraps them onto one line
- **Purpose** - one or two sentences: what the notebook produces and why it matters to the wider work; prose, not a task list

**Optional menu - add when the problem calls for it**
- **More provenance** - further `<br>`-terminated lines after Date: `**Pipeline stage**`, `**Dataset**`, `**Model**`, `**Branch**`
- **Mechanism overview** - a short paragraph on HOW the approach works when the method is non-obvious: the key model / algorithm / technique, what it computes, the operating regime a reader needs to trust the result
- **Approach** - `## Approach`, numbered verb-first steps, each naming its why
- **Outputs** - `## Outputs`, persisted artefacts plus what the notebook shows inline

**Math in the header** - inline expressions as unicode glyphs (`d(A,B) = Σᵢ ...`), any display equation as a standalone `$$...$$` block on its own line so it copies cleanly and rasterises for export; same rule as any markdown cell - see "Equations in markdown cells".

Example - mandatory blocks (Title, Author, Date, Purpose) plus optional pipeline-stage, mechanism, approach, outputs; note the trailing `<br>` on each stacked provenance line:

```markdown
# Document Segmentation with SaT

**Author**: Konrad Jelen (kj) <br>
**Date**: 2026-05-30 <br>
**Pipeline stage**: 1 - statement-level segmentation <br>

Splits a source document into atomic statements with the SaT `sat-3l-sm` segmenter - the first stage of the document-distance pipeline, so this split bounds the quality of every later measure.

Downstream each statement is embedded and two documents are compared by optimal transport over the pairwise-cost matrix C:

$$W(A, B) = \min_{T \in U(a, b)} \sum_{i, j} T_{ij}\, C_{ij}$$

## Approach
1. **Extract** raw text from the PDF - the corpus arrives as PDF, SaT needs plain text
2. **Segment** into sentence-level statements - the natural transport unit
3. **Persist** to parquet - a typed artefact the embedding stage consumes

## Outputs
- `data/interim/01-statements.parquet` - one row per statement (id, text, length)
- In-notebook: statement count, length stats, distribution histogram
```

## GPU Selection (MUST be first code cell)

Default: pin ONE specific GPU by its **UUID** - reproducible across reboots, driver reloads, and hardware changes, immune to index reshuffling. Ask the user once at build time which behaviour they want:

- **Pin a specific GPU** (default) - pick the best card (highest compute capability, then most free memory) and hardcode its UUID
- **Auto-pick a free GPU** - only when the user says "pick whatever is free" - resolve the freest card at runtime (snippet in `GPU-SETUP.md`)

```python
import os

# Deterministic ordering so a UUID/index always names the same physical card
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
# Pin by UUID (from `nvidia-smi -L`) - survives reboots and hardware changes
os.environ["CUDA_VISIBLE_DEVICES"] = "GPU-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import torch  # CUDA reads the env vars once, here - never set them after this import
```

Why UUID not index: CUDA's `FASTEST_FIRST` order ≠ nvidia-smi PCI order, so `CUDA_VISIBLE_DEVICES=2` can grab a different card; a UUID names one card, immune to ordering and re-enumeration. Full mechanism + auto-pick-free snippet: `GPU-SETUP.md`.

## Import Cell Pattern

- **One cell** - all imports together, never import later; sole exception is a use case that genuinely needs an import elsewhere (e.g. `torch` in the GPU-selection cell after `CUDA_VISIBLE_DEVICES` is set, per GPU Selection)
- **Grouped** - block by category with a blank line and a `# Category` heading per group
- **Annotated** - inline `# comment` on each import stating what it is for
- Full annotated template - `examples/import-cell.md`

## Configuration Cell

All hyperparameters defined here with inline `# comment` per field. End with a Rich render that groups fields into sections so a scrolling reader can scan structure without reading code - full mirrorable template + colour grammar in `examples/config-cell.md`.

**GPU rule (mandatory when CUDA is used)**: the rendered Configuration MUST include the GPU's `torch.cuda.get_device_name(0)` in a `[bold]Device[/bold]` sub-section. Catches the silent wrong-device bug where `CUDA_VISIBLE_DEVICES` was set wrong but `device="cuda"` still works on the wrong GPU. See `GPU-SETUP.md` for the full Device-block template (adds compute capability + memory).

**Minimal variant** - notebook with <5 hyperparameters and no natural sub-sections: a flat `rprint` of Model / Batch size / Device / GPU instead of the sectioned block. The sectioned template above is the default.

## Section overviews (MANDATORY)

Each section MUST have a 1-2 sentence overview directly below its `## Section Name` header, BEFORE the first code cell. Bullet lists (3-5 items) acceptable when the content is naturally listy. The overview answers "what does this section do, and why" so a scrolling reader can decide whether to expand the code or skip. Empty sections without overviews fail the standard.

Sole exception: the file-level Header section (the very top of the notebook) - the header itself IS the overview for the notebook as a whole.

### Example overviews

`## Configuration` ->
> Training hyperparameters for the ModernBERT contrastive run. Lower temperature increases discrimination but risks gradient instability; larger effective batch size improves contrastive learning but requires more memory.

`## Data Loading` ->
> Loads the cached parquet from `data/processed/`. Schema is validated against the training contract; rows with null targets are dropped here so downstream cells assume clean input.

`## Evaluation` ->
> Reports the four metrics tracked across iterations:
> - **Accuracy** on the held-out test split
> - **F1 macro** to weight rare classes equally
> - **Latency p95** measured on a 1k-row sample
> - **Memory peak** captured via `torch.cuda.max_memory_allocated`

The overview lives in the SAME markdown cell as the header (so you don't need a third cell type). Pattern:

```markdown
## Configuration

Training hyperparameters for the ModernBERT contrastive run. Lower
temperature increases discrimination but risks gradient instability.
```

## Equations in markdown cells

Write math liberally - every quantitative relationship as an equation, not prose. Unicode glyphs inline (`τ(i) = Σⱼ Tᵢⱼ·posⱼ / Σⱼ Tᵢⱼ`) so they survive copy-paste; each full/display equation as a standalone `$$...$$` block on its own line, since these are rasterised to images later for export surfaces (Medium, DOCX) that do not run MathJax. Escape dollar amounts in prose as `\$`. See `references/equations.md` for the full glyph set and rules.

## Cell Rules

- Markdown header before each code section, with overview below (see above)
- One logical operation per cell
- Progress bars in SEPARATE cell from setup text - avoids overwriting

## Rich Output

`rich.print()` with semantic colors. Single multiline call. Never multiple individual prints for related output. See `references/rich-output.md` for the full semantic palette, status colours, ML-eval and table-column colours.

## Progress and checkpoints

Any loop a reader would wait on shows a Rich progress bar, and any run measured in minutes writes intermediate checkpoints so a crash or a mid-run inspection never loses the work.

- **Progress bar by design** - every medium or long loop (batch inference, training epochs, per-file processing, API sweeps) wraps its iterable in a Rich `Progress`; a bare loop with no visible progress is a defect, not a style choice
- **Threshold** - a cell that runs more than a few seconds needs a bar; sub-second cells do not
- **Fine granularity** - `total` counts the real unit of work so the bar advances often and the ETA is honest; an LLM judge over a large corpus tracks per-document (hundreds of steps), never a handful of coarse chunks - a 4-step bar that sits minutes per step is uninformative. The costlier each step, the finer the bar
- **Separate cell** - the `Progress` block gets its own cell, away from setup prints, per Cell Rules
- **Checkpoint long runs** - a run measured in minutes persists intermediate results (every N steps or per epoch) to a temp dir - `tempfile.gettempdir()` or a `checkpoints/` under the output dir - so partial work survives a crash and stays inspectable mid-run
- **Named and resumable** - checkpoint files carry the step/epoch in the name (`ckpt_epoch03.pt`, `batch_00500.parquet`); on restart the cell skips work already on disk

## Figures (inline by default)

Plots render inline in the notebook - the `.ipynb` itself is the artefact. Do NOT write figures to disk by default.

- **Inline display** - end a plotting cell with `plt.show()` (or let the figure be the cell's last expression); the rendered image is captured in the notebook output
- **No `plt.savefig` unless asked** - do not add file exports (`plt.savefig(...)`, `fig.savefig(...)`) on your own; the inline figure is enough. Add an export only when the user explicitly asks to export/save figures
- **When export IS requested** - write to a named path (e.g. `reports/figures/<name>.png`), `dpi` 150+, `bbox_inches="tight"`, and still keep the inline `plt.show()`
- **Section 9 Save/Export** covers model and data artefacts, not figures - figures stay inline unless an export is explicitly requested

## Plotting (matplotlib)

Object-oriented API only - `fig, ax = plt.subplots(figsize=(w, h), constrained_layout=True)`, then `ax.` calls; the pyplot state machine silently draws onto the wrong axes in saved code.

- **`constrained_layout=True`** - default it on; auto-spaces labels, titles and colorbars so nothing overlaps or clips
- **Full-width figures** - to span the notebook width edge-to-edge, use a wide landscape `figsize` and reserve the margins by hand (`fig.subplots_adjust(left=0.05, right=0.99, ...)` for a panel grid, or `fig.add_axes([...])` for a single axes) with `constrained_layout` off; see `references/matplotlib.md`
- **Colormaps by data kind** - sequential (`viridis`) for magnitudes, diverging (`coolwarm`) for centred data, qualitative (`tab10`) for categories; never `jet`, default to colourblind-safe `viridis` / `cividis`
- **Reuse the palette** - semantic hexes (primary `#3498DB`, secondary `#E74C3C`, tertiary `#2ECC71`) live in `references/rich-output.md`; don't invent a parallel one
- **Value pins** - to label a key point with a hard number that stays readable over lines and grid, annotate with a semi-transparent background box matching the plot background (`bbox=dict(boxstyle="round,pad=0.15", facecolor=BG, edgecolor="none", alpha=0.85)`, high `zorder`); see `references/matplotlib.md`
- Full conventions - plot-type quick reference, subplots, styling, saving, gotchas - in `references/matplotlib.md`

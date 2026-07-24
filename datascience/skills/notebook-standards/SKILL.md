---
name: notebook-standards
description: Jupyter notebook structure standards - section order, GPU-by-UUID selection, grouped imports, the configuration render, the semantic colour system (rich output + matplotlib colormaps), Polars-over-pandas dataframes, equations, charting every load-bearing result inline, fine-grained progress bars, and checkpoint-and-restore for long runs. Use when creating or modifying a Jupyter notebook (.ipynb or Jupytext .py), or when the user mentions notebook structure, the config cell, GPU selection, rich output, colours / colour palette / colormap / plot styling, polars or pandas dataframes, notebook equations, matplotlib plots, charting or visualising results / conclusions / statistics, saving or exporting figures, progress bars, a slow or long-running cell, or checkpointing / resuming / restoring an interrupted run.
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

Math in the header follows the Equations section below. Full mirrorable template: `examples/header-cell.md`.

## GPU Selection (first code cell)

Pin ONE GPU by its **UUID** before any torch/tf/jax import - the CUDA runtime reads these env vars once, at the first CUDA call, so setting them after the import silently has no effect. Ask the user once at build time:

- **Pin a specific GPU** (default) - pick the best card (highest compute capability, then most free memory) and hardcode its UUID
- **Auto-pick a free GPU** - only when the user says "pick whatever is free" - resolve the freest card at runtime

```python
import os

# Deterministic ordering so a UUID/index always names the same physical card
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
# Pin by UUID (from `nvidia-smi -L`) - survives reboots and hardware changes
os.environ["CUDA_VISIBLE_DEVICES"] = "GPU-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import torch  # CUDA reads the env vars once, here - never set them after this import
```

UUID not index because CUDA's `FASTEST_FIRST` order ≠ nvidia-smi's PCI order, so `CUDA_VISIBLE_DEVICES=2` can grab a different card. Mechanism, auto-pick-free snippet, multi-GPU limits, pitfalls: `references/gpu-setup.md`.

## Import Cell Pattern

- **One cell** - all imports together, never import later; sole exception is a use case that genuinely needs an import elsewhere (e.g. `torch` in the GPU-selection cell after `CUDA_VISIBLE_DEVICES` is set, per GPU Selection)
- **Grouped** - block by category with a blank line and a `# Category` heading per group
- **Annotated** - inline `# comment` on each import stating what it is for
- Full annotated template - `examples/import-cell.md`

## Configuration Cell

All hyperparameters here, inline `# comment` per field, closed by a Rich render that groups them into sections so a scrolling reader scans structure without reading code - mirrorable template + colour grammar in `examples/config-cell.md`.

- **GPU line** - a CUDA notebook's render carries `torch.cuda.get_device_name(0)` in a `[bold]Device[/bold]` sub-section; nothing else catches the silent wrong-device bug where `CUDA_VISIBLE_DEVICES` was misset but `device="cuda"` still runs, on the wrong card. Device-block template with compute cap + memory: `references/gpu-setup.md`
- **Minimal variant** - under 5 hyperparameters and no natural sub-sections: a flat `rprint` of Model / Batch size / Device / GPU; the sectioned template stays the default

## Section overviews (mandatory)

Every `## Section` header carries a 1-2 sentence overview in the SAME markdown cell, above the first code cell - it answers "what does this section do, and why" so a scrolling reader decides whether to expand the code or skip past it. Bullets (3-5) when the content is naturally listy. A header with no overview fails the standard. Sole exception: the file-level Header, which IS the notebook's own overview.

`## Configuration` ->
> Training hyperparameters for the ModernBERT contrastive run. Lower temperature increases discrimination but risks gradient instability; larger effective batch size improves contrastive learning but requires more memory.

`## Evaluation` ->
> Reports the four metrics tracked across iterations:
> - **Accuracy** on the held-out test split
> - **F1 macro** to weight rare classes equally
> - **Latency p95** measured on a 1k-row sample
> - **Memory peak** captured via `torch.cuda.max_memory_allocated`

## Equations in markdown cells

Write math liberally - every quantitative relationship as an equation, not prose. Unicode glyphs inline (`τ(i) = Σⱼ Tᵢⱼ·posⱼ / Σⱼ Tᵢⱼ`), each display equation as a standalone `$$...$$` block on its own line, dollar amounts in prose escaped `\$`. Why each form, plus the glyph set: `references/equations.md`.

## Cell Rules

- Markdown header before each code section, with overview below (see above)
- One logical operation per cell
- Progress bars in SEPARATE cell from setup text - avoids overwriting

## Dataframes - Polars by default

`import polars as pl`, not pandas. Reach for pandas ONLY when genuinely required - a library returns or demands a `pd.DataFrame`, or a needed operation has no Polars equivalent - and name the reason in a comment at the import. Convert at the boundary (`pl.from_pandas()` / `.to_pandas()`) and keep the notebook body Polars.

Naming (`purpose_df` / `purpose_lf`) and lazy-for-large-data conventions: `datascience:datascience` skill.

## Rich Output

`rich.print()` with semantic colours, ONE call per block of related output.

- **One multiline call, never a run of prints** - a block of related output goes out as a single `rprint` of one multiline string. Each separate print is its own output block in JupyterLab, rendered as its own paragraph with a large vertical gap after it, so a five-line summary lands as five scattered paragraphs instead of one compact block
- **Layout inside the string** - newlines, indentation and `[dim]` do the spacing; when the content is genuinely tabular or needs a border use one `Table` / `Panel` / `Group`, still emitted in a single call

See `references/rich-output.md` for the full semantic palette, status colours, ML-eval and table-column colours.

## Colours (one system, every surface)

Colour carries meaning or it does not appear. ONE palette spans rich output and every figure - never invent a second one per notebook. Full palette + hexes: `references/rich-output.md`.

- **Semantic, never decorative** - a colour encodes a state (good / warn / error), a category, or a magnitude. Colour chosen because it looks nice is a defect
- **One palette, both surfaces** - rich semantic names for terminal output, the matching hexes for matplotlib (primary `#3498DB`, secondary `#E74C3C`, tertiary `#2ECC71`). The same concept keeps the same colour in every cell and every figure
- **Colormap by data kind** - sequential (`viridis`) for magnitudes, diverging (`coolwarm`) for data centred on a midpoint, qualitative (`tab10`) for UNORDERED categories. An ordered discrete variable (batch size, epoch, quantile bin) is a magnitude, not a category - give it a sequential colormap sampled at N points so the colour ramp tracks the order; a qualitative palette there throws the ordering away. The wrong family misreads the data
- **Never `jet` / rainbow** - it invents banding the data does not contain; default to colourblind-safe `viridis` / `cividis`
- **Never colour alone** - pair it with a label, marker or pattern so the figure survives greyscale print and colourblind readers
- **Legible on both themes** - notebooks get read in light AND dark JupyterLab; avoid pale-on-white and near-black-on-dark. Rich standard colour names (not hex) keep terminal output readable across themes
- **Consistent across figures** - a series or class keeps its colour for the whole notebook; the same label in two different colours is a defect

## Progress and checkpoints (MANDATORY for every long run)

A long-running job does both: shows a fine-grained progress bar, AND checkpoints partial results so an interrupted run restores what it already computed instead of starting over. Missing either is a defect, not a style choice.

- **Progress bar** - every medium or long loop (batch inference, training epochs, per-file processing, API sweeps) wraps its iterable in a Rich `Progress`; a cell running more than a few seconds needs one, sub-second cells do not
- **Fine enough to show REAL progress** - `total` counts the actual unit of work so the bar moves often and the ETA is honest. An LLM judge over a corpus tracks per-document (hundreds of steps), never a handful of coarse chunks - a 4-step bar sitting minutes per step tells the reader nothing. The costlier each step, the finer the bar; nested work gets a nested bar (outer epoch, inner batch)
- **Separate cell** - the `Progress` block sits in its own cell, away from setup prints, per Cell Rules
- **Checkpoint** - a run measured in minutes persists intermediate results (every N steps or per epoch) to `checkpoints/` under the output dir, or `tempfile.gettempdir()`, so partial work survives a crash, a kernel restart, or a mid-run inspection
- **Restore on restart - the whole point** - checkpoint files carry the step/epoch in the name (`ckpt_epoch03.pt`, `batch_00500.parquet`); on re-run the cell scans what is already on disk, loads it, and computes only what is missing. A checkpoint written but never read back is dead weight

Progress-bar mechanics (tqdm vs rich, Jupyter quirks, completion fixes): `datascience:progressbars` skill.

## Two-pass build (compute, then interpret)

Build in at least two passes: the first computes the numbers, the second adds the meaning. A notebook that only prints results is half-finished - the interpretation is what a reader comes for.

- **Pass 1 - compute** - run the cells that generate the data and numbers: load, process, train / infer, collect metrics into variables and to disk; no conclusions yet
- **Pass 2 - interpret** - revisit the executed notebook and add the reasoning: a conclusion for each result, plus a graph for every load-bearing number (per Figures) that demonstrates the specific feature or phenomenon the number claims
- **What a conclusion carries** - terse `technical-documentation` shape (overview sentence, then factual bullets), grounded in the run's actual values not adjectives (`recall 0.91 vs 0.78 baseline`, not "much better"); state the **mechanism** (why the number moved) when it applies, the **meaning** (why it matters to the work), and the **impact** (effect on performance / quality / cost)
- **Colour amplifies the key message** - the headline figure or verdict wears the notebook's semantic palette (per Colours) so the deciding number stands out on a skim - meaning-bearing, never decoration
- **Where the conclusion lands** - a markdown cell after the result, or Rich text in the output cell directly under its graph; a headline number never stands without the sentence saying what it means
- **More passes when a result raises a question** - a surprising number earns another compute-then-interpret pass, not an unexplained value

## Figures (inline by default)

Plots render inline - the `.ipynb` itself is the artefact, so no figure goes to disk unless the user asks for it.

- **Load-bearing numbers get a figure** - every conclusion the notebook argues for, and every headline statistic it rests on, is SHOWN as a plot, not only printed: distributions, class balance, metric vs baseline, sweep and ablation results, error breakdowns, before/after. A printed number is a claim; the figure is the evidence a reader checks at a glance, and it is what survives into a report or a deck. Incidental or diagnostic values stay text-only - the rule is about the numbers the argument rests on
- **Figure earns its caption** - the markdown around a load-bearing figure states what the reader should see in it (the gap, the shift, the outlier), so the conclusion and its evidence sit together
- **Inline display** - end a plotting cell with `plt.show()` (or let the figure be the cell's last expression); the rendered image is captured in the notebook output
- **No `plt.savefig` on your own** - add a file export only when the user explicitly asks; Section 9 Save/Export covers model and data artefacts, not figures
- **When export IS requested** - named path (`reports/figures/<name>.png`), `dpi` 150+, `bbox_inches="tight"`, and keep the inline `plt.show()` as well

## Plotting (matplotlib)

Object-oriented API only - `fig, ax = plt.subplots(figsize=(w, h), constrained_layout=True)`, then `ax.` calls; the pyplot state machine silently draws onto the wrong axes once a figure has more than one.

- **`constrained_layout=True`** - default it on; auto-spaces labels, titles and colorbars so nothing overlaps or clips
- **Colours** - the Colours section above; never invent a per-plot palette

`references/matplotlib.md` carries the rest: plot-type quick reference, subplots, full-width edge-to-edge figures, value pins, styling, saving, gotchas.

<!-- improved 2026-07-24 | body 2338→1924w / 197→158L | quality 50/50 assertions, 4 blinded graders (n=1/cell, uncalibrated, ceiling) | trigger n/a (skill-creator harness measures spontaneous invocation of a fabricated slash-command; same input flips 0↔1, all-zero under load) | via improve-skill -->


---
name: notebook-standards
description: Jupyter notebook structure standards - section order, GPU-by-UUID selection, grouped imports, the configuration render, the semantic colour system (rich output + matplotlib colormaps), Polars-over-pandas dataframes, equations, charting every load-bearing result inline, fine-grained progress bars, checkpoint-and-restore for long runs, and the post-write compliance checklist. Use when creating or modifying a Jupyter notebook (.ipynb or Jupytext .py), when verifying or reviewing a finished notebook against the standards, or when the user mentions notebook structure, the config cell, GPU selection, rich output, colours / colour palette / colormap / plot styling, polars or pandas dataframes, notebook equations, matplotlib plots, charting or visualising results / conclusions / statistics, saving or exporting figures, progress bars, a slow or long-running cell, checkpointing / resuming / restoring an interrupted run, or a notebook checklist / standards check.
---

# Notebook Structure Standards

Patterns for Jupyter notebook creation.

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

## Checklist task (MANDATORY when the notebook changes)

Writing or modifying a notebook - `TaskCreate` one task BEFORE the first cell, carrying the checklist inside it:

- **`subject`** - `Verify <notebook path> against post-write checklist`
- **`description`** - the Post-write checklist at the end of this file, verbatim, all 17 boxes
- **`activeForm`** - `Verifying notebook against standards`

Complete it only once every box is ticked or explicitly `n/a`.

- **Description carries the boxes so this file need not stay in context** - a long build fills the window and gets compacted, taking the checklist with it; `TaskGet` returns the description on demand
- **Register up front, never at the end** - the checklist sits at the end of this file, exactly where an agent deep in a build never returns. An open task survives the whole build; a rule below the fold does not
- **Only when the notebook changes** - a question about a rule (a colormap, an equation form, a colour name) writes no notebook and creates no task
- **One task, not one per box** - the 17 boxes are its definition of done

## Mandatory Section Order

1. **Header** - mandatory title + author + date + purpose, then an optional problem-specific menu (see below)
2. **GPU Selection** - `CUDA_VISIBLE_DEVICES` before any torch/tf/jax import
3. **Imports** - one cell, grouped, inline comments, autoreload
4. **Reproducibility** - `set_seed(42)` for random, numpy, torch
5. **Configuration** - hyperparameters in one cell, inline comments, Rich render at the end
6. **Data Loading**
7. **Model/Processing**
8. **Execution** (training, inference)
9. **Save/Export**
10. **Evaluation/Summary**

## Header (first markdown cell)

Orients the reader and doubles as the notebook's own overview, so the Header needs no separate one. Title, author, date and purpose are mandatory; the rest is a menu - pick what fits, drop what does not. Mirrorable template: `examples/header-cell.md`.

Per-field detail (the `<br>` stacking and why), the Purpose guidance, and the optional menu - more provenance, mechanism overview, approach, outputs: `references/header.md`.

## GPU Selection (first code cell)

Pin ONE GPU by its **UUID** before any torch/tf/jax import - CUDA reads these env vars once, at the first CUDA call, so setting them after the import silently does nothing. Ask the user once at build time:

- **Pin a specific GPU** (default) - the best card (highest compute capability, then most free memory), UUID hardcoded
- **Auto-pick a free GPU** - only when the user says "pick whatever is free"; resolve the freest card at runtime

UUID not index, because CUDA's `FASTEST_FIRST` order ≠ nvidia-smi's PCI order, so `CUDA_VISIBLE_DEVICES=2` can grab a different card. Mirrorable cell: `examples/gpu-cell.md`. Mechanism, auto-pick snippet, multi-GPU limits, pitfalls: `references/gpu-setup.md`.

## Import Cell Pattern

- **One cell** - all imports together, never later; the sole exception is an import that genuinely must sit elsewhere (`torch` in the GPU cell after `CUDA_VISIBLE_DEVICES`, per GPU Selection)
- **Grouped** - blocks by category, a blank line and a `# Category` heading each
- **Annotated** - inline `# comment` per import stating what it is for
- Template: `examples/import-cell.md`

## Configuration Cell

All hyperparameters here, inline `# comment` per field, closed by a Rich render grouping them into sections so a scrolling reader scans structure without reading code. Template + colour grammar: `examples/config-cell.md`.

- **GPU line** - a CUDA notebook's render carries `torch.cuda.get_device_name(0)` under `[bold]Device[/bold]`; nothing else catches the silent wrong-device bug where `CUDA_VISIBLE_DEVICES` was misset but `device="cuda"` still runs, on the wrong card. Device block with compute cap + memory: `references/gpu-setup.md`
- **Minimal variant** - under 5 hyperparameters and no natural sub-sections: a flat `rprint` of Model / Batch size / Device / GPU; the sectioned template stays the default

## Section overviews (mandatory)

Every `## Section` header carries a 1-2 sentence overview in the SAME markdown cell, above the first code cell - it answers "what does this section do, and why" so a scrolling reader decides whether to expand the code or skip past it. Bullets (3-5) when the content is naturally listy. A header with no overview fails the standard. Sole exception: the file-level Header, which IS the notebook's overview. Worked examples of both forms: `examples/section-overview.md`.

## Equations in markdown cells

Write math liberally - every quantitative relationship as an equation, not prose. Unicode glyphs inline (`τ(i) = Σⱼ Tᵢⱼ·posⱼ / Σⱼ Tᵢⱼ`), each display equation as a standalone `$$...$$` block on its own line, dollar amounts in prose escaped `\$`. Why each form, plus the glyph set: `references/equations.md`.

## Cell Rules

- Markdown header before each code section, overview below it (per Section overviews)
- One logical operation per cell
- Progress bar in its own cell, away from setup prints - a print issued after the bar starts overwrites it

## Dataframes - Polars by default

`import polars as pl`, not pandas. Reach for pandas ONLY when genuinely required - a library returns or demands a `pd.DataFrame`, or a needed operation has no Polars equivalent - and name the reason in a comment at the import. Convert at the boundary (`pl.from_pandas()` / `.to_pandas()`) and keep the notebook body Polars.

Naming (`purpose_df` / `purpose_lf`) and lazy-for-large-data conventions: `datascience:datascience` skill.

## Rich Output

`rich.print()` with semantic colours, ONE call per block of related output.

- **One multiline call, never a run of prints** - each print is its own JupyterLab output block, rendered as its own paragraph with a large vertical gap after it, so a five-line summary scatters into five paragraphs instead of one compact block
- **Layout inside the string** - newlines, indentation and `[dim]` do the spacing; genuinely tabular or bordered content uses one `Table` / `Panel` / `Group`, still one call

Full semantic palette, status / ML-eval / table-column colours: `references/rich-output.md`.

## Colours (one system, every surface)

Colour carries meaning or it does not appear. ONE palette spans rich output and every figure - never invent a second one per notebook.

- **Semantic, never decorative** - a colour encodes a state (good / warn / error), a category, or a magnitude. Colour chosen because it looks nice is a defect
- **One palette, both surfaces** - rich semantic names for terminal output, the matching hexes for matplotlib (primary `#3498DB`, secondary `#E74C3C`, tertiary `#2ECC71`). The same concept keeps the same colour in every cell and every figure
- **Never `jet` / rainbow** - it invents banding the data does not contain; default to colourblind-safe `viridis` / `cividis`
- **Consistent across figures** - a series or class keeps its colour for the whole notebook; the same label in two different colours is a defect

Three more rules sit in `references/rich-output.md` → Colour selection, with the palette and hexes: which colormap family a given data kind takes, never colour alone (pair it with a label, marker or pattern for greyscale and colourblind readers), and legibility in both light and dark JupyterLab.

## Progress and checkpoints (MANDATORY for every long run)

A long-running job does both: shows a fine-grained progress bar, AND checkpoints partial results so an interrupted run restores what it already computed instead of starting over. Missing either is a defect, not a style choice.

- **Progress bar** - every medium or long loop (batch inference, training epochs, per-file processing, API sweeps) wraps its iterable in a Rich `Progress`; a cell running more than a few seconds needs one, sub-second cells do not
- **Checkpoint** - a run measured in minutes persists intermediate results (every N steps or per epoch) to disk, and reads them back on re-run

Bar granularity, nested bars, checkpoint dirs and filenames, the restore mechanic, bar mechanics (tqdm vs rich, Jupyter quirks): `references/long-runs.md`.

## Two-pass build (compute, then interpret)

At least two passes: the first computes the numbers, the second adds the meaning. A notebook that only prints results is half-finished - the interpretation is what a reader comes for.

- **What a conclusion carries** - terse `technical-documentation` shape (overview sentence, then factual bullets), grounded in the run's actual values not adjectives (`recall 0.91 vs 0.78 baseline`, not "much better"); state the **mechanism** (why the number moved) when it applies, the **meaning** (why it matters to the work), and the **impact** (effect on performance / quality / cost)
- **More passes when a result raises a question** - a surprising number earns another compute-then-interpret pass, not an unexplained value

Pass split, where a conclusion lands, colour on the headline result: `references/two-pass-build.md`.

## Figures (inline by default)

Plots render inline - the `.ipynb` is the artefact. No figure goes to disk unless the user explicitly asks; Section 9 Save/Export covers model and data artefacts, not figures. Every conclusion the notebook argues for, and every headline statistic it rests on, gets a figure.

What counts as load-bearing, the claim-vs-evidence rule, captions, `plt.show()`, and the export spec: `references/figures.md`.

## Plotting (matplotlib)

Object-oriented API only - `fig, ax = plt.subplots(figsize=(w, h), constrained_layout=True)`, then `ax.` calls; the pyplot state machine silently draws onto the wrong axes once a figure has more than one.

- **`constrained_layout=True`** - default it on; auto-spaces labels, titles and colorbars so nothing overlaps or clips
- **Colours** - the Colours section above; never invent a per-plot palette

Plot-type reference, subplots, full-width figures, value pins, styling, saving, gotchas: `references/matplotlib.md`.

## Post-write checklist (MANDATORY)

Closes the task registered at the top of this file. Fill it in after writing or modifying a notebook and report it in the reply - a standard nobody checks is a standard nobody follows. An unticked box is a defect to fix now, not a note to leave behind. `n/a` is a valid tick where the notebook genuinely has no GPU, no long loop or no figure - say which.

**Structure**
- [ ] Header - title, author, date, purpose
- [ ] Sections follow the mandatory order
- [ ] Every `##` header carries its 1-2 sentence overview above the first code cell
- [ ] GPU pinned by UUID BEFORE the torch / tf / jax import
- [ ] All imports in one grouped, annotated cell, autoreload enabled
- [ ] Seeds set for reproducibility
- [ ] Config cell closes with a Rich render (with the Device sub-section when CUDA)

**Output**
- [ ] Rich - one multiline call per block, never a run of prints
- [ ] Tabular output goes through one `Table` / `Panel`, still one call
- [ ] Colours semantic, one palette across rich output AND every figure
- [ ] Dataframes are Polars, or the pandas reason is named at the import

**Long runs**
- [ ] Progress bar on every loop running more than a few seconds, in its own cell
- [ ] Bar `total` counts the real unit of work, so the ETA is honest
- [ ] Checkpoints written every N steps AND read back on re-run

**Evidence**
- [ ] Every load-bearing number has a figure
- [ ] Every result has a conclusion carrying mechanism, meaning, impact
- [ ] Plots use the OO API and inline `plt.show()`, never `jet`

<!-- improved 2026-08-06 | body 2899→2067w / 221→178L (wc -w on body; the 2026-07-24 line used a different counter, so the two word figures are NOT comparable) | quality n/a (skill-creator eval loop skipped by request - token cost); verified instead by a 7-agent workflow whose adversarial reviewer raised 9 regressions - 8 fixed, 1 declined as already-covered - plus 0 broken links dir-wide and 17/17 boxes traced to a stated rule | trigger n/a (skipped) | 67w over the 2000 ideal - the test-pinned gate fence (~150w) and the 17 boxes (~200w) cannot move | via improve-skill -->

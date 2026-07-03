# Matplotlib - Notebook Plotting Conventions

Resource for the `notebook-standards` skill. How to write good matplotlib figures in a notebook. Where a figure goes (inline by default vs export) lives in the skill's Figures section; semantic Rich/brand hexes live in `rich-output.md` - this file does not restate either.

## Object-oriented API (always)

- Create explicitly: `fig, ax = plt.subplots(figsize=(w, h), constrained_layout=True)` - never the pyplot state machine (`plt.plot(...)` onto an implicit current axes) in saved code
- Draw and label on the axes: `ax.plot`, `ax.scatter`, `ax.set_xlabel`, `ax.set_title`, `ax.legend`, `ax.grid(alpha=0.3)`
- OO scales to subplots and is debuggable; pyplot's global state silently draws onto the wrong axes once there is more than one

## Figure creation

- **figsize** - inches, set at creation `plt.subplots(figsize=(10, 6))`; pixels = dpi × inches, so a 4×3 at dpi 300 is 1200×900 px
- **constrained_layout=True** - default it on; auto-spaces labels, titles and colorbars so nothing overlaps or clips (replaces manual `tight_layout()` / `subplots_adjust`)
- **dpi** - screen/notebook 72-100, web 150, print 300; only bites on export, inline uses the notebook's own dpi

## Plot types (one call each)

- Line (trend / time series): `ax.plot(x, y, lw=2, marker="o")`
- Scatter (relationship): `ax.scatter(x, y, s=sizes, c=vals, cmap="viridis", alpha=0.6)`
- Bar (categorical): `ax.bar(cats, vals)`, horizontal `ax.barh(cats, vals)`
- Histogram (distribution): `ax.hist(data, bins=30, edgecolor="black")`
- Heatmap (matrix): `im = ax.imshow(M, cmap="coolwarm"); fig.colorbar(im, ax=ax)`
- Box / violin (grouped distributions): `ax.boxplot([a, b, c])` / `ax.violinplot([a, b, c])`
- Contour (2D field): `ax.contour(X, Y, Z, levels=10)`

## Subplots

- Grid: `fig, axes = plt.subplots(2, 2, figsize=(12, 10), constrained_layout=True)` → index `axes[r, c]`
- Named / uneven: `plt.subplot_mosaic([["left", "top"], ["left", "bottom"]])` → index `axes["left"]`
- Full control: `GridSpec` for spanning cells (`gs[0, :]` top row, `gs[1:, 0]` first column of lower rows)

## Colormaps - pick by data kind

- **Sequential** (`viridis`, `plasma`, `cividis`) - ordered magnitudes, low → high
- **Diverging** (`coolwarm`, `RdBu`) - data with a meaningful centre (zero, a mean)
- **Qualitative** (`tab10`, `Set2`) - unordered categories
- Never `jet` / rainbow - not perceptually uniform, invents structure the data does not have
- Colourblind-safe by default: `viridis` / `cividis`; for categoricals add hatch or marker shape on top of colour so the plot survives greyscale

## Styling

- Global defaults once via `rcParams` (`plt.rcParams["font.size"] = 12`) or a style sheet (`plt.style.use("seaborn-v0_8-darkgrid")`)
- Every axes carries `set_xlabel` / `set_ylabel` / `set_title`, `legend()` when >1 series, `grid(alpha=0.3)`
- Annotate a point: `ax.annotate("note", xy=(x, y), xytext=(x1, y1), arrowprops=dict(arrowstyle="->"))`
- Brand / semantic hexes (primary `#3498DB`, secondary `#E74C3C`, tertiary `#2ECC71`) live in `rich-output.md` - reuse them, do not invent a parallel palette

## Saving (only when the user asks - see the Figures section)

- `fig.savefig("reports/figures/<name>.png", dpi=150, bbox_inches="tight")` - `bbox_inches="tight"` trims surrounding whitespace
- `facecolor="white"` when the theme is transparent and the target needs a solid background; `transparent=True` for overlays
- Vector (`.pdf` / `.svg`) for publication; `rasterized=True` on dense artists keeps vector files small
- Keep the inline `plt.show()` as well - the export is in addition to the inline figure, not instead of it

## Gotchas

- Overlapping / clipped labels → `constrained_layout=True`; rotate long ticks `ax.tick_params(axis="x", rotation=45)`
- Many figures in a loop → `plt.close(fig)` after each, or memory climbs
- Colorbar shrinks its subplot → `constrained_layout=True`, or share one across a row `fig.colorbar(im, ax=axes, shrink=0.95)`
- Plotting onto the wrong axes → you are on the pyplot state machine; switch to `ax.` calls

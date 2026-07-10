# Matplotlib - Notebook Plotting Conventions

Resource for the `notebook-standards` skill. How to write good matplotlib figures in a notebook. Where a figure goes (inline by default vs export) lives in the skill's Figures section; semantic Rich/brand hexes live in `rich-output.md` - this file does not restate either.

## Object-oriented API (always)

- Create explicitly: `fig, ax = plt.subplots(figsize=(w, h), constrained_layout=True)` - never the pyplot state machine (`plt.plot(...)` onto an implicit current axes) in saved code
- Draw and label on the axes: `ax.plot`, `ax.scatter`, `ax.set_xlabel`, `ax.set_title`, `ax.legend`, `ax.grid(alpha=0.3)`
- OO scales to subplots and is debuggable; pyplot's global state silently draws onto the wrong axes once there is more than one

## Figure creation

- **figsize** - inches, set at creation `plt.subplots(figsize=(10, 6))`; pixels = dpi × inches, so a 4×3 at dpi 300 is 1200×900 px
- **constrained_layout=True** - default it on; auto-spaces labels, titles and colorbars so nothing overlaps or clips (replaces manual `tight_layout()` / `subplots_adjust`) - the exception is a full-width figure, which turns it off and sets margins by hand (see Full-width figures)
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

## Full-width figures (span the frame)

Make a figure render edge-to-edge across the notebook output (or a README image) - the aspect ratio sets how wide it renders, and you reserve the margins yourself instead of letting matplotlib pad ~12% of dead space on each side.

- **Wide figsize drives the width** - landscape aspect renders wide inline: single narrative panel ~1.65:1 (`figsize=(9.4, 5.6)`, `(11, 6.7)`, `(14, 6)`); a 1xN panel strip goes very wide (`(18.5, 5.0)` for 1x4); a heatmap ~2:1 (`(15.2, 7.2)`)
- **Panel grid** - after `plt.subplots(1, 4, figsize=(18.5, 5))`, call `fig.subplots_adjust(left=0.05, right=0.99, top=0.80, bottom=0.13, wspace=0.13)` so the panels fill the full width; `top` / `bottom` reserve room for a title+subtitle and a caption, `wspace` sets the inter-panel gap
- **Single axes / heatmap** - place the axes by hand: `ax = fig.add_axes([left, bottom, w, h])` with `left` ≈ 0.10-0.12 (room for the y-label) and `w` ≈ 0.85 so the right edge lands near 0.97; give a colorbar its own thin rect hugging the edge `fig.add_axes([0.972, bottom, 0.010, h])` so no gap opens between plot and bar
- **`constrained_layout` OFF here** - it re-adds automatic margins and shrinks the axes back, undoing the fill; manual `subplots_adjust` / `add_axes` is what buys the edge-to-edge span. Left-aligned titles (`ax.set_title(..., loc="left", pad=38)`) and captions (`fig.text(x, -0.02, ...)`) then live in the reserved top / bottom bands
- **Analysis vs presentation** - inline analysis figures keep `constrained_layout=True` and default margins; reach for hand-set margins only when the figure is presentation-grade and must span the width

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

## Labelling key points (value pins)

Put a hard number directly on a curve at a key x - readable against gridlines and neighbouring lines without a heavy opaque box, by giving the label a semi-transparent background that matches the plot's own background.

- **Reusable bbox** - define the style once, reuse on every label: `PIN = dict(boxstyle="round,pad=0.15", facecolor=BG, edgecolor="none", alpha=0.85)`, where `BG` is the axes / figure background colour
- **Why it reads** - `facecolor=BG` + `edgecolor="none"` makes the box a soft cut-out of the background, not a bordered label; `alpha=0.85` lets gridlines faintly through so the number sits in the plot yet stays legible
- **Apply** - `ax.annotate(f"${y:,.0f}", xy=(x, y), xytext=(x*1.04, y*1.06), color=SERIES, fontsize=8, fontweight="bold", ha="left", va="bottom", bbox=PIN, zorder=6)`
- **Colour to the series** - set the label `color` to its line's colour so the number ties to the right curve; nudge it off the point with `xytext` and `ha` / `va`
- **High `zorder`** - pin the label above the lines and grid (`zorder=6`) so it never hides behind them

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

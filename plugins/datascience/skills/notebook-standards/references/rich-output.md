# Rich Output - Semantic Colour Palette

Resource for the `notebook-standards` skill. Semantic colour assignments for the `rich` library - colour by role, not by taste. Used in notebook Configuration renders, status output, and any `rprint()` styling; the `/datascience:apply-style` and `/datascience:fix-notebook` commands defer here for colours.

## Text Colors

| Category | Color | Example |
|----------|-------|---------|
| Headers | `medium_purple` | `[bold medium_purple]Title[/bold medium_purple]` |
| Subheaders | `slate_blue1` | `[bold slate_blue1]Section[/bold slate_blue1]` |
| Data values (no units) | `dark_sea_green` | `[dark_sea_green]42[/dark_sea_green]` |
| Values with units | `light_sea_green` | `[light_sea_green]44,100 Hz[/light_sea_green]` |
| File names | `cadet_blue` | `[cadet_blue]model.pt[/cadet_blue]` |
| Paths | `dim` | `[dim]/path/to/file[/dim]` |
| Config values | `grey70` | `[grey70]batch_size=16[/grey70]` |

## Status Colors

| Status | Color | Symbol |
|--------|-------|--------|
| Success | `dark_sea_green` | `✓` |
| Warning | `dark_goldenrod` | `⚠` |
| Error | `indian_red` | `✗` |
| Info | `steel_blue` | - |

## ML Evaluation

| Metric | Color |
|--------|-------|
| TP | `dark_sea_green4` |
| TN | `dark_sea_green` |
| FP | `indian_red` |
| FN | `dark_goldenrod` |

## Table Columns

| Type | Color |
|------|-------|
| Row labels | `grey70` |
| Category A | `light_coral` |
| Category B | `steel_blue` |
| Totals | `dark_sea_green` |

## Colour selection

Choosing the colour, once the palette above has named the options. The SKILL.md Colours section carries the four rules governing whether a colour appears and stays consistent; these three govern which colormap family fits the data and whether the result stays readable for every reader and every theme. All seven have equal force - none of these is optional detail.

- **Colormap by data kind** - sequential (`viridis`) for magnitudes, diverging (`coolwarm`) for data centred on a midpoint, qualitative (`tab10`) for UNORDERED categories. An ordered discrete variable (batch size, epoch, quantile bin) is a magnitude, not a category - sample a sequential map at N points so the ramp tracks the order; a qualitative palette throws the ordering away. The wrong family misreads the data
- **Never colour alone** - pair it with a label, marker or pattern so the figure survives greyscale print and colourblind readers
- **Legible on both themes** - notebooks get read in light AND dark JupyterLab; avoid pale-on-white and near-black-on-dark. Rich standard colour names (not hex) keep terminal output readable across themes

## Rules

- Single multiline `rich.print()` for related output. NEVER multiple individual prints - each call is a separate JupyterLab output block, rendered as its own paragraph with a large vertical gap after it, so a run of prints scatters one summary across the cell instead of rendering it compact
- `Table` / `Panel` / `Group` when the content is tabular or needs a border - still ONE call
- `[dim]` for visual variation without changing color
- Dynamic boolean: `"dark_sea_green" if val else "indian_red"`
- Matplotlib hex: primary `#3498DB`, secondary `#E74C3C`, tertiary `#2ECC71`
- Rich standard colors only (no hex) for terminal compatibility

```python
# WRONG - four output blocks, four paragraphs, large gaps between them
rprint(f"[bold medium_purple]Run summary[/bold medium_purple]")
rprint(f"Rows: [dark_sea_green]{n_rows:,}[/dark_sea_green]")
rprint(f"Device: [light_sea_green]{device}[/light_sea_green]")
rprint(f"[dark_sea_green]✓[/dark_sea_green] complete in [light_sea_green]{secs:.1f}s[/light_sea_green]")

# RIGHT - one call, one compact block
rprint(
    f"[bold medium_purple]Run summary[/bold medium_purple]\n"
    f"  Rows:   [dark_sea_green]{n_rows:,}[/dark_sea_green]\n"
    f"  Device: [light_sea_green]{device}[/light_sea_green]\n"
    f"[dark_sea_green]✓[/dark_sea_green] complete in [light_sea_green]{secs:.1f}s[/light_sea_green]"
)
```

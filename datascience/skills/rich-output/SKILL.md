---
name: rich-output
description: Rich text styling patterns for Python notebooks and scripts. Auto-triggered when formatting output with the rich library, creating tables, status indicators, progress bars, or any colored console output in data science or ML workflows.
---

# Rich Output Styling

Semantic color assignments for the rich library.

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

## Rules

- Single multiline `rich.print()` for related output - NEVER multiple individual prints
- `[dim]` for visual variation without changing color
- Dynamic boolean coloring: `"dark_sea_green" if val else "indian_red"`
- Matplotlib hex: primary `#3498DB`, secondary `#E74C3C`, tertiary `#2ECC71`
- Rich standard colors only (no hex) for terminal compatibility

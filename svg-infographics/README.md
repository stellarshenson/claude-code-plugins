# SVG Infographics

Create production-quality SVG infographics with grid-first design, CSS theme classes, dark/light mode support, and automated validation. Builds card grids, timelines, flowcharts, banners, stats panels, hub-and-spoke diagrams, layered models, and creative organic layouts.

Unlike generic SVG generation that produces approximate layouts requiring manual cleanup, this plugin enforces a 6-phase sequential workflow where every coordinate is Python-calculated, every colour traces to an approved theme swatch, and every deliverable passes three automated checkers before delivery.

## Skills

| Skill | Trigger |
|-------|---------|
| **svg-standards** | Auto-triggered when creating or modifying SVG infographics - grid layout, CSS classes, cards, arrows, typography, contrast rules |
| **workflow** | Auto-triggered alongside svg-standards - enforces 6-phase sequential creation with gate checks |
| **theme** | Auto-triggered when defining colour palettes, generating swatches, or working with brand themes |
| **validation** | Auto-triggered when validating, checking, or fixing SVG quality issues |

## Commands

| Command | Purpose |
|---------|---------|
| `/svg-infographics:create` | Create SVG infographic(s) following the full 6-phase workflow |
| `/svg-infographics:theme` | Generate or update a theme swatch for brand colour approval |
| `/svg-infographics:validate` | Run all validation checks on existing SVGs |
| `/svg-infographics:fix-style` | Fix CSS, contrast, dark mode, and colour compliance |
| `/svg-infographics:fix-layout` | Fix overlaps, alignment, spacing, and grid violations |

## Workflow

```
Theme swatch -> user approval -> per image:
  1. Research (read examples, confirm conventions)
  2. Invisible Grid (Python-calculated positions)
  3. Scaffold (structural elements, no content)
  4. Content (text, icons, legends)
  5. Finishing (arrows verified, description comment)
  6. Validation (check_overlaps, check_contrast, check_alignment)
```

Each image completes all 6 phases before the next image starts. No batching.

## Validation Tools

Five Python tools in `tools/` enforce quality:

- **check_overlaps.py** - bounding box overlap detection with inner/outer bbox model
- **check_contrast.py** - WCAG 2.1 contrast verification (AA/AAA) in light and dark mode
- **check_alignment.py** - grid snapping, vertical rhythm, topology verification
- **check_connectors.py** - connector quality: zero-length, edge-snap, L-routing, label clearance
- **calc_connector.py** - geometry calculator for diagonal connectors with SVG snippet output

## Examples

64 production SVG examples in `examples/` covering card grids, timelines, flowcharts, header banners, stats panels, architecture diagrams, delivery models, and theme swatches. Read relevant examples before creating each image.

## Design Principles

- **Grid-first**: Define viewBox, margins, columns, vertical rhythm BEFORE placing any content
- **CSS theme classes**: `<style>` block with `prefers-color-scheme` for OS-aware dark/light mode
- **Transparent background**: No full-viewport background fills - document controls the background
- **Horizontal-first arrows**: Define arrows flat, rotate into position with `calc_connector.py`
- **Fail-first validation**: All checker findings are real defects until individually defended

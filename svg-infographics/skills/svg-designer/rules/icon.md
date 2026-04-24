**Icon rule card** - rules when preflight declares `--icons N`.

## Source

Use one of:

- **draw.io stencil library** (1000+ icons, built-in): `svg-infographics shapes render --library aws --name EC2 --size 48`. Returns a ready-to-paste `<g>`.
- **Bundled primitives** (gear, cog, arrow, check, cross, star, etc.): `svg-infographics primitives icon --type gear --size 32`.

DO NOT:
- Source icons by pasting from web (SVG files may embed scripts, external font references, or a different coordinate system).
- Draw icons by hand from basic primitives unless the icon is genuinely custom (domain-specific logo, bespoke brand mark).
- Use emoji as icons - they render inconsistently across platforms.

## Sizing

- Standard size: 24, 32, or 48px. Pick one per SVG and stick to it. Mixed sizes read as chaos.
- Within a card: 24-32px at top-left or top-right corner (consistent position per SVG).
- Standalone section headers: 48-64px.
- Inline with text: match x-height of surrounding text (typically 12-16px).

## Positioning on grid

All icons must snap to a 4-pixel grid (24px at (20, 40) is fine; 24px at (23, 41) is not). `check_alignment` enforces this.

Within a card:
- Top-left position: `(card.x + 12, card.y + 12)` for 24px icons with 12px padding
- Top-right: `(card.x + card.w - 12 - icon.size, card.y + 12)`
- Centred: `(card.x + card.w/2 - icon.size/2, card.y + card.h/2 - icon.size/2)`

## Colour and theme

- Single-colour icons: fill with `.fg-1` or `.accent-1` class (theme-aware, dark-mode-aware).
- Multi-colour icons from stencil libraries: accept the source palette but adjust opacity to 0.8-0.95 so it harmonises with the theme.
- Monochrome preferred over multi-colour for dense SVGs (high icon count).

## Stroke-width consistency

If any icon uses strokes (outline style), ALL icons in the SVG must use the same stroke-width (typically 1.5 or 2.0). Different widths scatter visual attention.

## Group conventions (MANDATORY for check)

Every icon `<g>` MUST use one of:
- `id="icon-<slug>"` (preferred)
- `class` containing `"icon"`

Plural container groups (`<g id="icons">`) are NOT counted as icons - only the individual per-icon groups inside. This way a single SVG with 6 icons returns `icons: 6`, not `icons: 1`.

## When NOT to use an icon

- As pure decoration with no semantic content (use `type: background` decorative texture instead)
- In place of labelled text - if the icon needs a caption, an explicit text label would serve better
- Below 16px - legibility drops; use a coloured dot or shape primitive instead

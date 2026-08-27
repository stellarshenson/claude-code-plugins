**Icon rule card** - rules when preflight declares `--icons N`.

## Source

Three icon libraries, preferred order, plus a primitives fallback:

- **Lucide** (1000+, ISC): paste the `<path>` from lucide.dev into `<g transform="translate(x,y) scale(s)" fill="none" stroke="<theme hex>" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">`. Comment `<!-- Icon: <name> (Lucide, ISC license) -->`
- **Custom (bundled with the plugin)**: the plugin's own icons (e.g. `brain-circuit`). `svg-infographics icons list` to browse, `svg-infographics icons render <name> --size 32 --stroke <hex>` for a paste-ready `<g>`. Same 24-grid stroke convention as Lucide, so they sit side by side. The catalogue also points at Lucide + draw.io
- **draw.io stencils** (1000+): `svg-infographics shapes render EC2 --library aws --width 48 --height 48` (name is positional; size via `--width`/`--height`, not `--size`)
- **Primitives fallback** (trivial geometric marks - gear, star, hexagon, diamond): each is its own subcommand (`svg-infographics primitives gear`, `primitives star`, ...); each needs explicit geometry flags, so run `primitives <shape> --help` first. `primitives --list` for the set. Not a full icon set - simple glyphs only

### Lucide paths stay verbatim (MANDATORY)

Copy the Lucide `d` data byte-for-byte. Size, colour, position all come from `transform` + `stroke` - NEVER from rewriting coordinates. Re-typed paths drift off the 24-grid and break stroke geometry. Touch a path only when the icon genuinely needs a bespoke change (trim a sub-glyph, merge two marks); comment the why right there. Default = paste, scale, recolour, done.

DO NOT:
- Paste arbitrary SVG off the web (may embed scripts, external fonts, or a foreign coordinate system)
- Hand-draw from primitives unless genuinely custom (domain logo, bespoke brand mark) - and if it earns reuse, add it to the bundled `icons` library
- Use emoji as icons - they render inconsistently across platforms

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

## Default placement (moved from standards.md)

Place icons upper-right quadrant (graphic-level) or upper-right corner of each card (per-card). Western reading path terminates upper-right; the icon reinforces identity without competing with the title.

- **Graphic-level**: inside header band at `x = viewBox.width - margin - icon_size`, vertically centred on title baseline
- **Card-level**: top-right corner with equal corner padding measured from the accent-bar bottom - position via `place --corner top-right --ref-id accent-bar` (see `rules/card.md` "Card anatomy")
- **Override only when**: symmetric grid, process flow with icon anchoring row start, timeline with icon on event marker

Embed in `<g transform="translate(x,y) scale(s)">`, override stroke. Lucide scale factors: 0.5 (~12px), 0.583 (~14px), 0.667 (~16px) from the 24px grid.

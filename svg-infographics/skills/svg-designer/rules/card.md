**Card rule card** - rules when manifest declares `type: card`.

## Geometry

- Corner radius: 3-5px for small cards (<200px wide), 8-12px for large. Consistent across the SVG - do not mix.
- Padding: 16-24px from card boundary to any content. Bigger on focal cards, smaller on dense inventories.
- Min dimensions: 120w x 60h. Below that, use `type: callout` instead.
- Accent bar convention: a 3-4px tall colour strip across the card top-edge acts as a colour-coded section marker. Use for role-coding (phase colour, tier colour). Width = full card width; position flush with the top rounded-corner radius.

## Role semantics

Manifest field `role:` drives what the card represents:

- `phase` - a step in a sequence. MUST carry a numbered badge in the top-left corner (circle or square, 20-24px, contains the step number). Accent bar colour matches the phase family. Phase cards usually go in `grid_row: 1` or 2.
- `metric` - a single quantitative value. Layout: big value centred (24-36pt), label below (10-11pt), unit/context as the bottom strap (8-9pt italic).
- `narrative` - prose content. Title on top (12pt bold, letter-spacing 0.3-0.6), 2-3 bullet-equivalents below (9-10pt). No more than 4 text lines per card.
- `callout` - one pull quote or annotation. Use sparingly; callouts distract from the body. Prefer a dedicated `type: callout` declaration.

## Layout discipline

- **Equal widths in a row**: cards sharing a `grid_row` MUST be the same width (use `geom align` or `distribute`). Exception: an outer card meant to frame smaller ones.
- **Equal heights in a column**: same rule for cards in a column.
- **Grid rhythm**: card top edges snap to 5-pixel multiples. Card bottom edges snap similarly. `check_alignment` enforces this.
- **Gaps**: 20-32px between cards horizontally, 16-24px vertically. Pick one gap value per axis and keep it constant.
- **No content outside the card rect**: badges, accent bars, and icons can sit at the boundary but all free text must be at least 8px inside the card edge.

## Typography

- Title: `font-size: 11-13` bold, letter-spacing 0.3-0.6. Use the CSS class `.fg-1`.
- Body: `font-size: 9-10` regular. Class `.fg-2`.
- Strap / footnote: `font-size: 7-9`, class `.fg-3` or `.fg-2 font-style="italic"`.
- Line height: add +2-3px above baseline per extra line (so a 10pt line gets 12-13px spacing).

## Colour and theme

- Card fill: always translucent (`fill-opacity` 0.04-0.08 on the card body). The theme colour tints the card; it never dominates.
- Card stroke: use the `.card-stroke` class from the theme. Width 0.8-1.2px. Opacity 0.3-0.4.
- Accent bar: full theme colour at `opacity 0.7-0.9`, no translucency.
- Dark mode: every colour used on a card must have a `@media (prefers-color-scheme: dark)` override in the top `<style>` block.

## ID convention (MANDATORY for check-manifest)

Every card `<g>` MUST use one of:

- `id="card-<slug>"` (preferred), OR
- `id="box-<slug>"` (legacy but accepted), OR
- `class="card"` (anywhere in the class list)

`check-manifest` counts cards by scanning for these; no convention = no count = failed check.

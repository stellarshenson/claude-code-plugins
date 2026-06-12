**Card rule card** - rules when manifest declares `type: card`.

## Geometry

- Corner radius (bottom corners of the body path; top stays square): 3-5px for small cards (<200px wide), 8-12px for large. Consistent across the SVG - do not mix.
- Padding: 16-24px from card boundary to any content. Bigger on focal cards, smaller on dense inventories.
- Min dimensions: 120w x 60h. Below that, use `type: callout` instead.
- Accent bar convention: a 5px tall colour strip across the card top-edge acts as a colour-coded section marker. Use for role-coding (phase colour, tier colour). Width = full card width; flush with the card top, no rx. See "Card anatomy" below.

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
- Accent bar: full theme colour at `opacity="0.6"`.
- Dark mode: every colour used on a card must have a `@media (prefers-color-scheme: dark)` override in the top `<style>` block.

## ID convention (MANDATORY for check-manifest)

Every card `<g>` MUST use one of:

- `id="card-<slug>"` (preferred), OR
- `id="box-<slug>"` (legacy but accepted), OR
- `class="card"` (anywhere in the class list)

`check-manifest` counts cards by scanning for these; no convention = no count = failed check.

## Card body construction (moved from standards.md)

Square-top, rounded-bottom path. Accent bar flush. Bottom corner radius r=3.

```
fill:   M{x},{y} H{x+w} V{y+h-r} Q{x+w},{y+h} {x+w-r},{y+h} H{x+r} Q{x},{y+h} {x},{y+h-r} Z
bar:    <rect x={x} y={y} width={w} height="5" fill="{colour}" opacity="0.6"/>
```

Fill-opacity 0.04, stroke-width 1, accent bar height 5 at opacity 0.6.

**Container cards** (an outer card framing smaller ones): fill-opacity 0.02, stroke-width 0.8, opacity 0.25, bar height 4 at opacity 0.15.

## Card anatomy (MANDATORY - closes known production failure modes)

- **Body path, not rect rx** - the card body is the square-top/rounded-bottom path above. `<rect rx="...">` is FORBIDDEN for card bodies: a rounded top corner clips the accent bar and the corner radii drift apart across the deck. `rx` stays legal for non-body primitives (chips, badges, container boxes)
- **Accent bar** - height 5, `opacity="0.6"`, flush with the card top edge, full card width, no rx. Never floats below the top edge, never inset
- **Icon slot top-right** - icon sits in the top-right corner with EQUAL corner padding on both axes, measured from the accent-bar bottom edge (not the card top). Position via `svg-infographics place --container <card-id> --corner top-right --ref-id accent-bar`, never by eye
- **Slot parity across grid cards** - every card in a grid carries the SAME slot types: if one card has a stat/digit slot, all cards in that grid have one; if one has an icon slot, all do. Empty slots read as broken, mismatched slots as unrelated cards
- **One card primitive per deck** - a single SVG (and a multi-SVG deck) uses ONE card construction. Never mix path-based bodies with rect-based bodies, or two different corner treatments, in the same deliverable

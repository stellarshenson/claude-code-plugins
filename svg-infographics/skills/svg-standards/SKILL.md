---
name: svg-standards
description: Core SVG infographic standards - grid-first design, CSS theme classes with dark/light mode, card shapes, arrows, connectors, typography, icons, z-order layering, layout topology, and structural rules. Auto-triggered when creating or modifying SVG infographics, diagrams, banners, timelines, flowcharts, or any visual SVG content.
---

# SVG Infographic Standards

Apply these standards when generating or modifying SVG infographics for documents. Read the **workflow** skill for the mandatory 6-phase per-image creation process. Read the **theme** skill for palette approval and swatch generation. Read the **validation** skill for checker tool usage.

## Task Tracking

**MANDATORY**: Use Claude Code task tracking (TaskCreate/TaskUpdate) throughout all SVG work. Create a task list at the start of any multi-step SVG creation or modification. Mark each task in_progress when starting, completed when done. This provides visible progress to the user and prevents skipping steps.

## Key Principles (Quick Reference)

1. **Theme First** - Generate and approve `theme_swatch.svg` before any deliverables
2. **Grid-First Design** - Define viewBox, margins, panel origins, columns, vertical rhythm BEFORE placing content. Use invisible guide grid
3. **CSS Theme Classes** - `<style>` block with `prefers-color-scheme` media query. Use `class=` not inline `fill=` for theme-dependent text
4. **File Description Comment** - Every SVG starts with XML comment BEFORE `<svg>`: filename, shows, intent, theme
5. **Grid Comment** - After `<style>`, document panel origins, columns, vertical rhythm in `GRID REFERENCE` comment
6. **Layout Topology Comment** - Describe relationships (not coordinates): h-align, v-align, h-stack, v-stack, contain, mirror
7. **Named Component Groups** - Wrap logical chunks in `<g id="component-name">`. Lowercase-hyphen names
8. **Transparent Background** - `fill="transparent"` on root rect. No full-viewport background fills
9. **Contrast Rules** - Every element contrasts its immediate background using theme colours. No `#000000` or `#ffffff`
10. **Verify All Three** - Run `check_contrast.py`, `check_overlaps.py`, `check_alignment.py` before delivery
11. **Examples** - Read relevant SVG examples from `examples/` before creating each image

## CSS Theme Classes and Dark Mode Detection

Use `<style>` block with `prefers-color-scheme` media query for OS-theme-aware colours. Use `class=` not inline `fill=` for theme-dependent text.

### Usage on Elements

```xml
<!-- Theme-aware: switches with dark mode -->
<text class="fg-2" font-size="12">Heading</text>
<text class="on-fill" font-size="9">75%</text>

<!-- Fixed colour: use fill= for elements that must not change -->
<rect fill="#E61C29" opacity="0.6"/>
```

### The `on-fill` Class

Text on saturated accent fills needs:
- **Light mode**: dark text (fg-1) for contrast against coloured fill
- **Dark mode**: very light text (pale tint) for contrast against coloured fill on dark background

### Font Opacity Rule

**Never apply `opacity` to text elements.** Fonts render at full opacity always. Contrast via colour selection, not transparency. Applies to `opacity`, `fill-opacity` on `<text>`, and parent `<g>` opacity inheritance.

### Opacity and Transparency Rule

Default to solid fills. Opacity appropriate for:
- Card background tints (`fill-opacity="0.04-0.06"`)
- Track lines (`opacity="0.3"`)
- Decorative background imagery (`opacity="0.10-0.35"`)

**Never use opacity on**: data bars, progress bars, legend chips, text, logos.

### CSS-First Rule

**MANDATORY**: Define all colours in `<style>` block, reference via `class=`. Inline `fill="#hex"` acceptable only for structural shape fills, fixed-colour swatch elements, and decorative low-opacity imagery.

### Dark Mode Limitations

`prefers-color-scheme` works in standalone/`<object>`/inline SVG but **not** via `<img>` or markdown `![alt](path)`. Design for light background primary. Assume `#1e1e1e` as dark bg.

## Contrast Rules

Every element must contrast its immediate background using theme colours only.

### Background-Foreground Pairing

| Background | Foreground |
|------------|-----------|
| Transparent (document bg) | fg-1 or fg-2 |
| bg-1 (accent at 0.04-0.08) | fg-1 headings, fg-3/fg-4 labels |
| bg-2 (accent at 0.3-0.6) | fg-1 or fg-2 |
| Full accent fill (0.8-1.0) | fg-4 or fg-1 (whichever contrasts) |
| Accent swatch (solid chip) | fg-1 label below, not on top |

### Colours to Avoid

- `#000000` - invisible on dark backgrounds
- `#ffffff` - invisible on light backgrounds, breaks dark mode
- Pure greys below `#404040` or above `#c0c0c0`
- Any colour not in the approved theme palette

### Transparent Background

Always use transparent background. Exception: banner gradient bars that ARE the design element.

### Safe Neutral Palette (when no brand defined)

| Purpose | Colour |
|---------|--------|
| Dark text | `#1e3a5f` |
| Primary accent | `#0284c7` |
| Secondary accent | `#7c3aed` |
| Tertiary accent | `#059669` |
| Muted text | `#6b7280` |
| Subtle fills | accent + `fill-opacity="0.06"` |

## Grid-Based Layout

**MANDATORY**: Every SVG uses an explicit grid documented in XML comment.

### Design Workflow: Grid-First, Details-Last

1. **Grid and guide lines** - viewBox, guide grid `<g>`, grid comment, layout topology
2. **Placeholder rectangles** - large rects for key motifs at correct positions
3. **Structural elements** - card paths, track lines, accent bars, dividers
4. **Content** - text, icons, arrows, data elements
5. **Styling** - CSS classes, fills, opacities, dark mode overrides
6. **Validation** - overlap, contrast, alignment checks

### Vertical Rhythm

Single step size (typically 14px), all content rows on multiples:

```
y_title  = 14
y_row1   = 34   (title + 20)
y_row2   = 48   (row1 + 14)
y_row3   = 62   (row2 + 14)
```

### Invisible Guide Grid

**MANDATORY**: First element after `<style>` is `<g id="guide-grid" display="none">`. Hierarchical bisection:

| Level | Step (800px) | Purpose |
|-------|-------------|---------|
| grid-1 | ViewBox edges | Canvas boundaries |
| grid-2 | Bisects grid-1 | Centre line |
| grid-3 | Bisects grid-2 | Quarter points |
| grid-4 | Bisects grid-3 | Eighth points |
| grid-5 | Bisects grid-4 | Sixteenth points |
| grid-6 | Bisects grid-5 | Thirty-second points |

### Grid Comment Template

```xml
<!-- === GRID REFERENCE ===
  Panel origins: left x=20, right x=410
  Divider: x=400
  Columns (offset from origin): mark +11, text +20, bar +220
  Vertical rhythm (14px): y=14 title, y=34 row1, y=48 row2
  Mark vertical: 6px tall, centred at text_y-3
=== -->
```

### Layout Topology Comment

**MANDATORY**: Describes relationships, not coordinates.

| Operation | Meaning |
|-----------|---------|
| `h-align` | Same x (vertical column) |
| `v-align` | Same y (horizontal row) |
| `h-stack` | Adjacent left to right |
| `v-stack` | Adjacent top to bottom |
| `v-spacing` | Equal vertical gaps |
| `h-spacing` | Equal horizontal gaps |
| `contain` | Element inside another |
| `mirror` | Symmetric layout |

### Named Component Groups

Wrap logical components in `<g id="component-name">`. Names lowercase-hyphen. Light/dark variants use `-light`/`-dark` suffix.

### Multi-Card Grids

All cards in a row same width: `(viewBox_width - 2*margin - (n-1)*gap) / n`. Inter-card gap 12px (timeline) or 20px (content). Card padding 16px left/right, 20px top from accent bar.

### Mandatory Margins

All elements respect minimum margins from card borders and neighbours. Compute final bounding box after all transforms.

### Inner and Outer Bounding Boxes

Every element has two bboxes:
- **Inner bbox**: rendered extent including stroke width
- **Outer bbox**: inner + per-element-type padding

| Element type | Padding |
|-------------|---------|
| Text | 12px from card edge |
| Decorative icon | 6px edges, 4px text |
| Logo mark | 6px edges, 4px text |
| Card | 10px from adjacent cards/viewBox |
| Accent bar | 0px (flush with card) |

## SVG Structure Standards

### File Description Comment

Every SVG starts with comment before `<svg>`: filename, shows, intent, theme.

```xml
<!--
  filename.svg - Short role description
  Shows: visual elements in reading order
  Intent: purpose in document
  Theme: palette name, shade assignments
-->
```

### ViewBox and Sizing

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
```

- `viewBox` only - no `width`/`height` attributes
- Default width: `1800` for new infographics
- Common sizes: `1800x200` (stats), `1800x280` (timelines), `1800x320` (flows), `1800x400` (headers), `1800x700` (grids)

### Typography

- `font-family="Helvetica, Arial, sans-serif"` - system fonts only
- Sizes 7-28px. Size progression: hero stats (18-28px) > headings (12-14px) > labels (10-11px) > metadata (8-9px)
- `text-anchor="middle"` for centred, explicit `x` for left-aligned
- **Never use `<tspan>` for mixed styling** - separate `<text>` elements with explicit x positions

## Icon Sourcing Policy

Prefer standard open-source SVG icon libraries.

| Library | License | Icons |
|---------|---------|-------|
| Lucide | ISC | 1000+ |
| Feather | MIT | 280+ |

Embed in `<g transform="translate(x,y) scale(s)">`, override stroke to match palette. Comment: `<!-- Icon: {name} (Lucide, ISC license) -->`. Scale: 0.583 (~14px), 0.667 (~16px), 0.5 (~12px).

## Card Backgrounds

**Square-top, rounded-bottom** path so accent bar sits flush. Bottom corner radius r=3.

```
fill:   M{x},{y} H{x+w} V{y+h-r} Q{x+w},{y+h} {x+w-r},{y+h} H{x+r} Q{x},{y+h} {x},{y+h-r} Z
bar:    <rect x={x} y={y} width={w} height="5" fill="{colour}" opacity="0.6"/>
```

Fill-opacity 0.04, stroke-width 1, accent bar height 5 at opacity 0.6.

**Container cards**: fill-opacity 0.02, stroke-width 0.8, opacity 0.25, bar height 4 at opacity 0.15.

## Arrow Construction (Horizontal-First Rule)

**Always define arrows as horizontal shapes first, then rotate.**

Template: `translate(tipX, tipY) rotate(angleDeg)` wrapping:
- Stem: `<line x1="-length" y1="0" x2="-10" y2="0"/>`
- Head: `<polygon points="0,0 -10,-5 -10,5"/>`

Angle = `atan2(dy, dx)` degrees. Stem ends at `-10` (arrowhead base). Arrows fully opaque.

**MANDATORY for diagonal connectors**: Run `calc_connector.py` to compute geometry. Never hand-calculate angles.

### Angular Arrow Design (Chamfered L-Routing)

Chamfer at 90-degree bends with 4px diagonal:

```
Instead of: M{x1},{y1} V{y_mid} H{x2}
Use:        M{x1},{y1} V{y_mid-4} L{x1+4},{y_mid} H{x2-4} L{x2},{y_mid+4}
```

## Z-Order Layering

SVG renders in document order. Use:
1. **Background** - track lines, grid lines, subtle fills
2. **Connectors** - arrows, progress indicators
3. **Nodes** - circles, boxes, cards
4. **Content** - icons and text inside nodes

### Track Line Cutouts

Cut gaps in track at milestone nodes. **Never use `fill="white"` as knockout.**

## Timeline Style: Signal Timing Hexagons

Vertically symmetric hexagon segments. Centre line y=42, top y=34, bottom y=50, slope 3px.

```xml
<path d="M64,42 L67,34 H157 L160,42 L157,50 H67 Z" class="wave-work"/>
```

Phase boundaries: vertical lines in brand colour. Module labels above hexagons. Cards below uniform width. Segment widths proportional to time.

## Layered Model Style: Stacked Sections

Thin horizontal bands stacked vertically. Header row at layer_top+14px, sub-items at +26px. Layer height 34px, gap 4px. Left margin x=30.

## Header Banner Layout

Left column (title 28px, subtitle 18px, credits 12px), right column (imagery + logos), accent gradient bar. ViewBox 800x110.

## Decorative Background Imagery

Faint icons at fg-1 colour, opacity 0.10-0.35, 15-20px extent, between text and logos. Add `.decor` CSS class for dark mode switching.

## Bars and Shapes Consistency

| Primitive | Standard rx |
|-----------|------------|
| Data/progress bars | `rx="2"` |
| Legend chips | `rx="2"` |
| Grid squares | `rx="3"` |
| Container boxes | `rx="8"` |
| Cards (path-based) | Q curves |

## Data-Driven Curves

Use **PCHIP interpolation** from `scipy.interpolate` for smooth data-driven paths. Dense sample 200-250 points. `stroke-linejoin="round"`, stroke 2-2.5px, fill segments at `fill-opacity="0.18-0.25"`.

## Markdown Integration

```markdown
![Description](path/to/image.svg)
```

No HTML `<img>` unless width control needed.

## Creative Infographics

Organic visual forms - flowing paths, concentric rings, orbital loops, funnels, constellations. Same theme swatch, CSS classes, transparent background. Use `<path>`, `<circle>`, `<ellipse>`. Low fill opacities (0.04-0.15). Layout topology uses `flow:`, `orbit:`, `scatter:`, `radial:`.

## Troubleshooting

- **Text invisible in dark mode**: Use CSS class instead of inline fill
- **Overlapping elements**: Re-verify against grid comment, run `check_overlaps.py`
- **Arrows wrong direction**: Use horizontal-first rule with `calc_connector.py`
- **Colours off-theme**: Check every hex against swatch, run `check_contrast.py`
- **Wrong size in markdown**: Remove `width`/`height` from `<svg>`, use `viewBox` only

---
name: svg-standards
description: Core SVG infographic standards - grid-first design, CSS theme classes with dark/light mode, card shapes, arrows, connectors, typography, icons, z-order layering, layout topology, and structural rules. Auto-triggered when creating or modifying SVG infographics, diagrams, banners, timelines, flowcharts, or any visual SVG content.
---

# SVG Infographic Standards

Apply these standards when generating or modifying SVG infographics for documents. Read the **workflow** skill for the mandatory 6-phase per-image creation process. Read the **theme** skill for palette approval and swatch generation. Read the **validation** skill for checker tool usage.

## Task Tracking

**MANDATORY**: Use Claude Code task tracking (TaskCreate/TaskUpdate) throughout all SVG work. Create a task list at the start of any multi-step SVG creation or modification. Mark each task in_progress when starting, completed when done. This provides visible progress to the user and prevents skipping steps.

## Key Principles (Quick Reference)

1. **Theme first** - approve `theme_swatch.svg` before deliverables
2. **Grid first** - viewBox, margins, panel origins, columns, rhythm BEFORE content. Invisible guide grid
3. **CSS theme classes** - `<style>` block + `prefers-color-scheme` media query. `class=`, never inline `fill=`
4. **File description comment** - before `<svg>`: filename, shows, intent, theme
5. **Grid comment** - after `<style>`, `GRID REFERENCE` documenting panel origins, columns, rhythm
6. **Layout topology comment** - h-align / v-align / h-stack / v-stack / contain / mirror, relationships not coords
7. **Five named layers** - `<g id="background">`, `<g id="nodes">`, `<g id="connectors">`, `<g id="content">`, `<g id="callouts">`. Every element belongs to exactly one. See Z-Order Layering
8. **Named component groups** - logical chunks in `<g id="component-name">`, lowercase-hyphen
9. **Transparent background** - `fill="transparent"` on root rect. No full-viewport fills
10. **Contrast rules** - every element contrasts its immediate background via theme colours. No `#000000`, no `#ffffff`
11. **Callouts via empty-space workflow** - never eyeball text positions. `empty-space` + `geom contains` + `geom rect-edge`. See Callout construction workflow
12. **Connector tool for every arrow** - no `rotate()`, no `atan2`, no hand paths. See Arrow Construction
13. **Verify all five** - `overlaps`, `contrast`, `alignment`, `css`, `connectors` before delivery
14. **Examples** - read relevant `examples/` SVGs before creating each image

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

**MANDATORY**: Define all colours in `<style>` block, reference via `class=`. Inline `fill="#hex"` acceptable only for structural shape fills, fixed-colour swatch elements, and decorative low-opacity imagery. Validate with `svg-infographics css --svg file.svg`.

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

### Default Placement

Place icons in the **upper-right** quadrant of the graphic (top-level decorative/identity icons) or the **upper-right** corner of each card (per-card icons), unless the composition explicitly requires otherwise. Rationale: upper-right is the western reading path's terminal scan point for a title row, so the icon reinforces identity without competing with the left-aligned title.

- **Graphic-level icon**: position inside the header band at `x = viewBox.width - margin - icon_size`, vertically centred on the title baseline
- **Card-level icon**: position inside the card at `x = card.x + card.w - 6 - icon_size`, `y = card.y + 6`, clear of the accent bar and the title text
- **Override only when**: the layout is a symmetric grid where centring reads better, a process flow where the icon anchors the start of a row, or a timeline where the icon sits on the event marker

## Card Backgrounds

**Square-top, rounded-bottom** path so accent bar sits flush. Bottom corner radius r=3.

```
fill:   M{x},{y} H{x+w} V{y+h-r} Q{x+w},{y+h} {x+w-r},{y+h} H{x+r} Q{x},{y+h} {x},{y+h-r} Z
bar:    <rect x={x} y={y} width={w} height="5" fill="{colour}" opacity="0.6"/>
```

Fill-opacity 0.04, stroke-width 1, accent bar height 5 at opacity 0.6.

**Container cards**: fill-opacity 0.02, stroke-width 0.8, opacity 0.25, bar height 4 at opacity 0.15.

## Arrow Construction (Connector Tool)

Every arrow, every connector, every shape built via `svg-infographics connector`. No exceptions. All output goes inside `<g id="connectors">` - never at root.

Tool returns in world coordinates:
- `trimmed_path_d` - stem path with arrowhead clearance subtracted. Paste directly as `<path d="...">`
- Per-end arrowhead polygon in world coordinates. Paste directly as `<polygon points="...">`
- `tangent` / `angle_deg` at each end
- `samples` along the path (tangent labels, progress markers, midpoint callouts)

No `rotate()` transforms. No `atan2` math. No horizontal-first templating. Tool does world-space rotation.

**Modes**:

| Mode | Use |
|------|-----|
| `straight` | Single line, two points |
| `l` | Axis-aligned L, sharp corner. First-axis inferred per segment |
| `l-chamfer` | L with 4px corner cut. Default for any L route |
| `spline` | Cubic Bezier via `bezier` lib when `start_dir`/`end_dir` given; PCHIP through waypoints otherwise |
| `manifold` | N starts → single merge → spine → single fork → M ends. Canonical Sankey bundle |

Flags (all modes): `--arrow {none,start,end,both}`, `--head-size L,H`, `--margin N`, `--standoff N|start,end` (default 1px), `--color`, `--width`, `--opacity`. Spline tangent magnitude: `--tangent-magnitude N` (default 0.5×chord).

### Canonical manifold

One merge = `spine_start`, one fork = `spine_end`. All start strands terminate at `spine_start`, tangent to spine. All end strands leave from `spine_end`, tangent to spine. No branch distribution. Strands = cubic Beziers. Tangent magnitude = `tension`:

- `tension=0` → long tangents → floppy bow
- `tension=1` → short tangents → stiff near-straight
- `tension=0.5` default → Sankey S-curve
- Scalar or `(start,end)` tuple

Strands inherit spine direction. Override per endpoint via 3-tuple `(x,y,"E")` or `(x,y,45)` (compass or deg CW from north).

### Auto-edge mode

Pass shapes to `calc_connector`, skip coordinates:

- `src_rect=(x,y,w,h)` / `tgt_rect=(x,y,w,h)` - axis-aligned rects
- `src_polygon=[(x,y),...]` / `tgt_polygon=[(x,y),...]` - closed polygon

Tool computes centroid → rays to target centroid → perimeter intersection as endpoint. Explicit coords override.

### Edge midpoint rule

Connector endpoints = shape EDGE MIDPOINTS. Never centres, never arbitrary corners. Arrow meets card perpendicular, text clash avoided.

Tools:

1. `geom attach --shape rect --side right|left|top|bottom --pos mid` - midpoint per side per rect
2. `connector ... --src-rect ... --tgt-rect ...` (or `--src-polygon`/`--tgt-polygon`) - auto-edge
3. `geom curve-midpoint --points "[(x,y),...]"` - arc-length midpoint of polyline. Labels ON a connector
4. `geom shape-midpoint --points "[(x,y),...]"` - area-weighted centroid. Direction inference only, never endpoint

Never eyeball endpoint coords. `primitives <shape>` for named anchors. `geom attach` for edge snap. Hand-authored `<g transform="rotate(...)">` arrow groups = workflow violation.

### Callout placement rules

Callout = leader line + italic text annotating element. Six rules:

1. Text in empty zone, close to target. Close-but-clear > far-but-safe.
2. Leader must not cross shapes or edges. Unavoidable: minimise crossings, fewest wins.
3. Leader length: short-but-not-too-short. Clear text bbox, reach target at visible angle, readable in one glance.
4. Text never overlaps own connector. Even with clean leader, bbox must sit in empty space.
5. Callouts never overlap each other. Stack one zone or distribute.
6. Leader anchor stops `standoff` px short of text bbox. Never glue to edge, never enter interior. Compute: `geom offset-rect --rect <text-bbox> --by <standoff>` inflates, then `geom rect-edge --rect <inflated> --from <target>` returns anchor. Default standoff 3px.

### Callout naming convention (MANDATORY)

Every callout uses the `callout` namespace in THREE places - otherwise invisible to tooling:

1. **Group id**: `<g id="callout-<name>">`. Prefix `callout-` mandatory. `empty-space` skips via default `exclude_ids=("callout-*",)`. `overlaps` parses prefix for CALLOUT CROSS-COLLISIONS block.
2. **Text class**: `class="callout-text"` on every `<text>` child. Font/fill/size from CSS class.
3. **Line class**: `class="callout-line"` on every `<line>` / `<path>` / `<polyline>` leader. Stroke/width/opacity from class.

All callout groups live inside the top-level `<g id="callouts">` layer - never at root, never mixed with nodes or connectors.

Example:
```html
<style>
  .callout-text { font-family: Segoe UI; font-size: 8.5px; font-style: italic; fill: #7a4a15; }
  .callout-line { stroke: #7a4a15; stroke-width: 1; fill: none; }
</style>
<g id="callouts">
  <g id="callout-merge">
    <text x="445" y="130" class="callout-text">merge point</text>
    <text x="445" y="141" class="callout-text">(single convergence)</text>
    <line x1="410" y1="230" x2="464" y2="144" class="callout-line"/>
  </g>
</g>
```

Non-compliant callouts invisible to `empty-space`, `overlaps`, and workflow.

### Callout construction workflow

7 steps, two audit gates. SVG is source of truth.

1. **Pre-audit**: `svg-infographics overlaps --svg file.svg`. Fix any CALLOUT CROSS-COLLISIONS before adding new work.
2. **Empty space**: `svg-infographics empty-space --svg file.svg --tolerance 20`. Returns boundary polygons per free island, shrunk inward 20px. Tool parses SVG directly, every visible element is an obstacle, existing `<g id="callout-*">` excluded by default. Larger tolerance (25-30) for dense scenes.
3. **Text bbox**: width ≈ `len(text) * font_size * 0.55`, height ≈ `font_size + 2` per line. Stack lines if multi-line.
4. **Best placement**: for each island, `geom contains --polygon <island> --bbox <text-bbox>`. Pass condition `contained=YES convex-safe=YES` (islands often L-shaped - bbox must fit the polygon, NOT its axis-aligned bounds). Then audit leader vs all hard shapes. Leader may start inside target's own shape, must not touch others. Prefer islands closest to target, ties broken by shortest leader.
5. **Iterate**: place one, append to `<g id="callouts">` with `callout-` prefix, re-run empty-space. Default exclude filters placed callouts automatically.
6. **Render**: text at chosen position, leader drawn, placed inside `<g id="callouts">`. Bbox was scaffold - discard.
7. **Post-audit**: re-run `overlaps --svg file.svg`. CALLOUT CROSS-COLLISIONS must be clean. Any violation means reposition + repeat.

**Empty zones for manifold scenes** (highest yield first):

- Above spine between merge/fork: `x∈[spine_start.x, spine_end.x], y<spine.y`, no strand traffic
- Below spine between merge/fork: same x range, `y>spine.y`
- Shoulder gaps between src/sink rows (~18-20px, one-line each)
- Above title row, below last row of cards

**Audit gates**:

- `overlaps --svg file.svg` - CALLOUT CROSS-COLLISIONS checks leader-vs-text, leader-vs-leader, text-vs-text pairwise across every `<g id="callout-*">`. Run before (baseline) and after (acceptance).
- `collide` - callout leaders vs non-callout geometry. Run before shipping, reposition offenders.

**`empty-space` not callout-only**: any "where to put X without overlapping Y" problem - legends, badges, logos, secondary labels, decorative imagery. Point at SVG, pick largest island that fits, drop element in `<g id="content">` or a named layer.

### Angular Arrow Design (Chamfered L-Routing)

Chamfer at 90-degree bends with 4px diagonal:

```
Instead of: M{x1},{y1} V{y_mid} H{x2}
Use:        M{x1},{y1} V{y_mid-4} L{x1+4},{y_mid} H{x2-4} L{x2},{y_mid+4}
```

## Z-Order Layering (MANDATORY)

SVG renders in document order. Five named groups, bottom-up. Every drawable element belongs to exactly one layer. No mixed content, no stray top-level shapes.

```xml
<svg ...>
  <style>...</style>
  <g id="background">...</g>   <!-- fills, grids, banners -->
  <g id="nodes">...</g>         <!-- cards, circles, hexes -->
  <g id="connectors">...</g>    <!-- arrows, strands, L-routes, manifold, spine -->
  <g id="content">...</g>       <!-- icons, labels, text inside nodes -->
  <g id="callouts">...</g>      <!-- callout groups - ALWAYS topmost -->
</svg>
```

**Connectors layer**: every arrow, strand, L-chamfer, spine, manifold bundle lives in `<g id="connectors">`. Never draw connectors at root. Connector tool output goes inside this group.

**Callouts layer**: every callout group lives in `<g id="callouts">`. Each callout is a child `<g id="callout-<name>">` - see Callout naming convention below. Callouts on their own layer means they render on top of everything, they batch-exclude cleanly from empty-space detection via `exclude_ids=("callout-*",)`, and they can be stripped / regenerated without touching the rest of the SVG.

### Track Line Cutouts

Cut gaps in track at milestone nodes. Never use `fill="white"` as knockout.

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

**MANDATORY**: For ANY curve that passes through known waypoints - decision boundaries, distribution shapes, trend lines, score trajectories, ROC/PR curves, isolines, sigmoid/logistic shapes - generate the path with the bundled `primitives spline` tool. Do NOT hand-write `C` (cubic) or `Q` (quadratic) bezier commands. Hand-rolled beziers require guessing control-point placement, overshoot waypoints, kink at segment joins, and fail visual review every time.

```bash
svg-infographics primitives spline \
  --points "80,200 150,80 300,120 450,60 600,140" \
  --samples 200
```

The tool runs PCHIP (Piecewise Cubic Hermite Interpolating Polynomial) which is monotonicity-preserving (no overshoot between waypoints), produces continuous tangents at every waypoint, and emits a ready-to-paste `<path d="...">` plus the resampled point list.

Required parameters:
- **Waypoints**: 4-8 points, X strictly increasing. Pick visual landmarks the curve must hit, not control points
- **Samples**: 200-250 for smooth output (fewer for jagged debug renders)
- **Render**: `stroke-linejoin="round"`, `stroke-width="2"` to `2.5"`, fill segments at `fill-opacity="0.18-0.25"` if shading under the curve

Hand-written `<path d="M... C... C..."/>` for data curves is a workflow violation - rerun with `primitives spline` and replace the path.

## Markdown Integration

```markdown
![Description](path/to/image.svg)
```

No HTML `<img>` unless width control needed.

## Creative Infographics

Organic visual forms - flowing paths, concentric rings, orbital loops, funnels, constellations. Same theme swatch, CSS classes, transparent background. Use `<path>`, `<circle>`, `<ellipse>`. Low fill opacities (0.04-0.15). Layout topology uses `flow:`, `orbit:`, `scatter:`, `radial:`.

## Troubleshooting

- **Text invisible in dark mode**: Use CSS class instead of inline fill
- **Overlapping elements**: Re-verify against grid comment, run `svg-infographics overlaps`
- **Arrows wrong direction**: Rerun `svg-infographics connector` with the correct `--from` and `--to` coordinates; paste the returned `trimmed_path_d` and arrowhead polygons
- **Colours off-theme**: Check every hex against swatch, run `svg-infographics contrast`
- **CSS compliance errors**: Run `svg-infographics css --svg file.svg` to find inline fills and missing dark mode overrides
- **Imprecise coordinates**: Use `svg-infographics primitives <shape>` for exact anchor points
- **Wrong size in markdown**: Remove `width`/`height` from `<svg>`, use `viewBox` only

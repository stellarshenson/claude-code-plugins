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
10. **Verify All Four** - Run `svg-infographics contrast`, `svg-infographics overlaps`, `svg-infographics alignment`, `svg-infographics css` before delivery
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

**Every arrow, every connector, every shape - built with `svg-infographics connector`. No exceptions.**

The tool returns everything needed to drop an arrow into the SVG in world coordinates:
- `trimmed_path_d` - the stem path with arrowhead clearance already subtracted (paste directly as `<path d="...">`)
- Per-end arrowhead polygon in world coordinates (paste directly as `<polygon points="...">`)
- `tangent` and `angle_deg` at each end (for placing labels or joining to other elements)
- `samples` along the path (for tangent labels, progress markers, midpoint callouts)

No `rotate()` transforms, no `atan2` math, no horizontal-first templating. The connector tool already does the rotation in world space and returns final coordinates.

**Modes:**

| Mode | Use |
|------|-----|
| `straight` | Single line, two points |
| `l` | Axis-aligned L (sharp corner). First-axis inferred per segment |
| `l-chamfer` | L with 4px corner cut. Default for any L route |
| `spline` | Cubic Bezier via `bezier` lib when `start_dir`/`end_dir` given; PCHIP through waypoints otherwise |
| `manifold` | N starts → single merge (`spine_start`) → spine → single fork (`spine_end`) → M ends. Canonical Sankey bundle |

Flags on every mode: `--arrow {none,start,end,both}`, `--head-size L,H`, `--margin N`, `--standoff N|start,end` (default 1px), `--color`, `--width`, `--opacity`. Spline tangent magnitude: `--tangent-magnitude N` (default: 0.5×chord).

### Canonical manifold

One merge = `spine_start`, one fork = `spine_end`. All start strands terminate at `spine_start`, tangent to spine. All end strands leave from `spine_end`, tangent to spine. No branch distribution. Strands = cubic Beziers. Tangent magnitude = `tension`:

- `tension=0` → long tangents → floppy bow
- `tension=1` → short tangents → stiff near-straight
- `tension=0.5` default → Sankey S-curve
- Scalar or `(start,end)` tuple

Strands inherit spine direction. Override per endpoint via 3-tuple `(x,y,"E")` or `(x,y,45)` (compass or deg CW from north).

### Auto-edge mode

Pass whole shapes to `calc_connector`, skip coordinates:

- `src_rect=(x,y,w,h)` / `tgt_rect=(x,y,w,h)` — axis-aligned rects
- `src_polygon=[(x,y),...]` / `tgt_polygon=[(x,y),...]` — closed polygon

Tool computes centroid → rays to target centroid → returns perimeter intersection as endpoint. Explicit coords override.

### Edge midpoint rule

**Connector endpoints = shape EDGE MIDPOINTS, never centres or arbitrary corners.** Arrow meets card perpendicular to edge, text clash avoided.

Tools:

1. `svg-infographics geom attach --shape rect --side right|left|top|bottom --pos mid` — exact midpoint per side per rect
2. `svg-infographics connector ... --src-rect ... --tgt-rect ...` (or `--src-polygon`/`--tgt-polygon`) — auto-edge: tool intersects centroid-to-centroid ray with perimeter
3. `svg-infographics geom curve-midpoint --points "[(x,y),...]"` — arc-length midpoint of polyline (Bezier/L/spline). For labels ON a connector
4. `svg-infographics geom shape-midpoint --points "[(x,y),...]"` — area-weighted centroid of closed polygon. For direction inference only, NEVER as endpoint

Never eyeball endpoint coords. Use `primitives <shape>` for named anchors, `geom attach` for edge snap points. Hand-authored `<g transform="rotate(...)">` arrow groups are a workflow violation — connector tool replaces them.

### Callout placement rules

Callout = leader line + italic text annotating element. Six rules:

1. Text in empty zone, close to target. Close-but-clear > far-but-safe.
2. Leader should not cross any shapes or edges. If unavoidable, minimise crossings (pick the route with the fewest).
3. Leader length: short-but-not-too-short. Long enough to clear the text bbox and reach the target with a visible angle; short enough that the reader's eye follows it in one glance.
4. Text must not overlap own connector. Even if leader clean, text bbox must sit in empty space.
5. Callouts must not overlap each other. Stack in one zone or distribute.
6. Leader anchor stops `standoff` px short of text bbox. Never glue to bbox edge, never enter bbox interior. Compute: `svg-infographics geom offset-rect --rect <text-bbox> --by <standoff>` (inflate), then `svg-infographics geom rect-edge --rect <inflated> --from <target>` returns anchor point. Default standoff 3px.

### Callout naming convention (MANDATORY)

Every callout MUST use the `callout` namespace across THREE places so that tooling can find, exclude, and audit them:

1. **Group id prefix**: wrap every callout in `<g id="callout-<name>">`. The `callout-` prefix is mandatory — `svg-infographics empty-space` skips matching groups via the default `exclude_ids=["callout-*"]`, so existing callouts don't pollute the obstacle set when re-running placement. `svg-infographics overlaps` also uses the prefix to detect the CALLOUT CROSS-COLLISIONS audit block.
2. **Text class**: every `<text>` child uses `class="callout-text"`. Font style, fill colour, and size come from the CSS class; `check_overlaps` resolves it to compute text bboxes for cross-collision checks.
3. **Line class**: every leader `<line>` / `<path>` / `<polyline>` uses `class="callout-line"`. Stroke colour, width, and opacity come from the class.

Example:
```html
<style>
  .callout-text { font-family: Segoe UI; font-size: 8.5px; font-style: italic; fill: #7a4a15; }
  .callout-line { stroke: #7a4a15; stroke-width: 1; fill: none; }
</style>
<g id="callout-merge">
  <text x="445" y="130" class="callout-text">merge point</text>
  <text x="445" y="141" class="callout-text">(single convergence)</text>
  <line x1="410" y1="230" x2="464" y2="144" class="callout-line"/>
</g>
```

No other id prefix or class scheme is accepted. Callouts that don't follow the convention are invisible to `empty-space`, `overlaps`, and the callout placement workflow.

### Callout construction workflow

7 steps per callout (two audit gates - pre-placement and post-placement):

1. **Pre-audit existing callouts**: `svg-infographics overlaps --svg file.svg` reports a CALLOUT CROSS-COLLISIONS section. Any prior leader/text overlap must be resolved before adding new callouts - stacking new work on top of broken layout wastes iterations.
2. **Empty space islands**: `svg-infographics empty-space --svg file.svg --tolerance 20` → boundary polygons per free island, each shrunk inward by 20px. `--tolerance 20` is the minimum for callouts; anything smaller lets leaders clip adjacent shapes. Larger values (25-30) for denser scenes. The tool reads the SVG directly — every visible element becomes an obstacle automatically. Existing `<g id="callout-*">` groups are excluded by default via `--exclude-id`. No manual shape list needed.
3. **Text bbox**: width ≈ `len(text) * font_size * 0.55`, height ≈ `font_size + 2` per line. Stack lines if multi-line.
4. **Best placement**: for each island, verify text bbox fits via `svg-infographics geom contains --polygon <island> --bbox <text-bbox>` - use returned polygon boundary, NEVER its axis-aligned bbox (islands can be L-shaped or horseshoe; text dropped in an empty sub-rectangle of the bbox may land inside an occluded shape). `contained=YES convex-safe=YES` is the pass condition. Then audit leader vs ALL hard shapes (not just the island) - leader may start inside the shape containing target but must not touch any other shape. Prefer islands closest to target, ties broken by shortest leader.

   **Iterate callouts**: place one at a time, then add its text bbox to the hard-shape list OR append it to the SVG file with the `callout-` prefix before re-running. Either approach works because empty-space excludes `callout-*` by default. Skipping this step causes the next placement to land on top of the previous one - caught by step 7's post-audit but wastes iteration cycles.
5. **Leader audit**: no shape crossings. If unavoidable, pick fewest. Short-but-not-too-short per rule 3.
6. **Render** text at chosen position, draw leader. Bbox was scaffold, discard.
7. **Post-audit**: re-run `svg-infographics overlaps --svg file.svg`. The CALLOUT CROSS-COLLISIONS section must be clean (no "leader of X crosses text of Y", "leader of X crosses leader of Y", "text of X overlaps text of Y"). Also re-check general overlaps against all other geometry. Any violation means the placement failed - reposition and repeat.

**SVG IS the source of truth**: `svg-infographics empty-space --svg ...` reads the actual SVG. No shape list is built by the caller. Shoulders near curved connectors appear as genuine free regions.

**`empty-space` not callout-only**: any "where to put X without overlapping Y" question. Legends, badges, secondary labels, logos, icons, decorative imagery, orphan annotations. Point it at your SVG, pick the largest island that fits the element, drop the element there.

**Empty zones for manifold scenes** (highest yield first):

- Above spine between merge/fork: `x∈[spine_start.x, spine_end.x], y<spine.y` — no strand traffic
- Below spine between merge/fork: same x range, `y>spine.y`
- Gaps between src/sink rows (~18-20px, one line each)
- Above title row, below last row of cards

**Audit gates** (both mandatory):

- `svg-infographics overlaps --svg file.svg` — the CALLOUT CROSS-COLLISIONS section checks leader-vs-other-callout-text, leader-vs-leader, and text-bbox-vs-text-bbox pairwise across all `<g id="callout-*">` groups. Run before (no-regression baseline) and after (acceptance gate).
- `svg-infographics collide` on callout leaders + shape rects catches crossings against non-callout geometry; run before shipping, reposition offenders.

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

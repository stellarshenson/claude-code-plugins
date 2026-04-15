---
name: svg-standards
description: Core SVG infographic standards - grid-first design, CSS theme classes with dark/light mode, card shapes, arrows, connectors, typography, icons, z-order layering, layout topology, and structural rules. Auto-triggered when creating or modifying SVG infographics, diagrams, banners, timelines, flowcharts, or any visual SVG content.
---

# SVG Infographic Standards

Apply these standards when generating/modifying SVG infographics for documents. Read **workflow** skill for mandatory 6-phase per-image process. Read **theme** skill for palette approval and swatch generation. Read **validation** skill for checker tool usage.

## Task Tracking

**MANDATORY**: Use Claude Code task tracking (TaskCreate/TaskUpdate) throughout all SVG work. Task list at start of any multi-step SVG creation or modification. Mark in_progress on start, completed on finish. Visible progress, prevents skipping steps.

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

`<style>` block with `prefers-color-scheme` media query for OS-theme-aware colours. `class=` not inline `fill=` for theme-dependent text.

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

**Never apply `opacity` to text elements.** Fonts always render at full opacity. Contrast via colour selection, not transparency. Applies to `opacity`, `fill-opacity` on `<text>`, and parent `<g>` opacity inheritance.

### Opacity and Transparency Rule

Default solid fills. Opacity appropriate for:
- Card background tints (`fill-opacity="0.04-0.06"`)
- Track lines (`opacity="0.3"`)
- Decorative background imagery (`opacity="0.10-0.35"`)

**Never use opacity on**: data bars, progress bars, legend chips, text, logos.

### CSS-First Rule

**MANDATORY**: Define all colours in `<style>` block, reference via `class=`. Inline `fill="#hex"` acceptable only for structural shape fills, fixed-colour swatch elements, decorative low-opacity imagery. Validate with `svg-infographics css --svg file.svg`.

### Dark Mode Limitations

`prefers-color-scheme` works in standalone/`<object>`/inline SVG but **not** via `<img>` or markdown `![alt](path)`. Design for light background primary. Assume `#1e1e1e` dark bg.

## Contrast Rules

Every element MUST contrast immediate background using theme colours only.

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

Always transparent background. Exception: banner gradient bars that ARE the design element.

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

**MANDATORY**: Every SVG uses explicit grid documented in XML comment.

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

**MANDATORY**: First element after `<style>` = `<g id="guide-grid" display="none">`. Hierarchical bisection:

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

Wrap logical components in `<g id="component-name">`. Lowercase-hyphen names. Light/dark variants use `-light`/`-dark` suffix.

### Multi-Card Grids

All cards in a row same width: `(viewBox_width - 2*margin - (n-1)*gap) / n`. Inter-card gap 12px (timeline) or 20px (content). Card padding 16px left/right, 20px top from accent bar.

### Mandatory Margins

All elements respect minimum margins from card borders and neighbours. Compute final bbox after all transforms.

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

Every SVG starts with comment before `<svg>`. Filename, shows, intent, theme.

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

Place icons **upper-right** quadrant of graphic (top-level decorative/identity) or **upper-right** corner of each card (per-card), unless composition explicitly requires otherwise. Rationale: upper-right = western reading path terminal scan point for a title row, so icon reinforces identity without competing with left-aligned title.

- **Graphic-level icon**: inside header band at `x = viewBox.width - margin - icon_size`, vertically centred on title baseline
- **Card-level icon**: inside card at `x = card.x + card.w - 6 - icon_size`, `y = card.y + 6`, clear of accent bar and title text
- **Override only when**: symmetric grid where centring reads better, process flow where icon anchors start of row, timeline where icon sits on event marker

## Card Backgrounds

**Square-top, rounded-bottom** path - accent bar sits flush. Bottom corner radius r=3.

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
| `straight` | Single line. Auto edge-snap from src/tgt rects |
| `l` | Axis-aligned L, sharp corner. Edge-aware via rects + directions |
| `l-chamfer` | L with 4px corner cut. Default for any L route |
| `spline` | Cubic Bezier via `bezier` lib when `start_dir`/`end_dir` given; PCHIP through waypoints otherwise |
| `manifold` | N starts → single merge → spine → single fork → M ends. Canonical Sankey bundle |

Flags (all modes): `--arrow {none,start,end,both}`, `--head-size L,H`, `--margin N`, `--standoff N|start,end` (default 1px), `--color`, `--width`, `--opacity`. Spline tangent magnitude: `--tangent-magnitude N` (default 0.5×chord).

### L-route edge-aware API (CANONICAL)

`l` / `l-chamfer` between rects: pass BOTH rects AND cardinal directions. Tool snaps endpoints to edge midpoints, locks first-axis, no parallel-to-edge drift.

```bash
svg-infographics connector --mode l-chamfer \
  --src-rect "70,90,60,40"  --start-dir E \
  --tgt-rect "370,160,60,40" --end-dir S \
  --chamfer 4 --standoff 4 --arrow end
```

**Direction semantics**:
- `start_dir`: exit direction from src. `E`/`W` → horizontal, `N`/`S` → vertical.
- `end_dir`: travel direction at tgt arrival. `S` = "moving south" → enters TOP edge. Inverse: `E`→left, `W`→right, `N`→bottom, `S`→top.
- Perpendicular pair (`start=E, end=S`) → 1-bend L, corner at `(tgt_mid_x, src_mid_y)`.

**Failure mode without directions**: points `--from 630,160 --to 870,260`; tool infers first-axis from `|dx|>|dy|`; vertical segment at `x=870` runs along tgt's left edge; arrow dives from the side. Fix = `start=E, end=S` — vertical lands at `x=tgt_mid_x=900` entering top cleanly.

**Missing direction = warning**. Rects without directions fall back to centre-to-target ray snap; tool emits warning. Always pass directions for L-routes.

### Multi-elbow L via `controls`

Long or crowded routes: pass explicit waypoints via `--controls "[(x1,y1),(x2,y2),...]"`. Each waypoint becomes an elbow; tool threads axis-aligned segments between consecutive points. Soft cap 5 - exceed it and tool warns. Prefer auto-route over hand-authored waypoints.

### Auto-route (A*) for L-routes

`--auto-route --svg scene.svg` runs grid A* on the SVG obstacle bitmap and picks multi-elbow waypoints that clear every shape in the file. Cell-based; default cell=10 px, margin=5 px clearance. Use when a 1-bend L collides with other elements:

```bash
svg-infographics connector --mode l-chamfer \
  --src-rect "70,90,60,40"  --start-dir E \
  --tgt-rect "670,180,80,40" --end-dir W \
  --auto-route --svg scene.svg \
  --chamfer 4 --standoff 4 --arrow end
```

Flags: `--route-cell-size N` (smaller = higher fidelity + slower), `--route-margin N` (obstacle clearance), `--container-id ID` (clip routing to one element). Router fails gracefully: unroutable = fallback to 1-bend L + warning in output. Always inspect `warnings` field.

### Container-scoped routing and detection

`--container-id ID` on `empty-space`, `callouts`, and `connector --auto-route` clips operation to the interior of a specific closed shape. Element must be rect/circle/ellipse/polygon/polyline/path - groups rejected because `<g>` has no geometry. Use when placing callouts or routing connectors BETWEEN two shapes that both live inside the same card:

```bash
svg-infographics empty-space --svg scene.svg --container-id card-1
svg-infographics callouts --svg scene.svg --plan plan.json --container-id card-1
svg-infographics connector --mode l --auto-route --svg scene.svg \
  --container-id card-1 --src-rect ... --tgt-rect ... --start-dir E --end-dir W
```

**Picking rule**: the container ID must name a shape whose interior geometrically contains BOTH endpoints (or both callout targets). Outside obstacles are ignored; inside obstacles still occupy. Regions returned by `empty-space` carry a `container_id` field for caller verification.

### Spline waypoints

`--waypoints "x1,y1 x2,y2 x3,y3 x4,y4"` for PCHIP. 3-5 waypoints enough — monotonicity-preserving, more points overfit. Showcase with visible markers: place `<g id="cell-4-waypoints">` AFTER path in connectors layer (render on top). Tiny cross glyphs (two crossing `<line>` + `stroke-linecap: round`) per waypoint, varied accent-2 shades for distinction.

### Canonical manifold

One merge = `spine_start`, one fork = `spine_end`. All start strands terminate at `spine_start`, tangent to spine. All end strands leave from `spine_end`, tangent to spine. No branch distribution. Strands = cubic Beziers. Tangent magnitude = `tension`:

- `tension=0` → long tangents → floppy bow
- `tension=1` → short tangents → stiff near-straight
- `tension=0.5` default → Sankey S-curve
- Scalar or `(start,end)` tuple

Strands inherit spine direction. Override per endpoint via 3-tuple `(x,y,"E")` or `(x,y,45)` (compass or deg CW from north).

### Auto-edge mode (straight)

Shapes to `calc_connector`, skip coordinates:

- `src_rect=(x,y,w,h)` / `tgt_rect=(x,y,w,h)` - axis-aligned rects
- `src_polygon=[(x,y),...]` / `tgt_polygon=[(x,y),...]` - closed polygon

Straight mode: centroid → target ray → perimeter intersection = endpoint. L / l-chamfer: use edge-aware API above (rects + directions), NOT centroid-ray snap — risks parallel-to-edge failure. Explicit coords override rects.

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

**Primary path: `svg-infographics callouts`.** One tool, one call, all callouts placed jointly. Greedy solver with random-ordering restarts. Handles leader + leaderless callouts in a single pass, text bbox containment, leader cleanness (auto walk-out of target container), pairwise conflicts (text-vs-text overlap, leader-vs-text crossing, leader-vs-leader crossing), preferred-side hints. Returns best layout plus top-5 alternatives per callout with penalty breakdowns.

**Two modes: leader vs leaderless.** Different semantics, different defaults, different scoring.

**Leader mode** (default, `"leader": true` or omitted):
- Text block + visible leader line from target to text bbox edge.
- Use: dense diagrams, label sits in free whitespace away from target, leader connects the two.
- Standoff default 20 px (leader tip stops 20 px short of text for arrowhead clearance).
- Score: leader length (sweet spot 55 px), diagonal angle preference, target-distance overshoot, preferred side.

**Leaderless mode** (`"leader": false`):
- Text block placed close to target, NO connecting line. Text IS the pointer.
- Use: group headers ("5 INPUTS" above a card stack), waypoint tags, legend entries, anywhere spatial proximity alone reads as "this label belongs to that thing".
- Standoff default 5 px (much tighter than leader — no leader inflation).
- Score: pulls text bbox CENTRE toward target point (sweet spot 0). Single unique minimum → horizontally-symmetric labels settle centred on target instead of drifting to one side.
- **Target placement trick**: to make the label land ABOVE the shape (not on top of it), place the target ~8-12 px above the shape's top edge. The centre-distance solver will position the label centre at the target → text bbox sits just above the shape with natural breath. Same trick for below/left/right.

**Selection rule**:
- Leaderless → group header, waypoint tag, legend entry, "floating above/below" label.
- Leader → target inside dense content, label must float away from target with visible connection.

Three-step workflow:

1. **Pre-audit**: `svg-infographics overlaps --svg file.svg`. Fix any CALLOUT CROSS-COLLISIONS before adding new work.
2. **Propose**: build a plan JSON listing every callout you need (id, target, text). Call `svg-infographics callouts --svg file.svg --plan callouts.json`. Paste the returned coordinates into the SVG inside the `<g id="callouts">` layer, each callout wrapped in its own `<g id="callout-<name>">` group.
3. **Post-audit**: re-run `overlaps --svg file.svg`. CALLOUT CROSS-COLLISIONS must be clean. Any violation means the plan was under-constrained (unusual - the tool already checks these). Reposition or adjust weights and re-run.

Plan file shape (see `svg-infographics callouts --help` for the full schema):

```json
[
  {"id": "callout-merge",  "target": [410, 230], "text": "merge point\n(single convergence)"},
  {"id": "callout-fork",   "target": [650, 230], "text": "fork point\n(single divergence)"},
  {"id": "callout-label",  "target": [150,  95], "text": "source 1", "leader": false}
]
```

Targets can be points `[x, y]` or bboxes `[x, y, w, h]`. Multi-line text uses `\n`. `"leader": false` marks a leaderless label (see Leader vs leaderless above for semantics and defaults). Optional `preferred_side` is `"above" | "below" | "left" | "right"` (soft penalty, not a hard filter).

**Common failure mode: target coordinates in the wrong visual region.** The tool places text AT / CENTRED ON the target point. If a "group label" target like `(140, 40)` actually sits in the title band at `y=40` rather than above the card group at `y=62`, the label lands in the title band - visually wrong even though the tool is doing exactly what it was told. When leaderless placements look off, check the target first: it should be the point where you want the label to appear, not a semantic anchor like "the group centroid".

**Debug path: manual primitives.** When the tool's result looks wrong or you want to investigate why a specific candidate was rejected, drop down to the individual primitives:

- `svg-infographics empty-space --svg file.svg --tolerance 20` - returns free-region boundary polygons, shrunk inward by 20 px, with `<g id="callout-*">` already excluded by default
- `svg-infographics geom contains --polygon <island> --bbox <text-bbox>` - verifies a proposed text bbox fits inside a region polygon (`contained=YES convex-safe=YES` pass condition; islands are often L-shaped so axis-aligned bbox bounds are not enough)
- `svg-infographics geom offset-rect --rect <text-bbox> --by <standoff>` - inflates the text bbox by standoff
- `svg-infographics geom rect-edge --rect <inflated> --from <target>` - returns the leader anchor (point on the inflated bbox where the leader terminates)
- `svg-infographics overlaps --svg file.svg` - post-audit; the `CALLOUT CROSS-COLLISIONS` block reports leader-vs-text, leader-vs-leader, text-vs-text violations pairwise across every `<g id="callout-*">`

**Empty zones for manifold scenes** (highest yield first, useful context when reading the tool's output):

- Above spine between merge/fork: `x∈[spine_start.x, spine_end.x], y<spine.y`, no strand traffic
- Below spine between merge/fork: same x range, `y>spine.y`
- Shoulder gaps between src/sink rows (~18-20 px, one-line each)
- Above title row, below last row of cards

**`empty-space` not callout-only**: any "where to put X without overlapping Y" problem - legends, badges, logos, secondary labels, decorative imagery. Point at SVG, pick the largest island that fits, drop the element in `<g id="content">` or a named layer.

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

**Callouts layer**: every callout group lives in `<g id="callouts">`. Each callout = child `<g id="callout-<name>">` - see Callout naming convention below. Own layer means: renders on top of everything, batch-excludes cleanly from empty-space detection via `exclude_ids=("callout-*",)`, strippable/regeneratable without touching rest of SVG.

### Track Line Cutouts

Cut gaps in track at milestone nodes. Never `fill="white"` as knockout.

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

**MANDATORY**: For ANY curve passing through known waypoints - decision boundaries, distribution shapes, trend lines, score trajectories, ROC/PR curves, isolines, sigmoid/logistic shapes - generate path with bundled `primitives spline` tool. Do NOT hand-write `C` (cubic) or `Q` (quadratic) bezier commands. Hand-rolled beziers: guess control-point placement, overshoot waypoints, kink at segment joins, fail visual review every time.

```bash
svg-infographics primitives spline \
  --points "80,200 150,80 300,120 450,60 600,140" \
  --samples 200
```

Tool runs PCHIP (Piecewise Cubic Hermite Interpolating Polynomial) - monotonicity-preserving (no overshoot between waypoints), continuous tangents at every waypoint, emits ready-to-paste `<path d="...">` plus resampled point list.

Required parameters:
- **Waypoints**: 4-8 points, X strictly increasing. Pick visual landmarks the curve must hit, not control points
- **Samples**: 200-250 for smooth output (fewer for jagged debug renders)
- **Render**: `stroke-linejoin="round"`, `stroke-width="2"` to `2.5"`, fill segments at `fill-opacity="0.18-0.25"` if shading under curve

Hand-written `<path d="M... C... C..."/>` for data curves = workflow violation. Rerun `primitives spline`, replace path.

## Markdown Integration

```markdown
![Description](path/to/image.svg)
```

No HTML `<img>` unless width control needed.

## Creative Infographics

Organic visual forms - flowing paths, concentric rings, orbital loops, funnels, constellations. Same theme swatch, CSS classes, transparent background. Use `<path>`, `<circle>`, `<ellipse>`. Low fill opacities (0.04-0.15). Layout topology: `flow:`, `orbit:`, `scatter:`, `radial:`.

## Troubleshooting

- **Text invisible in dark mode**: Use CSS class instead of inline fill
- **Overlapping elements**: Re-verify against grid comment, run `svg-infographics overlaps`
- **Arrows wrong direction**: Rerun `svg-infographics connector` with correct `--from`/`--to` coordinates; paste returned `trimmed_path_d` and arrowhead polygons
- **Colours off-theme**: Check every hex against swatch, run `svg-infographics contrast`
- **CSS compliance errors**: Run `svg-infographics css --svg file.svg` - finds inline fills and missing dark mode overrides
- **Imprecise coordinates**: Use `svg-infographics primitives <shape>` for exact anchor points
- **Wrong size in markdown**: Remove `width`/`height` from `<svg>`, use `viewBox` only

---
name: svg-standards
description: Core SVG infographic standards - grid-first design, CSS theme classes with dark/light mode, card shapes, arrows, connectors, typography, icons, z-order layering, layout topology, and structural rules. Auto-triggered when creating or modifying SVG infographics, diagrams, banners, timelines, flowcharts, or any visual SVG content.
---

# SVG Infographic Standards

Design application for AI agents. Agent is the designer, CLI tools are the application. Never hand-write coordinates, colours, or connector paths. Every position from a tool call. Every colour from a CSS class. Every arrow from the connector tool.

**Core tools** (drawing canvas):

| Tool | Purpose |
|------|---------|
| `svg-infographics primitives <shape>` | Shape geometry + anchors (18 built-in: rect, circle, hexagon, gear, cloud, document, etc) |
| `svg-infographics connector --mode <m>` | 5 modes: straight, l, l-chamfer, spline, manifold. Auto-routes around obstacles |
| `svg-infographics geom <op>` | Alignment constraints: midpoint, perpendicular, attach, contains, offset, polar |
| `svg-infographics callouts` | Joint label placement via solver. Leader and leaderless modes |
| `svg-infographics empty-space` | Free-region detection |
| `svg-infographics charts <type>` | Pygal charts with theme-matched dual-mode palettes |
| `svg-infographics shapes search` | draw.io stencil library (1000+ shapes, on demand) |

**Quality panel** (refuse delivery until clean):

| Tool | Catches |
|------|---------|
| `svg-infographics overlaps` | Text/shape overlap, spacing, font floors, callout collisions |
| `svg-infographics contrast` | WCAG 2.1 light + dark |
| `svg-infographics alignment` | Grid snap, rhythm, topology |
| `svg-infographics connectors` | Dead ends, edge-snap, chamfer, dangling |
| `svg-infographics css` | Inline fills, missing dark mode, forbidden colours |
| `svg-infographics collide` | Pairwise connector intersections |

Read **workflow** skill for 6-phase process. Read **theme** for palette approval. Read **validation** for checker usage.

## Task Tracking

**MANDATORY**: TaskCreate/TaskUpdate throughout. Task list at start, mark in_progress/completed. Prevents skipped steps.

## Key Principles

1. **Tool first** - every coordinate from `primitives`, every arrow from `connector`, every placement from `geom`/`callouts`/`empty-space`. Never eyeball
2. **Place via empty-space** - before placing inside a container, run `empty-space --edges-only --container-id <id>`. Text/strokes/outlines = obstacles, fills = not. Role-shared elements h-aligned or v-aligned via `geom align`
3. **Theme first** - approve `theme_swatch.svg` before deliverables
4. **Grid first** - viewBox, margins, columns, rhythm as comments BEFORE content
5. **Group everything** - every visual unit = a `<g>`. Topology comment declares relationships. No loose elements
6. **CSS classes** - `<style>` + `prefers-color-scheme`. `class=`, never inline `fill=`
7. **File description comment** before `<svg>`: filename, shows, intent, theme
8. **Five named layers** - `background`, `nodes`, `connectors`, `content`, `callouts`
9. **Transparent background** - `fill="transparent"` on root rect
10. **Contrast via theme** - no `#000000`, no `#ffffff`
11. **Validate before delivery** - all six checkers. No run, no ship
12. **Read examples** - study `examples/` (66 references) before each image

## CSS Theme Classes and Dark Mode

`<style>` block with `prefers-color-scheme`. `class=` not inline `fill=`.

### Usage

```xml
<!-- Theme-aware -->
<text class="fg-2" font-size="12">Heading</text>
<text class="on-fill" font-size="9">75%</text>

<!-- Fixed colour: use fill= when it must not change -->
<rect fill="#E61C29" opacity="0.6"/>
```

### The `on-fill` Class

Text on saturated accent fills:
- Light mode: dark text (fg-1)
- Dark mode: pale tint

### Font Opacity Rule

**Never apply `opacity` to text.** Fonts render at full opacity. Contrast via colour, not transparency. Applies to `opacity`, `fill-opacity` on `<text>`, and parent `<g>` opacity inheritance.

### Opacity and Transparency

Opacity only for:
- Card background tints (`fill-opacity="0.04-0.06"`)
- Track lines (`opacity="0.3"`)
- Decorative background imagery (`opacity="0.10-0.35"`)

**Never use opacity on**: data bars, progress bars, legend chips, text, logos.

### CSS-First Rule

**MANDATORY**: Define all colours in `<style>`, reference via `class=`. Inline `fill="#hex"` OK only for structural shape fills, fixed-colour swatch elements, decorative low-opacity imagery. Validate with `svg-infographics css`.

### Dark Mode Limitations

`prefers-color-scheme` works in standalone/`<object>`/inline SVG. Fails via `<img>` or markdown `![alt](path)`. Design light-primary. Assume `#1e1e1e` dark bg.

## Contrast Rules

Every element MUST contrast its background via theme colours.

### Background-Foreground Pairing

| Background | Foreground |
|------------|-----------|
| Transparent (doc bg) | fg-1 or fg-2 |
| bg-1 (accent at 0.04-0.08) | fg-1 headings, fg-3/fg-4 labels |
| bg-2 (accent at 0.3-0.6) | fg-1 or fg-2 |
| Full accent fill (0.8-1.0) | fg-4 or fg-1 (whichever contrasts) |
| Accent swatch chip | fg-1 label below, not on top |

### Forbidden Colours

- `#000000` - invisible on dark
- `#ffffff` - invisible on light, breaks dark mode
- Pure greys below `#404040` or above `#c0c0c0`
- Anything not in approved theme

### Transparent Background

Always transparent. Exception: banner gradient bars that ARE the design element.

### Safe Neutral Palette (no brand defined)

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

### Design Workflow

1. Grid and guide lines - viewBox, guide grid `<g>`, grid comment, topology
2. Placeholder rectangles at correct positions
3. Structural elements - card paths, track lines, accent bars, dividers
4. Content - text, icons, arrows, data
5. Styling - CSS classes, fills, opacities, dark mode
6. Validation

### Vertical Rhythm

Single step size (14px typical), content rows on multiples:

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

### Layout Topology and Grouping

**CRITICAL**: Every visual unit = a `<g>` group. Topology comment declares relationships. Grouping is mandatory foundation for maintainability, alignment, rework.

#### Topology comment (MANDATORY)

Declares relationships, NOT coordinates.

```xml
<!-- TOPOLOGY:
  h-stack: card-research, card-plan, card-implement, card-review (gap=20)
  v-align: card-research.top = card-plan.top = card-implement.top = card-review.top
  contain: section-header > title, subtitle
  contain: card-research > icon-search, label-research, desc-research
  h-spacing: card-research .. card-review (equal)
  mirror: section-left ~ section-right (x-axis)
-->
```

| Operation | Meaning |
|-----------|---------|
| `h-stack` | Adjacent left to right |
| `v-stack` | Adjacent top to bottom |
| `h-align` | Share x (column) |
| `v-align` | Share y (row) |
| `h-spacing` | Equal horizontal gaps |
| `v-spacing` | Equal vertical gaps |
| `contain` | Group inside another |
| `mirror` | Symmetric groups |

#### Grouping rules (MANDATORY)

Every visual unit = a `<g>`. No loose elements at root or inside layer groups.

| Visual unit | Group pattern |
|-------------|--------------|
| Card | `<g id="card-name">` containing rect + accent-bar + title + description + icon |
| Icon + label | `<g id="icon-name">` containing scaled icon `<g>` + adjacent `<text>` |
| Section | `<g id="section-name">` containing header + card groups |
| Legend | `<g id="legend">` containing swatch rects + label texts |
| Connector + label | connector in `<g id="connectors">`, label in `<g id="callout-name">` |
| Decorative cluster | `<g id="deco-name">` for embroidery, particle fields |

**Build at origin, position via translate.** Child elements use local coords (0,0 relative). Group positioned by one `transform="translate(x,y)"`. Move the group = change one number.

```xml
<g id="card-pricing" transform="translate(320, 120)">
  <rect x="0" y="0" width="200" height="140" class="card-body"/>
  <rect x="0" y="0" width="200" height="5" class="accent-bar"/>
  <g id="icon-tag" transform="translate(164, 8) scale(0.667)">
    <!-- Lucide icon at local coords -->
  </g>
  <text x="16" y="32" class="fg-1">Pricing</text>
  <text x="16" y="52" class="fg-3">per-seat model</text>
</g>
```

#### Group transforms

- `translate(x, y)` - primary positioning
- `scale(sx, sy)` - icon sizing: `scale(0.667)` = 16px from 24px Lucide
- `rotate(deg, cx, cy)` - rare. Prefer tool-computed geometry
- Combine: `transform="translate(100, 200) scale(0.5)"` - translate first (parent coords), then scale

#### Positioning via tools

```bash
# Align 4 card groups to same top edge
geom align --rects "[(0,0,200,140),(0,0,200,140),(0,0,200,140),(0,0,200,140)]" --edge top

# Distribute with equal gaps
geom distribute --rects "[(50,120,200,140),(270,120,200,140),(490,120,200,140),(710,120,200,140)]" --axis h --mode gap
```

Returned positions = `translate(x, y)` values.

#### Nesting

Max 3 levels deep: layer > section > card. Transforms compose.

```
<g id="nodes">                          <!-- layer -->
  <g id="section-inputs">              <!-- section -->
    <g id="card-api" transform="...">  <!-- card -->
```

#### Group bbox

After transforms, effective bbox = child bbox in root coords. `geom` tools operate in root coords. Pass world-space rects, not local group coords.

### Multi-Card Grids

Same width per row: `(viewBox_width - 2*margin - (n-1)*gap) / n`. Inter-card gap 12px (timeline) or 20px (content). Card padding 16px left/right, 20px top from accent bar.

### Mandatory Margins

All elements respect minimum margins from card borders and neighbours. Compute final bbox after all transforms.

### Inner and Outer Bounding Boxes

Every element has two bboxes:
- **Inner**: rendered extent including stroke width
- **Outer**: inner + per-element padding

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

- `viewBox` only, no `width`/`height`
- Default width: `1800` for new infographics
- Common sizes: `1800x200` (stats), `1800x280` (timelines), `1800x320` (flows), `1800x400` (headers), `1800x700` (grids)

### Typography

- `font-family="Helvetica, Arial, sans-serif"` - system fonts only
- Sizes 7-28px. Progression: hero stats (18-28px) > headings (12-14px) > labels (10-11px) > metadata (8-9px)
- `text-anchor="middle"` for centred, explicit `x` for left-aligned
- **Never `<tspan>` for mixed styling** - separate `<text>` elements

### Unicode glyphs in text

Use Unicode directly, never ASCII fallbacks.

| Intent | Write | Don't write |
|---|---|---|
| right arrow | `→` (U+2192) | `->`, `-&gt;` |
| left arrow | `←` (U+2190) | `<-`, `&lt;-` |
| up / down arrow | `↑` / `↓` | `^`, `v` |
| bidirectional | `↔` (U+2194) | `<->` |
| heavy right arrow | `➜` / `➔` | `>` |
| em-dash | `—` (U+2014) | `--` |
| en-dash | `–` (U+2013) | `-` in ranges |
| ellipsis | `…` (U+2026) | `...` |
| multiplication / cross | `×` (U+00D7) | `x` |
| bullet | `•` (U+2022) | `*` |
| chevron right | `›` (U+203A) | `>` |

XML comments differ: `--` breaks parsing. Keep ASCII prose in comments. Unicode only in text nodes.

## Icon Sourcing

Prefer open-source SVG libraries.

| Library | License | Icons |
|---------|---------|-------|
| Lucide | ISC | 1000+ |
| Feather | MIT | 280+ |

Embed in `<g transform="translate(x,y) scale(s)">`, override stroke. Comment: `<!-- Icon: {name} (Lucide, ISC license) -->`. Scale: 0.583 (~14px), 0.667 (~16px), 0.5 (~12px).

### Default Placement

Place icons upper-right quadrant (graphic-level) or upper-right corner of each card (per-card). Western reading path terminates upper-right; icon reinforces identity without competing with title.

- **Graphic-level**: inside header band at `x = viewBox.width - margin - icon_size`, vertically centred on title baseline
- **Card-level**: inside card at `x = card.x + card.w - 6 - icon_size`, `y = card.y + 6`
- **Override only when**: symmetric grid, process flow with icon anchoring row start, timeline with icon on event marker

### Text placement relative to visual elements

Place text AFTER icons/shapes/decorations. Compute label coords from placed geometry via `geom midpoint`, `geom attach`, `geom perpendicular`. Never eyeball. Prevents overlap between icons and labels, titles and accent bars, connector labels and arrowheads.

## Card Backgrounds

Square-top, rounded-bottom path. Accent bar flush. Bottom corner radius r=3.

```
fill:   M{x},{y} H{x+w} V{y+h-r} Q{x+w},{y+h} {x+w-r},{y+h} H{x+r} Q{x},{y+h} {x},{y+h-r} Z
bar:    <rect x={x} y={y} width={w} height="5" fill="{colour}" opacity="0.6"/>
```

Fill-opacity 0.04, stroke-width 1, accent bar height 5 at opacity 0.6.

**Container cards**: fill-opacity 0.02, stroke-width 0.8, opacity 0.25, bar height 4 at opacity 0.15.

## Arrow Construction (Connector Tool)

Every arrow, every connector, every shape via `svg-infographics connector`. No exceptions. Output goes inside `<g id="connectors">`.

Tool returns in world coordinates:
- `trimmed_path_d` - stem with arrowhead clearance. Paste as `<path d="...">`
- Per-end arrowhead polygon. Paste as `<polygon points="...">`
- `tangent` / `angle_deg` at each end
- `samples` along path (for tangent labels, progress markers, midpoint callouts)

No `rotate()` transforms. No `atan2`. No horizontal-first templating.

**Modes**:

| Mode | Use |
|------|-----|
| `straight` | Single line. Auto edge-snap from src/tgt rects |
| `l` | Axis-aligned L, sharp corner. Edge-aware via rects + directions |
| `l-chamfer` | L with 4px corner cut. Default for any L route |
| `spline` | Cubic Bezier via `bezier` lib when `start_dir`/`end_dir` given; PCHIP through waypoints otherwise |
| `manifold` | N starts → single merge → spine → single fork → M ends. Sankey bundle |

Flags (all modes): `--arrow {none,start,end,both}`, `--head-size L,H`, `--margin N`, `--standoff N|start,end` (default 1px), `--color`, `--width`, `--opacity`. Spline: `--tangent-magnitude N` (default 0.5×chord).

### L-route edge-aware API (CANONICAL)

`l` / `l-chamfer` between rects: pass BOTH rects AND cardinal directions. Tool snaps endpoints to edge midpoints, locks first-axis.

```bash
svg-infographics connector --mode l-chamfer \
  --src-rect "70,90,60,40"  --start-dir E \
  --tgt-rect "370,160,60,40" --end-dir S \
  --chamfer 4 --standoff 4 --arrow end
```

**Direction semantics**:
- `start_dir`: exit from src. `E`/`W` → horizontal, `N`/`S` → vertical
- `end_dir`: travel INTO tgt. `S` = moving south → enters TOP edge. Inverse: `E`→left, `W`→right, `N`→bottom, `S`→top
- Perpendicular pair (`start=E, end=S`) → 1-bend L, corner at `(tgt_mid_x, src_mid_y)`

**Missing direction = warning**. Rects without directions fall back to centre-to-target ray snap. Always pass directions for L-routes.

### Multi-elbow L via `controls`

`--controls "[(x1,y1),(x2,y2),...]"` for explicit waypoints. Soft cap 5. Prefer auto-route over hand waypoints.

### Auto-route (A*)

`--auto-route --svg scene.svg` runs grid A* on SVG obstacle bitmap. Default cell=10px, margin=5px. Use when 1-bend L collides:

```bash
svg-infographics connector --mode l-chamfer \
  --src-rect "70,90,60,40"  --start-dir E \
  --tgt-rect "670,180,80,40" --end-dir W \
  --auto-route --svg scene.svg \
  --chamfer 4 --standoff 4 --arrow end
```

Flags: `--route-cell-size N` (smaller = higher fidelity + slower), `--route-margin N`, `--container-id ID`. Unroutable = fallback 1-bend L + warning. Inspect `warnings` field.

### Straight-line collapse (`--straight-tolerance`)

Default 20px. When src and tgt can slide along edges to a shared coordinate within tolerance, L degenerates to single straight segment. No corner, no chamfer, no twist.

**Slide bias**: smaller geometry slides less. Larger rect absorbs displacement. Disable with `--straight-tolerance 0`.

### Stem preservation (`--stem-min`)

Default 20px. Reserves clean cardinal stem behind each arrowhead. Three layers:

- **A\* penalty zone**: turns near endpoints cost `STEM_TURN_PENALTY=100`. Zone radius `ceil(reserve / cell_size) + 1` cells
- **Cell-centre snap**: first and last waypoints snap so non-cardinal axis matches real endpoints exactly
- **Chamfer clamp**: first/last bevels clamped so arrowhead trim never walks into bevel

Geometry-impossible = non-fatal warning with actual stem achieved. Set `--stem-min 0` for legacy.

### Container-scoped routing

`--container-id ID` on `empty-space`, `callouts`, `connector --auto-route` clips to interior of one closed shape. Must be rect/circle/ellipse/polygon/polyline/path - groups rejected.

```bash
svg-infographics empty-space --svg scene.svg --container-id card-1
svg-infographics callouts --svg scene.svg --plan plan.json --container-id card-1
svg-infographics connector --mode l --auto-route --svg scene.svg \
  --container-id card-1 --src-rect ... --tgt-rect ... --start-dir E --end-dir W
```

Container ID must name a shape whose interior contains BOTH endpoints. Outside obstacles ignored, inside obstacles respected.

### Spline waypoints

`--waypoints "x1,y1 x2,y2 x3,y3 x4,y4"` for PCHIP. 3-5 waypoints enough. Showcase with markers: `<g id="cell-4-waypoints">` AFTER path in connectors layer. Tiny cross glyphs (two crossing `<line>` + `stroke-linecap: round`) in varied accent-2 shades.

### Canonical manifold

One merge = `spine_start`, one fork = `spine_end`. Start strands terminate at `spine_start`, tangent to spine. End strands leave `spine_end`, tangent to spine. Strands = cubic Beziers. Tangent magnitude = `tension`:

- `tension=0` → long tangents → floppy bow, strands cross easily
- `tension=1` → short tangents → stiff near-straight, max separation
- `tension=0.75` default → clean S-curves with good separation
- Scalar or `(start,end)` tuple for asymmetric stiffness

Strands inherit spine direction. Override per endpoint via 3-tuple `(x,y,"E")` or `(x,y,45)`.

### Manifold quality warnings

Two non-fatal warning types. Always inspect `warnings`.

**"strands CROSS each other"** - two strands in same fan intersect. Fix:
1. Increase `tension` toward 1.0
2. Move `spine_start`/`spine_end` further from endpoints
3. Pass explicit `fork_points`/`merge_points`

**"curves BACKWARD against spine flow"** - strand S-curve overshoots opposite spine direction before turning back. Fix:
1. Increase `tension` (0.85-0.95)
2. Reduce perpendicular spread of endpoints
3. Move fork/merge point further along spine

### Auto-edge mode (straight)

Shapes to `calc_connector`, skip coordinates:

- `src_rect=(x,y,w,h)` / `tgt_rect=(x,y,w,h)` - axis-aligned rects
- `src_polygon=[(x,y),...]` / `tgt_polygon=[(x,y),...]` - closed polygon

Straight mode: centroid → target ray → perimeter intersection. L / l-chamfer: use edge-aware API (rects + directions), NOT centroid-ray snap. Explicit coords override rects.

### Edge midpoint rule

Connector endpoints = shape EDGE MIDPOINTS. Never centres, never arbitrary corners.

Tools:

1. `geom attach --shape rect --side right|left|top|bottom --pos mid` - edge midpoint
2. `connector ... --src-rect ... --tgt-rect ...` - auto-edge
3. `geom curve-midpoint --points "[(x,y),...]"` - arc-length midpoint of polyline. Labels ON a connector
4. `geom shape-midpoint --points "[(x,y),...]"` - area-weighted centroid. Direction inference only, never endpoint

Never eyeball endpoints. Hand-authored `<g transform="rotate(...)">` arrow groups = workflow violation.

### Callout placement rules

Callout = leader line + italic text annotating element. Six rules:

1. Text in empty zone, close to target. Close-but-clear > far-but-safe
2. Leader must not cross shapes or edges. Unavoidable: minimise crossings
3. Leader length: short-but-not-too-short. Clear bbox, reach target at visible angle
4. Text never overlaps own connector
5. Callouts never overlap each other
6. Leader stops `standoff` px short of text bbox. Compute: `geom offset-rect --rect <text-bbox> --by <standoff>` inflates, then `geom rect-edge --rect <inflated> --from <target>` returns anchor. Default standoff 3px

### Callout naming convention (MANDATORY)

Every callout uses the `callout` namespace in THREE places:

1. **Group id**: `<g id="callout-<name>">`. `empty-space` skips via `exclude_ids=("callout-*",)`. `overlaps` parses prefix for CALLOUT CROSS-COLLISIONS
2. **Text class**: `class="callout-text"` on every `<text>` child
3. **Line class**: `class="callout-line"` on every `<line>`/`<path>`/`<polyline>` leader

All callout groups live inside top-level `<g id="callouts">` layer.

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

Non-compliant callouts invisible to `empty-space`, `overlaps`, workflow.

### Callout construction workflow

**Primary path: `svg-infographics callouts`.** One tool, one call, all callouts placed jointly. Greedy solver with random-ordering restarts. Handles leader + leaderless in single pass. Returns best layout + top-5 alternatives per callout with penalty breakdowns.

**Two modes: leader vs leaderless.**

**Leader mode** (default, `"leader": true` or omitted):
- Text block + visible leader line
- Use: dense diagrams, label in free whitespace away from target
- Standoff default 20px
- Score: leader length (sweet spot 55px), diagonal angle, target overshoot, preferred side

**Leaderless mode** (`"leader": false`):
- Text block close to target, no connecting line. Text IS the pointer
- Use: group headers, waypoint tags, legend entries, spatial-proximity labels
- Standoff default 5px (tighter - no leader)
- Score: pulls bbox CENTRE toward target (sweet spot 0). Symmetric labels settle centred
- **Target trick**: to land label ABOVE shape, place target ~8-12px above shape top edge

**Selection**:
- Leaderless → group header, waypoint tag, legend, floating label
- Leader → target inside dense content, label floats away with connection

Three-step workflow:

1. **Pre-audit**: `svg-infographics overlaps`. Fix CALLOUT CROSS-COLLISIONS before adding work
2. **Propose**: build plan JSON. Call `svg-infographics callouts --svg file.svg --plan callouts.json`. Paste coordinates into `<g id="callouts">` layer, each in own `<g id="callout-<name>">` group
3. **Post-audit**: re-run `overlaps`. CALLOUT CROSS-COLLISIONS must be clean

Plan file shape (see `--help` for full schema):

```json
[
  {"id": "callout-merge",  "target": [410, 230], "text": "merge point\n(single convergence)"},
  {"id": "callout-fork",   "target": [650, 230], "text": "fork point\n(single divergence)"},
  {"id": "callout-label",  "target": [150,  95], "text": "source 1", "leader": false}
]
```

Targets: points `[x, y]` or bboxes `[x, y, w, h]`. Multi-line: `\n`. `"leader": false` = leaderless. Optional `preferred_side` is `"above"|"below"|"left"|"right"` (soft penalty).

**Common failure mode**: target coordinates in wrong visual region. Tool places text AT/CENTRED ON target. When leaderless looks off, check target first - it should be the point where the label appears, not a semantic anchor.

**Debug path: manual primitives**:

- `svg-infographics empty-space --svg file.svg --tolerance 20` - free-region polygons, shrunk 20px, `<g id="callout-*">` excluded by default
- `svg-infographics geom contains --polygon <island> --bbox <text-bbox>` - verifies bbox fits inside region. `contained=YES convex-safe=YES` pass condition
- `svg-infographics geom offset-rect --rect <text-bbox> --by <standoff>` - inflates bbox
- `svg-infographics geom rect-edge --rect <inflated> --from <target>` - leader anchor point
- `svg-infographics overlaps --svg file.svg` - post-audit

**Empty zones for manifold scenes** (highest yield first):

- Above spine between merge/fork: `x∈[spine_start.x, spine_end.x], y<spine.y`
- Below spine between merge/fork: same x range, `y>spine.y`
- Shoulder gaps between src/sink rows (~18-20px)
- Above title row, below last row

**`empty-space` not callout-only**: works for legends, badges, logos, secondary labels, decorative imagery. Point at SVG, pick largest island that fits, drop into `<g id="content">` or named layer.

### Angular Arrow Design (Chamfered L-Routing)

Chamfer at 90-degree bends with 4px diagonal:

```
Instead of: M{x1},{y1} V{y_mid} H{x2}
Use:        M{x1},{y1} V{y_mid-4} L{x1+4},{y_mid} H{x2-4} L{x2},{y_mid+4}
```

## Z-Order Layering (MANDATORY)

SVG renders in document order. Five named groups, bottom-up. Every drawable element in exactly one layer. No mixed content, no stray top-level shapes.

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

**Connectors layer**: every arrow, strand, L-chamfer, spine, manifold bundle inside `<g id="connectors">`. Never draw at root.

**Callouts layer**: every callout group inside `<g id="callouts">`. Each callout = child `<g id="callout-<name>">`. Renders on top, batch-excludes from empty-space via `exclude_ids=("callout-*",)`, strippable/regeneratable.

### Track Line Cutouts

Cut gaps in track at milestone nodes. Never `fill="white"` as knockout.

## Timeline Style: Signal Timing Hexagons

Vertically symmetric hexagons. Centre line y=42, top y=34, bottom y=50, slope 3px.

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

**MANDATORY**: For ANY curve through known waypoints - decision boundaries, distributions, trends, scores, ROC/PR, isolines, sigmoid/logistic - generate with `primitives spline`. Never hand-write `C` or `Q` bezier commands for data curves. Hand-rolled beziers guess control points, overshoot waypoints, kink at joins.

```bash
svg-infographics primitives spline \
  --points "80,200 150,80 300,120 450,60 600,140" \
  --samples 200
```

Tool runs PCHIP: monotonicity-preserving, continuous tangents at every waypoint. Emits paste-ready `<path d="...">` + resampled points.

Required:
- **Waypoints**: 4-8 points, X strictly increasing. Visual landmarks, not control points
- **Samples**: 200-250 for smooth (fewer for jagged debug)
- **Render**: `stroke-linejoin="round"`, `stroke-width="2"` to `2.5"`, fill segments at `fill-opacity="0.18-0.25"` if shading

Hand-written `<path d="M... C... C..."/>` for data curves = workflow violation.

## Markdown Integration

```markdown
![Description](path/to/image.svg)
```

No HTML `<img>` unless width control needed.

## Shape Primitives

### Built-in shapes (18 types)

`svg-infographics primitives <shape>` returns exact anchors + paste-ready SVG.

Basic: `rect`, `square`, `circle`, `ellipse`, `diamond`, `hexagon`, `star`, `arc`
3D wireframe: `cube`, `cuboid`, `cylinder`, `sphere`, `plane`, `axis`
Symbolic: `gear`, `pyramid`, `cloud`, `document`
Curves: `spline` (PCHIP through waypoints)

Each returns `{"svg": "...", "anchors": {"centre": [x,y], "top": [x,y], ...}, "bbox": [x,y,w,h]}`. Use anchors for connector attachment, labels, alignment.

### draw.io shape catalogue (1000+ stencils, on demand)

For shapes beyond the 18 built-ins (AWS icons, network, UML, BPMN, electrical):

```bash
# Download and index a stencil library (first use)
svg-infographics shapes index --source https://raw.githubusercontent.com/jgraph/drawio/master/src/main/webapp/stencils/general.xml

# Search
svg-infographics shapes search "database" --limit 5

# Render at target size
svg-infographics shapes render --name "database" --x 100 --y 200 --w 80 --h 60

# Browse a category
svg-infographics shapes catalogue --category general --output catalogue.svg
```

Cached after first use. Index ~500KB for full draw.io set. Scaled via `transform`, returns same `{"svg", "anchors", "bbox"}` contract.

**Shape selection rule**: check built-in primitives FIRST (faster, theme-matched, anchor-rich). Use draw.io only when no built-in matches. draw.io shapes get bbox-derived anchors only - no named semantic anchors.

## Creative Infographics

Organic forms - flowing paths, concentric rings, orbital loops, funnels, constellations. Same theme swatch, CSS classes, transparent background. Use `<path>`, `<circle>`, `<ellipse>`. Low fill opacities (0.04-0.15). Topology: `flow:`, `orbit:`, `scatter:`, `radial:`.

### Beautify (`/svg-infographics:beautify`)

Decoration pass on existing SVGs. Seven dimensions (colour variation, shapes, icons, embroidery, abstract graphics, bg texture, glow) at four intensities (low/medium/high/absurd). Additive only - never breaks layout. All additions live in `<g id="beautify-decorations">` + `<g id="beautify-icons">`, nothing outside. Bg strokes: thick (2.5-4) + ghost-transparent (opacity 0.04-0.06, HARD CAP 0.10). Geometry guard via `validate --baseline`. Local directive at project root: `./svg-infographics-beautify.md`. Mandatory `<!-- beautify -->` comment. Run `validate` + `overlaps` + `contrast` after every pass.

## Troubleshooting

- **Text invisible in dark mode**: use CSS class, not inline fill
- **Overlapping elements**: re-verify against grid comment, run `overlaps`
- **Arrows wrong direction**: rerun `connector` with correct `--from`/`--to`; paste `trimmed_path_d` and arrowhead polygons
- **Colours off-theme**: check every hex against swatch, run `contrast`
- **CSS compliance errors**: run `css --svg file.svg`
- **Imprecise coordinates**: use `primitives <shape>` for exact anchors
- **Wrong size in markdown**: remove `width`/`height` from `<svg>`, use `viewBox` only

# SVG Infographics Toolbox

Quick-reference tool palette. Find the right tool, get the command, follow the link.

## Design Tools (geometry + placement)

### Shapes
| Tool | Purpose |
|------|---------|
| [`primitives rect`](#primitives) | Rectangle with anchors |
| [`primitives circle`](#primitives) | Circle with anchors |
| [`primitives hexagon`](#primitives) | Hexagon with flat-top |
| [`primitives star`](#primitives) | Star polygon |
| [`primitives diamond`](#primitives) | Diamond/rhombus |
| [`primitives ellipse`](#primitives) | Ellipse |
| [`primitives arc`](#primitives) | Arc segment |
| [`primitives gear`](#primitives) | Toothed gear wheel |
| [`primitives cloud`](#primitives) | Cloud shape (5-7 lobes) |
| [`primitives document`](#primitives) | Page with dog-ear fold |
| [`primitives cube`](#primitives) | Isometric cube wireframe |
| [`primitives cuboid`](#primitives) | Isometric cuboid |
| [`primitives cylinder`](#primitives) | Isometric cylinder |
| [`primitives sphere`](#primitives) | Wireframe sphere |
| [`primitives pyramid`](#primitives) | Isometric pyramid |
| [`primitives plane`](#primitives) | Ground plane |
| [`primitives axis`](#primitives) | 3-axis coordinate system |
| [`primitives spline`](#primitives) | PCHIP curve through waypoints |

### Connectors
| Tool | Purpose |
|------|---------|
| [`connector --mode straight`](#connectors) | Direct line, auto edge-snap |
| [`connector --mode l`](#connectors) | Right-angle bend, sharp corners |
| [`connector --mode l-chamfer`](#connectors) | Right-angle with beveled corners, auto-route around obstacles |
| [`connector --mode spline`](#connectors) | Smooth curve through waypoints or cubic Bezier with tangent dirs |
| [`connector --mode manifold`](#connectors) | Sankey bundle: N starts -> merge -> spine -> fork -> M ends |

### Alignment and Constraints
| Tool | Purpose |
|------|---------|
| [`geom midpoint`](#geom) | Midpoint between two points |
| [`geom perpendicular`](#geom) | Perpendicular foot from point to line |
| [`geom parallel`](#geom) | Parallel line through a point |
| [`geom intersect`](#geom) | Line-line intersection |
| [`geom intersect-line-circle`](#geom) | Line-circle intersection |
| [`geom polar`](#geom) | Point at angle + distance from centre |
| [`geom evenly-spaced`](#geom) | N points on a circle |
| [`geom attach`](#geom) | Snap to rect edge or circle perimeter |
| [`geom contains`](#geom) | Point/bbox/polygon inside outer polygon? |
| [`geom align`](#geom) | Align rects: left, right, top, bottom, h-center, v-center |
| [`geom distribute`](#geom) | Space rects evenly: by centroids or by edge gaps |
| [`geom stack`](#geom) | H-stack or v-stack with fixed gap |
| [`geom offset-rect`](#geom) | Parallel offset (halo, padding) |
| [`geom offset-line`](#geom) | Parallel offset of a line |
| [`geom bisector`](#geom) | Angle bisector direction |
| [`geom curve-midpoint`](#geom) | Arc-length midpoint + tangent on polyline |
| [`geom rect-edge`](#geom) | Ray from centre to edge intersection |

### Placement
| Tool | Purpose |
|------|---------|
| [`callouts`](#callouts) | Joint label placement (leader + leaderless modes) |
| [`empty-space`](#empty-space) | Free-region detection for placement decisions |
| [`charts`](#charts) | Pygal chart generation with theme palette |
| [`shapes search`](#shapes) | Search draw.io stencil library (1000+ shapes) |
| [`shapes render`](#shapes) | Render draw.io shape at target size |

## Quality Panel (validation)

| Tool | Catches | Run when |
|------|---------|----------|
| [`overlaps`](#overlaps) | Text/shape overlap, spacing, font floors | After every content change |
| [`contrast`](#contrast) | WCAG 2.1 in light + dark mode | After colour/theme changes |
| [`alignment`](#alignment) | Grid snap, vertical rhythm, topology | After layout changes |
| [`connectors`](#connectors-check) | Dead ends, edge-snap, chamfers | After connector changes |
| [`css`](#css) | Inline fills, missing dark mode | After any style change |
| [`collide`](#collide) | Pairwise connector intersections | After adding connectors |

## Enhancement

| Tool | Purpose |
|------|---------|
| [`/svg-infographics:add-life`](#add-life) | Creative enhancement: glow, icons, embroidery, abstract shapes. 4 levels: low/medium/high/absurd |

---

## Tool Details

<a id="primitives"></a>
### primitives

```bash
svg-infographics primitives <shape> --x N --y N [--w N --h N | --r N] [--mode filled|outline|wire]
```

Returns `{"svg": "...", "anchors": {"centre": [x,y], ...}, "bbox": [x,y,w,h]}`. Paste `svg` directly. Use `anchors` for connector attachment.

<a id="connectors"></a>
### connector

```bash
svg-infographics connector --mode l-chamfer \
  --src-rect "x,y,w,h" --start-dir E --tgt-rect "x,y,w,h" --end-dir S \
  --chamfer 5 --standoff 4 --arrow end \
  [--auto-route --svg scene.svg --container-id ID] \
  [--straight-tolerance 20] [--stem-min 20]
```

Returns `trimmed_path_d` (paste as `<path d="...">`), arrowhead `polygon` (paste as `<polygon points="...">`), `tangent`, `angle_deg`, `bbox`, `warnings`.

Auto-route: A* grid around obstacles. Straight-line collapse: near-aligned endpoints slide to straight. Stem-min: guarantees clean cardinal segment behind arrowhead.

<a id="geom"></a>
### geom

```bash
svg-infographics geom <subcommand> [args]
```

Alignment subcommands (NEW):
- `align --rects "[(x,y,w,h),...]" --edge left|right|top|bottom|h-center|v-center`
- `distribute --rects "[(x,y,w,h),...]" --axis h|v --mode center|gap`
- `stack --rects "[(x,y,w,h),...]" --axis h|v --gap 10 --anchor start|center`

All return adjusted rect positions as JSON.

<a id="callouts"></a>
### callouts

```bash
svg-infographics callouts --svg scene.svg --plan callouts.json [--container-id ID]
```

Joint solver: leader mode (line + text, 20px standoff) or leaderless (text-only, 5px standoff). Hard constraints: no text overlap, no leader crossing.

<a id="empty-space"></a>
### empty-space

```bash
svg-infographics empty-space --svg scene.svg [--tolerance 20] [--container-id ID]
```

Rasterises SVG, finds free regions via distance transform + connected components. Returns boundary polygons sorted by area.

<a id="charts"></a>
### charts

```bash
svg-infographics charts bar --data "[('Q1',42),('Q2',55)]" --colors "#005f7a,#da8230" --colors-dark "#5cc8e0,#d4a04a"
```

Pygal SVG charts. Both `--colors` and `--colors-dark` required. WCAG contrast audit on every series.

<a id="shapes"></a>
### shapes (draw.io)

```bash
svg-infographics shapes index --source URL    # download + cache on first use
svg-infographics shapes search "database"     # fuzzy search
svg-infographics shapes render --name X --x 100 --y 200 --w 80 --h 60
svg-infographics shapes catalogue --category general --output cat.svg
```

Stencils downloaded on demand to `~/.cache/svg-infographics/drawio-stencils/`. NOT bundled.

<a id="overlaps"></a><a id="contrast"></a><a id="alignment"></a><a id="connectors-check"></a><a id="css"></a><a id="collide"></a>
### Validators

```bash
svg-infographics overlaps --svg file.svg
svg-infographics contrast --svg file.svg
svg-infographics alignment --svg file.svg
svg-infographics connectors --svg file.svg
svg-infographics css --svg file.svg
svg-infographics collide --connectors "[('a', [(0,0),(100,100)])]" --tolerance 4
```

All six MUST pass before delivery. Findings classified as Fixed / Accepted / Checker limitation.

<a id="add-life"></a>
### add-life

```bash
/svg-infographics:add-life path/to/file.svg medium
```

Six dimensions x four levels. Additive only - never breaks layout. Mandatory `<!-- add-life -->` comment in the SVG.

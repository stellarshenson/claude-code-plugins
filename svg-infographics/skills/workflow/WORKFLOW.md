# SVG Infographics - Mandatory Workflow

Exact workflow for creating SVG infographics. Every step in order, for every image. No shortcuts, no batching.

## Tool Inventory

Plugin tools. Reach for them whenever their task comes up - they exist so you don't guess coordinates, control points, tangents, contrast values.

**Calculators** (produce numbers + paste-ready SVG):

- `svg-infographics primitives` - rect, square, circle, ellipse, diamond, hex, star, arc, cube, cylinder, sphere, cuboid, plane, axis, **spline** (PCHIP through control points). Returns geometry + all named anchors (top, bottom, center, corners). Use for primitive shapes with exact anchors, isometric 3D, smooth waypoint curves
- `svg-infographics connector` - straight, L, L-chamfer, PCHIP spline connectors. Returns path d, trimmed path d (arrowhead clearance), arrowhead polygons (world coords), tangent angle per end. Pick mode matching style (straight = direct, l-chamfer = turning, spline = organic)
- `svg-infographics geom` - Fusion-360 sketch constraints: midpoints, perpendicular foot, line extension, tangent points, intersections, parallel/perpendicular, polar, evenly-spaced, concentric, bisector, attachment on rect/circle, parallel offsets. Run `geom --help` for full menu

**Validators** (read finished SVG, report problems):

- `svg-infographics overlaps` - text/shape overlaps, spacing rhythm, font-size floors
- `svg-infographics contrast` - WCAG 2.1 text AND object-vs-background (cards too faint) in light + dark
- `svg-infographics alignment` - grid snapping, vertical rhythm, layout topology
- `svg-infographics connectors` - zero-length, edge-snap, missing chamfer, dangling endpoints
- `svg-infographics css` - inline fills, missing dark-mode overrides, forbidden colours

Scan this list before computing values yourself. One bash call vs. a failed validation + rework cycle. Each calculator's `--help` includes a "use for" hint.

## Skill Activation

Before creating any SVG:

1. Read 3-5 examples from `examples/` closest to requested type
2. Read theme swatch (`theme_swatch_*.svg`) for target brand palette and CSS class names
3. Create `svg-workflow-checklist.md` in target images directory

## Per-Image Workflow (6 Phases)

Each image goes through all 6 phases sequentially. Do NOT move to next image until current completes. Do NOT batch-create.

### Phase 1: Research

- Read 3-5 relevant examples for THIS image type (e.g. `header_banner_*.svg` for headers, `timeline_hexagon.svg` for timelines, `card_grid.svg` for card grids)
- Read theme swatch for CSS class names (fg-1, fg-2, fg-3, accent-1, accent-2) and hex values
- Identify closest pattern: card grid, flow diagram, timeline, stats banner, header banner, bar chart, hub-and-spoke, layered model
- Note conventions: card dimensions, arrow style, text sizes, spacing

### Phase 2: Invisible Grid

Write grid BEFORE any visuals. Blueprint.

1. Write `=== GRID ===` comment defining:
   - ViewBox width and height
   - Margins (min 10px from viewBox edge)
   - All column x-positions: card lefts, card rights, divider positions, arrow midpoints, legend x
   - All row y-positions: card tops, card bottoms, accent bar heights, text baselines, legend rows
   - Vertical rhythm step (14px for card content, 10px for legend)
   - Card internal padding: 12px from accent bar bottom to first text baseline, 14px between text lines
   - Arrow paths: start, end, chamfer midpoint x, stem end x (4px before target), tip x
   - Track line segments: start x, end x for each segment between milestone cutouts (cx-r to cx+r)

2. Write `=== LAYOUT TOPOLOGY ===` comment defining relationships (NOT coordinates):
   - Operations: h-align, v-align, h-stack, v-stack, contain, mirror, flow
   - Reference named components (card-1, arrow-1, legend), not coordinates
   - No `--` inside XML comments (invalid XML)

### Phase 3: Scaffold

Place structural elements at grid positions. No text, no icons, no content.

1. `<style>` with ALL CSS classes:
   - fg-1, fg-2, fg-3 (+ fg-4 if needed) with hex from theme swatch
   - accent-1, accent-2 if used
   - `@media (prefers-color-scheme: dark)` overrides for every class

2. `<g id="guide-grid" display="none">` with reference lines at major grid positions

3. Card outlines as `<path>`:
   - Flat-top, rounded-bottom: `M{x},{y} H{x+w} V{y+h-r} Q{x+w},{y+h} {x+w-r},{y+h} H{x+r} Q{x},{y+h} {x},{y+h-r} Z`
   - Bottom corner radius r=3
   - Fill: accent at `fill-opacity="0.04"`
   - Stroke: accent at `stroke-width="1"`

4. Accent bars as `<rect>`:
   - At card top, height=5, accent colour, opacity=0.6
   - x, y, width match card path exactly (flush)

5. All arrows and connectors via `svg-infographics connector`. **No separate "arrow" concept** - simple point-to-point arrow is a `straight` connector with `--arrow end`. Same tool handles straight, L-routes, chamfered L, PCHIP splines. Rotating horizontal templates by hand is forbidden.

   Tool returns (world coordinates):
   - `trimmed_path_d` - stem with arrowhead clearance. Paste as `<path d="...">`
   - Per-end arrowhead polygon. Paste as `<polygon points="...">`
   - `tangent` / `angle_deg` at each end
   - `samples` along path

   Do not author `<g transform="rotate(...)">`. Do not compute `atan2`. Do not write horizontal stem templates and rotate them.

6. **Pick the right mode**:

   | When | Mode | Command |
   |------|------|---------|
   | One straight line | `straight` | `svg-infographics connector --from X,Y --to X,Y` |
   | Right-angle route | `l` | `svg-infographics connector --mode l --from X,Y --to X,Y --first-axis h\|v` |
   | Right-angle with softened corner | `l-chamfer` | `svg-infographics connector --mode l-chamfer --from X,Y --to X,Y --first-axis h\|v --chamfer 4` |
   | Smooth curve through 3+ waypoints | `spline` | `svg-infographics connector --mode spline --waypoints "x1,y1 x2,y2 ..." --samples 200` |
   | N fans to M via merges/forks | `manifold` | `svg-infographics connector --mode manifold --starts "..." --ends "..." --merge-points "..." --fork-points "..." --shape l-chamfer` |

   All modes accept `--arrow {none,start,end,both}`, `--head-size L,H`, `--margin N`, `--color`, `--width`, `--opacity`. Tool returns trimmed path d, world-space arrowhead polygons, tangent angle at each end.

   **Manifold specifics**: takes `--starts`, `--ends`, required `--spine-start` and `--spine-end`, optional `--tension` scalar or 2-tuple. Merge/fork points inferred via perpendicular projection through spine endpoints, scaled by tension: `tension=0` collapses strands at spine anchor, `tension=1` pulls each strand to full projection. Scalar applies to both sides; 2-tuple `(start, end)` applies independently. `--merge-points`/`--fork-points` override inference. `--spine-controls` add PCHIP waypoints for spline shape or elbow corners for L. Per-strand routing via `--start-controls` and `--end-controls` (list-of-lists, soft cap 5 waypoints each).

   `--shape` flag (`straight`|`l`|`l-chamfer`|`spline`) applies to every strand, spine, exit. For L / L-chamfer the `--align-elbows` flag forces all start-strand elbows onto a common coordinate (and end-strand elbows similarly), chosen from spine orientation - horizontal spine aligns on x, vertical on y. Clean rail-style visuals.

   Result exposes `start_strands`, `spine`, `end_strands`, `convergence_strands`, `divergence_strands` as individual polylines, plus manifold-level `bbox`, `warnings`, `all_trimmed_d` (pre-concatenated for pasting as single block). Every sub-result carries own `bbox` and `warnings`.

7. **Collision detection** via `svg-infographics collide` (or `detect_collisions` Python function). Takes list of polyline results + `tolerance` (default 0 = strict). Returns crossing / near-miss / touching with coords and min distance. Built on shapely's `LineString.intersects`/`intersection`/`buffer`. Use to flag near-misses during iteration, or find anchors for crossover markers, overlap dots, junction decorations.

   Rules:
   - Default to `l-chamfer` with `--chamfer 4` for any multi-segment connection. Sharp corners forbidden
   - Use `spline` for organic flows, fork/merge manifolds, curves a designer would draw freehand. NEVER hand-write `C` or `Q` commands
   - Stagger vertical midpoints when multiple L-routes share a gap
   - Manifold: document fork/merge points in grid comment; fork uses one source colour, merge uses single pipeline colour
   - Connector endpoints meet card edges or arrow stems exactly - `check_connectors` flags misses

8. For 3D shapes: `svg-infographics primitives cube/cylinder/sphere/cuboid/plane`

9. **For geometry constraints and attachment points** use `geom` subcommands instead of hand-computing:

    | Need | Command |
    |------|---------|
    | Snap point on card edge | `geom attach --shape rect --geometry X,Y,W,H --side right --pos mid` |
    | Snap point on circle perimeter at angle | `geom attach --shape circle --geometry CX,CY,R --side perimeter --angle 45` |
    | Midpoint between two points | `geom midpoint --p1 X,Y --p2 X,Y` |
    | Extend a line endpoint by N px | `geom extend --line X1,Y1,X2,Y2 --by N --end end` |
    | Point at parameter t along a line | `geom at --line X1,Y1,X2,Y2 --t 0.5` |
    | Perpendicular foot from point to line | `geom perpendicular --point X,Y --line X1,Y1,X2,Y2` |
    | Tangent from external point to circle | `geom tangent --circle CX,CY,R --from X,Y` |
    | Tangent lines between two circles | `geom tangent-circles --c1 CX,CY,R --c2 CX,CY,R --kind external\|internal` |
    | Line/line, line/circle, circle/circle intersections | `geom intersect-lines\|intersect-line-circle\|intersect-circles` |
    | N points evenly on a circle | `geom evenly-spaced --center X,Y --r R --count N` |
    | Concentric rings | `geom concentric --center X,Y --radii r1,r2,r3` |
    | Polar to cartesian | `geom polar --center X,Y --r R --angle DEG` |
    | Angle bisector at vertex | `geom bisector --p1 X,Y --vertex X,Y --p2 X,Y` |
    | Parallel/perpendicular line through point | `geom parallel\|perpendicular-line --line X1,Y1,X2,Y2 --through X,Y` |
    | **Offset line at perpendicular distance** | `geom offset-line --line X1,Y1,X2,Y2 --distance N --side left\|right` |
    | **Offset polyline (mitered)** | `geom offset-polyline --points "..." --distance N --side left\|right` |
    | **Inflate / deflate card outline** | `geom offset-rect --rect X,Y,W,H --by N` (negative shrinks) |
    | **Halo / shrink a circle** | `geom offset-circle --circle CX,CY,R --by N` |
    | **Offset closed polygon** | `geom offset-polygon --points "..." --distance N --direction outward\|inward` |
    | **Standoff label point along connector** | `geom offset-point --line X1,Y1,X2,Y2 --t 0.5 --distance 12 --side left` |

    Every subcommand prints computed values + small SVG verification snippet. Run geometry tool before authoring by hand - eyeballed positions break alignment, miss tangents by 1-2px.

10. **For ANY smooth curve through known waypoints** (decision boundaries, distributions, ROC/PR, sigmoid, score trajectories, isolines, organic flows) MUST run `primitives spline --points "x1,y1 x2,y2 ..." --samples 200` and paste `<path d="...">` verbatim. Never hand-write `C` or `Q` bezier for data curves. Only `Q` curves allowed for card corner radii.

11. Track line segments (timeline):
    - `<line>` from cx+r of one milestone to cx-r of next
    - NO continuous line through circles - segmented with cutouts
    - Track line stroke-width 1.5, opacity 0.15

12. **Verify**: every coordinate matches grid comment; every connector `<path>` and arrowhead `<polygon>` matches `connector` output for same params; endpoints meet card edges (`connectors` flags misses). Fix before proceeding.

### Phase 4: Content

**Text**:
- Every `<text>` uses CSS class (`class="fg-1"`) - NEVER inline `fill=`
- No `opacity`/`fill-opacity` on any `<text>`
- No parent `<g>` with opacity inheriting to text
- `font-family="Segoe UI, Arial, sans-serif"` on every text
- Title at accent_bar_bottom + 12px (first baseline)
- Description at title_baseline + 14px (rhythm)
- Min font 7px
- `text-anchor="middle"` for centred, explicit `x` for left-aligned
- No `<tspan>` for mixed styling - separate `<text>` elements with explicit x

**Legend**:
- Legend text colour MATCHES swatch (NOT fg-3/fg-4)
- Inline `fill=` matching swatch hex, or CSS class if exists
- Vertical rhythm between rows (typically 10px)
- Swatches: small `<rect>` with `rx="1"`

**Icons**:
- Lucide (ISC license)
- Attribution: `<!-- Icon: {name} (Lucide, ISC license) -->`
- Embed in `<g transform="translate(x,y) scale(s)">` with `fill="none"` + stroke
- Scale: 0.583 (~14px), 0.667 (~16px), 0.5 (~12px)
- Bbox (after scale) clears card right 6px, top 6px, nearest text 4px
- All icons in a card set use same scale and relative position

**Decorative imagery** (header banners only):
- fg-1 or brand accent colours
- Opacity 0.30-0.35
- Small scale (~15-20px)
- In gap between text block and logos

**Logos** (header banners only):
- Local bounds computed from actual path data
- Scale = target_height / local_height
- Translate: `translate_x = desired_abs_x - local_min_x * scale`
- Aspect ratio preserved (height from scale, never hardcoded)
- Full opacity - no `opacity` on logo `<g>`
- Right edge at viewBox_width - 12px padding
- 8px gap between logos

### Phase 5: Finishing

1. Verify arrows (placed Phase 3 via `connector`):
   - Every arrow is `<path d="...">` + `<polygon points="...">` in world coords - no wrapping `<g transform="rotate(...)">`, no hand-computed angles
   - Re-run connector tool for any arrow off, paste new output - do not nudge by hand
   - Endpoints meet card edges exactly (`connectors` verifies)
   - Fully opaque (no opacity)

2. Callout labels:
   - Centred in gap between source and target (x=midpoint, text-anchor=middle)
   - Vertically clear of arrow outer bbox (min 8px gap from nearest arrow path point)
   - Horizontally within gap (not extending into any card)

3. File description comment BEFORE `<svg>`:
   - Filename + role
   - Shows: visuals in reading order
   - Intent: purpose in document
   - Theme: palette name + shade assignments

### Phase 6: Validation

1. Run `svg-infographics overlaps --svg {file}` - record summary
2. Run `svg-infographics css --svg {file}` - record CSS compliance
3. Count by classification: violation, sibling, label-on-fill, contained
4. Examine EACH violation individually (no bulk dismissals):
   - **Fixed**: element repositioned, re-run confirms
   - **Accepted**: specific reason not a defect (e.g. text inside its own card)
   - **Checker limitation**: manual computation proving compliance
5. Fix all genuine errors (label overflow, arrowhead penetration, margin violations, inline fills)
6. Re-run and record new summary
7. Visual sanity: arrows connect to card edges? Labels fit gaps? Spacing even?
8. Confirm: no `#000000`/`#ffffff`; no colours outside swatch; transparent background; no fixed width/height on `<svg>`

## Per-Image Checklist

Create `svg-workflow-checklist.md` in target images directory with ~30 grouped checks per image.

**Required groups per image** (`[x]` verified, `[-]` N/A, `[!]` failed):

1. **File comments** - description (filename, shows, intent, theme); grid with all positions; layout topology with relationships
2. **CSS block** - `<style>` with all classes; `@media (prefers-color-scheme: dark)` overrides for every class
3. **Text rules** - CSS classes (zero inline fill); no opacity; `font-family="Segoe UI, Arial, sans-serif"`
4. **Text positions** - titles at accent_bar_bottom + 12px; descriptions at +14px rhythm; within boundaries (12px padding); min font 7px
5. **Card shapes** - flat top, rounded bottom r=3; fill-opacity 0.04; stroke-width 1; accent bar height 5, opacity 0.6, flush
6. **Arrow construction** - every arrow via `connector`; `trimmed_path_d` as `<path>`, arrowhead polygons as `<polygon>` in world coords; no `rotate()` wrappers; `l-chamfer` mode 4px chamfer; endpoints meet card edges; stroke-linecap/linejoin round
7. **Track lines** - segmented with cutouts (cx-r to cx+r); no continuous line through circles
8. **Grid/spacing** - vertical rhythm consistent; horizontal alignment; 12px card padding; 10px viewBox edge; 10px inter-card
9. **Legend** - text colour matches swatch; consistent row rhythm; swatches aligned
10. **Icons** - Lucide source; ISC comment; same scale across cards; clearance 6px edges, 4px text
11. **Logos** - computed bounds; scale from target height; aspect ratio; full opacity; right-aligned with padding
12. **Decorative imagery** - fg-1 or accent colours; opacity 0.30-0.35; small scale; in gap
13. **Colours** - no #000000/#ffffff; all traceable to swatch; transparent background
14. **ViewBox** - matches content; no width/height on `<svg>`
15. **Validation** - `overlaps` + `css` summaries; each violation classified; errors fixed; re-run confirms

See `clients/arelion/agentic-workflow/images/svg-workflow-checklist.md` for complete template.

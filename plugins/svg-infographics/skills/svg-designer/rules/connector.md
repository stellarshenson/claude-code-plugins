**Connector rule card** - rules when preflight declares `--connectors N`.

## Direction semantics (MANDATORY)

Arrow direction is NOT inferred from input point order. Declare it explicitly via `--connector-direction` or the `calc_connector --direction` flag:

- **straight / L / L-chamfer / spline modes**:
  - `forward` = arrowhead at `--to` (source -> target; most common)
  - `reverse` = arrowhead at `--from` (target -> source; "supported by", "depends on")
  - `both` = double-headed (bidirectional, sync protocols)
  - `none` = no arrowhead (undirected; use sparingly)
- **manifold mode**:
  - `sources-to-sinks` = arrowheads at sinks (broadcast / 1-to-many)
  - `sinks-to-sources` = arrowheads at sources (converge / many-to-1)
  - `both` = arrowheads at every strand-end (sync)
  - `none` = flow only, no arrowheads

Canonical direction per diagram type:

| Diagram type | Direction | Meaning |
|--------------|-----------|---------|
| platform stack | `sinks-to-sources` | supported by (arrows UP) |
| orchestration / control | `sources-to-sinks` | drives (arrows out/down) |
| dataflow / pipeline | `forward` or `sources-to-sinks` | data travels from source to sink |
| dependency graph | `reverse` or `sinks-to-sources` | depends on (arrows UP/in) |
| sync / bidirectional | `both` | two-way channel |

If the wrong direction ships the diagram tells the wrong story. The `check` subcommand catches declared-vs-rendered mismatches.

## Mode selection

- `straight` - two endpoints with optional standoff. Use when source and target are on a clear sight-line.
- `L` - two axis-aligned segments with a right-angle bend. Pass `--first-axis h` or `v` to force the initial direction.
- `L-chamfer` - L-route with a soft chamfer (4-12px radius) at the corner. Preferred over hard L; reads as polished rather than technical-drawing.
- `spline` - PCHIP through 3+ waypoints. Use when the path must curve around existing geometry.
- `manifold` - N starts converge through a shared spine, fork to M ends. Use for "many sources produce into one pipeline" or "one source broadcasts to many consumers". Spine MUST pass through a deliberate gap between intermediate elements.

## L / L-chamfer direction gates (MANDATORY, both ends)

When passing `--src-rect` and / or `--tgt-rect` to `calc_connector --mode l` / `--mode l-chamfer`, ALWAYS pass `--start-dir` and `--end-dir` (E / W / N / S). The route is then VERIFIED against the declaration on BOTH ends - axis, sign, stem length, and interior piercing:

- **`ROUTE-AXIS-MISMATCH` / `ROUTE-AXIS-MISMATCH-END`** - the first / last leg's axis disagrees with the declared cardinal: the route exits / arrives PARALLEL to the shape edge. Also fires when a same-axis direction pair (e.g. E→E) needs a 2-bend Z-route the 1-bend threader cannot produce - add a `--controls` waypoint or use `--auto-route`.
- **`ROUTE-DIR-REVERSED` / `ROUTE-DIR-REVERSED-END`** - the axis matches but the SIGN is opposite (e.g. last leg moves north with `end_dir=S`): the connector reaches the declared edge from the WRONG side, typically piercing the shape on the way. The direction pair is infeasible for a 1-bend route at this geometry - route around (waypoint / auto-route) or change the direction. Never ack to force a wrong-face arrival.
- **`ROUTE-THROUGH-SOURCE` / `ROUTE-THROUGH-TARGET`** - the routed path travels through the interior of the src / tgt rect. The strongest symptom of an infeasible direction pair.
- **`SHORT-FIRST-SEGMENT` / `SHORT-LAST-SEGMENT`** - axis and sign right, but the leg is under the 28px clarity floor (suppressed with `--stem-min 0`).

Post-hoc, `svg-infographics connectors` (and `finalize`, as HARD findings) mirror these for hand-written SVGs: `[l-chamfer-exit]` (first segment parallel to the origin edge), `[edge-arrival]` (final segment parallel to the edge it terminates on), `[arrowhead-edge]` (arrowhead tip on a card edge pointing along it instead of into the card), `[arrowhead-axis]` (head rotated off the stroke it terminates - see below).

## The head continues its own stroke

The stroke stops one head length short of the tip so the head has room, so the last stretch of curve is never drawn. The head must follow the CHORD across that trimmed stretch - the direction the stroke arrives from - not the tangent at the endpoint, which describes curve nobody sees. On a straight run the two agree; on a curve whose tangent turns near the target they diverge, and a head built on the tangent reads as a bent flag hanging off the line.

- The tool does this for you - the head it returns follows the chord the stroke arrives on. Paste `trimmed_path_d` and the polygon together; never re-derive an angle. A small tangent kink remains where stroke meets head, hidden under the head's width
- `[arrowhead-axis]` fires (HARD) when a head's axis is more than 10 degrees off the chord from its connector's endpoint to the tip
- Highest risk on manifold fans, where every outer strand must swing from the spine direction to the target approach in its last few pixels. Shipped examples ran 18-22 degrees off before the chord rule; the straight middle strand of the same fan was exact. A curved arrival now enters up to ~21 degrees off square, so straighten the last 15-20px of a strand where square arrival carries meaning

Declaration gate: **`MISSING-START-DIR-LCHAMFER` / `MISSING-END-DIR-LCHAMFER`** (pre-routing) - fires whenever `src_rect` / `tgt_rect` is supplied without the corresponding direction. Geometric inference can then exit / arrive parallel to an edge. Fix by passing the direction; ack only with reason `'inferred-axis-intended'`.

All route gates flow through `calc_connector`'s stop-and-think warning-ack mechanism (see below); the post-hoc validators run automatically in `svg-infographics connectors` and `finalize`.

## Stem-to-head ratio (40/60 rule)

Arrowhead must be AT MOST 40% of total connector length. Equivalently: stem length >= 60% of total. Stubby arrows (head dominates) read as misclicked shapes rather than directional connectors.

- `head_fraction = head_length / (stem_length + head_length)` must be `<= 0.40`
- Rule of thumb: 8-10px head on a >= 40px connector. Short connectors (< 30px) should use straight mode without an arrowhead and rely on the geometry for direction.
- `check_connectors` raises SOFT warning when `head_fraction > 0.40`.
- Override via `--max-head-fraction 0.30` when a tighter ratio is needed.

## Geometry discipline

- **Standoff**: 8-24px between connector endpoint and source/target boundary. Project minimum 2px, 8-12px is the sweet spot. Standoff is SYMMETRIC by default - `--standoff N` gives N px on both start and end. Asymmetric gaps require an explicit 2-tuple (future parser work; currently scalar only). `--standoff 0` triggers a BLOCKED warning; fix or ack with a specific reason ("flush attachment intentional for cluster", "legend tail touches frame by design").
- **Chamfer radius**: 4-12px for L-chamfer. Matches card corner radius roughly.
- **Spline tension**: 0.3-0.6 for dataflow curves. Higher values produce loops that look uncontrolled.
- **Manifold spine**: place through a deliberate gap in the middle layout so the spine passes cleanly without overlapping intermediate cards. Example: if middle tier has 4 cards, plan a 40px gap between cards 2 and 3 so the spine at x=spine_x passes through.

## Arrowhead polygon

- Size: 8-12 wide, 6-9 tall. Tool default is `--head-size 10,5`.
- Filled triangle, no stroke. Use `.arrow-fill` class for theming.
- Opacity: 0.7-0.9 on both strokes and polygon. Never 1.0 (reads as a solid shape).
- Dark-mode override: accent-colour fill for light, brighter tint for dark. Always paired with the connector stroke colour.

## CSS classes (theme + dark mode)

Always use named classes, never inline `fill=` / `stroke=` for themed colours:

```css
.arrow-stroke { stroke: #5456f3; }
.arrow-fill { fill: #5456f3; }
@media (prefers-color-scheme: dark) {
  .arrow-stroke { stroke: #7374ff; }
  .arrow-fill { fill: #7374ff; }
}
```

## Group conventions (MANDATORY for check)

Every connector path MUST live inside a `<g>` that matches one of:

- `id="connectors"` (canonical; one group containing all connector paths in the SVG)
- `class="connector"` (on the parent `<g>` or individual path)
- `class="manifold-connector"` for manifold groups

`check` counts connectors by scanning for these. Paths outside any such group get counted as zero, which will fail the component count.

## Mixed directions in one group

A single `<g id="connectors">` containing connectors pointing in opposite axes (some up, some down; some left, some right) is almost always a copy-paste mistake. `check_connectors` raises a SOFT warning when it detects this, unless the group has `data-connector-pattern="mixed"` which opt-ins the user into an explicit mixed-direction pattern.

## Stop-and-think warning-ack gate (MANDATORY)

`calc_connector` blocks SVG output on exit 2 whenever any warning fires (WARNING / CONSIDER / HINT - ALL severity levels). Output resumes only after every warning is consciously acknowledged with `--ack-warning TOKEN=reason`. Tokens are deterministic `hash(input, warning_text)` so reruns with the same input reproduce them.

One `--ack-warning` flag per warning. There is NO bulk override. Every warning gets its own token AND its own reason - the whole point is conscious pause per item.

**Reasoning MUST be terse**. One short clause describing why the warning is safe to ignore, not a paragraph. Examples:

- `--ack-warning W-03c26fa7='card column locked, stem cannot grow'` (good)
- `--ack-warning W-03c26fa7='T-junction middle, chamfer drop is the desired visual'` (good)
- `--ack-warning W-03c26fa7='known limitation of the current layout'` (weak - explain which layout constraint)
- `--ack-warning W-03c26fa7='I know what I am doing'` (bad - no content; will fail review)

Workflow:

1. Run the tool. Gate blocks with a BLOCKED block listing each warning + its token.
2. Read each warning. Decide: fix the input, or ack with a terse reason.
3. Rerun with one `--ack-warning TOKEN=reason` flag per warning being ignored.
4. Audit trail prints each ack with its reason to stderr before SVG output.

Fixing the geometry is ALWAYS preferred over acking. Only ack when the warning is a known trade-off tied to a specific constraint (e.g. card-column geometry fixed, desired visual pattern, adjacent element clearance). A stack of acks without specific reasoning is a signal the layout needs rework.

## Connector tool reference (moved from standards.md)

Every arrow, connector, routed line comes from `svg-infographics connector`. Output goes inside `<g id="connectors">`. The tool returns, in world coordinates:

- `trimmed_path_d` - stem with arrowhead clearance. Paste as `<path d="...">`
- Per-end arrowhead polygon. Paste as `<polygon points="...">`
- `tangent` / `angle_deg` at each end
- `samples` along path (for tangent labels, progress markers, midpoint callouts)

No `rotate()` transforms. No `atan2`. No horizontal-first templating. Hand-authored `<g transform="rotate(...)">` arrow groups = workflow violation.

Flags (all modes): `--arrow {none,start,end,both}`, `--head-size L,H`, `--margin N`, `--standoff N|start,end` (tool default 1px; see Geometry discipline above for the project sweet spot), `--color`, `--width`, `--opacity`. Spline: `--tangent-magnitude N` (default 0.5 x chord).

### L-route edge-aware API (CANONICAL)

`l` / `l-chamfer` between rects: pass BOTH rects AND cardinal directions. Tool snaps endpoints to edge midpoints, locks first-axis.

```bash
svg-infographics connector --mode l-chamfer \
  --src-rect "70,90,60,40"  --start-dir E \
  --tgt-rect "370,160,60,40" --end-dir S \
  --chamfer 4 --standoff 4 --arrow end
```

**Cardinal direction semantics**:
- `start_dir`: exit from src. `E`/`W` → horizontal, `N`/`S` → vertical
- `end_dir`: travel INTO tgt. `S` = moving south → enters TOP edge. Inverse: `E`→left, `W`→right, `N`→bottom, `S`→top
- Perpendicular pair (`start=E, end=S`) → 1-bend L, corner at `(tgt_mid_x, src_mid_y)`

Missing direction = warning. Rects without directions fall back to centre-to-target ray snap. Always pass directions for L-routes.

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

Default 20px. When src and tgt can slide along edges to a shared coordinate within tolerance, L degenerates to single straight segment. No corner, no chamfer, no twist. Slide bias: smaller geometry slides less, larger rect absorbs displacement. Disable with `--straight-tolerance 0`.

### Stem preservation (`--stem-min`)

Default 20px. Reserves clean cardinal stem behind each arrowhead. Three layers:

- **A\* penalty zone**: turns near endpoints cost `STEM_TURN_PENALTY=100`. Zone radius `ceil(reserve / cell_size) + 1` cells
- **Cell-centre snap**: first and last waypoints snap so non-cardinal axis matches real endpoints exactly
- **Chamfer clamp**: first/last bevels clamped so arrowhead trim never walks into bevel

Geometry-impossible = non-fatal warning with actual stem achieved. Set `--stem-min 0` for legacy.

### Container-scoped routing

`--container-id ID` on `empty-space`, `callouts`, `connector --auto-route` clips to interior of one closed shape. Must be rect/circle/ellipse/polygon/polyline/path - groups rejected. Container ID must name a shape whose interior contains BOTH endpoints. Outside obstacles ignored, inside obstacles respected.

```bash
svg-infographics connector --mode l --auto-route --svg scene.svg \
  --container-id card-1 --src-rect ... --tgt-rect ... --start-dir E --end-dir W
```

### Spline waypoints

`--waypoints "x1,y1 x2,y2 x3,y3 x4,y4"` for PCHIP. 3-5 waypoints enough. Showcase with markers: `<g id="cell-4-waypoints">` AFTER path in connectors layer. Tiny cross glyphs (two crossing `<line>` + `stroke-linecap: round`) in varied accent-2 shades.

### Canonical manifold

One merge = `spine_start`, one fork = `spine_end`. Start strands terminate at `spine_start`, tangent to spine. End strands leave `spine_end`, tangent to spine. Strands = cubic Beziers. Tangent magnitude = `tension`:

- `tension=0` → long tangents → floppy bow, strands cross easily
- `tension=1` → short tangents → stiff near-straight, max separation
- `tension=0.75` default → clean S-curves with good separation
- Scalar or `(start,end)` tuple for asymmetric stiffness

Strands inherit spine direction. Override per endpoint via 3-tuple `(x,y,"E")` or `(x,y,45)`.

### Manifold quality - use `--auto-tune`, do NOT hand-tune

Strand crossings and backward curves are both fixed by raising tension. The tool does this for you - pass `--auto-tune` and it escalates tension (up to `--auto-tune-max`, default 0.95) until those warnings clear, returning the clean build in ONE call. Output shows `Auto-tune: 0.50 -> 0.85 (... cleared)`.

```bash
svg-infographics connector --mode manifold --shape spline --auto-tune \
  --starts ... --ends ... --spine-start ... --spine-end ...
```

Never run a manifold, read a "CROSS" / "bends BACKWARD" warning, bump `--tension` by hand, and re-run - that manual loop is exactly what `--auto-tune` exists to eliminate. One call, not five.

When auto-tune reports residual strand warnings (it hit `--auto-tune-max` and still could not clear), the geometry itself is the problem, not the tension - widen the perpendicular spread of endpoints, move `spine_start`/`spine_end` further out, or pass explicit `merge_points`/`fork_points`. Then run once more.

**Not tension-fixable** (auto-tune leaves these in `warnings` - act on them): `TWIST` and `FLOW REVERSED` mean starts/ends are mis-wired (swap coords or flip the spine); `SPINE bends BACKWARD` means conflicting `spine_controls` / direction hints.

### Auto-edge mode (straight)

Shapes to `calc_connector`, skip coordinates:

- `src_rect=(x,y,w,h)` / `tgt_rect=(x,y,w,h)` - axis-aligned rects
- `src_polygon=[(x,y),...]` / `tgt_polygon=[(x,y),...]` - closed polygon

Straight mode: centroid → target ray → perimeter intersection. L / l-chamfer: use edge-aware API (rects + directions), NOT centroid-ray snap. Explicit coords override rects.

### Edge midpoint rule

Connector endpoints = shape EDGE MIDPOINTS. Never centres, never arbitrary corners. Tools:

1. `geom attach --shape rect --side right|left|top|bottom --pos mid` - edge midpoint
2. `connector ... --src-rect ... --tgt-rect ...` - auto-edge
3. `geom curve-midpoint --points "[(x,y),...]"` - arc-length midpoint of polyline. Labels ON a connector
4. `geom shape-midpoint --points "[(x,y),...]"` - area-weighted centroid. Direction inference only, never endpoint

### Angular arrow design (chamfered L-routing)

Chamfer at 90-degree bends with 4px diagonal:

```
Instead of: M{x1},{y1} V{y_mid} H{x2}
Use:        M{x1},{y1} V{y_mid-4} L{x1+4},{y_mid} H{x2-4} L{x2},{y_mid+4}
```

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

- Size: 8-12 wide, 6-9 tall. Tool default `--head-size 8,6` is correct for most cases.
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

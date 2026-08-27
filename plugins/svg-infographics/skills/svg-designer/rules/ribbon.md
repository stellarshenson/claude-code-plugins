**Ribbon rule card** - rules when preflight declares `--ribbons N`.

A ribbon is a CLOSED FILLED SHAPE representing a flow between two elements. NOT a stroked path. NOT a connector with arrowheads. Think Sankey diagram: width variation encodes magnitude; the translucent fill reads as flow rather than discrete edge.

## When to use ribbons vs arrows

- **ribbons**: convergence / funnel / fusion / soft many-to-one aggregation. "Multiple signal categories flow into a central model." "Four tributaries merge into the main river." "Ten inputs combine in a weighted sum."
- **arrows**: discrete relationships. "A triggers B." "X orchestrates Y." "Function f calls function g."

Diagram clue: if the phrase uses "flows into", "feeds", "contributes to", "merges with", "distributes across" -> ribbon. If "triggers", "calls", "depends on", "controls" -> arrow.

## Stick-to-geometry rule (MANDATORY)

Ribbon endpoints MUST lie EXACTLY on the boundary of source and target elements. No standoff, no gap, no margin. The ribbon's left edge is coincident with the source element's right edge (or whichever edge faces the target); same on the target side.

Concretely, if the source card has right edge at x=280 from y=80 to y=145, and the ribbon is supposed to flow from that full edge, the ribbon path starts and ends at:

- `M 280, 80` (top of source edge)
- `... some curves ...`
- `L 280, 145` (bottom of source edge)
- ... closes back to start ...

NOT `M 285, 80` or `M 275, 80` - the EXACT boundary coordinate.

The tool validates this when generating a ribbon via `calc_connector --mode ribbon`; deviation from declared element bbox edges raises a warning.

## Path shape

Closed filled path with two cubic-bezier curves (`C` commands) connecting the source edge to the target edge:

```
<path d="M Sx0,Sy0 C cp1x,cp1y cp2x,cp2y Tx0,Ty0 L Tx1,Ty1 C cp3x,cp3y cp4x,cp4y Sx1,Sy1 Z" fill="..."/>
```

- `M Sx0,Sy0` start at source top (or leftmost, for vertical-flow ribbons)
- `C ... Tx0,Ty0` cubic curve sweeps to target top, control points placed at 0.4-0.6 of the horizontal / vertical midpoint with `--curve-tension` spread
- `L Tx1,Ty1` traces along target edge to target bottom (straight segment; target edge is a sharp boundary)
- `C ... Sx1,Sy1` cubic sweeps back to source bottom
- `Z` closes along source edge back to start

## Fill and opacity

- `fill-opacity: 0.18-0.32` - crucial for the "flow" reading. Too opaque -> ribbon reads as a filled shape, not a channel.
- `stroke: none` - stroke makes the ribbon look outlined, which kills the translucent flow effect.
- `fill` colour matches source element's colour family (inherits the source's accent hue).
- Dark-mode override: slightly higher opacity (0.25-0.38) because dark backgrounds absorb more of the translucency.

## Width taper (direction cue)

- `--connector-direction sources-to-sinks` (broadcast): ribbon wider at source, narrower at target.
- `--connector-direction sinks-to-sources` (converge): ribbon wider at target, narrower at source.
- `both`: narrow at both ends, wide in the middle (lens shape). Uncommon.
- `none`: constant width (pure stroke-style channel).

The taper direction reinforces the semantic direction. Getting this wrong inverts the message.

## Group conventions

All ribbons in one group. The group's `id` must end in `-ribbons` or be exactly `ribbons`:

```xml
<g id="flow-ribbons" fill-opacity="0.25" stroke="none">
  <path d="M... C... L... C... Z" fill="#3999fd"/>
  ...
</g>
```

`check` counts each `<path>` inside such a group as one ribbon.

## Reference example

See `svg-infographics/skills/svg-designer/references/examples/ribbon_flow.svg` (based on the scandi_standard/broilers_growth_optimisation multivariate-to-growth SVG): four funnel ribbons converge from signal cards into a central hexagon, two divergence ribbons fan out from the hexagon to outcome panels. Study this pattern before authoring ribbons from scratch.

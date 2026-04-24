**Timeline rule card** - rules when preflight declares `--timelines N`.

A timeline shows sequential events along a linear axis. Cards sit above / below the axis; ticks mark event points; optional connectors link cards to ticks.

## Geometry discipline

- **Axis line**: single horizontal (or vertical) stroke, full width / height of the viewBox minus margin. Position centred on the timeline's vertical rhythm.
- **Ticks**: equal spacing along the axis. Each tick is a short perpendicular segment (6-10px). Place labels (dates, phases, milestone numbers) at the tick position.
- **Cards**: equal width, equal height. This is the #1 timeline visual rule - cards of unequal width destroy the reading of the sequence. Use `svg-infographics geom distribute` to enforce.
- **Card-to-tick link**: short connector (8-20px) from tick to card bottom / top. Optional but helps when cards are offset from ticks.

## Vertical rhythm

For a horizontal timeline:

- axis at y = 225 (viewBox midline) is standard
- cards above: bottom edge at y=195, heights 80-120
- cards below: top edge at y=255, heights 80-120
- alternating above/below ("zigzag") works well for dense timelines (6+ events)

For a vertical timeline:
- axis at x = viewBox width / 3 (cards fan right into the wider area)
- cards left or right of axis; same equal-size rule

## Card equivalence

**EVERY card in a timeline MUST be the same size (width AND height).** No exceptions for "the summary card needs more space" - if the summary needs more space, it's not a timeline card, it's a separate summary callout.

This rule is independent of the card rule card's row-wise equal-width constraint; timeline cards are equal both per-row AND per-column across the whole timeline.

## Tick-to-card alignment

Tick x-coordinate MUST equal the card's horizontal centre. If tick is at x=200 and card spans x=160..240, the tick at x=200 is correct (card centre = 200). Offset by > 2px = misalignment.

## Typography

- Phase / tick label (date, milestone #): 8-10pt, class `.fg-3` (muted). Position above tick for cards-below-axis, below tick for cards-above-axis.
- Card title: 11-13pt bold. Class `.fg-1`.
- Card body: 9-10pt. Class `.fg-2`.

## Group conventions (MANDATORY for check)

The timeline `<g>` MUST have `id="timeline"` OR `class` containing `"timeline"`. One timeline per declaration - multi-timeline SVGs are rare and should use distinct root IDs (`id="timeline-milestones"`, `id="timeline-deliverables"`) with `class="timeline"` for the counter.

## Connector discipline inside timeline

Connectors linking ticks to cards must:
- be mode `straight` (L-routes read as logic, not timeline)
- have no arrowhead (`--connector-direction none`)
- stroke-width 0.8-1.2, opacity 0.4-0.6 (subdued; the axis is the primary visual)

Timeline connectors are EXCLUDED from the main connector count - they are structural, not semantic edges. Use `<g id="timeline-links">` to keep them separate from the main `<g id="connectors">`.

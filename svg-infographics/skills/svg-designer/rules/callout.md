**Callout rule card** - rules when preflight declares `--callouts N`.

A callout is an annotation pointing at something in the main layout: a pull quote, a metric highlight, a warning label, a marginal note. Callouts sit in whitespace around the primary composition. A callout reaches its target by a short leader line OR by sitting close enough that position alone carries the link.

Reach for a callout only after classification (see `references/workflow.md` Phase 4). A region's own title or label is NOT a callout - it sits inside the region, no callout machinery.

## Leader vs leaderless - AI decides per callout

No default. For each callout, judge the target↔text link, then pick:

- **Leader** (`"leader": true` or omitted) - visible line to target. Use when position alone leaves the link unclear: target buried in dense content, text parked far out in whitespace, or many callouts crowd one zone. The line removes the ambiguity
- **Leaderless** (`"leader": false`) - no line, text IS the pointer. Use when position already carries the link: text hugs the target, group header above an unboxed group, tag on a waypoint

Wrong call reads as clutter (needless leader) or an orphan (missing leader). The solver scores both modes; you set the mode per request via the `"leader"` flag - it does not guess intent for you.

## Use the callout solver (MANDATORY)

`svg-infographics callouts` runs a joint optimisation over all callout placements simultaneously:

```bash
svg-infographics callouts --svg <file> --plan callouts.json
```

Plan entry per callout: numeric `target` (`[x,y]` point or `[x,y,w,h]` bbox), `text`, optional `leader` (bool - see above), optional `preferred_side` (`"above"|"below"|"left"|"right"`). Tool returns the best joint layout + top-N alternatives per callout (default 5) with penalty breakdowns. Full schema + worked example: `standards.md` "Callout construction workflow" or `callouts --help`.

DO NOT hand-place callouts. Hand placement overlaps content roughly 30% of the time and makes later edits painful. The solver considers every other placed element's bbox.

## Placement zones

Callouts live in the **margin / whitespace** around the primary composition. Run `svg-infographics empty-space --svg <file>` to get the free-region polygons; the callout solver uses these internally.

- Prefer placement 40-80px from target, in the natural reading direction (right for left-to-right, below for top-to-bottom).
- AVOID placing callouts inside another element's bbox - that's a collision, not a callout.
- For a target near the viewBox edge: place the callout INSIDE the viewBox, even if it means the connector has to wrap slightly.

## Leader line (leader mode only)

Leaderless callouts skip this section entirely - no line at all.

- Straight line (no L-route or curve). Callout lines are direct pointers.
- Stroke-width 0.8-1.2, opacity 0.4-0.6.
- Colour: `.fg-3` or dedicated `.callout-link` class.
- No arrowhead (the callout IS the arrowhead conceptually). If a clear arrow is needed, use a 4-6px triangle at the target end.
- Length 30-80px ideal. Below 20px is cramped; above 120px loses the connection.

## Typography

- Callout body: 9-10pt. Class `.fg-2`.
- Callout title / lead-in (optional, one word or short phrase): 10-11pt bold. Class `.fg-1`.
- Maximum 3 lines per callout. Longer notes belong in a dedicated narrative card.

## Visual style

Callouts are TEXT-FIRST. No boxes, no fills, no rounded backgrounds (that converts them into mini-cards, competing with the main cards). The only visual elements are:

1. the connector line
2. the text itself

Optional: a single colour-coded mark at the start of the text (small bullet / icon / letter badge) in the accent colour, matching whichever category the callout belongs to.

## Callout naming convention

For the solver + check to track them, each callout gets a stable ID:

- `id="callout-<target-slug>"` when uniquely tied to one target
- `id="callout-<topic-slug>-<n>"` when multiple callouts share a topic

Each callout must be its own `<g>` (so the count = one `<g>` per callout).

## Group conventions (MANDATORY for check)

Callouts must be inside groups matching:
- `class` containing `"callout"`
- OR `id` starting with `"callout-"`

Plural container groups (`<g id="callouts">`) wrap them all but are NOT counted; each per-callout `<g>` inside is one count.

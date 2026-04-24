**Callout rule card** - rules when preflight declares `--callouts N`.

A callout is an annotation pointing at something in the main layout: a pull quote, a metric highlight, a warning label, a marginal note. Callouts sit in whitespace around the primary composition, connected to their target by a short line.

## Use the callout solver (MANDATORY)

`svg-infographics callouts` runs a joint optimisation over all callout placements simultaneously:

```bash
svg-infographics callouts --svg <file> --requests callouts.json
```

Request shape per callout: target element id, body text, preferred placement hint (e.g. `"above-right"`), collision tolerance. Tool returns best layout + top-3 alternatives with penalty breakdowns (overlap penalty, distance penalty, direction penalty).

DO NOT hand-place callouts. Hand placement overlaps content roughly 30% of the time and makes later edits painful. The solver considers every other placed element's bbox.

## Placement zones

Callouts live in the **margin / whitespace** around the primary composition. Run `svg-infographics empty-space --svg <file>` to get the free-region polygons; the callout solver uses these internally.

- Prefer placement 40-80px from target, in the natural reading direction (right for left-to-right, below for top-to-bottom).
- AVOID placing callouts inside another element's bbox - that's a collision, not a callout.
- For a target near the viewBox edge: place the callout INSIDE the viewBox, even if it means the connector has to wrap slightly.

## Connector (line from callout to target)

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

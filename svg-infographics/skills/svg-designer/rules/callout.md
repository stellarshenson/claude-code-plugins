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

Plan entry per callout: numeric `target` (`[x,y]` point or `[x,y,w,h]` bbox), `text`, optional `leader` (bool - see above), optional `preferred_side` (`"above"|"below"|"left"|"right"`). Tool returns the best joint layout + top-N alternatives per callout (default 5) with penalty breakdowns. Full schema + worked example: "Callout construction workflow" below or `callouts --help`.

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

## Callout placement rules (moved from standards.md)

Callout = leader line + italic text annotating element. Six rules:

1. Text in empty zone, close to target. Close-but-clear > far-but-safe
2. Leader must not cross shapes or edges. Unavoidable: minimise crossings
3. Leader length: short-but-not-too-short. Clear bbox, reach target at visible angle
4. Text never overlaps own connector
5. Callouts never overlap each other
6. Leader stops `standoff` px short of text bbox. Compute: `geom offset-rect --rect <text-bbox> --by <standoff>` inflates, then `geom rect-edge --rect <inflated> --from <target>` returns anchor. Default standoff 3px

Mode scoring detail (solver):

- **Leader mode**: standoff default 20px. Score: leader length (sweet spot 55px), diagonal angle, target overshoot, preferred side
- **Leaderless mode**: standoff default 5px (tighter - no leader). Score pulls bbox CENTRE toward target (sweet spot 0); symmetric labels settle centred. **Target trick**: to land label ABOVE shape, place target ~8-12px above shape top edge

## Callout naming convention (moved from standards.md)

Every callout uses the `callout` namespace in THREE places:

1. **Group id**: `<g id="callout-<name>">`. `empty-space` skips via `exclude_ids=("callout-*",)`. `overlaps` parses prefix for CALLOUT CROSS-COLLISIONS
2. **Text class**: `class="callout-text"` on every `<text>` child
3. **Line class**: `class="callout-line"` on every `<line>`/`<path>`/`<polyline>` leader

All callout groups live inside top-level `<g id="callouts">` layer. Non-compliant callouts are invisible to `empty-space`, `overlaps`, and the workflow.

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

## Callout construction workflow (moved from standards.md)

Three-step workflow around the solver:

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

Targets: points `[x, y]` or bboxes `[x, y, w, h]`. Multi-line: `\n`. `"leader": false` = leaderless. Optional `preferred_side` is `"above"|"below"|"left"|"right"` (soft penalty). Solver returns best joint layout + top-5 alternatives per callout with penalty breakdowns.

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

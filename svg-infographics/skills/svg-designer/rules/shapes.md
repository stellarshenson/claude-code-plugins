**Shapes rule card** - shape primitives, bar/shape consistency, data-driven curves, and the `boolean` calculator. Served when preflight declares `--shapes N`; the boolean sections also apply to any `boolean` op regardless of declaration.

## When to use

| Op | Inputs | Margin | Use case |
|----|--------|--------|----------|
| `union` | 2+ shapes | n/a | Merge overlapping cards / hexagons / banners into one filled path |
| `intersection` | 2+ shapes | optional inset both | Lens-shape highlight where two regions overlap; clip a decoration to a card frame |
| `difference` | 2+ shapes (A minus rest) | optional inflate B | Remove a sub-shape from a container |
| `xor` | 2+ shapes | n/a | Highlight only the not-overlapping parts (rare; mostly for diff diagrams) |
| `buffer` | 1 shape | REQUIRED `--margin` | Inflate a hit-zone (positive) or shrink for inner padding (negative). Inkscape Outset / Inset |
| `cutout` | 2 shapes (container, hole) | REQUIRED | One-step "cut B from A with N units of breathing room around B". No standard editor exposes this as one button |
| `outline` | 1 shape | REQUIRED `--margin` | One-step closed annulus of width N tracing the boundary - a stroked-look filled ring. Use instead of `<path stroke="..."/>` when fill semantics matter |

## Margin semantics

- `--margin DIST` - distance in user units (px in viewBox space)
- Sign: `+` grows (outset), `−` shrinks (inset). Matches every desktop editor (Inkscape, Illustrator, Affinity, Figma)
- `--join {round,mitre,bevel}` default `round` - corner style for buffer-based ops
- `--mitre-limit 5.0` default - active only with `--join mitre`
- `--quad-segs 16` default - round-corner sample count. Increase for smoother arcs at cost of larger `d=` strings
- For `intersection` / `difference` the margin pre-buffers inputs (insets both for intersection, inflates B for difference) before the op

## Output

- Default: paste-ready `<path d="..." class="...">` snippet to stdout
- `--out FILE` - write the snippet to a file
- `--replace-id ID` - in-place mode: rewrite the named element's `d=` attribute and emit the full SVG. Class / style / transform survive the round-trip
- Multi-island result (XOR of disjoint shapes, certain differences) emits as one `<path>` with multiple `M ... Z` subpaths. Browsers + svgelements honour the nonzero / even-odd fill-rule per inner-ring direction. Split into separate elements only when each island needs its own class / animation

## Polygon-only - curves flatten

`shapely` operates on straight-segment polygons. SVG Bezier / Arc inputs (anything that uses `<circle>`, `<ellipse>`, or a path with `C` / `Q` / `A` segments) flatten to polylines via adaptive sampling before the op. Round-trip is lossy:

- `CURVE-FLATTENED` warning fires per curved input; ack with a real reason ("circle approximated as polygon - acceptable here") or rerun with `--tolerance N` to drop near-collinear noise
- For organic icons (thousands of cubic Bezier nodes) the polyline output stays large; consider running the op interactively in Inkscape if the result will ship as-is

## Warnings (the nine gate tokens)

| Token | Meaning | Typical fix |
|-------|---------|-------------|
| `INPUT-NOT-FOUND` | id not in source SVG | Check id spelling, run after authoring |
| `INPUT-OPEN-PATH` | subpath has no `Z` | Add explicit close in source, or ack if implicit-close is intended |
| `INPUT-DEGENERATE` | <3 points or zero area | Source element is not a fillable shape - skip or replace |
| `CURVE-FLATTENED` | Bezier / Arc input - lossy round-trip | Ack with reason, or use `--tolerance` to control simplification |
| `RESULT-EMPTY` | op produced nothing | Inputs disjoint? Margin too aggressive? |
| `RESULT-MULTI-ISLAND` | N>1 disconnected components | Acceptable for XOR; for difference inspect whether intent was a hole, not multi-piece |
| `BUFFER-COLLAPSE` | negative margin erased shape | Reduce `|margin|` or accept empty result |
| `MARGIN-EXCEEDS-SHAPE` | `|margin|` > 0.5 × min(bbox dim) | Sanity-check the value; usually a typo (4 vs 40) |
| `COMMENTS-NEED-REVIEW` | source SVG had `<!-- -->` comments; preserved verbatim in output but the boolean op may have changed surrounding structure | Review each listed comment in the output - edit the wording or delete it if it no longer applies. Ack with `'comments still apply'` or `'edited comments after review'`. Fires only when `--replace-id` is used AND the source had at least one comment |

Acks reuse the standard pattern: `--ack-warning TOKEN='terse reason'` per warning. Tokens are deterministic; reruns reproduce them.

## Anti-patterns

- Hand-editing a `d=` string to merge two cards. Use `boolean --op union` and let the gate tell you if anything is degenerate
- Faking a "ring" with stroke + fill:none on a complex path. Use `outline` so downstream tools see a real filled annulus
- Running `cutout` then manually tweaking corner radii of the hole. Set `--quad-segs` higher (32+) instead - reproducible, traceable
- Using `xor` to "find what's different between two shapes" as a debug tool. Fine for ad-hoc inspection, but never ship the XOR result - it represents nothing semantically meaningful in an infographic

## Cross-references

- Warning ack mechanism: `SKILL.md` Warning ack gate section (top of file)
- Z-order placement of result: `references/standards-core.md` five-layer rule (boolean output usually slots into `nodes` layer where the source shape lived)
- After running boolean: re-run `validate` + `overlaps` + `contrast` to confirm the new path doesn't break neighbouring elements' rhythm

## Shape primitives (moved from standards.md)

### Built-in shapes (18 types)

`svg-infographics primitives <shape>` returns exact anchors + paste-ready SVG.

- Basic: `rect`, `square`, `circle`, `ellipse`, `diamond`, `hexagon`, `star`, `arc`
- 3D wireframe: `cube`, `cuboid`, `cylinder`, `sphere`, `plane`, `axis`
- Symbolic: `gear`, `pyramid`, `cloud`, `document`
- Curves: `spline` (PCHIP through waypoints)

Each returns `{"svg": "...", "anchors": {"centre": [x,y], "top": [x,y], ...}, "bbox": [x,y,w,h]}`. Use anchors for connector attachment, labels, alignment.

### draw.io shape catalogue (1000+ stencils, on demand)

For shapes beyond the 18 built-ins (AWS icons, network, UML, BPMN, electrical): `shapes index --source <url>` (first use, cached, ~500KB for full draw.io set), `shapes search`, `shapes render`, `shapes catalogue` - command details in `references/tools.md`. Scaled via `transform`, returns the same `{"svg", "anchors", "bbox"}` contract.

**Shape selection rule**: check built-in primitives FIRST (faster, theme-matched, anchor-rich). Use draw.io only when no built-in matches. draw.io shapes get bbox-derived anchors only - no named semantic anchors.

## Bars and shapes consistency (moved from standards.md)

| Primitive | Standard rx |
|-----------|------------|
| Data/progress bars | `rx="2"` |
| Legend chips | `rx="2"` |
| Grid squares | `rx="3"` |
| Container boxes | `rx="8"` |
| Cards (path-based) | Q curves - see `rules/card.md` |

## Data-driven curves (moved from standards.md)

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
- **Render**: `stroke-linejoin="round"`, `stroke-width="2"` to `2.5`, fill segments at `fill-opacity="0.18-0.25"` if shading

Hand-written `<path d="M... C... C..."/>` for data curves = workflow violation.

## Group conventions (MANDATORY for check)

Free-standing declared shapes (counted by `--shapes N`) MUST live in a `<g>` matching one of:

- `id="shape-<slug>"` (preferred)
- `class` containing `"shape"`

`check` counts shapes by scanning for these; no convention = not counted = failed declaration. Shapes that are internal parts of another component (a card body, a connector arrowhead) belong to that component's group and are NOT declared as shapes.

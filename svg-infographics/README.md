# svg-infographics - stop fixing your AI's SVGs

You ask Claude for "an architecture diagram." It ships an SVG with text overlapping connectors, no dark mode, contrast failures, and a `<path d="M ...">` glued together by hand. You spend twice as long fixing the output as you would have spent drawing it.

This plugin makes that impossible. Every coordinate goes through a Python calculator. Every colour traces to an approved theme swatch with a `@media (prefers-color-scheme: dark)` block. Six independent validators block delivery on overlap / contrast / alignment / connector / CSS / pairwise-collision findings. A stop-and-think warning gate forces a conscious ack with terse reasoning per finding before any producer tool emits its primary output.

Read the full article: [Stop Fixing Your AI's SVGs](https://medium.com/towards-artificial-intelligence/stop-fixing-your-ai-svgs-715df70ccca0).

13 CLI tools (6 validators + 7 calculators), 60+ production examples in [`examples/`](examples/), and headless boolean / margin operations on path shapes (Inkscape Path menu plus one-step cutout-with-margin and outline-as-band).

## Production proof: declarative bar cutouts

Real session feedback after using the v1.4.14 boolean tool to cut 9 lightning-glyph holes (with a 10 px breathing-room margin) into a 9-bar chart - replacing ~25 manually-computed rect splits with 9 declarative cutout calls:

> "The boolean tool worked very well. Output was multipolygon paths (2 disconnected islands per bar) with curved edges that follow the lightning's actual silhouette - not approximated rectangular gaps. One-step cutout-with-margin (Inkscape / Illustrator need 2 steps). Deterministic warning tokens that block until acknowledged caught two intentional conditions and forced a conscious ack rather than silently producing weird output. In-place rewrite via `--replace-id` kept the SVG structure intact, just swapped each bar's `d=` attribute. Output validates clean (`svg-infographics validate` 0 issues, contrast AAA 6/6 text pass)."

## Installation

```bash
/plugin marketplace add stellarshenson/claude-code-plugins
/plugin install svg-infographics@stellarshenson-marketplace
```

The validator and calculator CLI ships as a Python package and must also be installed:

```bash
pip install stellars-claude-code-plugins
svg-infographics --help
```

## Capabilities

The plugin is organised around five capabilities. Every command, skill, and CLI subcommand belongs to one of them.

### 1. Design Foundations

Grid-first layout, shape primitives, theme and CSS, dark mode, typography, the 6-phase mandatory workflow, and the Fusion-360-style geometry toolkit. Start here: everything else builds on top of approved theme colours, a defined grid, and exact-coordinate primitives.

Grid is defined before content is placed. Shape primitives (`rect`, `circle`, `ellipse`, `hexagon`, `star`, `diamond`, `arc`, `cube`, `cylinder`, `sphere`, `axis`, `spline`) return named anchor points and paste-ready SVG snippets so positions are never eyeballed. Theme swatches define a palette with dark/light variants; the approved swatch then drives every subsequent deliverable via CSS classes and a `@media (prefers-color-scheme: dark)` block. The geometry toolkit adds sketch-constraint math (midpoint, perpendicular, parallel, tangent, intersection, polar, evenly-spaced, concentric, bisector, attachment, offset, `contains`, `rect-edge`, `curve-midpoint`, `shape-midpoint`) used by every downstream capability.

Backing tools: `svg-infographics primitives`, `svg-infographics geom`.
Commands: `/svg-infographics:theme`, `/svg-infographics:create`.
Skills: `svg-infographics:svg-designer`, `svg-infographics:theme`.
Reference: `skills/svg-designer/references/standards.md`, `skills/svg-designer/references/workflow.md`, `examples/`.

### 2. Boolean and margin operations

Headless equivalent of Inkscape's Path menu. `svg-infographics boolean --op <op>` operates on existing SVG path / shape elements by `id` and emits a paste-ready `<path d="...">` (or, with `--replace-id ID`, rewrites that element's `d=` in place). Supported ops: `union` (A ∪ B), `intersection` (A ∩ B), `difference` (A \ B), `xor` (symmetric difference / Inkscape Exclusion), `buffer` (Inset / Outset by `--margin`), `cutout` (one-step "subtract B inflated by N units from A" - the breathing-room cut), and `outline` (one-step closed annulus of width N around a shape's boundary).

Cutout-with-margin and outline-as-band are not standard one-button ops in Inkscape, Illustrator, Affinity, Figma, Sketch, or CorelDRAW - each requires a 2-step workflow there. Bundling them as primitives is the main agentic value-add. Polygon-only via `shapely`: SVG Bezier and Arc segments flatten to polylines before the op (lossy round-trip surfaces a `CURVE-FLATTENED` warning through the gate; `--tolerance` controls simplification post-pass).

Examples:

```bash
# Merge two cards into one filled path
svg-infographics boolean --op union --svg scene.svg --ids card-a card-b

# Cut a hole around an icon with 4 px breathing room
svg-infographics boolean --op cutout --svg scene.svg --ids banner icon --margin 4

# Filled ring 6 px wide around a shape
svg-infographics boolean --op outline --svg scene.svg --ids hex --margin 6

# Inflate a hit-zone by 8 px (Inkscape Outset)
svg-infographics boolean --op buffer --svg scene.svg --ids button --margin 8

# In-place rewrite of the source element
svg-infographics boolean --op union --svg scene.svg --ids a b --replace-id a --out scene.svg
```

Backing tools: `svg-infographics boolean`.
Reference: `skills/svg-designer/rules/shapes.md`.

### 3. Connectors

Every arrow, every flow line, every connection is generated by one tool with five routing modes: `straight`, `l` (axis-aligned right angle), `l-chamfer` (softened corner), `spline` (cubic Bezier via the `bezier` library when start/end directions are given, PCHIP through waypoints otherwise), and `manifold` (canonical Sankey bundle with single merge, single fork, and tension-controlled Bezier tangents). Auto-edge routing takes rect or polygon endpoints and snaps to edge midpoints so arrows meet cards perpendicular to the face, never at a centre. Output is world-space: trimmed path, arrowhead polygons, per-end tangent and angle, all paste-ready.

Backing tools: `svg-infographics connector`.
Reference: Arrow Construction section of `skills/svg-designer/references/standards.md`.

### 4. Callouts and Empty Space

Joint callout placement via greedy solver plus SVG-native free-region detection. Never lands text inside occluded zones and never crosses leaders.

`svg-infographics callouts` is the primary path: one tool call, a JSON plan listing every callout, one optimised layout out. Supports both **leader callouts** (text-plus-line connecting target to label, standoff 20 px, scored on leader length sweet spot 55 px, diagonal angle, target distance) and **leaderless callouts** (text-only labels that sit close to their target, standoff 5 px, scored on bbox-centre-to-target distance so symmetric labels settle centred). Hard pairwise constraints on text-text overlap, leader-vs-text crossing, and leader-vs-leader crossing; soft scoring for preferred side, length, and angle. Returns best layout plus top-5 alternatives per callout with penalty breakdowns.

Every callout uses the `callout` namespace in three places so tooling can find, exclude, and audit them: wrap the group in `<g id="callout-<name>">`, set `class="callout-text"` on every `<text>` child, and set `class="callout-line"` on every leader `<line>` / `<path>` / `<polyline>`. The `callout-*` id prefix lets `empty-space` exclude placed callouts from the obstacle set, and lets `overlaps` run the cross-collisions audit. See `skills/svg-designer/references/standards.md` for the construction workflow, leader-vs-leaderless selection rules, audit gates, and a minimal example.

`empty-space` reads an SVG file directly via `svgelements`, rasterises every visible element (rects, circles, paths with adaptively sampled Beziers and arcs, text bboxes via Pillow font metrics, transforms composed for `<g>` groups), applies Euclidean distance erosion, runs connected-component labelling, and returns boundary polygons of every free island sorted by area. Used under the hood by `callouts`, and directly for legends, badges, logos, and any "where does X fit without overlapping Y" question.

Backing tools: `svg-infographics callouts`, `svg-infographics empty-space`, `svg-infographics geom contains`, `svg-infographics geom rect-edge`, `svg-infographics overlaps`.
Reference: Callout construction workflow in `skills/svg-designer/references/standards.md`.

### 5. Charts

Data visualisations via `pygal` with caller-provided palette args and a `@media (prefers-color-scheme: dark)` block injected post-render so the chart respects the host document theme. Line, bar, horizontal bar, area, radar, dot, histogram, and pie. No hardcoded colour scheme; the caller passes `--colors`, `--fg-light`, `--fg-dark`, `--grid-light`, `--grid-dark` to match the approved theme swatch.

Backing tools: `svg-infographics charts`.

### 6. Validation

Mandatory pre-delivery gate with five checkers plus a pairwise connector collision detector. Nothing ships without a clean pass.

- **Overlap** detection catches text/shape overlaps, spacing rhythm violations, and font-size floors, and surfaces a `CALLOUT CROSS-COLLISIONS` block that checks leader-vs-text, leader-vs-leader, and text-vs-text across every `<g id="callout-*">` group.
- **Contrast** enforces WCAG 2.1 AA/AAA for text AND object-vs-background in both light and dark mode.
- **Alignment** enforces grid snapping, vertical rhythm, and topology (x-alignment, rect alignment).
- **Connector quality** catches zero-length segments, edge-snap violations, missing chamfers, and dangling endpoints.
- **CSS compliance** catches inline fills that should be classes, forbidden colours, and missing dark mode overrides.
- **Collide** detects pairwise intersections across a set of connectors with tolerance-aware near-miss detection.

Backing tools: `svg-infographics overlaps`, `svg-infographics contrast`, `svg-infographics alignment`, `svg-infographics connectors`, `svg-infographics css`, `svg-infographics collide`.
Commands: `/svg-infographics:validate`, `/svg-infographics:fix`.
Skill: `svg-infographics:svg-designer` (see `references/validation.md`).

### 7. Stop-and-think warning-ack gate

Every producer tool (`calc_connector`, `charts`, `drawio_shapes`, `empty-space`, `finalize`) blocks its primary output whenever any warning fires - WARNING, CONSIDER, HINT, contrast finding, stem-length, spine-offset, everything. The caller must acknowledge each warning explicitly with `--ack-warning TOKEN=reason`. Tokens are deterministic `sha256(canonical_argv, warning_text)[:8]` so reruns reproduce them. One flag per warning, one terse reason per warning - no bulk override. Forces a conscious per-finding decision instead of letting warnings scroll past unread.

Fixing the input is always preferred over acking. A stack of vague acks ("known issue", "see ticket") fails review - reasons must name a specific constraint ("card column locked", "T-junction middle, desired visual", "palette anchored on brand spec").

See `references/validation.md` for the full gate matrix and workflow.

## Use cases

**Build a branded marketplace banner.** Generate and approve a theme swatch first. Scaffold the 6-phase workflow grid, drop cards via `primitives rect`, connect them with `connector --mode l-chamfer`, validate with all five checkers before shipping.

```bash
/svg-infographics:theme
/svg-infographics:create
svg-infographics validate --svg banner.svg
```

**Annotate a dense diagram with callouts.** Build a plan JSON listing every callout (id, target, text, optional `leader: false` for leaderless group labels), then call `svg-infographics callouts` for a joint placement. Gate on the `overlaps` cross-collision audit before and after. No manual coordinate hunting.

```bash
svg-infographics overlaps --svg diagram.svg
svg-infographics callouts --svg diagram.svg --plan callouts.json
svg-infographics overlaps --svg diagram.svg
```

**Draw a Sankey flow.** Use `connector --mode manifold` with N sources and M sinks. The tool produces canonical merge/fork topology with cubic Bezier tangents controlled by `--tension`. Paste the returned path and arrowhead polygons directly into the SVG.

**Port a foreign SVG to your theme.** Run `css` to find inline fills that should become classes, `contrast` to check object-vs-background in both modes, `alignment` to catch eyeballed positions, then `/svg-infographics:fix <file> style` and `/svg-infographics:fix <file> layout` to repair automatically.

```bash
/svg-infographics:validate
/svg-infographics:fix <file> style
```

**Place a legend on a populated canvas.** Call `empty-space` and let it find the largest island that fits the legend bbox. Drop the legend group there. Same tool as callouts, used for any "where does X go" problem.

## Commands

| Command | What it does |
|---------|--------------|
| `/svg-infographics:create` | Create SVG infographic(s) following the full grid-first workflow. Spawns `svg-designer` agent (fork context) so user keeps working |
| `/svg-infographics:theme` | Generate or update a theme swatch SVG for brand colour approval |
| `/svg-infographics:validate` | Run all validation checks on one or more files |
| `/svg-infographics:fix` | Fix issues in existing SVGs (layout / style / contrast / connectors / geometry / all). Argument-driven. Spawns `svg-designer` agent |
| `/svg-infographics:beautify` | Additive decoration pass on existing SVGs - glow, per-item icons, colour variation, shape flourishes, bg texture (thick + ghost-transparent), abstract particles at 4 intensity levels (low/medium/high/absurd). Questionnaire-driven, geometry-guarded, local directive at `./svg-infographics-beautify.md` |
| `/svg-infographics:export-png` | Render SVG to PNG (light/dark/both) via Playwright |

## Skills

Two skills. Both auto-trigger based on context.

| Skill | Triggers when |
|-------|---------------|
| `svg-infographics:svg-designer` | Any SVG / infographic / diagram / banner / timeline / flowchart / chart / graphics work. Phrases: "create svg", "make svg", "create graphics", "make infographic", "validate svg", "fix svg", "design svg". Fork context — spawned via commands or `Agent(subagent_type="svg-designer")`. Holds design rules, tool palette, 6-phase workflow, validation gates |
| `svg-infographics:theme` | Defining colour palettes, generating swatches, working with brand themes |

## Tool inventory

Every subcommand is invoked as `svg-infographics <subcommand> [args]`. Run `--help` on any subcommand for flags.

| Subcommand | Kind | What it gives you |
|------------|------|-------------------|
| `overlaps` | validator | Text/shape overlap, spacing rhythm, font-size floors, callout cross-collisions audit |
| `contrast` | validator | WCAG 2.1 contrast for text and objects vs background in both light and dark mode |
| `alignment` | validator | Grid snapping, vertical rhythm, x-alignment, rect alignment, layout topology |
| `connectors` | validator | Connector quality: zero-length segments, edge-snap, missing chamfer, dangling endpoints |
| `css` | validator | CSS compliance: inline fills, forbidden colours, missing dark mode overrides |
| `collide` | validator | Pairwise connector collision detection with tolerance-aware intersection |
| `primitives` | calculator | Named anchors and paste-ready SVG for 14 primitive shape types |
| `connector` | calculator | Trimmed path and arrowhead polygons for 5 connector modes with auto edge-snap |
| `geom` | calculator | Sketch constraints: midpoint, perpendicular, tangent, intersections, offset, contains, rect-edge, curve-midpoint |
| `charts` | calculator | Pygal SVG charts with caller-provided palette and injected dark mode |
| `empty-space` | calculator | SVG-native free-region detection, returns boundary polygons for callout/legend/badge placement |
| `callouts` | calculator | Joint placement for a list of leader + leaderless callouts via greedy solver with pairwise constraints |
| `text-to-path` | on request | Render text as SVG `<path>` glyph outlines via fontTools |

## Examples

60+ production SVG examples in [`examples/`](examples/) covering card grids, timelines, flowcharts, header banners, stats panels, architecture diagrams, delivery models, manifold flows, theme swatches, and creative organic layouts. Read the 3-5 examples closest to the target image type before creating each new SVG.

## Documentation

- [`skills/svg-designer/SKILL.md`](skills/svg-designer/SKILL.md) - main design skill (fork context). Links to reference files below
- [`skills/svg-designer/references/tools.md`](skills/svg-designer/references/tools.md) - full tool palette tree with quick lookup
- [`skills/svg-designer/references/standards.md`](skills/svg-designer/references/standards.md) - grid-first rules, CSS theme classes, arrow construction, callout construction workflow, audit gates
- [`skills/svg-designer/references/workflow.md`](skills/svg-designer/references/workflow.md) - sequential 6-phase workflow with gate checks + per-image checklist
- [`skills/svg-designer/references/validation.md`](skills/svg-designer/references/validation.md) - validator usage, severity ladder, classification rules, browser visual testing
- [`skills/theme/SKILL.md`](skills/theme/SKILL.md) - theme swatch generation and brand palette management

---
name: workflow
description: Mandatory 6-phase sequential workflow for creating SVG infographics. Enforces research, invisible grid, scaffold, content, finishing, and validation phases with gate checks. Auto-triggered alongside svg-standards when creating any SVG visual content.
---

# SVG Infographics - Mandatory Workflow

Every SVG follows 6 sequential phases. No shortcuts. No batching. Complete all phases for one image before starting next.

## Available Tools (consider these before hand-computing)

Plugin ships three calculators and five validators. Scan menu before computing by hand.

| Tool | What it gives you |
|------|-------------------|
| `svg-infographics primitives <shape>` | Geometry + named anchors for 18 built-in shapes: rect, square, circle, ellipse, diamond, hexagon, star, arc, cube, cuboid, cylinder, sphere, plane, axis, **gear**, **pyramid**, **cloud**, **document**, spline (PCHIP). Returns `{"svg", "anchors", "bbox"}` |
| `svg-infographics shapes <cmd>` | draw.io stencil library: `search "query"` finds shapes (1000+), `render --name X --x --y --w --h` returns scaled SVG with bbox anchors, `catalogue --category X` renders grid, `index --source URL` downloads + caches. NOT bundled, downloaded on demand. Use for AWS/Azure/GCP icons, UML, BPMN, network, electrical. Check built-in `primitives` FIRST (faster, theme-matched, anchor-rich) |
| `svg-infographics connector --mode <m>` | 5 modes: `straight`, `l`, `l-chamfer`, `spline`, `manifold`. Returns trimmed path_d, arrowhead polygons (world coords), tangent/angle per end, bbox, warnings. Flags: `--standoff N\|start,end` (default 1px), auto-edge via `src_rect`/`tgt_rect` (straight + L modes) or `src_polygon`/`tgt_polygon`. **Canonical L-route: `--src-rect ... --start-dir E --tgt-rect ... --end-dir S`** — endpoint snaps to edge midpoint, first-axis locked, no parallel-to-edge drift. Direction semantics: `start_dir` is exit direction from src (`E`→right edge), `end_dir` is travel direction into tgt (`S`→entering top edge). Missing direction = warning. **Multi-elbow L**: `--controls "[(x,y),...]"` for explicit waypoints (soft cap 5). **Auto-route**: `--auto-route --svg scene.svg` runs grid A* on obstacle bitmap; tuning `--route-cell-size` (default 10px) and `--route-margin` (default 5px); `--container-id ID` clips to one closed shape. **Straight-line collapse**: `--straight-tolerance N` (default 20px) — L degenerates to single segment when endpoints can slide to shared coordinate; slide bias favours smaller geometry. **Stem preservation**: `--stem-min N` (default 20px) reserves clean cardinal stem behind arrowheads via A* turn-zone penalty + cell-centre snap + chamfer clamp; non-fatal warning when geometry can't honour target. Unroutable → fallback 1-bend L + warning. `spline` with `start_dir`/`end_dir` → cubic Bezier (`bezier` lib), else PCHIP through waypoints. `manifold`: single merge=`spine_start`, single fork=`spine_end`, strands inherit spine direction, `tension` scales Bezier tangent magnitude |
| `svg-infographics geom <op>` | Sketch constraints: midpoint, perpendicular foot, line extension, tangent, intersections, parallel/perpendicular, polar, evenly-spaced, concentric, bisector, attachment on rect/circle edges, parallel offset of line/polyline/rect/circle/polygon. Plus: `curve-midpoint` (arc-length midpoint + tangent on polyline), `shape-midpoint` (area-weighted centroid of closed polygon), `contains` (point/bbox/line/polyline/polygon inside outer polygon? reports `contained` + `convex-safe` - catches concave re-entry through notches) |
| `svg-infographics charts <type>` | Pygal SVG charts: line, bar, hbar, area, radar, dot, histogram, pie. **MANDATORY: never hand-author chart SVG.** Palette: `--colors` (light) AND `--colors-dark` (dark) - both required, baked into same SVG via `@media (prefers-color-scheme: dark)`. Rule: light-mode colours DARK (readable on `#ffffff`), dark-mode colours BRIGHT (readable on `#0b0b0b`). Tool audits every series for WCAG 2.1 contrast, warns below **7:1 (target 7-10:1)**. Stellars-tech accent-1/2 naturally land at 7-10:1. Audit advisory, WORKFLOW VIOLATION to ship with unresolved warnings. Also supports `--fg-light`/`--fg-dark`, `--grid-light`/`--grid-dark`, `--bg-light`/`--bg-dark` |
| `svg-infographics empty-space` | Input: `--svg file.svg` + `--tolerance N` (default 20, callout minimum) + `--min-area N` (default 500, drop slivers) + `--exclude-id PATTERN` (default `callout-*`) + `--container-id ID` (clip to interior of closed shape; rect/circle/ellipse/polygon/polyline/path; groups rejected). Output: boundary polygons of free regions, sorted by area descending, tagged with `container_id` (or `null`). Use for callout/label/legend/badge/logo/icon/decorative placement, slot validation. `--container-id` mode answers "where is the free space INSIDE this card?" |
| `svg-infographics callouts` | Input: `--svg file.svg` + `--plan callouts.json` (list of requests with id, target, text, optional `leader: false` for leaderless) + optional `--container-id ID`. Output: joint best layout + top-5 alternatives per callout with penalty breakdowns. Greedy solver + random-ordering restarts with hard pairwise constraints (text bbox overlap, leader-vs-text crossing, leader-vs-leader crossing). Leader callouts score on length (sweet spot 55px), diagonal angle, target overshoot, preferred side. Leaderless score on BBOX CENTRE distance to target (sweet spot 0) so symmetric labels settle centred. Leader standoff default 20px; `leaderless_standoff` default 5px. Call `--help` for full plan schema |
| `svg-infographics overlaps` | Text/shape overlap, spacing rhythm, font-size floors, callout cross-collisions (leader-vs-other-text, leader-vs-leader, text-vs-text across all `callout-*` groups) |
| `svg-infographics contrast` | WCAG 2.1 contrast for text AND objects vs document background (light + dark) |
| `svg-infographics alignment` | Grid snapping, vertical rhythm, layout topology |
| `svg-infographics connectors` | Zero-length, edge-snap, missing chamfer, dangling endpoints |
| `svg-infographics collide` | Pairwise collision over a set of connectors. Tolerance-aware (buffered shapely intersection). Reports crossing / near-miss / touching with coords and min distance |
| `svg-infographics css` | Inline fills, missing dark-mode overrides, forbidden colours |

Each calculator's `--help` describes subcommand use. Skim menu before computing coordinate, control point, contrast by hand.

See `WORKFLOW.md` for full inventory.

## Task Tracking

**MANDATORY**: TaskCreate/TaskUpdate throughout. Task list at start showing all phases per image. Mark each in_progress on start, completed on finish.

## Skill Activation (once per session)

Before creating any SVG:

1. Read 3-5 examples from `examples/` closest to requested types
2. Read relevant theme swatch (`theme_swatch_*.svg`)
3. Create `svg-workflow-checklist.md` in target images directory

## Phase 1: Research

- Read 3-5 relevant examples for THIS image type
- Confirm CSS class names and hex values from theme swatch
- Identify pattern: card grid, flow diagram, timeline, stats banner, header banner, bar chart, hub-and-spoke, layered model
- Note conventions: card dimensions, arrow style, text sizes, spacing

**GATE**: Write summary to user - image type, examples consulted, dimensions, colour classes. Do NOT proceed until shared.

## Phase 2: Invisible Grid

Write grid BEFORE any visual elements. Blueprint.

1. **Use `primitives` to calculate grid** - never eyeball. `primitives rect`, `primitives circle`, `primitives axis` for exact anchors.

   **For ANY curve through known waypoints**: MUST run `primitives spline --points "x1,y1 x2,y2 ..." --samples 200` and paste `<path d="...">` verbatim. Hand-written `C`/`Q` bezier paths for data curves forbidden. PCHIP is monotonicity-preserving.

   **For connectors between elements**: use `connector` with matching mode: `straight`, `l`, `l-chamfer`, `spline`. **For L/L-chamfer ALWAYS pass both rects AND `--start-dir`/`--end-dir`** - otherwise tool infers first-axis from `|dx| vs |dy|` and vertical segment may run parallel to target edge.
2. Write `=== GRID ===` comment: viewBox, all x/y, rhythm step, margins, arrow paths
3. Write `=== LAYOUT TOPOLOGY ===` comment: container-child, h-stack, v-stack, mirror, flow
4. No visual elements yet - grid only
5. Write grid to SVG file as comments only

**GATE**: SVG contains ONLY grid + topology comments. No `<rect>`, `<path>`, `<text>`.

## Phase 3: Scaffold

Structural elements at grid positions. No text, no icons, no content.

1. `<style>` block with all CSS classes + `@media (prefers-color-scheme: dark)` overrides
2. `<g id="guide-grid" display="none">` reference lines
3. Card `<path>` outlines via `primitives rect --radius 3` (flat-top, rounded-bottom, fill-opacity 0.04, stroke 1)
4. Accent bars (`<rect>` height 5, opacity 0.6, flush with card top)
5. Arrows and connectors via `connector` in appropriate mode. Paste returned `trimmed_path_d` and arrowhead polygons directly. No `rotate()` templates, no hand-calculated angles
6. Prefer `l-chamfer --chamfer 4` for any L-route. Sharp corners forbidden
7. Track line segments with cutouts (if timeline)
8. 3D shapes: `primitives cube/cylinder/sphere/cuboid/plane` for isometric
9. **Verify**: every coordinate matches grid comment

**GATE**: style block, card outlines, accent bars, arrows - but NO `<text>`.

## Phase 4: Content

- `<text>` with CSS classes (NEVER inline fill), no opacity, font-family Segoe UI
- Title at accent_bar_bottom + 12px, descriptions at +14px rhythm, minimum 7px
- Legend text colour matches swatch colour (NOT fg-3/fg-4)
- Lucide icons in `<g>` with fill="none" + stroke, ISC license comment
- Decorative imagery: fg-1 colour, opacity 0.30-0.35 (banners only)
- Logos: computed scale from local bounds, preserved aspect ratio (banners only)

## Phase 5: Finishing

1. Verify arrow placement - every `<path>` and `<polygon>` matches `connector` output for same `--from`/`--to`/`--mode`. Discrepancy = workflow violation
2. Callout labels: centred in gap, 8px clear of arrow path
3. File description comment before `<svg>`: filename, shows, intent, theme

## Phase 6: Validation

**DO NOT deliver without running validation.**

1. Run `svg-infographics overlaps --svg {file}` - record summary
2. Run `svg-infographics css --svg {file}` - record compliance
3. Classify each violation individually (no bulk dismissals): Fixed / Accepted / Checker limitation
4. Fix layout and CSS errors, re-run, record new summary
5. Confirm: no #000000/#ffffff, all colours in swatch, transparent background, no width/height on `<svg>`

**GATE**: Paste validation output (overlaps + CSS). Scripts not run = phase incomplete.

## Per-Image Checklist

`svg-workflow-checklist.md` with these check groups per image (`[x]` verified, `[-]` N/A, `[!]` failed):

1. **File comments** - description, grid, layout topology
2. **CSS block** - style with all classes and dark mode overrides
3. **Text rules** - CSS classes, no opacity, font-family
4. **Text positions** - titles at +12px, descriptions at +14px, within boundaries
5. **Card shapes** - flat top, rounded bottom r=3, fill-opacity 0.04, accent bar
6. **Arrow construction** - all connectors built via `connector`, paste-ready `trimmed_path_d` + arrowhead polygons, `l-chamfer` mode 4px chamfer, no hand-authored `rotate()` groups
7. **Track lines** - segmented with cutouts
8. **Grid/spacing** - vertical rhythm, horizontal alignment, padding
9. **Legend** - text colour matches swatch
10. **Icons** - Lucide source, ISC comment, same scale
11. **Logos** - computed bounds, aspect ratio, full opacity
12. **Decorative imagery** - fg-1 colour, opacity 0.30-0.35
13. **Colours** - no #000000/#ffffff, all from swatch
14. **ViewBox** - dimensions match content, no width/height on `<svg>`
15. **Validation** - `overlaps` + `css` summaries, violations classified, errors fixed

## Detailed Phase Reference

See `WORKFLOW.md` for expanded instructions, formulas, checklists.

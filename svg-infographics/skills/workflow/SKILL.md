---
name: workflow
description: Mandatory 6-phase sequential workflow for creating SVG infographics. Enforces research, invisible grid, scaffold, content, finishing, and validation phases with gate checks. Auto-triggered alongside svg-standards when creating any SVG visual content.
---

# SVG Infographics - Mandatory Workflow

Every SVG image follows 6 sequential phases. No shortcuts, no batching. Complete all phases for one image before starting next.

## Available Tools (consider these before computing by hand)

Plugin ships with **three calculators** and **five validators**. Scan the menu for any sub-problem - likely a tool already solves it.

| Tool | What it gives you |
|------|-------------------|
| `svg-infographics primitives <shape>` | Geometry + named anchors: rect, circle, ellipse, hex, star, arc, cube, cylinder, sphere, axis, spline (PCHIP). Use for primitive coords and smooth waypoint curves |
| `svg-infographics connector --mode <m>` | 5 modes: `straight`, `l`, `l-chamfer`, `spline`, `manifold`. Returns trimmed path_d, arrowhead polygons (world coords), tangent/angle per end, bbox, warnings. Flags: `--standoff N\|start,end` (default 1px), auto-edge via `src_rect`/`tgt_rect` (straight + L modes) or `src_polygon`/`tgt_polygon`. **Canonical L-route: `--src-rect ... --start-dir E --tgt-rect ... --end-dir S`** — endpoint snaps to matching edge midpoint, first-axis locked, no parallel-to-edge drift. Direction semantics: `start_dir` is exit direction from src (`E`→right edge), `end_dir` is travel direction into tgt (`S`→entering top edge). Missing direction = tool emits warning. `spline` with `start_dir`/`end_dir` → cubic Bezier (`bezier` lib), else PCHIP through waypoints. `manifold`: single merge=`spine_start`, single fork=`spine_end`, strands inherit spine direction, `tension` scales Bezier tangent magnitude |
| `svg-infographics geom <op>` | Sketch constraints: midpoint, perpendicular foot, line extension, tangent, intersections, parallel/perpendicular, polar, evenly-spaced, concentric, bisector, attachment points on rect/circle edges, parallel offset of line/polyline/rect/circle/polygon. Plus: `curve-midpoint` (arc-length midpoint + tangent on any polyline), `shape-midpoint` (area-weighted centroid of closed polygon), `contains` (point/bbox/line/polyline/polygon inside outer polygon? reports `contained` + `convex-safe` - catches concave re-entry through notches) |
| `svg-infographics charts <type>` | Pygal SVG charts: line, bar, hbar, area, radar, dot, histogram, pie. **MANDATORY: never hand-author chart SVG - always go through this tool.** Palette: `--colors` (light mode) AND `--colors-dark` (dark mode) - both required, baked into the same SVG via `@media (prefers-color-scheme: dark)`. Rule: light-mode colours must be DARK (readable on `#ffffff`), dark-mode colours must be BRIGHT (readable on `#0b0b0b`). Tool audits every series for WCAG 2.1 contrast against its background, prints both palettes to stderr, and warns when any colour falls below **7:1 (target 7-10:1)** with `too pale - use a darker shade` (light) or `too dark - use a brighter shade` (dark). Stellars-tech accent-1/2 naturally land at 7-10:1. Audit advisory, NOT blocking, but WORKFLOW VIOLATION to ship with unresolved warnings. Also supports `--fg-light`/`--fg-dark` for axis text, `--grid-light`/`--grid-dark` for axes, `--bg-light`/`--bg-dark` for plot background |
| `svg-infographics empty-space` | Input: `--svg file.svg` + `--tolerance N` (default 20, callout minimum) + `--min-area N` (default 500, drop slivers) + `--exclude-id PATTERN` (default `callout-*`). Output: boundary polygons of free regions, sorted by area descending. Use for callout/label/legend/badge/logo/icon/decorative-imagery placement, slot validation before committing layout - any "where to put X without overlapping Y" question. Works on any SVG - yours or foreign |
| `svg-infographics callouts` | Input: `--svg file.svg` + `--plan callouts.json` (list of callout requests with id, target, text, optional `leader: false` for leaderless). Output: joint best layout for all callouts plus top-5 alternatives per callout with penalty breakdowns. Greedy solver + random-ordering restarts with hard pairwise constraints (text bbox overlap, leader-vs-text crossing, leader-vs-leader crossing). Leader callouts score on leader length (sweet spot 55 px), diagonal angle preference, target distance overshoot, preferred side. Leaderless callouts score on BBOX CENTRE distance to target (sweet spot 0) so horizontally-symmetric labels settle centred. Leader standoff default 20 px (leader-tip-to-text breath); `leaderless_standoff` default 5 px (leaderless text has no leader, must sit close to its target). Call `svg-infographics callouts --help` for the full plan JSON schema |
| `svg-infographics overlaps` | Text/shape overlap, spacing rhythm, font-size floors, callout cross-collisions (leader-vs-other-text, leader-vs-leader, text-vs-text across all `callout-*` groups) |
| `svg-infographics contrast` | WCAG 2.1 contrast for text AND for objects vs the document background (light + dark mode) |
| `svg-infographics alignment` | Grid snapping, vertical rhythm, layout topology |
| `svg-infographics connectors` | Connector quality: zero-length, edge-snap, missing chamfer, dangling endpoints |
| `svg-infographics collide` | Pairwise collision detection over a set of connectors. Tolerance-aware (buffered shapely intersection). Reports crossing / near-miss / touching with intersection coordinates and min distance |
| `svg-infographics css` | CSS compliance: inline fills, missing dark-mode overrides, forbidden colours |

Each calculator's `--help` describes subcommand use. Skim menu before computing coordinate, control point, contrast by hand - tool output paste-ready for SVG.

See `WORKFLOW.md` for full inventory with usage notes.

## Task Tracking

**MANDATORY**: Use Claude Code task tracking (TaskCreate/TaskUpdate) throughout workflow. Task list at start showing all phases per image. Mark each phase in_progress on start, completed on finish. Visible progress to user.

## Skill Activation (once per session)

Before creating any SVG content:

1. Read 3-5 examples from `examples/` closest to the requested image types
2. Read the relevant theme swatch (`theme_swatch_*.svg`) for the target brand
3. Create `svg-workflow-checklist.md` in the target images directory

## Phase 1: Research

- Read 3-5 relevant examples for THIS specific image type
- Confirm CSS class names and hex values from theme swatch
- Identify closest pattern: card grid, flow diagram, timeline, stats banner, header banner, bar chart, hub-and-spoke, layered model
- Note conventions: card dimensions, arrow style, text sizes, spacing

**GATE**: Write summary to user: image type, examples consulted, dimensions, colour classes. Do NOT proceed until shared.

## Phase 2: Invisible Grid

Write grid BEFORE any visual elements. Blueprint.

1. **Use `svg-infographics primitives` to calculate grid** - NEVER eyeball positions. Use `primitives rect`, `primitives circle`, `primitives axis` etc. for exact anchor coordinates.

   **For ANY curve passing through known waypoints (decision boundary, distribution shape, score trajectory, ROC/PR, sigmoid, isoline, trend line, organic flow path)**: MUST run `primitives spline --points "x1,y1 x2,y2 ..." --samples 200` and paste returned `<path d="...">` verbatim. Hand-written `C` (cubic) or `Q` (quadratic) bezier paths for data curves forbidden - overshoot waypoints, kink at joins, never look right. PCHIP interpolator is monotonicity-preserving, produces the exact curve a designer would draw. Typing `d="M... C..."` for anything other than card corner radius - stop, rerun tool.

   **For connectors between elements**: use `svg-infographics connector` with matching mode: `straight` (one line, auto edge-snap via `--src-rect`/`--tgt-rect`), `l` (axis-aligned right-angle), `l-chamfer` (default L route, softened corners), `spline` (free curves through 3+ waypoints). All four modes return trimmed path d, world-space arrowhead polygons, tangent angles - never hand-author connector geometry. **For L/L-chamfer ALWAYS pass both rects AND cardinal `--start-dir`/`--end-dir`** (e.g. `--src-rect "x,y,w,h" --start-dir E --tgt-rect "x,y,w,h" --end-dir S`) — otherwise the tool infers first-axis from `|dx| vs |dy|` and the vertical segment may run parallel to a target edge. Missing direction triggers a warning in the tool output.
2. Write `=== GRID ===` comment: viewBox, all x/y positions, rhythm step, margins, arrow paths
3. Write `=== LAYOUT TOPOLOGY ===` comment: container-child, h-stack, v-stack, mirror, flow relationships
4. No visual elements yet - grid only
5. Write grid to SVG file as comments only

**GATE**: SVG file contains ONLY grid comment and topology comment. No `<rect>`, `<path>`, `<text>`, no visual elements.

## Phase 3: Scaffold

Structural elements at grid positions. No text, no icons, no content.

1. `<style>` block with all CSS classes + `@media (prefers-color-scheme: dark)` overrides
2. `<g id="guide-grid" display="none">` reference lines
3. Card `<path>` outlines - `svg-infographics primitives rect --radius 3` for exact anchor coordinates (flat-top, rounded-bottom, fill-opacity 0.04, stroke 1)
4. Accent bars (`<rect>` height 5, opacity 0.6, flush with card top)
5. Arrows and connectors built with `svg-infographics connector` in appropriate mode (`straight`, `l`, `l-chamfer`, `spline`) - paste returned `trimmed_path_d` and world-space arrowhead polygons directly. No `rotate()` templates, no hand-calculated angles
6. Prefer `l-chamfer --chamfer 4` for any L-route; sharp corners forbidden in finished SVGs
7. Track line segments with cutouts (if timeline)
8. 3D shapes: `primitives cube/cylinder/sphere/cuboid/plane` for isometric coordinates
8. **Verify**: every coordinate matches grid comment

**GATE**: SVG has style block, card outlines, accent bars, arrows - but NO `<text>` content.

## Phase 4: Content

Content at grid positions:

- `<text>` with CSS classes (NEVER inline fill), no opacity, font-family Segoe UI
- Title at accent_bar_bottom + 12px, descriptions at +14px rhythm, minimum 7px
- Legend text colour matches swatch colour (NOT fg-3/fg-4)
- Lucide icons in `<g>` with fill="none" + stroke, ISC license comment
- Decorative imagery: fg-1 colour, opacity 0.30-0.35 (banners only)
- Logos: computed scale from local bounds, preserved aspect ratio (banners only)

## Phase 5: Finishing

1. Verify arrow placement - every arrow `<path>` and arrowhead `<polygon>` matches `svg-infographics connector` output for same `--from`/`--to`/`--mode`. Discrepancy = workflow violation
2. Callout labels: centred in gap, 8px clear of arrow path
3. File description comment before `<svg>`: filename, shows, intent, theme

## Phase 6: Validation

**DO NOT deliver without running validation.**

1. Run `svg-infographics overlaps --svg {file}` - record summary
2. Run `svg-infographics css --svg {file}` - record CSS compliance
3. Classify each violation individually (no bulk dismissals): Fixed / Accepted / Checker limitation
4. Fix layout and CSS errors, re-run checkers, record new summary
5. Confirm: no #000000/#ffffff, all colours in swatch, transparent background, no width/height on `<svg>`

**GATE**: Paste validation output (overlaps + CSS) in response. Scripts not run = phase incomplete.

## Per-Image Checklist

`svg-workflow-checklist.md` with these check groups per image (`[x]` verified, `[-]` N/A, `[!]` failed):

1. **File comments** - description, grid, layout topology
2. **CSS block** - style with all classes and dark mode overrides
3. **Text rules** - CSS classes, no opacity, font-family
4. **Text positions** - titles at +12px, descriptions at +14px, within boundaries
5. **Card shapes** - flat top, rounded bottom r=3, fill-opacity 0.04, accent bar
6. **Arrow construction** - all arrows and connectors built via `svg-infographics connector`, paste-ready `trimmed_path_d` + world-space arrowhead polygons, `l-chamfer` mode with 4px chamfer for L-routes, no hand-authored `rotate()` groups
7. **Track lines** - segmented with cutouts
8. **Grid/spacing** - vertical rhythm, horizontal alignment, padding
9. **Legend** - text colour matches swatch
10. **Icons** - Lucide source, ISC comment, same scale
11. **Logos** - computed bounds, aspect ratio, full opacity
12. **Decorative imagery** - fg-1 colour, opacity 0.30-0.35
13. **Colours** - no #000000/#ffffff, all from swatch
14. **ViewBox** - dimensions match content, no width/height on `<svg>`
15. **Validation** - `svg-infographics overlaps` + `svg-infographics css` summaries, violations classified, errors fixed

## Detailed Phase Reference

See `WORKFLOW.md` in this skill directory for expanded instructions, formulas, checklists per phase.

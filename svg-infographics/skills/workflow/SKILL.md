---
name: workflow
description: Mandatory 6-phase sequential workflow for creating SVG infographics. Enforces research, invisible grid, scaffold, content, finishing, and validation phases with gate checks. Auto-triggered alongside svg-standards when creating any SVG visual content.
---

# SVG Infographics - Mandatory Workflow

Every SVG image follows 6 sequential phases. No shortcuts, no batching. Complete all phases for one image before starting the next.

## Available Tools (consider these before computing by hand)

The plugin ships with **three calculators** and **five validators**. Glance over the menu whenever you face a sub-problem - chances are a tool already solves it.

| Tool | What it gives you |
|------|-------------------|
| `svg-infographics primitives <shape>` | Geometry + named anchors for rect, circle, ellipse, hex, star, arc, cube, cylinder, sphere, axis, **spline** (PCHIP through control points). Reach for it whenever you need a primitive's coordinates or a smooth waypoint curve |
| `svg-infographics connector --mode <m>` | Connector geometry in 4 modes: `straight`, `l`, `l-chamfer`, `spline`. Returns trimmed path, arrowhead polygons in world coords, tangent angle at each end. Pick the mode by connection style |
| `svg-infographics geom <op>` | Sketch constraints in the Fusion-360 style: midpoint, perpendicular foot, line extension, tangent points, intersections (line/line, line/circle, circle/circle), parallel/perpendicular construction, polar layout, evenly-spaced ring, concentric, angle bisector, **attachment points** on rect/circle edges, parallel **offset** of line/polyline/rect/circle/polygon (halos, rails, label standoff) |
| `svg-infographics overlaps` | Text/shape overlap, spacing rhythm, font-size floors |
| `svg-infographics contrast` | WCAG 2.1 contrast for text AND for objects vs the document background (light + dark mode) |
| `svg-infographics alignment` | Grid snapping, vertical rhythm, layout topology |
| `svg-infographics connectors` | Connector quality: zero-length, edge-snap, missing chamfer, dangling endpoints |
| `svg-infographics css` | CSS compliance: inline fills, missing dark-mode overrides, forbidden colours |

Each calculator's `--help` output describes when to reach for each subcommand. Skim the menu before computing a coordinate, control point, or contrast value by hand - the tool's output is also paste-ready for the SVG.

See `WORKFLOW.md` for the full inventory with usage notes.

## Task Tracking

**MANDATORY**: Use Claude Code task tracking (TaskCreate/TaskUpdate) throughout the workflow. Create a task list at the start showing all phases for each image. Mark each phase in_progress when starting, completed when done. This provides visible progress to the user.

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

**GATE**: Write summary to user listing image type, examples consulted, dimensions, colour classes. Do NOT proceed until shared.

## Phase 2: Invisible Grid

Write the grid BEFORE any visual elements. This is the blueprint.

1. **Use `svg-infographics primitives` to calculate the grid** - NEVER eyeball positions. Use `primitives rect`, `primitives circle`, `primitives axis` etc. to get exact anchor coordinates for all elements.

   **For ANY curve passing through known waypoints (decision boundary, distribution shape, score trajectory, ROC/PR, sigmoid, isoline, trend line, organic flow path)**: you MUST run `primitives spline --points "x1,y1 x2,y2 ..." --samples 200` and paste the returned `<path d="...">` verbatim. Hand-written `C` (cubic) or `Q` (quadratic) bezier paths for data curves are forbidden - they overshoot waypoints, kink at joins, and never look right. The PCHIP interpolator the tool uses is monotonicity-preserving and produces the exact curve a designer would draw. If you catch yourself typing `d="M... C..."` for anything other than a card corner radius, stop and rerun the tool.

   **For connectors between elements** use `svg-infographics connector` with the matching mode: `straight` for one line, `l` for axis-aligned right-angle routes, `l-chamfer` (default for any L route) for softened corners, `spline` for free curves through 3+ waypoints. All four modes return the trimmed path d, world-space arrowhead polygons, and tangent angles - never hand-author connector geometry.
2. Write `=== GRID ===` comment: viewBox, all x/y positions, rhythm step, margins, arrow paths
3. Write `=== LAYOUT TOPOLOGY ===` comment: container-child, h-stack, v-stack, mirror, flow relationships
4. No visual elements yet - grid only
5. Write grid to SVG file as comments only

**GATE**: SVG file contains ONLY grid comment and topology comment. No `<rect>`, `<path>`, `<text>`, or visual elements.

## Phase 3: Scaffold

Structural elements at grid positions. No text, no icons, no content.

1. `<style>` block with all CSS classes + `@media (prefers-color-scheme: dark)` overrides
2. `<g id="guide-grid" display="none">` reference lines
3. Card `<path>` outlines - use `svg-infographics primitives rect --radius 3` for exact anchor coordinates (flat-top, rounded-bottom, fill-opacity 0.04, stroke 1)
4. Accent bars (`<rect>` height 5, opacity 0.6, flush with card top)
5. Arrows using horizontal-first rule with `svg-infographics connector` for diagonal connectors
6. Connectors: chamfered L-routes (4px diagonal at 90-degree turns)
7. Track line segments with cutouts (if timeline)
8. For 3D shapes use `primitives cube/cylinder/sphere/cuboid/plane` for isometric coordinates
8. **Verify**: every coordinate matches grid comment

**GATE**: SVG has style block, card outlines, accent bars, arrows - but NO `<text>` content.

## Phase 4: Content

Add content at grid positions:

- `<text>` with CSS classes (NEVER inline fill), no opacity, font-family Segoe UI
- Title at accent_bar_bottom + 12px, descriptions at +14px rhythm, minimum 7px
- Legend text colour matches swatch colour (NOT fg-3/fg-4)
- Lucide icons in `<g>` with fill="none" + stroke, ISC license comment
- Decorative imagery: fg-1 colour, opacity 0.30-0.35 (banners only)
- Logos: computed scale from local bounds, preserved aspect ratio (banners only)

## Phase 5: Finishing

1. Verify arrow placement (horizontal-first rule, run `svg-infographics connector` to confirm)
2. Callout labels: centred in gap, 8px clear of arrow path
3. File description comment before `<svg>`: filename, shows, intent, theme

## Phase 6: Validation

**DO NOT deliver without running validation.**

1. Run `svg-infographics overlaps --svg {file}` - record summary
2. Run `svg-infographics css --svg {file}` - record CSS compliance
3. Classify each violation individually (no bulk dismissals): Fixed / Accepted / Checker limitation
4. Fix layout and CSS errors, re-run checkers, record new summary
5. Confirm: no #000000/#ffffff, all colours in swatch, transparent background, no width/height on `<svg>`

**GATE**: Paste validation output (overlaps + CSS) in response. If scripts not run, phase incomplete.

## Per-Image Checklist

Create `svg-workflow-checklist.md` with these check groups per image (`[x]` verified, `[-]` N/A, `[!]` failed):

1. **File comments** - description, grid, layout topology
2. **CSS block** - style with all classes and dark mode overrides
3. **Text rules** - CSS classes, no opacity, font-family
4. **Text positions** - titles at +12px, descriptions at +14px, within boundaries
5. **Card shapes** - flat top, rounded bottom r=3, fill-opacity 0.04, accent bar
6. **Arrow construction** - horizontal-first, chamfered L-routes, stem ends 4px before target
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

See `WORKFLOW.md` in this skill directory for expanded instructions, formulas, and checklists for each phase.

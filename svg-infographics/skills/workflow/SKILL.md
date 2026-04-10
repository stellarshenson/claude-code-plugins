---
name: workflow
description: Mandatory 6-phase sequential workflow for creating SVG infographics. Enforces research, invisible grid, scaffold, content, finishing, and validation phases with gate checks. Auto-triggered alongside svg-standards when creating any SVG visual content.
---

# SVG Infographics - Mandatory Workflow

Every SVG image follows 6 sequential phases. No shortcuts, no batching. Complete all phases for one image before starting the next.

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

1. **Use Python to calculate the grid** - NEVER eyeball positions. Run a Python script to compute all x/y positions, widths, gaps, clearances, vertical rhythm, viewBox dimensions
2. Write `=== GRID ===` comment: viewBox, all x/y positions, rhythm step, margins, arrow paths
3. Write `=== LAYOUT TOPOLOGY ===` comment: container-child, h-stack, v-stack, mirror, flow relationships
4. No visual elements yet - grid only
5. Write grid to SVG file as comments only

**GATE**: SVG file contains ONLY grid comment and topology comment. No `<rect>`, `<path>`, `<text>`, or visual elements.

## Phase 3: Scaffold

Structural elements at grid positions. No text, no icons, no content.

1. `<style>` block with all CSS classes + `@media (prefers-color-scheme: dark)` overrides
2. `<g id="guide-grid" display="none">` reference lines
3. Card `<path>` outlines (flat-top, rounded-bottom r=3, fill-opacity 0.04, stroke 1)
4. Accent bars (`<rect>` height 5, opacity 0.6, flush with card top)
5. Arrows using horizontal-first rule with `svg-infographics connector` for diagonal connectors
6. Connectors: chamfered L-routes (4px diagonal at 90-degree turns)
7. Track line segments with cutouts (if timeline)
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
2. Classify each violation individually (no bulk dismissals): Fixed / Accepted / Checker limitation
3. Fix layout errors, re-run, record new summary
4. Confirm: no #000000/#ffffff, all colours in swatch, transparent background, no width/height on `<svg>`

**GATE**: Paste validation script output in response. If scripts not run, phase incomplete.

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
15. **Validation** - check_overlaps summary, violations classified, layout errors fixed

## Detailed Phase Reference

See `WORKFLOW.md` in this skill directory for expanded instructions, formulas, and checklists for each phase.

# SVG Infographics - Mandatory Workflow

This document defines the exact workflow for creating SVG infographics. Every step must be followed in order, for every single image. No shortcuts, no batching.

## Skill Activation

Before creating any SVG content:

1. Read 3-5 examples from `examples/` closest to the type of infographic requested
2. Read the relevant theme swatch (`theme_swatch_*.svg`) for the target brand's colour palette and CSS class names
3. Create `svg-workflow-checklist.md` in the target images directory (see Checklist section below)

## Per-Image Workflow (6 Phases)

Each image goes through all 6 phases sequentially. Do NOT move to the next image until the current one completes all phases. Do NOT batch-create multiple SVGs.

### Phase 1: Research

- Read 3-5 relevant examples from `examples/` for THIS specific image type (e.g. read `header_banner_*.svg` before creating a header, read `timeline_hexagon.svg` before creating a timeline, read `card_grid.svg` before creating a card grid)
- Read the target theme swatch to confirm CSS class names (fg-1, fg-2, fg-3, accent-1, accent-2) and hex values
- Identify the closest example pattern: card grid, flow diagram, timeline, stats banner, header banner, bar chart, hub-and-spoke, layered model
- Note specific conventions from the example: card dimensions, arrow style, text sizes, spacing values

### Phase 2: Invisible Grid

Write the grid BEFORE any visual elements. This is the blueprint - everything else derives from it.

1. Write `=== GRID ===` comment block defining:
   - ViewBox width and height
   - Left margin, right margin, top margin, bottom margin (minimum 10px from viewBox edge)
   - All column x-positions: card lefts, card rights, divider positions, arrow midpoints, legend x
   - All row y-positions: card tops, card bottoms, accent bar heights, text baselines, legend rows
   - Vertical rhythm step size (typically 14px for card content, 10px for legend)
   - Card internal padding: 12px from accent bar bottom to first text baseline, 14px between subsequent text lines
   - Arrow paths: start (x,y), end (x,y), chamfer midpoint x, stem end x (4px before target), tip x (at target edge)
   - Track line segments: start x, end x for each segment between milestone cutouts (cx-r to cx+r)

2. Write `=== LAYOUT TOPOLOGY ===` comment block defining relationships (NOT coordinates):
   - Use operations: h-align, v-align, h-stack, v-stack, contain, mirror, flow
   - Reference named components (card-1, arrow-1, legend) not coordinates
   - No `--` inside XML comments (invalid XML)

### Phase 3: Scaffold

Place structural elements at grid positions. No text, no icons, no content yet.

1. Write `<style>` block with ALL CSS classes used in this image:
   - fg-1, fg-2, fg-3 (and fg-4 if needed) with hex values from theme swatch
   - accent-1, accent-2 if used
   - `@media (prefers-color-scheme: dark)` with overrides for every class

2. Place `<g id="guide-grid" display="none">` with reference lines at major grid positions

3. Place card outlines as `<path>` shapes:
   - Flat-top, rounded-bottom formula: `M{x},{y} H{x+w} V{y+h-r} Q{x+w},{y+h} {x+w-r},{y+h} H{x+r} Q{x},{y+h} {x},{y+h-r} Z`
   - Bottom corner radius r=3
   - Fill: accent colour with `fill-opacity="0.04"`
   - Stroke: accent colour with `stroke-width="1"`

4. Place accent bars as `<rect>`:
   - At card top, height=5, accent colour, opacity=0.6
   - x, y, width must match the card path exactly (flush)

5. Place arrows using the **horizontal-first rule**:
   - Design every arrow as a horizontal shape first, then rotate into position
   - Template: `<g transform="translate(tipX, tipY) rotate(angleDeg)">` wrapping:
     - Stem: `<line x1="-length" y1="0" x2="-10" y2="0"/>` (ends at back of head, not at tip)
     - Head: `<polygon points="0,0 -10,-5 -10,5"/>` (6px base, 4px depth)
   - Angle = `atan2(dy, dx)` degrees from tail to tip; positive = clockwise
   - **Stem touches back of polygon** - stem x2=-10 meets polygon base at x=-10
   - After rotation, verify: tip lands at target edge, stem starts at source edge
   - Compute rotated tip/tail coordinates: `tipX + cos(angle)*(-length)`, `tipY + sin(angle)*(-length)` to confirm fit
   - Fully opaque - no `opacity` on line or polygon
   - See `examples/arrow_patterns.svg` for straight (0deg), fork-up (-54.5deg), merge-down (29.7deg)

6. Place connectors (chamfered L-routes):
   - For multi-segment connections that change direction (not straight arrows)
   - Chamfer: 4px diagonal at every 90-degree turn
   - Formula: instead of `V{y} H{x}`, use `V{y-4} L{x+4},{y} H{x2-4} L{x2},{y+4}`
   - Stagger vertical midpoints when multiple L-routes share a gap
   - Manifold design: document fork/merge points in grid comment; fork uses one source colour, merge uses single pipeline colour (not mixed)
   - Connector endpoints connect to arrow stems or directly to card edges

7. Place track line segments (if timeline) - unchanged from below

8. Place track line segments (if timeline):
   - `<line>` from cx+r of one milestone to cx-r of next
   - NO continuous line through circles - segmented with cutouts
   - Track line stroke-width 1.5, opacity 0.15

9. **Verify**: every x/y coordinate matches the grid comment; arrow tip coordinates verified after rotation; connector endpoints meet card edges or arrow stems. Fix before proceeding.

### Phase 4: Content

Add content at the positions documented in the grid.

**Text**:
- Every `<text>` element uses CSS class for fill (`class="fg-1"`) - NEVER inline `fill=` on text
- No `opacity` or `fill-opacity` on any `<text>` element
- No parent `<g>` with opacity that would inherit to child text
- `font-family="Segoe UI, Arial, sans-serif"` on every text element
- Title at accent_bar_bottom + 12px (first baseline)
- Description at title_baseline + 14px (vertical rhythm)
- Minimum font size: 7px
- `text-anchor="middle"` for centred text, explicit `x` for left-aligned
- No `<tspan>` for mixed styling - use separate `<text>` elements with explicit x positions

**Legend**:
- Legend text colour MUST match its swatch colour (NOT fg-3 or fg-4)
- Use inline `fill=` matching swatch hex, or CSS class if one exists for that colour
- Consistent vertical rhythm between legend rows (typically 10px)
- Swatches: small `<rect>` with `rx="1"`, same colour as the element they represent

**Icons**:
- Source from Lucide icon library (ISC license)
- Attribution comment: `<!-- Icon: {name} (Lucide, ISC license) -->`
- Embed in `<g transform="translate(x,y) scale(s)">` with `fill="none"` and stroke attributes
- Scale: 0.583 for ~14px, 0.667 for ~16px, 0.5 for ~12px
- Bounding box (after scale) clears card right edge by 6px, top by 6px, nearest text by 4px
- All icons in a card set use the same scale and relative position

**Decorative imagery** (header banners only):
- fg-1 colour or brand accent colours
- Opacity 0.30-0.35
- Small scale (~15-20px extent)
- Placed in gap between text block and logos

**Logos** (header banners only):
- Local bounds computed from actual path data (not assumed)
- Scale = target_height / local_height
- Translate computed: `translate_x = desired_abs_x - local_min_x * scale`
- Aspect ratio preserved (height derived from scale, never hardcoded)
- Full opacity - no `opacity` attribute on logo `<g>` groups
- Right edge at viewBox_width - 12px padding
- 8px gap between logos

### Phase 5: Finishing

1. Verify arrow placement (arrows placed in Phase 3 using horizontal-first rule):
   - Each arrow is a `<g transform="translate(tipX,tipY) rotate(angle)">` containing stem `<line>` + head `<polygon>`
   - Compute rotated endpoints to confirm: tip at target edge, tail at source edge
   - Stem touches back of polygon (stem x2=-10 meets polygon base at x=-10)
   - Fully opaque (no opacity on line or polygon)

2. Add connector callout labels:
   - Centred in gap between source and target (x=midpoint, text-anchor=middle)
   - Vertically clear of arrow outer bbox (minimum 8px gap from nearest arrow path point)
   - Horizontally within the gap (not extending into any card boundary)

3. Write file description comment BEFORE `<svg>` tag:
   - Filename and role description
   - Shows: visual elements in reading order
   - Intent: purpose in the document
   - Theme: palette name and key shade assignments

### Phase 6: Validation

1. Run `svg-infographics overlaps --svg {file}` and record the full summary line
2. Count violations by classification: violation, sibling, label-on-fill, contained
3. Examine EACH violation individually (no bulk dismissals "these are all decorative"):
   - **Fixed**: element repositioned, re-run confirms resolution
   - **Accepted**: specific reason this is not a defect (e.g. "text inside its own card")
   - **Checker limitation**: manual computation proving compliance
4. Fix all genuine layout errors (label overflow, arrowhead penetration, margin violations)
5. Re-run `svg-infographics overlaps` after fixes and record new summary
6. Visual sanity check: do arrows connect to card edges? Do labels fit within gaps? Is spacing even?
7. Confirm: no `#000000` or `#ffffff` in any fill or stroke; no colours outside theme swatch; transparent background; no fixed width/height on `<svg>`

## Per-Image Checklist

Before creating any images, create `svg-workflow-checklist.md` in the target images directory with ~30 grouped checks per image. Each check covers multiple related verifications.

**Required check groups per image** (mark `[x]` verified, `[-]` N/A, `[!]` failed):

1. **File comments** - description comment (filename, shows, intent, theme); grid comment with all positions; layout topology with relationships
2. **CSS block** - `<style>` with all classes; `@media (prefers-color-scheme: dark)` with overrides for every class
3. **Text rules** - all `<text>` use CSS classes (zero inline fill); no opacity on text; `font-family="Segoe UI, Arial, sans-serif"` throughout
4. **Text positions** - titles at accent_bar_bottom + 12px; descriptions at +14px rhythm; text within card boundaries (12px padding); minimum font 7px
5. **Card shapes** - flat top, rounded bottom r=3; fill-opacity 0.04; stroke-width 1; accent bar height 5, opacity 0.6, flush with card
6. **Arrow construction** - path-based chevron tips (NOT polygon); chamfered L-routes 4px diagonal; stem ends 4px before target; tip touches card edge; stroke-linecap/linejoin round
7. **Track lines** - segmented with cutouts (cx-r to cx+r); no continuous line through circles; circles in gaps
8. **Grid/spacing** - vertical rhythm consistent; horizontal alignment verified; 12px card padding; 10px viewBox edge; 10px inter-card
9. **Legend** - text colour matches swatch colour; consistent row rhythm; swatches aligned
10. **Icons** - Lucide source; ISC license comment; same scale across cards; clearance 6px edges, 4px text
11. **Logos** - computed bounds; scale from target height; aspect ratio preserved; full opacity; right-aligned with padding
12. **Decorative imagery** - fg-1 or accent colours; opacity 0.30-0.35; small scale; in gap between text and logos
13. **Colours** - no #000000/#ffffff; all colours traceable to theme swatch; transparent background
14. **ViewBox** - dimensions match content; no width/height attributes on `<svg>`
15. **Validation** - `svg-infographics overlaps` summary recorded; each violation individually classified; layout errors fixed; re-run confirms

See `clients/arelion/agentic-workflow/images/svg-workflow-checklist.md` in the proposals repository for a complete reference template with image-specific checks.

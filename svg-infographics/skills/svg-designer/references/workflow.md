# SVG Workflow — 6-Phase Process

Mandatory sequential workflow. Every SVG goes through all 6 phases in order. No shortcuts. No batching across images. Complete image N before starting image N+1.

See `tools.md` for full tool inventory. See `standards.md` for rules. See `validation.md` for checker usage.

## Task tracking (MANDATORY)

TaskCreate at start with one task per phase per image. Mark in_progress on entering a phase, completed on leaving. Prevents skipped steps.

## Skill activation (once per session)

Before creating any SVG:

1. Read 3-5 examples from `examples/` closest to requested types
2. Read relevant theme swatch (`theme_swatch_*.svg`) for CSS class names + hex values
3. Create `svg-workflow-checklist.md` in target images directory

## Phase 1 — Research

- Read 3-5 relevant examples for THIS image type
- Confirm CSS class names + hex values from theme swatch
- Identify pattern: card grid, flow diagram, timeline, stats banner, header banner, bar chart, hub-and-spoke, layered model
- Note conventions: card dimensions, arrow style, text sizes, spacing

**GATE**: write summary to user — image type, examples consulted, dimensions, colour classes. Do NOT proceed until shared.

## Phase 2 — Invisible Grid

Grid BEFORE any visual elements. Blueprint.

1. Use `primitives` to calculate grid — never eyeball. `primitives rect` / `circle` / `axis` for exact anchors
2. For ANY curve through known waypoints: run `primitives spline --points "x1,y1 x2,y2 …" --samples 200`. Paste `<path d="…">` verbatim. Hand-written `C`/`Q` beziers for data curves forbidden (PCHIP is monotonicity-preserving)
3. For connectors: use `connector --mode <m>` with `--standoff 2`. L/L-chamfer ALWAYS pass both rects + `--start-dir`/`--end-dir` — otherwise tool infers first-axis from `|dx| vs |dy|` and vertical segment may run parallel to target edge
4. Write `=== GRID ===` comment: viewBox, every x/y, rhythm step, margins, arrow paths
5. Write `=== LAYOUT TOPOLOGY ===` comment: container-child, h-stack, v-stack, mirror, flow
6. No visual elements yet — grid + topology comments only

**GATE**: SVG contains ONLY comments. No `<rect>`, `<path>`, `<text>`.

## Phase 3 — Scaffold

Structural elements at grid positions. No text, no icons, no content.

1. `<style>` block with all CSS classes + `@media (prefers-color-scheme: dark)` overrides
2. `<g id="guide-grid" display="none">` reference lines
3. Card `<path>` outlines via `primitives rect --radius 3` (flat-top, rounded-bottom, fill-opacity 0.04, stroke 1)
4. Accent bars (`<rect>` height 5, opacity 0.6, flush with card top, NO `rx`)
5. **Every arrow / connector via `svg-infographics connector`** with `--standoff 2`. Paste `trimmed_path_d` + arrowhead polygons directly. Hand-coded `<path d="M…">` for any routed line = FAIL. No `rotate()` templates. No `atan2`. No "just 10 pixels"
6. Prefer `l-chamfer --chamfer 4` for any L-route. Sharp corners forbidden
7. Track line segments with cutouts (if timeline)
8. 3D shapes via `primitives cube/cylinder/sphere/cuboid/plane` for isometric
9. Verify every coordinate matches grid comment

**GATE**: style block, card outlines, accent bars, arrows — but NO `<text>`.

## Phase 4 — Content

- `<text>` with CSS classes (NEVER inline `fill=`), no opacity, font-family Segoe UI
- Title at `accent_bar_bottom + 12px`, descriptions at `+14px` rhythm, minimum 7px
- Unicode glyphs in every `<text>` node — `→` not `->`, `…` not `...`, `×` not `x`, `•` not `*`. ASCII fallback = FAIL
- Legend text colour matches swatch colour (NOT fg-3/fg-4)
- Lucide icons in `<g>` with `fill="none"` + stroke, ISC license comment
- Decorative imagery: fg-1 colour, opacity 0.30-0.35 (banners only)
- Logos: computed scale from local bounds, preserved aspect ratio (banners only)

## Phase 5 — Finishing

1. Verify arrow placement — every `<path>` + `<polygon>` matches `connector` output for same `--from`/`--to`/`--mode`. Discrepancy = workflow violation
2. Callout labels via `svg-infographics callouts` (joint solver). See `standards.md` for plan JSON shape + workflow
3. File description comment before `<svg>`: filename, shows, intent, theme

## Phase 6 — Validation

DO NOT deliver without running ALL validators. See `validation.md` for tool specifics.

1. Run `svg-infographics validate <file>` (XML + baseline geometry if `+` variant)
2. Run `svg-infographics overlaps --svg <file>` — record summary
3. Run `svg-infographics contrast --svg <file>` — record summary (light + dark)
4. Run `svg-infographics alignment --svg <file>` — record
5. Run `svg-infographics connectors --svg <file>` — record
6. Run `svg-infographics css --svg <file>` — record
7. Classify each violation individually (no bulk dismissals): Fixed / Accepted / Checker limitation
8. Fix errors, re-run, record new summary

**GATE**: paste validator output for all six. Scripts not run = phase incomplete.

## Per-image checklist (required groups)

`svg-workflow-checklist.md` with these check groups per image. Marks: `[x]` verified, `[-]` N/A, `[!]` failed.

1. **File comments** — description (filename, shows, intent, theme); grid with all positions; layout topology with relationships
2. **CSS block** — `<style>` with all classes; `@media (prefers-color-scheme: dark)` overrides for every class
3. **Text rules** — CSS classes (zero inline fill); no opacity; `font-family="Segoe UI, Arial, sans-serif"`; Unicode glyphs only (`→` not `->`, `←` not `<-`, `↔` not `<->`, `…` not `...`, `—` not `--`, `×` not `x`, `•` not `*`); ASCII arrows in any `<text>` = FAIL
4. **Text positions** — titles at `accent_bar_bottom + 12px`; descriptions at `+14px` rhythm; within card boundaries (12px padding); min font 7px
5. **Card shapes** — flat top, rounded bottom r=3; fill-opacity 0.04; stroke-width 1; accent bar height 5, opacity 0.6, flush with card top
6. **Arrow construction** — every arrow via `svg-infographics connector` with `--standoff 2`; `trimmed_path_d` as `<path>`, arrowhead polygons as `<polygon>` in world coords; no `rotate()` wrappers; `l-chamfer` mode 4px chamfer; endpoints meet card edges; `stroke-linecap`/`stroke-linejoin` round; hand-coded paths for any routed line = FAIL
7. **Track lines** — segmented with cutouts (cx-r to cx+r); no continuous line through circles; no `fill="white"` knockouts
8. **Grid/spacing** — vertical rhythm consistent; horizontal alignment; 12px card padding; 10px viewBox edge; 10px inter-card
9. **Legend** — text colour matches swatch; consistent row rhythm; swatches aligned
10. **Icons** — Lucide source; ISC comment; same scale across cards; clearance 6px edges, 4px text
11. **Logos** — computed bounds; scale from target height; aspect ratio preserved; full opacity; right-aligned with padding
12. **Decorative imagery** — fg-1 or accent colours; opacity 0.30-0.35; small scale; placed in gaps
13. **Colours** — no `#000000`, no `#ffffff`; all traceable to swatch; transparent background
14. **ViewBox** — matches content; no `width`/`height` on `<svg>`
15. **Validation** — `validate` + `overlaps` + `contrast` + `alignment` + `connectors` + `css` + `collide` summaries; each violation classified (Fixed / Accepted / Checker limitation); errors fixed; re-run confirms

## Detailed phase notes

### Phase 1 depth

Before touching code:

- Which cell in the document does this SVG illustrate?
- Which patterns from `examples/` match closest? (card grid / timeline / flow / hub-and-spoke / layered)
- Numbers to surface — focal stats, thresholds, counts
- Which theme swatch? If none approved, halt: run `/svg-infographics:theme` first

### Phase 2 depth

Grid comment sections:

```xml
<!-- === GRID ===
  viewBox: 1800 x 700
  Outer margins: 40 left/right, 60 top/bottom

  Horizontal:
    col-1: x=40..600   w=560
    col-2: x=640..1200 w=560
    col-3: x=1240..1760 w=520

  Vertical rhythm (16px):
    row-1: y=80..240   h=160
    row-2: y=256..416  h=160
    row-3: y=432..592  h=160
    gap: 16
=== -->
```

Topology comment:

```xml
<!-- === LAYOUT TOPOLOGY ===
  h-stack: card-A, card-B, card-C (gap=40)
  v-align: all cards share top y=80
  contain: card-A > icon-A, title-A, desc-A
  connect: card-A -> card-B (l-chamfer, standoff 2)
  connect: card-B -> card-C (l-chamfer, standoff 2)
=== -->
```

### Phase 3 depth — connector examples

Straight between rects:

```bash
svg-infographics connector --mode straight \
  --src-rect "40,80,560,160"  --tgt-rect "640,80,560,160" \
  --standoff 2 --arrow end
```

L-chamfer between rects:

```bash
svg-infographics connector --mode l-chamfer \
  --src-rect "40,80,560,160" --start-dir E \
  --tgt-rect "640,256,560,160" --end-dir N \
  --chamfer 4 --standoff 2 --arrow end
```

Manifold (fan-in + fan-out):

```bash
svg-infographics connector --mode manifold \
  --starts "(100,100) (100,200) (100,300)" \
  --ends   "(700,100) (700,200) (700,300)" \
  --spine-start "400,200" --spine-end "500,200" \
  --tension 0.75 --standoff 2 --arrow end
```

Paste `trimmed_path_d` into `<path class="connector">`, polygons into `<polygon class="arrow-head">`.

### Phase 4 depth — text placement

Compute label position from placed geometry via:

- `geom midpoint` — midpoint between two points
- `geom attach --side <edge> --pos mid` — edge midpoint on rect
- `geom perpendicular` — perpendicular foot from point to line
- `geom curve-midpoint --points "[(x,y),…]"` — arc-length midpoint on polyline (for labels ON a connector)

Place text AFTER visuals. Never eyeball label coordinates.

### Phase 5 depth — callouts

Use `svg-infographics callouts` (joint solver) — see `standards.md` "Callout construction workflow" for plan JSON shape, leader vs leaderless selection, audit workflow.

### Phase 6 depth — validation loop

Loop until clean:

```bash
svg-infographics validate  <file>   # XML + geometry (with --baseline for + variants)
svg-infographics overlaps  --svg <file>
svg-infographics contrast  --svg <file>
svg-infographics alignment --svg <file>
svg-infographics connectors --svg <file>
svg-infographics css       --svg <file>
svg-infographics collide   --svg <file>  # pairwise connector collisions (when manifold present)
```

Classify each finding individually per the default-bad rule (see `validation.md`): Fixed / Accepted / Checker limitation. Bulk dismissals prohibited.

## Anti-patterns

- Batch-creating multiple SVGs in parallel — violates per-image sequential gate
- Skipping Phase 2 "grid only" gate — leads to ad-hoc coordinates throughout
- Hand-coding connector paths because "it's simple" — breaks validation reproducibility
- Eyeballing text positions — causes overlap failures that validators catch
- Skipping Phase 6 validation — final gate before delivery, never optional
- Reusing an arrow from another file by copy-paste coordinates — use the tool

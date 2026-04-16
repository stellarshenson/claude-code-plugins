---
name: validation
description: SVG validation tools and verification workflow - overlap detection, WCAG contrast checking, alignment verification, connector quality, and browser visual testing. Auto-triggered when validating, checking, or fixing SVG infographic quality issues.
---

# SVG Validation and Verification

Twelve tools shipped in `stellars-claude-code-plugins` pip package. Install once, use everywhere via `svg-infographics` CLI. All tools install with base package - no optional extras.

## Failure severity ladder

Three severities. Only HARD FAILs block delivery.

| Severity | Prefix | Meaning | Ship rule |
|---|---|---|---|
| HARD FAIL | `WARNING:` | Broken geometry / illegal state. Requires written justification in SVG comment to ship | Default: BLOCK |
| SOFT WARNING | `CONSIDER (snap rule):` | Aesthetic degradation, avoidable with small adjustment | Fix when convenient |
| HINT | `HINT:` | Rule was auto-applied, FYI (e.g. T-junction chamfer dropped) | No action |

### Hard-fail classes

Geometry defects where rendered output is visually broken:

1. **Text-on-edge overlap** - text glyph bbox crosses a stroke (axis, card border, divider). Unreadable where crossed. **Hard fail unless justified**
2. **Edge-on-edge overlap** - two strokes crossing wrongly (axis through card border, connector through unrelated divider). Reads as routing bug. **Hard fail unless justified**
3. **Text-outside-container** - text extends past parent rectangle. Layout overflow. **Hard fail**
4. **Connector-through-content** - connector mid-segment crosses content group. **Hard fail**
5. **XML malformation** - broken parse (e.g. `--` in comment). **Hard fail**

### Justifying a hard fail

Intentional hard fail? Add XML comment adjacent documenting reason:

```xml
<!-- Hard-fail justified: "4.5:1" label sits ON the WCAG threshold line by design,
     communicating the boundary visually. Not a layout bug. -->
<line class="target-quad-stroke" x1="430" y1="246" x2="430" y2="294"/>
<text class="accent-2 metric-unit" x="432" y="248">4.5:1</text>
```

No justification = no ship.

```bash
pip install stellars-claude-code-plugins
svg-infographics --help
```

## Task Tracking

**MANDATORY**: TaskCreate/TaskUpdate when running validation. Tasks per checker run and fix cycle.

## Tool: overlaps

Parses all visual elements, computes bboxes (text with font metrics, paths, rotated arrows, circles, rects), reports ALL overlaps.

Classifications: `violation` (fix), `sibling` (adjacent), `label-on-fill` (intentional), `contained` (child in parent).

```bash
# Analyse and report
svg-infographics overlaps --svg path/to/file.svg

# Ignore reviewed pairs
svg-infographics overlaps --svg file.svg --ignore "21x23,24x25"

# Inject/strip bounding box overlay
svg-infographics overlaps --svg file.svg --inject-bounds
svg-infographics overlaps --svg file.svg --strip-bounds
```

### Verification Workflow

Cycle: `--strip-bounds` → fix layout → run check → `--inject-bounds` → visually verify → repeat → `--strip-bounds` (final, mandatory).

### Default-Bad Rule (Fail-First)

All violations assumed **real defects** until individually defended. Resolve each:
- **Fixed**: repositioned, re-run confirms
- **Accepted**: specific reason not a defect
- **Checker limitation**: manual computation proves compliance

**Bulk dismissals prohibited.** Examine every finding individually.

## Tool: contrast

WCAG 2.1 contrast checker. Resolves CSS classes, alpha-blends backgrounds, checks AA (4.5:1 normal, 3.0:1 large) and AAA.

```bash
svg-infographics contrast --svg file.svg              # AA default
svg-infographics contrast --svg file.svg --level AAA  # stricter
svg-infographics contrast --svg file.svg --show-all   # include passing
svg-infographics contrast --svg file.svg --dark-bg "#272b31"
```

## Tool: alignment

Grid snapping, vertical rhythm, x-alignment, rect alignment, legend consistency, topology verification.

```bash
svg-infographics alignment --svg file.svg              # 5px grid default
svg-infographics alignment --svg file.svg --grid 10 --tolerance 1
```

## Tool: connectors

Connector quality: zero-length segments, edge-snap, L-routing, label clearance.

```bash
svg-infographics connectors --svg file.svg
```

## Tool: css

CSS compliance. Validates: all colours CSS-controlled, no inline fills on text, no forbidden colours (#000000/#ffffff), dark mode overrides present.

```bash
svg-infographics css --svg file.svg              # Check compliance
svg-infographics css --svg file.svg --strict     # Warnings as errors
```

## Tool: connector

Connector geometry calculator. Computes angle, stem coordinates, arrowhead points, SVG snippet.

```bash
svg-infographics connector --from 520,55 --to 590,135 --margin 4 --head-size 10,5

# With pill cutout (splits into two segments):
svg-infographics connector --from 353,122 --to 200,84 --margin 3 --cutout 236,90,78,13
```

## Tool: primitives

Geometry generator returning exact anchors for precise placement. Run `primitives --help` for full list.

```bash
# 2D shapes
svg-infographics primitives rect --x 20 --y 30 --width 200 --height 100 --radius 3
svg-infographics primitives circle --cx 400 --cy 200 --r 50
svg-infographics primitives hexagon --cx 300 --cy 200 --r 40
svg-infographics primitives diamond --cx 200 --cy 100 --width 80 --height 60
svg-infographics primitives arc --cx 200 --cy 200 --r 80 --start 0 --end 90

# 3D isometric shapes
svg-infographics primitives cube --x 50 --y 50 --width 100 --height 80 --mode fill
svg-infographics primitives cylinder --cx 200 --cy 50 --rx 60 --ry 20 --height 100
svg-infographics primitives sphere --cx 300 --cy 200 --r 50

# Curves and layout
svg-infographics primitives spline --points "80,200 150,80 300,120 450,60" --samples 50
svg-infographics primitives axis --origin 80,200 --length 300 --axes xyz --ticks 5
```

Each primitive returns named anchor points (center, top-left, vertices, tips, etc.) for precise positioning.

## Tool: text-to-path (ON REQUEST ONLY)

Converts text rendered in TTF/OTF font into SVG `<path>` outlines. **Do NOT run by default.** Use only when user explicitly asks for:

- Embedding custom font without renderer having it installed
- Print/hand-off SVGs identical across renderers (rsvg, CairoSVG, Inkscape, browsers)
- Headline/label needing deterministic bbox for fit-to-width without `textLength` distortion
- Branding marks (logos, wordmarks) that must never reflow

Tradeoffs caller accepts:

- No longer editable as text (no search/replace, no screen readers, no copy-paste)
- File size 5-20x larger than `<text>`
- `.ttf` or `.otf` path required - no system font resolution

Coordinates: `--x`/`--y` are **baseline** origin, `--anchor` mirrors `text-anchor` (start | middle | end). With `--fit-width`, natural advance exceeding width uniformly scales path down (aspect preserved).

```bash
# Minimal: render "Hello" at baseline (100, 200) using Inter.ttf at 24px
svg-infographics text-to-path --text "Hello" --font ./Inter.ttf --size 24 --x 100 --y 200

# Centered headline, fit into a 300px column, dark fill
svg-infographics text-to-path \
  --text "Quarterly Results" \
  --font ./InterDisplay-SemiBold.ttf \
  --size 32 --x 450 --y 80 --anchor middle \
  --fit-width 300 --fill "#1e3a5f"

# Use a CSS class instead of inline fill (preferred for theme-aware infographics)
svg-infographics text-to-path --text "TITLE" --font ./Inter.ttf \
  --size 28 --x 20 --y 60 --class headline-fg

# Machine-readable output (svg + bbox) for scripted composition
svg-infographics text-to-path --text "Hi" --font ./Inter.ttf --size 24 --json
```

Prints `<path>` on stdout, bbox + scale on stderr.

## Pre-Delivery Checklist

### Structure
- [ ] File description comment before `<svg>`
- [ ] Transparent background
- [ ] ViewBox set, no width/height on `<svg>`
- [ ] `<style>` with `@media (prefers-color-scheme: dark)`
- [ ] Guide grid present
- [ ] Grid comment after `<style>`
- [ ] No `#000000` or `#ffffff`

### Text
- [ ] All `<text>` use CSS classes - no hardcoded fill
- [ ] No opacity on text
- [ ] System fonts, 7px minimum
- [ ] Text within parent shapes

### Layout
- [ ] Z-order: track → connectors → nodes → content
- [ ] Card fills at 0.04-0.08 opacity
- [ ] 10px+ padding from edges
- [ ] Uniform spacing, consistent alignment
- [ ] All children within parent boundaries

### Automated
- [ ] `overlaps` - all violations reviewed
- [ ] `contrast` - zero FAIL in production
- [ ] `alignment` - topology passes
- [ ] `css` - no inline fills, no forbidden colours, dark mode verified
- [ ] Browser visual check via Playwright

## Multi-Agent Validation Workflow

1. **Generator** creates/edits SVG
2. **Checker agents** run all three scripts **in parallel** (3 concurrent)
3. **Generator** classifies findings, writes `verification_checklist.md`
4. **Critic agent** (separate context, fail-first) reviews every classification
5. **Fixer** addresses rejections, re-runs checkers
6. **Verifier** confirms with Playwright screenshots (light + dark)

## Browser Visual Verification

Playwright blocks `file://` URLs. Serve via HTTP:

1. `python3 -m http.server 8768` from images directory
2. HTML wrapper: `<body style="background:#1e1e1e"><img src="http://localhost:8768/file.svg" width="900"></body>`
3. Serve wrapper on different port, navigate Playwright
4. Screenshot dark + light modes
5. Check: text overlap, contrast failures, bar misalignment, asymmetric padding

## Generative Failure Investigation

Generate `verification_checklist.md` per failure:

```markdown
- [ ] `<filename>` | `"<text>"` | <ratio/overlap%> | <mode>
  - **Root cause**: <description>
  - **Fix**: <specific action>
```

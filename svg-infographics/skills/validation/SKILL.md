---
name: validation
description: SVG validation tools and verification workflow - overlap detection, WCAG contrast checking, alignment verification, connector quality, and browser visual testing. Auto-triggered when validating, checking, or fixing SVG infographic quality issues.
---

# SVG Validation and Verification

Five validation tools shipped with the `stellars-claude-code-plugins` pip package. Install once, use everywhere via the `svg-infographics` CLI.

```bash
pip install stellars-claude-code-plugins
svg-infographics --help
```

## Task Tracking

**MANDATORY**: Use Claude Code task tracking (TaskCreate/TaskUpdate) when running validation. Create tasks for each checker run and fix cycle.

## Tool: overlaps

Parses all visual elements, computes bounding boxes (text with font metrics, paths, rotated arrows, circles, rects), reports ALL overlaps.

Classifications: `violation` (fix needed), `sibling` (adjacent), `label-on-fill` (intentional), `contained` (child in parent).

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

Cycle: `--strip-bounds` -> fix layout -> run check -> `--inject-bounds` -> visually verify -> repeat -> `--strip-bounds` (final, mandatory).

### Default-Bad Rule (Fail-First)

All violations assumed **real defects** until individually defended. Each finding addressed as:
- **Fixed**: repositioned, re-run confirms
- **Accepted**: specific reason not a defect
- **Checker limitation**: manual computation proving compliance

**Bulk dismissals prohibited.** Each finding individually examined.

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

## Tool: connector

Connector geometry calculator. Computes angle, stem coordinates, arrowhead points, SVG snippet.

```bash
svg-infographics connector --from 520,55 --to 590,135 --margin 4 --head-size 10,5

# With pill cutout (splits into two segments):
svg-infographics connector --from 353,122 --to 200,84 --margin 3 --cutout 236,90,78,13
```

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
- [ ] Z-order: track -> connectors -> nodes -> content
- [ ] Card fills at 0.04-0.08 opacity
- [ ] 10px+ padding from edges
- [ ] Uniform spacing, consistent alignment
- [ ] All children within parent boundaries

### Automated
- [ ] `svg-infographics overlaps` - all violations reviewed
- [ ] `svg-infographics contrast` - zero FAIL in production
- [ ] `svg-infographics alignment` - topology passes
- [ ] Browser visual check via Playwright

## Multi-Agent Validation Workflow

1. **Generator** creates/edits SVG
2. **Checker agents** run all three scripts **in parallel** (3 concurrent agents)
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
5. Check for: text overlap, contrast failures, bar misalignment, asymmetric padding

## Generative Failure Investigation

Generate `verification_checklist.md` per failure:

```markdown
- [ ] `<filename>` | `"<text>"` | <ratio/overlap%> | <mode>
  - **Root cause**: <description>
  - **Fix**: <specific action>
```

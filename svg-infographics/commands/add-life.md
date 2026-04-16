---
description: Enhance existing SVGs with glow, icons, decorations, colour variation, abstract shapes at configurable intensity (low/medium/high/absurd)
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, Skill, TaskCreate, TaskUpdate]
argument-hint: "path(s) + level, e.g. 'docs/images/*.svg medium' or 'banner.svg high'"
---

# Add Life

Decoration pass on existing SVG. NOT a redesign - additive overlays, filters, fills. Positions, text, connectors stay unchanged.

**Input**: SVG file(s) + intensity level (low / medium / high / absurd). Default: medium.

## Before touching

1. Read target SVG completely
2. Read XML comment block - understand intent and theme
3. Identify theme swatch (CSS classes, palette, dark-mode overrides)
4. Reference `svg-infographics/skills/svg-standards/SKILL.md` for palette

**Never break layout.** Enhancements = additive only.

## Six dimensions

### 1. Colour variation

Expand palette within brand hue family. Derive new shades via lightness, saturation, opacity shifts. Never off-brand hues.

| Level | Treatment |
|-------|-----------|
| **low** | 2-3 opacity variants (0.08, 0.15, 0.25). Alternate row tinting |
| **medium** | 4-6 derived shades (analogous +-15 deg). Gradient fills on key cards. Varied stroke opacity |
| **high** | 8+ derived shades. Multi-stop gradients. Colour-coded groups. Spatial colour transitions |
| **absurd** | Chromatic harmonics. Iridescent overlays. Every element unique shade. Complementary accent splashes |

### 2. Shape and creative elements

Visual hierarchy, depth cues, compositional interest.

| Level | Treatment |
|-------|-----------|
| **low** | Rounded corners rx=8-12. Accent bars 3-4px at card tops. Slight size variation |
| **medium** | Layered shadows via offset rects at 0.06 opacity. Stagger 2-4px for depth. Decorative dividers |
| **high** | Overlapping card edges. Isometric tilt hints. Background section plates. Corner brackets |
| **absurd** | Irregular polygon cards. Translucent layers. Perspective distortion. Organic blob containers |

### 3. Icons and symbols

Small iconic glyphs reinforcing element meaning.

| Level | Treatment |
|-------|-----------|
| **low** | 2-3 geometric icons (dot, chevron, checkmark). Monochrome 12-16px in headers |
| **medium** | 5-8 contextual icons. 2-3 line weights. Mix filled/outline. Headers + endpoints + titles |
| **high** | Unique icon per card. Accent-coloured fills. Badge icons at junctions. Icon strips in headers |
| **absurd** | Icon patterns as card backgrounds. Floating particle icons. Inline icon glyphs on every label |

### 4. Decorative embroidery

Textile-inspired patterns, borders, ornamental detail.

| Level | Treatment |
|-------|-----------|
| **low** | Dotted borders on 1-2 cards. Dash patterns on dividers. Dots at grid intersections |
| **medium** | Cross-stitch dot backgrounds (8px spacing, 0.06 opacity). Decorative end-caps. Corner marks |
| **high** | `<pattern>` fills (herringbone, chevron, dot-grid). Alternating dash/dot borders. Filigree corners |
| **absurd** | Full textile overlays. Woven grid backgrounds. Lace borders. Celtic knot connectors |

### 5. Abstract graphics

Non-representational shapes creating visual energy.

| Level | Treatment |
|-------|-----------|
| **low** | 3-5 accent dots (r=2-4) in white space. One subtle background arc |
| **medium** | 10-20 particles (circles, diamonds) varied opacity 0.04-0.15. 2-3 background arcs. Concentric ring fragments |
| **high** | 30+ particle cloud with size/opacity gradient. Wave undulations. Constellation lines. Radial burst |
| **absurd** | Dense particle field. Ribbon paths between elements. Voronoi outlines. Orbital rings. Fractal branching |

### 6. Glow effects

Luminous highlights via SVG filters (feGaussianBlur, feColorMatrix, feComposite).

| Level | Treatment |
|-------|-----------|
| **low** | One glow filter (stdDeviation=2). Apply to 1-2 focal elements |
| **medium** | Two filters (cool accent-1 stdDev=3, warm accent-2 stdDev=2). All connectors + key borders. Title halos |
| **high** | Three-layer glow (inner 1, mid 4, outer 8). Connectors, accent bars, icons, focal shapes. Background radial glow |
| **absurd** | Every element glows. Bloom on entire composition. Neon double-glow on connectors. Light leak edges |

## Documentation comment

**MANDATORY**: append an `<!-- add-life -->` XML comment block inside the SVG (after the existing file description comment) documenting what was done:

```xml
<!-- add-life: medium
  colour: 4 derived shades, gradient fills on section headers
  shapes: card shadows at 0.06 opacity, accent bars 3px
  icons: 6 contextual icons (grid, connector, palette, align, check, chart)
  embroidery: dot backgrounds 8px spacing, decorative end-caps on dividers
  abstract: 15 accent particles, 2 background arcs
  glow: cool accent-1 stdDev=3 on connectors, warm accent-2 stdDev=2 on focal cards
-->
```

This comment allows future agents to understand what decorations were applied, at what level, and whether to preserve or replace them during rework.

## Rules

1. `<defs>` block after `<style>` for filters, gradients, patterns
2. Every new colour/gradient MUST have `@media (prefers-color-scheme: dark)` override
3. Decorations render BELOW content in DOM
4. Filter regions tight (`filterUnits="userSpaceOnUse"`). Max 3 blur passes per chain
5. Size targets: <50KB medium, <100KB high. Absurd unlimited
6. Text stays legible. Decoration interferes with contrast = reduce or remove
7. Run `overlaps` + `contrast` validators after. Broken validation = broken embroidery

## Workflow

1. Read SVG + theme
2. Task list: one task per dimension
3. Apply all six at requested level
4. Render PNG at 3x for visual check
5. Run `overlaps` + `contrast` validators
6. Fix validation failures
7. Report: dimensions applied, additions, final file size

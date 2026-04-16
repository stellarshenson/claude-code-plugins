---
description: Enhance existing SVGs with glow, icons, decorations, colour variation, abstract shapes at configurable intensity (low/medium/high/absurd)
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, Skill, TaskCreate, TaskUpdate]
argument-hint: "path(s) + level, e.g. 'docs/images/*.svg medium' or 'banner.svg high'"
---

# Add Life

Decoration pass on existing SVG. NOT a redesign - additive overlays, filters, fills. Positions, text, connectors stay unchanged.

**Input**: SVG file(s) + intensity level (low / medium / high / absurd). Default: medium.

**MANDATORY**: This command follows the svg-infographics skill and workflow. All placement uses tools (`empty-space`, `geom align`), all colours use CSS classes with dark mode, all elements respect topology and grouping. Read `svg-standards/SKILL.md` principles - they apply here.

## Before touching

1. Read target SVG completely
2. Read XML comment block - understand intent and theme
3. Identify theme swatch (CSS classes, palette, dark-mode overrides)
4. Reference `svg-infographics/skills/svg-standards/SKILL.md` for palette and placement rules
5. Run `empty-space --svg <file> --edges-only --tolerance 8 --min-area 100` to map available space

**Never break layout.** Enhancements = additive only.

## Six dimensions

### 1. Colour variation

Creative variation anchored in brand palette. Hue shifts, lightness and saturation tweaks, opacity layering. Apply to BOTH fills AND strokes - card outlines, connectors, accent bars should all get subtle hue variation, not remain uniform. May introduce complementary hues where they add depth - not limited to strict brand colours.

| Level | Character |
|-------|-----------|
| **low** | Subtle. Opacity variants, alternate row tinting, small hue shifts on accents |
| **medium** | Noticeable. Derived shades, gradient fills on focal cards, complementary accent hues where warranted |
| **high** | Rich. Many derived shades, multi-stop gradients, colour-coded groups, free use of complementary hues |
| **absurd** | Chromatic. Iridescent overlays, every element its own shade, bold complementary splashes |

### 2. Shape and creative elements

Visual hierarchy, depth cues, compositional interest.

| Level | Character |
|-------|-----------|
| **low** | Gentle. Rounded corners, thin accent bars, slight size variation |
| **medium** | Layered. Card shadows for depth, decorative dividers, staggered elements |
| **high** | Bold. Overlapping edges, isometric hints, background plates, corner brackets |
| **absurd** | Experimental. Irregular polygons, translucent layers, perspective distortion |

### 3. Icons and symbols

Detailed multi-stroke iconic glyphs reinforcing element meaning. NOT simple silhouettes - each icon should be a small but complete drawing with visible internal detail.

| Level | Character |
|-------|-----------|
| **low** | Few. Geometric icons in key headers, monochrome |
| **medium** | Contextual. Icons per section, mixed stroke weights and fill/outline |
| **high** | Comprehensive. Unique icon per card, accent-coloured, badge icons at junctions |
| **absurd** | Pervasive. Icon patterns as backgrounds, floating particles, inline glyphs on labels |

### 4. Decorative embroidery

Futuristic flourishes, tech-line accents, ornamental detail. Choose a domain theme from the embroidery gallery that matches SVG content.

**Domain themes**: electronics/circuit, AI/neural, cyberpunk HUD, sci-fi abstract, decorative flourishes, science/math

**Organic circuitry**: faded circuit-trace paths that grow organically across the background - branching lines with node dots at intersections, like PCB traces or neural dendrites. Low opacity, placed in the background layer behind all content. Density scales with level.

| Level | Character |
|-------|-----------|
| **low** | Sparse. Corner marks on focal cards, dash accents. One or two faded organic circuit traces in background |
| **medium** | Textured. Tech-line fragments, angular bracket decorations, micro geometric patterns. Several organic circuit branches |
| **high** | Intricate. Pattern fills, alternating motifs, filigree corners. Organic circuitry network spanning background |
| **absurd** | Dense. Full textile overlays, woven backgrounds, themed border systems. Dense organic circuitry everywhere |

### 5. Abstract graphics

Non-representational shapes creating visual energy.

| Level | Character |
|-------|-----------|
| **low** | Minimal. Few accent particles in whitespace, one subtle background sweep |
| **medium** | Atmospheric. Scattered particles with varied opacity, background arcs, ring fragments |
| **high** | Energetic. Particle clouds, wave undulations, constellation lines, radial bursts |
| **absurd** | Dense. Particle fields, ribbon paths, voronoi outlines, orbital rings, fractal branching |

### 6. Background texture

Faded organic patterns behind content adding visual depth. Low opacity, background layer only.

**Texture themes** (ask user which fits):
- Circuit / PCB traces - branching paths with node dots at intersections
- Neural / dendritic - organic branching like neurons or root systems
- Geographic / topographic - contour lines, map-like undulations
- Grid / technical - faded engineering grid, coordinate markers
- Organic / natural - flowing curves, leaf veins, water ripples
- None - skip this dimension

| Level | Character |
|-------|-----------|
| **low** | One or two faded traces, very sparse |
| **medium** | Several branching paths, subtle network |
| **high** | Full background network, clearly visible texture |
| **absurd** | Dense texture covering entire background |

### 7. Glow effects

Luminous highlights via SVG filters. Apply selectively where it reinforces visual hierarchy.

| Level | Character |
|-------|-----------|
| **low** | Restrained. Glow on one or two focal elements only |
| **medium** | Warm. Dual-tone glow on connectors and key borders, title halos |
| **high** | Dramatic. Multi-layer glow, connectors and accent bars, background radial glow |
| **absurd** | Full bloom. Everything glows, neon double-glow, light leak edges |

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

### Step 1: Read and analyse

Read SVG + theme. Understand content domain (tech, AI, science, business, etc.).

### Step 2: Propose treatment (MANDATORY - ask before applying)

Present a proposal table to the user covering all 7 dimensions. Suggest specific treatments based on SVG content and requested level. User must confirm or adjust before any edits.

**Proposal format:**

```
Add-life proposal for <filename> at <level>:

| Dimension | Proposed treatment | Skip? |
|-----------|-------------------|-------|
| Colour | Hue-shifted fills AND strokes, alternate card tinting | |
| Shapes | Accent bars, rounded corners, card shadows | |
| Icons | Detailed multi-stroke icons in headers | |
| Embroidery | Theme: <suggest based on content>. Corner marks, tech-line flourishes | |
| Abstract | Accent particles in whitespace, background arcs | |
| Bg texture | Theme: <circuit/neural/geographic/grid/organic/none>. Faded traces | |
| Glow | Selective glow on focal elements | |

Proceed? (or adjust any dimension)
```

For **embroidery**, suggest a domain theme: electronics/circuit, AI/neural, cyberpunk HUD, sci-fi abstract, decorative flourishes, science/math.

For **background texture**, suggest a theme: circuit/PCB traces, neural/dendritic, geographic/topographic, grid/technical, organic/natural, or none.

Pick the domain that matches the SVG content. User can override.

### Step 3: Apply

After user confirms, apply all six dimensions as approved. One task per dimension.

**Placement rules (MANDATORY)**:

1. **Empty-space first**: before placing ANY element (icon, flourish, particle), run `empty-space --svg <file> --edges-only --tolerance 8 --min-area 100` to find safe zones. For placement inside a specific card, add `--container-id <card-id>`. Only place within detected free regions
2. **Topology alignment**: elements sharing a role across containers (e.g. icons across cards, corner marks across sections) MUST be aligned via `geom align`. Icons in a row of cards share the same y. Corner marks at the same relative position in each card
3. **Group decorations**: all add-life elements go into a dedicated `<g id="add-life-decorations">` group. Icons into `<g id="add-life-icons">`. Maintain the five-layer structure
4. **Overlap validation**: run `overlaps` checker after placement. Any decoration that violates padding/margin/spacing rules gets repositioned or removed

### Step 4: Verify

1. Render PNG at 3x via `render-png --mode both`
2. Run `overlaps` + `contrast` validators
3. Fix validation failures
4. Report: dimensions applied, additions, final file size

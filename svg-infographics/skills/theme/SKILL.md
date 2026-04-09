---
name: theme
description: SVG theme swatch generation, palette approval workflow, colour naming, and brand palette management. Auto-triggered when creating theme swatches, defining colour palettes, or working with brand-specific SVG colour schemes.
---

# SVG Theme Management

Themes define the colour palette for all SVG infographics in a project. Every project needs an approved theme before producing deliverables.

## Task Tracking

**MANDATORY**: Use Claude Code task tracking (TaskCreate/TaskUpdate) when generating themes. Create tasks for swatch generation, user approval, and documentation.

## Theme Approval Workflow

1. **Ask the user** for brand colours, mood, or reference materials
2. **Generate theme swatch SVG** (`theme_swatch.svg`) showing all colours in context:
   - Primary, secondary, tertiary text colours with sample text
   - Accent colours with sample strokes and fills
   - Card background fills at intended opacity
   - Icon stroke colour samples
   - Mini timeline or flowchart snippet demonstrating palette
3. **Present to user** for approval before any deliverable SVGs
4. **Document approved palette** in project's `CLAUDE.md` or `theme.md`

### When to Skip

- Modifying existing SVGs with established palette
- User has explicitly provided and confirmed hex codes
- Single quick SVG with clear colour direction

## Theme Structure

Numbered shade grades in four roles:

| Role | Grade | Purpose |
|------|-------|---------|
| **fg-1** | Most contrastive | Headings, primary labels, hero stat numbers |
| **fg-2** | High contrast | Card titles, phase subtitles |
| **fg-3** | Medium contrast | Descriptions, sublabels |
| **fg-4** | Least contrastive | Metadata, tertiary text |
| **accent-1** | Primary | Strokes, icons, borders |
| **accent-2** | Secondary | Lighter strokes, later-phase elements |
| **bg-1** | Card fill | Accent-1 at fill-opacity 0.04-0.06 |
| **bg-2** | Track fill | Accent-1 at opacity 0.3 |

fg-4 must still be readable at small sizes (9-10px).

## Theme Definition Format

```
fg-1:       #103d82   (darkest - headings, primary labels)
fg-2:       #2a5f9e   (mid - card titles, stat numbers)
fg-3:       #4a7ba7   (medium - descriptions, sublabels)
fg-4:       #6b8db5   (lightest - metadata, tertiary text)
accent-1:   #00a6ff   (primary strokes, icons, borders)
accent-2:   #66ccff   (secondary strokes, later-phase)
bg-1:       #00a6ff at fill-opacity 0.04-0.06
bg-2:       #00a6ff at opacity 0.3
```

## Theme Swatch SVG

Three sections: palette reference (transparent bg), light background strip, dark background strip. Each strip demonstrates: card, stats, timeline, arrows, coverage bar.

### Swatch Requirements

- `=== COLOUR RULES ===` comment block documenting all hex values, dark mode mappings, accent usage guidance, hierarchy statement
- No hex values in label text - reference by name only
- Semantic colour labels use their own colour as fill
- Demonstration strips may use inline fills intentionally

## Colour Naming and Swatch Completeness

**MANDATORY**: Every hex colour in any SVG must have a named entry in the theme swatch.

Named categories:
- **Foreground shades** (fg-1..fg-4): via CSS classes
- **Accent shades** (accent-1, accent-2): via CSS classes
- **Background fills** (bg-1, bg-2): semi-transparent tints
- **Semantic data colours**: domain-specific, inline fills OK
- **Annotation colours** (err-text, on-fill): via CSS classes

When introducing a new colour:
1. Add to swatch palette reference with chip and role name
2. If dark mode variant needed, add CSS class
3. Document in project's theme section

## Reference Swatches

| File | Brand |
|------|-------|
| `theme_swatch_1_kolomolo.svg` | Kolomolo (deep blue/violet) |
| `theme_swatch_3_meridian.svg` | Meridian (blue palette) |
| `theme_swatch_5_optima_manufacturing.svg` | Optima Manufacturing (burgundy + gray) |

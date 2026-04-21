---
description: Generate or update a theme swatch SVG for brand colour approval
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion, TaskCreate, TaskUpdate]
argument-hint: "brand name or colour direction, e.g. 'corporate blue palette' or 'dark green tech theme'"
---

# Generate Theme Swatch

Create a theme swatch SVG for user approval before producing infographic deliverables.

## Task Tracking

**MANDATORY**: Create tasks for gathering requirements, generating swatch, getting approval, and documenting palette.

## Skills to apply

- **`theme` skill** — theme structure, swatch template, colour naming, approval workflow
- **`svg-designer` skill, `references/standards.md`** — CSS classes, dark mode, contrast rules

## Steps

1. **ASK the user**:
   - Brand colours, hex values, or mood direction?
   - Reference materials or existing brand guidelines?
   - Any colour constraints or preferences?

2. **Read reference swatches** from `examples/`:
   - `theme_swatch_1_kolomolo.svg` (blue/violet)
   - `theme_swatch_3_meridian.svg` (blue)
   - `theme_swatch_5_optima_manufacturing.svg` (burgundy)

3. **Generate theme swatch SVG** with three sections:
   - Palette reference (transparent background)
   - Light background strip with all element types
   - Dark background strip with all element types
   - `=== COLOUR RULES ===` comment block

4. **Present to user** for approval:
   - Show fg-1 through fg-4 with sample text
   - Show accent-1 and accent-2 with strokes and fills
   - Show card backgrounds, track lines, coverage bars
   - Identify any dark-mode failures with "FAIL?"

5. **On approval**: Document palette in project's `CLAUDE.md` or `theme.md`

6. **On rejection**: Adjust based on feedback, regenerate, re-present

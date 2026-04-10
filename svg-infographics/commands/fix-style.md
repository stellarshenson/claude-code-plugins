---
description: Fix CSS theme classes, contrast issues, dark mode, and colour compliance in existing SVGs
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Agent, TaskCreate, TaskUpdate]
argument-hint: "SVG file path or directory to fix"
---

# Fix SVG Style Issues

Apply fixes to existing SVG files for CSS compliance, contrast, dark mode support, and colour naming.

## Task Tracking

**MANDATORY**: Create a task list for each file being fixed. Track diagnosis, fix application, and validation re-run as separate tasks.

## Skills to apply

- **svg-standards**: CSS-First Rule, Contrast Rules, Font Opacity Rule
- **theme**: Colour Naming, swatch completeness
- **validation**: `svg-infographics contrast`, `svg-infographics overlaps`

## Steps

1. **Identify target**: Read the SVG file(s) to fix

2. **Run diagnostics** (create tasks per checker):
   - `svg-infographics css --svg {file}` - identify inline fills, forbidden colours, missing dark mode
   - `svg-infographics contrast --svg {file} --show-all` - identify FAIL and warn entries
   - `svg-infographics overlaps --svg {file}` - identify spacing violations
   - `svg-infographics alignment --svg {file}` - identify grid snap issues

3. **Apply fixes directly** (destructive - modifies files):
   - Replace inline `fill="#hex"` on text with CSS classes (`class="fg-1"`)
   - Add missing `@media (prefers-color-scheme: dark)` overrides
   - Remove `opacity` from `<text>` elements
   - Replace `#000000`/`#ffffff` with theme colours
   - Fix `<tspan>` mixed styling -> separate `<text>` elements
   - Add missing `font-family` attributes
   - Ensure transparent background (no full-viewport rect fill)
   - Fix ViewBox: remove `width`/`height` from `<svg>`, keep `viewBox`

4. **Re-run validation** to confirm fixes resolved issues

5. **Report**: changes made per file, before/after validation counts

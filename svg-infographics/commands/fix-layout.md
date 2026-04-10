---
description: Fix layout issues in SVG infographics - overlaps, alignment, spacing, grid violations
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Agent, TaskCreate, TaskUpdate]
argument-hint: "SVG file path to fix"
---

# Fix SVG Layout Issues

Diagnose and fix layout problems: element overlaps, alignment drift, spacing violations, grid snap issues.

## Task Tracking

**MANDATORY**: Create tasks for diagnosis, each fix category, and validation re-run.

## Skills to apply

- **svg-standards**: Grid layout, margins, bounding boxes, card shapes, arrows
- **validation**: `svg-infographics overlaps`, `svg-infographics alignment`, `svg-infographics connectors`

## Steps

1. **Read the SVG** and its grid comment to understand intended layout

2. **Run diagnostics**:
   - `svg-infographics overlaps --svg {file}` - bounding box violations
   - `svg-infographics alignment --svg {file}` - grid snap, rhythm, topology
   - `svg-infographics connectors --svg {file}` - connector quality

3. **Apply fixes directly** (destructive):
   - Reposition overlapping elements using grid coordinates
   - Fix vertical rhythm (consistent y-increments)
   - Fix horizontal alignment (shared x values)
   - Adjust card padding (10px+ from edges)
   - Recalculate arrow geometry with `svg-infographics connector`
   - Use `svg-infographics primitives <shape>` for exact anchor coordinates when repositioning
   - Update grid comment to match actual positions

4. **Re-run validation** to confirm resolution

5. **Optional**: `svg-infographics overlaps --inject-bounds` for visual bbox overlay, then `--strip-bounds` after verification

6. **Report**: fixes applied, before/after violation counts

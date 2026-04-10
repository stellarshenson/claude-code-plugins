---
description: Create SVG infographic(s) following the full grid-first design workflow
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, Skill, TaskCreate, TaskUpdate]
argument-hint: "describe the infographic, e.g. 'card grid showing 4 platform modules' or 'timeline of project milestones'"
---

# Create SVG Infographic

Create one or more SVG infographics following the mandatory 6-phase workflow. Each image goes through all phases sequentially - no batching.

## Task Tracking

**MANDATORY**: Create a task list at the start showing all phases for each image. Update task status as you progress. This is non-negotiable.

## Skills to apply

Read these skills before generating anything - they are the source of truth:

- **svg-standards**: Core design rules, grid layout, CSS classes, cards, arrows, typography
- **workflow**: 6-phase sequential process with gate checks
- **theme**: Palette approval and swatch generation
- **validation**: Checker tools and verification workflow

## Steps

1. **ASK the user**:
   - What infographic(s) to create? (type, content, purpose)
   - Target directory for output files?
   - Brand/theme? (existing swatch or new?)
   - Any specific style preferences?

2. **Create task list** with phases per image:
   - Phase 1: Research (read examples, confirm conventions)
   - Phase 2: Invisible Grid (Python-calculated, comment-only)
   - Phase 3: Scaffold (structural elements, no content)
   - Phase 4: Content (text, icons, legends)
   - Phase 5: Finishing (arrows verified, description comment)
   - Phase 6: Validation (run all checkers)

3. **Theme check**: If no approved swatch exists for this brand, run theme approval workflow first

4. **Per image** - execute all 6 phases sequentially:
   - Read 3-5 relevant examples from `examples/`
   - Calculate grid with `svg-infographics primitives` for exact anchor coordinates (Bash tool)
   - Build scaffold from grid positions using primitives for shapes and connectors
   - Add content at documented positions
   - Verify arrows and add finishing touches
   - Run `svg-infographics overlaps`, `svg-infographics contrast`, `svg-infographics alignment`, `svg-infographics css`
   - Classify every violation individually

5. **Report**: List created files, validation results, any remaining items

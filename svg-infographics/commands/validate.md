---
description: Run all SVG validation checks (validate, overlaps, contrast, alignment, connectors, css, collide) on one or more files. Triggers - "validate svg", "check svg", "audit svg", "validate infographic".
allowed-tools: [Read, Bash, Glob, Grep, Agent, TaskCreate, TaskUpdate]
argument-hint: "SVG file path or directory, e.g. 'docs/images/*.svg'"
---

# Validate SVG Infographics

Run the full validation suite on SVG files and report findings.

## Task Tracking

MANDATORY: create a task per checker per file. Track each validation run and classification as separate tasks.

## Steps

1. **Identify targets**: glob for SVG files in the specified path

2. **Run all checkers in parallel** (per file):
   - `svg-infographics validate <file>` — XML well-formedness, viewBox, empty paths
   - `svg-infographics overlaps --svg <file>` — text/shape overlap, container overflow, callout collisions
   - `svg-infographics contrast --svg <file>` — WCAG 2.1 light + dark
   - `svg-infographics alignment --svg <file>` — grid snap, rhythm, topology
   - `svg-infographics connectors --svg <file>` — dead ends, edge-snap, chamfers
   - `svg-infographics css --svg <file>` — inline fills, forbidden colours, dark mode
   - `svg-infographics collide --svg <file>` — pairwise connector intersections

3. **Classify findings** per the fail-first rule:
   - Every finding is a real defect until individually defended
   - No bulk dismissals
   - Each classified as: Fixed / Accepted / Checker limitation

4. **Generate `verification_checklist.md`** (if issues found):
   ```markdown
   - [ ] `<filename>` | `"<text>"` | <ratio/overlap%> | <mode>
     - **Root cause**: <description>
     - **Fix**: <specific action>
   ```

5. **Report summary**: files checked, pass/fail counts, top issues to fix

## Skill applied

The spawned `svg-designer` agent (fork context) reads `references/validation.md` for checker usage, severity ladder (HARD FAIL / SOFT / HINT), justification rules, pre-delivery checklist. For heavy validation work across many files, spawn `Agent(subagent_type="svg-designer", prompt="Validate <paths>. Run full checker suite. Classify findings.")` to keep main session responsive.

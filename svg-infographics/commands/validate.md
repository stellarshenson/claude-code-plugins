---
description: Run all SVG validation checks (overlaps, contrast, alignment, connectors) on one or more files
allowed-tools: [Read, Bash, Glob, Grep, Agent, TaskCreate, TaskUpdate]
argument-hint: "SVG file path or directory, e.g. 'docs/images/*.svg'"
---

# Validate SVG Infographics

Run the full validation suite on SVG files and report findings.

## Task Tracking

**MANDATORY**: Create a task per checker per file. Track each validation run and classification as separate tasks.

## Skills to apply

- **validation**: All checker tools, fail-first rule, verification workflow

## Steps

1. **Identify targets**: Glob for SVG files in the specified path

2. **Run all checkers in parallel** (per file):
   - `svg-infographics overlaps --svg {file}`
   - `svg-infographics contrast --svg {file}`
   - `svg-infographics alignment --svg {file}`
   - `svg-infographics connectors --svg {file}`
   - `svg-infographics css --svg {file}`

3. **Classify findings** per the fail-first rule:
   - Every finding is a real defect until individually defended
   - No bulk dismissals
   - Each classified as: Fixed / Accepted / Checker limitation

4. **Generate verification_checklist.md** (if issues found):
   ```markdown
   - [ ] `<filename>` | `"<text>"` | <ratio/overlap%> | <mode>
     - **Root cause**: <description>
     - **Fix**: <specific action>
   ```

5. **Report summary**: files checked, pass/fail counts, top issues to fix

---
description: Run the consolidated SVG validation gate (finalize - all checkers in one call) on one or more files. Triggers - "validate svg", "check svg", "audit svg", "validate infographic".
allowed-tools: [Read, Bash, Glob, Grep, Agent, TaskCreate, TaskUpdate]
argument-hint: "SVG file path or directory, e.g. 'docs/images/*.svg'"
---

# Validate SVG Infographics

Run the consolidated validation gate on SVG files and report findings.

## Task Tracking

Create ONE task per finalize run (not per checker - finalize runs all checkers internally).

## Steps

1. **Identify targets**: glob for SVG files in the specified path

2. **Run the consolidated gate** - one call for the whole set:

   ```bash
   svg-infographics finalize <file1> [<file2> …]        # all checkers, HARD/SOFT tiers
   svg-infographics finalize <file1> --json             # machine-readable report
   ```

   finalize runs validate, overlaps, connectors, contrast, collide, alignment
   and css internally. Do NOT invoke the seven checkers separately - drill
   into a single checker (`svg-infographics overlaps --svg <file>` etc.) only
   when a specific finding needs more detail.

3. **Batch-fix protocol**: fix ALL findings in one editing pass, re-run
   finalize ONCE. Hard cap 3 iterations; report residuals and stop.

4. **Classify findings**:
   - HARD findings: real defects until individually defended (Fixed / Accepted / Checker limitation)
   - SOFT findings: fix what is cheap, acknowledge remaining layers with `--ack-class SOFT-<LAYER>='reason'`

5. **Generate `verification_checklist.md`** (if issues found):
   ```markdown
   - [ ] `<filename>` | `"<text>"` | <ratio/overlap%> | <mode>
     - **Root cause**: <description>
     - **Fix**: <specific action>
   ```

6. **Report summary**: files checked, hard/soft counts per file, top issues to fix

## Skill applied

The spawned `svg-designer` agent (fork context) reads `references/validation.md` for checker usage, severity ladder (HARD FAIL / SOFT / HINT), justification rules, pre-delivery checklist. For heavy validation work across many files, spawn `Agent(subagent_type="svg-designer", prompt="Validate <paths>. Run finalize, batch-fix, classify findings.")` to keep main session responsive.

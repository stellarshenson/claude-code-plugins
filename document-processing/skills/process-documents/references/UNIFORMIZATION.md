# Uniformization Methodology

Uniformization ensures every output document meets consistent, measurable quality standards. Rules are task-specific but follow a common structure.

## Rule Design Principles

Each uniformization rule has:
- **ID**: Sequential identifier (R1, R2, R3...)
- **Name**: Descriptive short name
- **Criteria**: Measurable conditions that can be checked programmatically or by inspection
- **Examples**: What a violation looks like and how to fix it
- **Priority**: Rules are ordered by importance - structural first, content second, formatting last

## Standard Rule Categories

When generating task-specific rules, draw from these categories:

### Length & Scope
- Word count range (minimum-maximum)
- Section count requirements
- Depth of coverage per topic
- Brevity preference (always prefer shorter within range)

### Perspective & Voice
- Whose perspective (first person, third person, neutral)
- Tone (formal/informal, legal/conversational)
- Forbidden self-references or bias markers
- Language requirements (Polish, English, bilingual)

### Content Focus
- What to include (mandatory elements)
- What to exclude (forbidden content)
- What to emphasize (weight distribution)
- Topical boundaries (stay within scope)

### Structure
- Required sections and their order
- Heading format and nesting depth
- Entry format (for lists, timelines, catalogues)
- Cross-reference format

### Formatting
- Paragraph spacing
- Encoding (UTF-8)
- Link policy (allowed/forbidden)
- Citation format
- Date format consistency
- Typography rules (no em-dashes, no arrow symbols)

### Grounding
- Minimum source references per claim
- Citation format requirements
- Handling of unverified claims
- Required disclaimer language

## Uniformization Checklist Template

Generate a task-specific checklist following this format:

```markdown
# Uniformization Checklist: <task-name>

## R1: <Rule Name>
- [ ] <Specific measurable criterion>: <MEASURED VALUE>
- [ ] <Specific measurable criterion>: <MEASURED VALUE>
- [ ] In compliance: YES/NO
- [ ] Action: [<specific correction needed> / OK]

## R2: <Rule Name>
- [ ] <Specific measurable criterion>: <MEASURED VALUE>
- [ ] <Violation examples found>: [list or NONE]
- [ ] In compliance: YES/NO
- [ ] Action: [<specific correction needed> / OK]

...

## Summary
| Rule | Status | Action Required |
|------|--------|-----------------|
| R1   | PASS/FAIL | description or N/A |
| R2   | PASS/FAIL | description or N/A |
```

## Execution Process

### A. Create Checklist
Evaluate the draft against each rule. For every rule, measure the actual value (word count, violation count, pattern matches) and compare against the threshold. Record findings.

### B. Execute Corrections
Apply all required changes identified in the checklist. Work through rules in priority order (structural fixes first, then content, then formatting). Each correction should reference the specific rule it addresses.

### C. Re-evaluate
After corrections, re-run the full checklist on the corrected document. Update all measurements. Every rule must show PASS status before the document can move to `3-output/`.

If any rule still fails after corrections, iterate: identify the remaining issue, apply targeted fix, re-evaluate that specific rule.

## Task-Specific Rule Generation

When generating INSTRUCTIONS.md for a new task, derive rules from:

1. **User's stated quality criteria** - what they said matters during objective refinement
2. **Domain conventions** - legal documents have citation requirements, timelines need chronological consistency
3. **Output format requirements** - a timeline has different rules than a narrative statement
4. **Project-level rules** - from `.claude/CLAUDE.md` (typography standards, markdown standards)

Rules must be specific enough to be checkable. Avoid vague rules like "ensure quality" - instead specify "each timeline entry must contain a date in YYYY-MM-DD format" or "no entry exceeds 50 words".

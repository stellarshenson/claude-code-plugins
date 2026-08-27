# Folder Structure Convention

Standard three-folder convention for document processing tasks.

## Directory Layout

```
project-root/
  1-input/                    <- Source documents (NEVER modify)
  2-wip/                      <- Work in progress
    <task-name>/              <- Per-task subfolder
      README.md               <- Manifest of artifacts
      <task-name>-assumptions.md
      <task-name>-grounding-report.md
      <task-name>-uniformization-checklist.md
      <task-name>-draft-v1.md
      <task-name>-draft-v2.md
  3-output/                   <- Final documents only
    README.md                 <- Manifest of deliverables
  4-references/               <- Reference materials and universal facts
    examples/                 <- Example outputs for format guidance
    facts/                    <- Verified universal facts (legal provisions, standards)
```

## Rules

**1-input/** read-only. Never create, modify, delete files here. Source documents stay untouched through whole workflow.

**2-wip/** organized by task. Each workflow invocation creates subfolder named after task. All intermediate artifacts live here - drafts, assumptions registers, grounding reports, uniformization checklists, versioned iterations.

**3-output/** holds only final, reviewed, quality-checked documents. No drafts, no WIP artifacts. Document moves here only after passing all uniformization checks.

**4-references/** holds reference materials supporting workflow. Two subfolders:
- `examples/` - example output documents showing expected format, structure, style. Format guidance only, never source material or content to copy
- `facts/` - verified universal facts independent of any single source document. Legal provisions, statutory articles, court precedent summaries, scientific consensus statements. Serve as grounding anchors needing no per-document verification

## Naming Conventions

**Task name**: kebab-case derived from the objective
- `timeline-reconstruction`
- `court-statement-draft`
- `evidence-catalogue`

**WIP artifacts**: `<task-name>-<artifact-type>.md`
- `timeline-reconstruction-assumptions.md`
- `timeline-reconstruction-grounding-report.md`
- `timeline-reconstruction-uniformization-checklist.md`

**Draft versions**: `<task-name>-draft-v<N>.md`
- `timeline-reconstruction-draft-v1.md`
- `timeline-reconstruction-draft-v2.md`

**Output documents**: descriptive filename matching the objective
- `timeline.md`
- `court-statement.md`

## Manifest Format

Both WIP and output folders use a README.md manifest:

```markdown
# <Folder Purpose>

## Documents

| Document | Purpose | Status | Last Updated |
|----------|---------|--------|--------------|
| file.md  | Description | Draft/Final | YYYY-MM-DD |
```

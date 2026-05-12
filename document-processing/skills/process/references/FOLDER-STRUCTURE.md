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

**1-input/** is read-only. Never create, modify, or delete files here. All source documents remain untouched throughout the processing workflow.

**2-wip/** is organized by task. Each invocation of the processing workflow creates a subfolder named after the task. All intermediate artifacts live here - drafts, assumptions registers, grounding reports, uniformization checklists, and versioned iterations.

**3-output/** contains only final, reviewed, quality-checked documents. No drafts, no WIP artifacts. A document moves here only after passing all uniformization checks.

**4-references/** contains reference materials that support the processing workflow. Two subfolders:
- `examples/` - example output documents showing expected format, structure, and style. Used as format guidance only, never as source material or content to copy
- `facts/` - verified universal facts independent of any single source document. Legal provisions, statutory articles, court precedent summaries, scientific consensus statements. These serve as grounding anchors that do not need per-document verification

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

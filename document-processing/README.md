# document-processing

Structured document processing plugin for Claude Code. Turns raw source material in `1-input/` into verified, quality-controlled outputs in `3-output/` through a three-phase workflow (analyze and draft, verify and ground, uniformize and deliver) with full traceability from every claim back to its source.

Unlike ad-hoc summarization, this plugin generates a tailored processing program (`INSTRUCTIONS.md` + `BENCHMARK.md`) for the specific objective, enforces explicit phase gates, and ships a complete PDF manipulation toolkit alongside a dedicated validator for grounding and compliance audits.

## Installation

```bash
/plugin marketplace add stellarshenson/claude-code-plugins
/plugin install document-processing@stellarshenson-marketplace
```

## Commands (user-invoked)

| Command | What it does |
|---------|-------------|
| `/document-processing:run` | Full workflow: objective refinement -> `INSTRUCTIONS.md` -> `BENCHMARK.md` -> scaffold WIP -> execute three phases -> deliver |
| `/document-processing:update` | Update an existing output with new sources, corrections, rule changes, or re-verification against updated source material |
| `/document-processing:validate` | Validate a document against its source for grounding, then check tone, style, length, and format compliance |

## Skills (auto-triggered)

| Skill | Triggers when |
|-------|--------------|
| `process-documents` | Processing, analyzing, synthesizing, extracting, reconstructing, or transforming documents from `1-input/` into structured outputs in `3-output/` |
| `validate-document` | Validating, verifying, or auditing a document against source material for grounding and tone/style/format compliance |
| `pdf` | Comprehensive PDF toolkit - extraction, merging, splitting, form filling with pypdf, pdfplumber, and reportlab |
| `pdf-pro` | Production-ready PDF workflows - complex forms, table extraction, OCR, batch processing, validation with error handling and logging |

## Example usage

```
/document-processing:run synthesize expert opinions into unified position paper
```

The `process-documents` skill walks through objective refinement, generates `INSTRUCTIONS.md` and `BENCHMARK.md` for user approval, scaffolds a WIP folder under `2-wip/<task-name>/`, then executes the three-phase workflow (analyze and draft, verify and ground, uniformize and deliver) before evaluating the result against `BENCHMARK.md` and promoting it to `3-output/`.

## How it works

The plugin operates over a fixed project layout: `1-input/` holds read-only source material, `2-wip/<task-name>/` holds per-task drafts and reports, `3-output/` holds final delivered documents, and `4-references/` holds examples and verified facts used as grounding anchors. Every intermediate artifact stays in WIP until all rules pass. See `skills/process-documents/references/FOLDER-STRUCTURE.md` for the full convention.

Grounding validation classifies every factual claim against its source (direct quote, paraphrase, inference, interpretation, or unsupported) and records confirmed, unconfirmed, and contradicted counts in a grounding report. See `skills/process-documents/references/GROUNDING.md` for the complete methodology.

Uniformization applies task-specific measurable rules (R1, R2, R3...) derived from stated quality criteria and project-level standards, executed in priority order until every rule passes. See `skills/process-documents/references/UNIFORMIZATION.md` for rule categories.

The PDF toolkit covers both a library-focused guide (`pdf`) and production-ready scripts with CLI, logging, and error handling (`pdf-pro`) for forms, tables, OCR, and batch operations. See `skills/pdf-pro/FORMS.md`, `skills/pdf-pro/TABLES.md`, and `skills/pdf-pro/OCR.md` for the advanced workflows.

## Documentation

- `skills/process-documents/SKILL.md` - five-phase execution flow and phase gates
- `skills/process-documents/references/FOLDER-STRUCTURE.md` - folder convention
- `skills/process-documents/references/WORKFLOW.md` - three-phase execution detail
- `skills/process-documents/references/GROUNDING.md` - claim classification and verification rules
- `skills/process-documents/references/UNIFORMIZATION.md` - rule categories and generation template
- `skills/validate-document/SKILL.md` - validation audit phases
- `skills/pdf/SKILL.md` - PDF library reference
- `skills/pdf-pro/SKILL.md` - production PDF scripts and workflows

# document-processing

Structured document processing plugin for Claude Code. Turns raw source material in `1-input/` into verified, quality-controlled outputs in `3-output/` through a three-phase workflow (analyze and draft, verify and ground, uniformize and deliver) with full traceability from every claim back to its source.

Unlike ad-hoc summarization, this plugin generates a tailored processing program (`INSTRUCTIONS.md` + `BENCHMARK.md`) for the specific objective, enforces explicit phase gates, and ships a complete PDF manipulation toolkit alongside a dedicated validator for grounding and compliance audits.

## Grounding CLI

Ships the `document-processing` CLI with a three-layer lexical grounder plus an optional fourth semantic layer. Every hit returns line / column / paragraph / page / context snippet — the agent cites precisely without rereading the source. **Saves tokens: measured 64-86% reduction vs batched generative grounding** on real sources (SVG Medium article, Liu 2023 paper).

| Layer | What it catches | Dep |
|-------|-----------------|-----|
| Exact (regex) | Whitespace-tolerant verbatim quotes | core |
| Fuzzy (Levenshtein) | Near-verbatim paraphrases (char similarity ≥ threshold) | core |
| BM25 (topical) | Same key terms, different word order | core |
| Semantic (E5 + FAISS) | Same meaning, different wording AND different terms | opt-in |

The fourth layer is off by default — it pulls `torch`, `transformers`, `faiss-cpu`, `pyarrow` and downloads a ~120 MB retrieval model. Enable only when lexical layers leave too many UNCONFIRMED claims.

### Install (core)

```bash
pip install stellars-claude-code-plugins
document-processing --help
```

### Enable semantic (optional, opt-in)

```bash
pip install 'stellars-claude-code-plugins[semantic]'
document-processing setup                 # interactive prompt, writes settings
```

Settings live at `./.stellars-plugins/settings.json` (project-local, sibling to `.claude/`). Default model: `intfloat/multilingual-e5-small` (118M params, multilingual, trained for retrieval).

### Usage

```bash
# Single claim, three-layer default
document-processing ground \
  --claim "Kubernetes runs on 12 nodes" \
  --source docs/source.md \
  --threshold 0.85 --bm25-threshold 0.5

# Batch, all four layers including semantic
document-processing ground-many \
  --claims validation/claims.json \
  --source docs/source.md \
  --output validation/grounding-report.md \
  --semantic on --semantic-threshold 0.85
```

Output includes all layer scores per claim, the winning passage, and location metadata. See `skills/validate-document/SKILL.md` for how the agent should read the output (including "never blindly trust scores — verify via the pointer").

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

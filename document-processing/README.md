# document-processing

Structured document processing plugin for Claude Code. Takes input documents, processes them through a verified workflow (analyze, draft, ground, uniformize), and produces quality-controlled outputs with full source traceability.

## Skills (auto-triggered)

| Skill | Triggers when |
|-------|--------------|
| `process-documents` | Processing, analyzing, synthesizing, or transforming documents from inputs to outputs |
| `validate-document` | Validating a document against source material for grounding and compliance |
| `pdf` | Working with PDFs - extraction, merging, splitting, form filling |
| `pdf-pro` | Production PDF workflows - tables, OCR, batch operations, complex forms |

## Commands (user-invoked)

| Command | What it does |
|---------|-------------|
| `/document-processing:run` | Full workflow: objective refinement -> INSTRUCTIONS.md -> BENCHMARK.md -> scaffold -> execute |
| `/document-processing:update` | Update existing output with new sources, corrections, or re-verification |
| `/document-processing:validate` | Validate a document against source material (grounding + compliance) |

## Workflow

```
/document-processing:run synthesize all expert opinions into position paper
```

The plugin:
1. Reads `1-input/` to catalogue source material
2. Asks clarifying questions (end state, quality criteria, constraints)
3. Generates `INSTRUCTIONS.md` (processing program) and `BENCHMARK.md` (evaluation)
4. Scaffolds `2-wip/<task-name>/` working directory
5. Executes three phases: Analyze & Draft -> Verify & Ground -> Uniformize & Deliver
6. Final output to `3-output/`

## Folder Structure

```
1-input/          # Source documents (read-only, never modify)
2-wip/            # Working artifacts per task
3-output/         # Final delivered documents
4-references/     # Examples and universal facts
  examples/       # Format guidance (never copy content)
  facts/          # Grounding anchors (legal provisions, precedents)
```

## Grounding

Every factual claim in output documents is traceable to a specific passage in source documents. Claims are categorized as CONFIRMED, UNCONFIRMED, CONTRADICTED, INFERRED, or NOT APPLICABLE. Grounding score = confirmed / total factual claims.

## PDF Processing

Two PDF skills for different complexity levels:
- **pdf**: Basic operations with pypdf - merge, split, extract text, fill forms with annotations. Includes utility scripts for form analysis and filling
- **pdf-pro**: Production workflows with pdfplumber - table extraction, OCR, complex forms, batch processing with validation

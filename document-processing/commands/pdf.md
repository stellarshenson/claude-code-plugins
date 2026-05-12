---
description: PDF toolkit - extract text/tables, create/merge/split, fill and flatten forms, OCR scanned PDFs, batch-process
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Skill]
argument-hint: "what to do, e.g. 'fill this form', 'extract tables from report.pdf', 'OCR scanned.pdf'"
---

# PDF

Invoke the `document-processing:pdf` skill. It carries the PDF library reference (pypdf, pdfplumber, reportlab), the CLI tools (pdftotext, qpdf, pdftk, pdfimages), the pre-built scripts under `scripts/` (form analysis and fill, bounding-box checks, page-to-image conversion, validation images), and topic guides for forms, table extraction, and OCR.

## Common tasks

- Extract text / tables from a PDF
- Create a PDF, merge several, split into pages, rotate, watermark, password-protect
- Analyze a form's fields, fill it from data, flatten it
- OCR a scanned / image-only PDF
- Batch-process many PDFs with proper exit codes

The skill auto-triggers on PDF work; this command is the explicit entry point.

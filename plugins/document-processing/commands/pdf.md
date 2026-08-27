---
description: PDF toolkit - extract text/tables, create/merge/split, fill and flatten forms, OCR scanned PDFs, batch-process
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Skill]
argument-hint: "what to do, e.g. 'fill this form', 'extract tables from report.pdf', 'OCR scanned.pdf'"
---

# PDF

Invoke `document-processing:pdf` skill. Carries PDF library reference (pypdf, pdfplumber, reportlab), CLI tools (pdftotext, qpdf, pdftk, pdfimages), pre-built scripts under `scripts/` (form analysis and fill, bounding-box checks, page-to-image conversion, validation images), plus topic guides for forms, table extraction, OCR.

## Common tasks

- Extract text / tables from PDF
- Create PDF, merge several, split into pages, rotate, watermark, password-protect
- Analyze form's fields, fill from data, flatten
- OCR scanned / image-only PDF
- Batch-process many PDFs with proper exit codes

Skill auto-triggers on PDF work; this command = explicit entry point.

---
description: PDF toolkit - extract text/tables, create/merge/split, fill and flatten forms, OCR scanned PDFs, batch-process
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Skill]
argument-hint: "what to do, e.g. 'fill this form', 'extract tables from report.pdf', 'OCR scanned.pdf'"
---

# PDF

Invoke `document-processing:pdf` skill. Carries PDF library reference (pypdf, pdfplumber, reportlab), CLI tools (pdftotext, qpdf, pdftk, pdfimages), pre-built scripts under `scripts/` (form analysis and fill, bounding-box checks, page-to-image conversion, validation images), plus topic guides for forms, table extraction, OCR.

## Toolchain gate (MANDATORY - run before anything else)

Run this first, every session, before any other work. The upgrade always runs; a version mismatch blocks.

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && { echo "STALE: library $LIB != plugin $PLUG - refusing to run on a mismatched CLI; re-run the upgrade"; exit 1; }
echo "toolkit $LIB"
```

Both branches exit non-zero and neither is advisory: an absent library (`FATAL`) and a version mismatch (`STALE`). A mismatch means the CLI is not the one this file was written against, so its documented flags and rules are unverified. Report the line and stop; do not work around it.

## Common tasks

- Extract text / tables from PDF
- Create PDF, merge several, split into pages, rotate, watermark, password-protect
- Analyze form's fields, fill from data, flatten
- OCR scanned / image-only PDF
- Batch-process many PDFs with proper exit codes

Skill auto-triggers on PDF work; this command = explicit entry point.

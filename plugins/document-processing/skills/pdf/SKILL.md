---
name: pdf
description: Comprehensive PDF toolkit - extract text and tables, create / merge / split PDFs, fill and flatten forms, OCR scanned PDFs, batch-process many PDFs with error handling and exit codes. When Claude needs to fill in a PDF form or programmatically process, generate, analyze, or OCR PDF documents - one-off or at scale.
license: Proprietary. LICENSE.txt has complete terms
---

# PDF Processing Guide

## Toolchain gate (MANDATORY - run before anything else)

Run this first, every session, before any other work. The upgrade always runs; a version mismatch blocks.

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
OLDER=$(printf '%s\n%s\n' "$LIB" "$PLUG" | sort -V | head -1)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && [ "$OLDER" = "$LIB" ] && { echo "STALE: library $LIB older than plugin $PLUG - refusing to run on an outdated CLI; re-run the upgrade"; exit 1; }
echo "toolkit $LIB"
```

Both branches exit non-zero and neither is advisory: an absent library (`FATAL`) and a version mismatch (`STALE`). A mismatch means the CLI is not the one this file was written against, so its documented flags and rules are unverified. Report the line and stop; do not work around it.

## Overview

PDF ops via Python libraries, pre-built scripts, CLI tools. Basic operations (pypdf, pdfplumber, reportlab, pdftotext, qpdf, pdftk), advanced features, JS libraries: see `reference.md`. Form filling: `forms.md` (and `forms-production.md` for production form pipeline). OCR of scanned PDFs: `ocr.md`. Advanced table extraction: `tables.md`. Pre-built scripts live in `scripts/`.

## Quick Start

```python
from pypdf import PdfReader, PdfWriter

# Read a PDF
reader = PdfReader("document.pdf")
print(f"Pages: {len(reader.pages)}")

# Extract text
text = ""
for page in reader.pages:
    text += page.extract_text()
```

## Common Tasks

Watermarks, image extraction, password protection, and the pypdf / pdfplumber / reportlab / CLI basics: `reference.md`, Basic operations.

### Extract text from scanned PDFs

The plugin ships an offline OCR engine - OnnxTR detection + recognition, installed with the package (`onnxtr[cpu-headless]`), no system tesseract. `document-processing ground --ocr-lang <code> --source scanned.pdf ...` OCRs any source whose text extraction is sparse, writes the candidate as `<stem>.ocr.txt` beside it, and reads that sibling first on every later run. The candidate opens with a `# OCR candidate for` header; grounding raises `OCR-CANDIDATE` while it is there, and deleting the header after review marks the text accepted. Standalone use and the tesseract fallback: `ocr.md`.

## Quick Reference

| Task | Best Tool | Command/Code |
|------|-----------|--------------|
| Merge PDFs | pypdf | `writer.add_page(page)` |
| Split PDFs | pypdf | One page per file |
| Extract text | pdfplumber | `page.extract_text()` |
| Extract tables | pdfplumber | `page.extract_tables()` |
| Create PDFs | reportlab | Canvas or Platypus |
| Command line merge | qpdf | `qpdf --empty --pages ...` |
| OCR scanned PDFs | bundled OnnxTR via `document-processing ground --ocr-lang` | caches `<stem>.ocr.txt`; tesseract fallback in `ocr.md` |
| Fill PDF forms | pdf-lib or pypdf (see forms.md) | See forms.md |

## Pre-built scripts

`scripts/` holds ready-to-run helpers - all expose `--help`, validate inputs, return automation-friendly exit codes:

- `analyze_form.py input.pdf [--output fields.json] [--verbose]` - extract all form fields, types, positions
- `extract_form_field_info.py` - detailed per-field metadata
- `check_fillable_fields.py` - list fillable fields and their state
- `fill_fillable_fields.py` - fill AcroForm fields from data
- `fill_pdf_form_with_annotations.py` - fill forms that use annotations
- `check_bounding_boxes.py` (+ `check_bounding_boxes_test.py`) - verify text/element bounding boxes
- `convert_pdf_to_images.py` - rasterise pages to images (for OCR or visual diff)
- `create_validation_image.py` - render a page with overlays for visual QA

## Production patterns

For complex / high-volume PDF work, follow these conventions (carried over from production toolkit):

**Exit codes** (use across custom scripts, check them in automation):

```
0 - success
1 - file not found
2 - invalid input
3 - processing error
4 - validation error
```

**Batch processing** - process many PDFs, fail fast per file, keep going:

```python
import glob, subprocess
from pathlib import Path

for pdf_file in glob.glob("invoices/*.pdf"):
    out = Path("processed") / Path(pdf_file).name
    r = subprocess.run(["python", "scripts/convert_pdf_to_images.py", pdf_file, "--output", str(out)],
                       capture_output=True, text=True)
    if r.returncode == 0:
        print(f"ok: {pdf_file}")
    else:
        print(f"fail ({r.returncode}): {pdf_file} - {r.stderr.strip()}")
```

**Best practices**: validate inputs before processing; wrap custom scripts in try/except; log every operation; test on sample PDFs before a production run; set timeouts on long-running ops; back up originals before modification; for PDFs >50MB stream page-by-page (`for page in pdf.pages: ...`) rather than loading the whole file.

**OCR**: the bundled engine installs with the package; tesseract is the fallback for a platform or language it does not cover. See `ocr.md`.

## Topic guides

- Advanced pypdfium2 usage, JavaScript libraries (pdf-lib), troubleshooting: `reference.md`
- PDF form filling (basics): `forms.md`
- PDF form processing in production (analysis, validation, multi-page, flattening): `forms-production.md`
- Table extraction (multi-page, merged cells, nested tables, CSV/Excel export): `tables.md`
- OCR of scanned PDFs (bundled OnnxTR engine and its `<stem>.ocr.txt` cache; tesseract fallback with language support, preprocessing, confidence scoring, batch OCR): `ocr.md`

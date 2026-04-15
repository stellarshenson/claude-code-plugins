---
name: PDF Processing Pro
description: Production-ready PDF processing with forms, tables, OCR, validation, and batch operations. Use when working with complex PDF workflows in production environments, processing large volumes of PDFs, or requiring robust error handling and validation.
---

# PDF Processing Pro

Production-ready PDF toolkit. Pre-built scripts, error handling, complex workflow support.

## Quick start

### Extract text from PDF

```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    text = pdf.pages[0].extract_text()
    print(text)
```

### Analyze PDF form (using included script)

```bash
python scripts/analyze_form.py input.pdf --output fields.json
# Returns: JSON with all form fields, types, and positions
```

### Fill PDF form with validation

```bash
python scripts/fill_form.py input.pdf data.json output.pdf
# Validates all fields before filling, includes error reporting
```

### Extract tables from PDF

```bash
python scripts/extract_tables.py report.pdf --output tables.csv
# Extracts all tables with automatic column detection
```

## Features

### ✅ Production-ready scripts

All scripts include:
- **Error handling**: graceful failures, detailed error messages
- **Validation**: input validation, type checking
- **Logging**: configurable, timestamped
- **Type hints**: full annotations for IDE support
- **CLI interface**: `--help` flag on all scripts
- **Exit codes**: proper codes for automation

### ✅ Comprehensive workflows

- **PDF Forms**: complete form processing pipeline
- **Table Extraction**: advanced detection and extraction
- **OCR Processing**: scanned PDF text extraction
- **Batch Operations**: efficient multi-PDF processing
- **Validation**: pre/post-processing checks

## Advanced topics

### PDF Form Processing

Complete form workflows:
- Field analysis and detection
- Dynamic form filling
- Validation rules
- Multi-page forms
- Checkbox and radio button handling

See [FORMS.md](FORMS.md)

### Table Extraction

Complex extraction:
- Multi-page tables
- Merged cells
- Nested tables
- Custom detection
- CSV/Excel export

See [TABLES.md](TABLES.md)

### OCR Processing

Scanned PDFs and image-based documents:
- Tesseract integration
- Language support
- Image preprocessing
- Confidence scoring
- Batch OCR

See [OCR.md](OCR.md)

## Included scripts

### Form processing

**analyze_form.py** - extract form field info
```bash
python scripts/analyze_form.py input.pdf [--output fields.json] [--verbose]
```

**fill_form.py** - fill PDF forms with data
```bash
python scripts/fill_form.py input.pdf data.json output.pdf [--validate]
```

**validate_form.py** - validate form data before filling
```bash
python scripts/validate_form.py data.json schema.json
```

### Table extraction

**extract_tables.py** - extract tables to CSV/Excel
```bash
python scripts/extract_tables.py input.pdf [--output tables.csv] [--format csv|excel]
```

### Text extraction

**extract_text.py** - extract text, preserve formatting
```bash
python scripts/extract_text.py input.pdf [--output text.txt] [--preserve-formatting]
```

### Utilities

**merge_pdfs.py** - merge multiple PDFs
```bash
python scripts/merge_pdfs.py file1.pdf file2.pdf file3.pdf --output merged.pdf
```

**split_pdf.py** - split PDF into individual pages
```bash
python scripts/split_pdf.py input.pdf --output-dir pages/
```

**validate_pdf.py** - validate PDF integrity
```bash
python scripts/validate_pdf.py input.pdf
```

## Common workflows

### Workflow 1: Process form submissions

```bash
# 1. Analyze form structure
python scripts/analyze_form.py template.pdf --output schema.json

# 2. Validate submission data
python scripts/validate_form.py submission.json schema.json

# 3. Fill form
python scripts/fill_form.py template.pdf submission.json completed.pdf

# 4. Validate output
python scripts/validate_pdf.py completed.pdf
```

### Workflow 2: Extract data from reports

```bash
# 1. Extract tables
python scripts/extract_tables.py monthly_report.pdf --output data.csv

# 2. Extract text for analysis
python scripts/extract_text.py monthly_report.pdf --output report.txt
```

### Workflow 3: Batch processing

```python
import glob
from pathlib import Path
import subprocess

# Process all PDFs in directory
for pdf_file in glob.glob("invoices/*.pdf"):
    output_file = Path("processed") / Path(pdf_file).name

    result = subprocess.run([
        "python", "scripts/extract_text.py",
        pdf_file,
        "--output", str(output_file)
    ], capture_output=True)

    if result.returncode == 0:
        print(f"✓ Processed: {pdf_file}")
    else:
        print(f"✗ Failed: {pdf_file} - {result.stderr}")
```

## Error handling

Consistent error patterns across all scripts:

```python
# Exit codes
# 0 - Success
# 1 - File not found
# 2 - Invalid input
# 3 - Processing error
# 4 - Validation error

# Example usage in automation
result = subprocess.run(["python", "scripts/fill_form.py", ...])

if result.returncode == 0:
    print("Success")
elif result.returncode == 4:
    print("Validation failed - check input data")
else:
    print(f"Error occurred: {result.returncode}")
```

## Dependencies

Required for all scripts:

```bash
pip install pdfplumber pypdf pillow pytesseract pandas
```

Optional for OCR:
```bash
# Install tesseract-ocr system package
# macOS: brew install tesseract
# Ubuntu: apt-get install tesseract-ocr
# Windows: Download from GitHub releases
```

## Performance tips

- **Batch processing** for multiple PDFs
- **Multiprocessing** via `--parallel` flag (where supported)
- **Cache extracted data** - avoid re-processing
- **Validate inputs early** - fail fast
- **Streaming** for large PDFs (>50MB)

## Best practices

1. **Validate inputs** before processing
2. **try-except** in custom scripts
3. **Log all operations** for debugging
4. **Test with sample PDFs** before production
5. **Set timeouts** on long-running operations
6. **Check exit codes** in automation
7. **Backup originals** before modification

## Troubleshooting

### Common issues

**"Module not found" errors**:
```bash
pip install -r requirements.txt
```

**Tesseract not found**:
```bash
# Install tesseract system package (see Dependencies)
```

**Memory errors with large PDFs**:
```python
# Process page by page instead of loading entire PDF
with pdfplumber.open("large.pdf") as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        # Process page immediately
```

**Permission errors**:
```bash
chmod +x scripts/*.py
```

## Getting help

All scripts support `--help`:

```bash
python scripts/analyze_form.py --help
python scripts/extract_tables.py --help
```

Detailed topic docs:
- [FORMS.md](FORMS.md) - complete form processing guide
- [TABLES.md](TABLES.md) - advanced table extraction
- [OCR.md](OCR.md) - scanned PDF processing

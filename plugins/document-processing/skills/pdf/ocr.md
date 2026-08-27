# PDF OCR Processing Guide

Extract text from scanned PDFs and image-based documents.

## Bundled engine (default)

The package ships an offline OCR engine - OnnxTR detection + recognition models via `onnxtr[cpu-headless]`, no system tesseract, weights fetched once on first use.

- **Through grounding** - `document-processing ground --ocr-lang <code> --source scanned.pdf ...` OCRs a source whose text extraction is sparse; without `--ocr-lang` the CLI stops and names the flag with a suggested language
- **Cache** - the candidate is always written as `<stem>.ocr.txt` next to the source, even when quality is `failed`, so there is a file to edit; later runs read that sibling before anything else
- **Review** - the file opens with a `# OCR candidate for` header. Grounding raises `OCR-CANDIDATE` while the header is present; read the text for transcription errors (numbers, names, technical terms), fix them, delete the header - that marks it accepted and the warning stops
- **Standalone** - `from stellars_claude_code_plugins.document_processing import ocr`, then `r = ocr.ocr_pdf(Path("scanned.pdf"), "en")` and `ocr.cache_ocr_candidate(Path("scanned.pdf"), r)` write the same sibling; `ocr.ocr_available()` reports whether the engine imports

## Fallback: tesseract

For a platform without an `onnxtr` wheel, or a language the bundled models do not cover.

### Quick start

```python
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

# Convert PDF to images
images = convert_from_path("scanned.pdf")

# Extract text from each page
for i, image in enumerate(images):
    text = pytesseract.image_to_string(image)
    print(f"Page {i+1}:\n{text}\n")
```

## Installation

### Install Tesseract

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

**Windows:**
Download from: https://github.com/UB-Mannheim/tesseract/wiki

### Install Python packages

```bash
pip install pytesseract pdf2image pillow
```

## Language support

```python
# English (default)
text = pytesseract.image_to_string(image, lang="eng")

# Spanish
text = pytesseract.image_to_string(image, lang="spa")

# Multiple languages
text = pytesseract.image_to_string(image, lang="eng+spa+fra")
```

Install more languages:
```bash
# macOS
brew install tesseract-lang

# Ubuntu
sudo apt-get install tesseract-ocr-spa tesseract-ocr-fra
```

## Image preprocessing

```python
from PIL import Image, ImageEnhance, ImageFilter

def preprocess_for_ocr(image):
    """Optimize image for better OCR accuracy."""

    # Convert to grayscale
    image = image.convert("L")

    # Increase contrast
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)

    # Denoise
    image = image.filter(ImageFilter.MedianFilter())

    # Sharpen
    image = image.filter(ImageFilter.SHARPEN)

    return image

# Usage
image = Image.open("scanned_page.png")
processed = preprocess_for_ocr(image)
text = pytesseract.image_to_string(processed)
```

## Best practices

1. **Preprocess images** for better accuracy
2. **Use right language** models
3. **Batch process** large documents
4. **Cache results** to skip re-processing
5. **Validate output** - OCR not 100% accurate
6. **Check confidence scores** for quality

## Production example

```python
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

def ocr_pdf(pdf_path, output_path):
    """OCR PDF and save to text file."""

    # Convert to images
    images = convert_from_path(pdf_path, dpi=300)

    full_text = []

    for i, image in enumerate(images, 1):
        print(f"Processing page {i}/{len(images)}")

        # Preprocess
        processed = preprocess_for_ocr(image)

        # OCR
        text = pytesseract.image_to_string(processed, lang="eng")
        full_text.append(f"--- Page {i} ---\n{text}\n")

    # Save
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(full_text))

    print(f"Saved to {output_path}")

# Usage
ocr_pdf("scanned_document.pdf", "extracted_text.txt")
```

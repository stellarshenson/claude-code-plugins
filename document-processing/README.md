# document-processing

Structured document processing plugin for Claude Code. Turns raw source material in `1-input/` into verified, quality-controlled outputs in `3-output/` through a three-phase workflow (analyze and draft, verify and ground, uniformize and deliver) with full traceability from every claim back to its source.

Unlike ad-hoc summarization, this plugin generates a tailored processing program (`INSTRUCTIONS.md` + `BENCHMARK.md`) for the specific objective, enforces explicit phase gates, ships a deterministic grounding CLI, and provides a complete PDF toolkit. There is exactly one verification flow - the `grounding` skill - and everything that needs grounding (the `validate` skill, the `process` skill's verify phase, the `update` skill's closing step) calls it rather than re-implementing it.

## Grounding CLI

Ships the `document-processing` CLI with a three-layer lexical grounder plus an optional fourth semantic layer. Every hit returns line / column / paragraph / page / context snippet — the agent cites precisely without rereading the source. **Saves tokens: measured 64-86% reduction vs batched generative grounding** on real sources (SVG Medium article, Liu 2023 paper).

### Data-science calibrated

The grounding classifier was tuned via a six-iteration `autobuild` cycle with
a composite benchmark score and 3-fold cross-validation on three held-out
academic papers (Liu 2023, Ye 2024, Han 2024 - 14 labelled claims each,
12 real + 2 fabricated). Final CV mean accuracy 1.0 with zero overfit
gap. Every tunable parameter (29 fields: per-layer weights, ramp
endpoints, voter thresholds, entity-penalty factor, adaptive-gap
classifier mode, percentile floor, etc.) is exposed in
`stellars_claude_code_plugins/document_processing/config.yaml` and
documented per field; override via `.stellars-plugins/config.yaml`
project-local. A `scripts/calibrate.py` grid-search and
`scripts/calibrate_cv.py` cross-validation harness are shipped for
re-tuning on new corpora.

Full optimisation record: program definition, benchmark formula,
hypothesis + falsifiers, per-iteration artefacts, forensic report,
CV results, and corpus data all archived under
[`references/grounding-optimisation/`](../references/grounding-optimisation/).

### Local domain calibration (Bayesian)

Grounding scores are domain-shaped - what counts as a confident semantic match on legal contracts differs from farm telemetry or multilingual product docs. The verdict can be **locally calibrated to your own corpus** with a Bayesian logistic model (bambi / PyMC) over the per-layer features, and the learned weights then live in your config so every run uses them with no fitting.

The meaning feature is the model- and language-portable `semantic_ratio`, so cross-lingual true matches (no word overlap) still confirm while topical fabrications do not. The fit yields a full posterior (uncertainty), updates incrementally as feedback arrives, and fuses hard labels with LLM-eval soft labels.

```bash
# 1. Calibrate from labelled evidence. Each record is grounded to extract its
#    feature vector, then the Bayesian model is fit and the posterior saved.
document-processing calibrate --action update \
  --evidence evidence.json --profile .stellars-plugins/calibrator.json --semantic on

# 2. Inspect the learned posterior (coefficient mean +/- sd).
document-processing calibrate --action show --profile .stellars-plugins/calibrator.json

# 3. Transfer the learned weights into the project config - grounding then uses
#    them with no fitting at run time.
document-processing config set-calibrator --profile .stellars-plugins/calibrator.json
document-processing config show
```

Evidence is a JSON list of `{claim, sources:[paths] (or source_text), label:0|1, lang?, weight?}`. `config set-calibrator` writes a `calibration:` block into `.stellars-plugins/config_document_processing.yaml`:

```yaml
calibration:
  engine: calibrated
  threshold: 0.5
  weights:
    Intercept: -3.1
    exact: 5.8
    semantic: 4.6
    bm25_recall: 2.4
    # ... one per layer / voter / entity-penalty feature
```

Pass `--from <existing-profile>` to `calibrate` for an **incremental** update - the previous posterior seeds the new fit (posterior-as-prior), so feedback accumulates instead of resetting. A worked end-to-end demo is in [`notebooks/calibration_demo.ipynb`](../notebooks/calibration_demo.ipynb).

| Layer | What it catches | Dep |
|-------|-----------------|-----|
| Exact (regex) | Whitespace-tolerant verbatim quotes | core |
| Fuzzy (Levenshtein) | Near-verbatim paraphrases (char similarity ≥ threshold) | core |
| BM25 (topical) | Same key terms, different word order | core |
| Semantic (E5 + FAISS) | Same meaning, different wording AND different terms | opt-in |

The 4th layer needs the `[semantic]` extra (`torch`, `transformers`, `faiss-cpu`, `pyarrow`) and a ~120 MB retrieval model on first use. The `grounding` skill treats semantic as the **default** and recommends enabling it on first run (`document-processing setup`); a bare package install ships it off so nothing surprise-downloads, and the user can decline at `setup` time. Lexical-only is the path you fall to when the user has deliberately opted out.

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

### Enable OCR (optional, opt-in)

```bash
pip install 'stellars-claude-code-plugins[ocr]'
# plus a system tesseract install:
apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-deu  # etc per language
# brew install tesseract tesseract-lang                         # macOS
```

Enables auto-OCR fallback for scanned PDFs that have no sibling text file. The agent supplies `--ocr-lang <code>` per run (`eng`, `deu`, `fra`, `chi_sim`, etc) - the tool never auto-detects language. Auto-OCR results are written as `<stem>.ocr.txt` next to the source with a header carrying quality stats (mean confidence, page count, language, timestamp). Without the `[ocr]` extras the tool falls back to a vision-OCR workflow - the agent reads the PDF via the Read tool, transcribes pages, saves to `<stem>.ocr.txt`, reruns. Either path produces the same sibling-file convention so subsequent grounding runs use the cached candidate without re-OCR.

**Native source formats** (no extras required): `.txt`, `.md`, `.rst`, `.pdf` (text), `.docx`, `.odt`, `.rtf`, `.html` - extracted directly. The stop-and-think warning-ack gate surfaces per-source warnings (`OCR-FALLBACK`, `OCR-CANDIDATE`, `OCR-FAILED`, `OCR-LANG-NEEDED`, `OCR-MISSING`, `SOURCE-SKIPPED`) the agent must ack with terse reasoning before grounding consumes the result.

### Usage

```bash
# Single claim, three-layer default
document-processing ground \
  --claim "Kubernetes runs on 12 nodes" \
  --source docs/source.md \
  --threshold 0.85 --bm25-threshold 0.5

# One document: extract claims, then ground them all
document-processing extract-claims --document docs/brief.md --output validation/claims.json
document-processing batch-ground \
  --claims validation/claims.json \
  --source docs/source.md \
  --output validation/grounding-report.md \
  --semantic on --semantic-threshold 0.85

# Many documents via manifest
document-processing batch-validate --source-map source_map.yaml --output-dir validation/

# Intra-document self-consistency
document-processing check-consistency --document docs/brief.md --output validation/consistency-report.md
```

Output includes all layer scores per claim, the winning passage, and location metadata. See `skills/grounding/SKILL.md` for how the agent should read the output (including "never blindly trust scores — verify via the pointer", the three core verdict rules, and the OCR fallback chain).

## Installation

```bash
/plugin marketplace add stellarshenson/claude-code-plugins
/plugin install document-processing@stellarshenson-marketplace
```

## Commands (user-invoked)

Each command pairs with a skill of the same name; the skill auto-triggers, the command is the explicit entry point.

| Command | What it does |
|---------|-------------|
| `/document-processing:process` | Build a deliverable from sources: objective refinement -> `INSTRUCTIONS.md` -> `BENCHMARK.md` -> scaffold `2-wip/` -> analyze & draft -> verify & ground -> uniformize & deliver to `3-output/` |
| `/document-processing:validate` | Validate a finished document against rules AND its source: grounding (delegated to the `grounding` skill) + tone/style/length/format/focus/custom-rule compliance |
| `/document-processing:grounding` | Pure grounding via the CLI - a single claim, one document's claims, or a batch via `source_map.yaml`. No compliance layer |
| `/document-processing:update` | Update an existing `3-output/` document (new source, corrections, rule changes), always re-running the grounding CLI on the changed content before declaring done |
| `/document-processing:pdf` | PDF toolkit - extract text/tables, create/merge/split, fill and flatten forms, OCR scanned PDFs, batch-process |

## Skills (auto-triggered)

| Skill | Triggers when |
|-------|--------------|
| `process` | Building a structured deliverable FROM sources - reconstruct a timeline, draft a statement, assemble a catalogue, synthesize a position paper. Generates a tailored `INSTRUCTIONS.md` + `BENCHMARK.md`. NOT for validating an existing doc (use `validate`) or bare grounding (use `grounding`) |
| `grounding` | Grounding claims against source(s) via the CLI - "ground", "grounding", "check grounding", "run batch-ground", "verify claims against a source". Pure grounding, no compliance. The canonical verification flow; `validate`, `process`, and `update` all call it |
| `validate` | Validating a document against rules and against its source - "validate document", "validate against rules", "check compliance and grounding", "audit document against source". Runs the `grounding` skill, then adds the compliance layer |
| `update` | Updating an existing `3-output/` document - "update the document", "add a new source to the timeline", "re-verify after sources changed", "apply corrections to the output". Ends with a mandatory CLI-grounding pass |
| `pdf` | PDF work - fill a form, extract text/tables, create/merge/split PDFs, OCR a scanned PDF, batch-process. Library reference + pre-built scripts + topic guides for forms, tables, OCR |

## Example usage

```
/document-processing:process synthesize expert opinions into unified position paper
```

The `process` skill walks through objective refinement, generates `INSTRUCTIONS.md` and `BENCHMARK.md` for user approval, scaffolds a WIP folder under `2-wip/<task-name>/`, then executes the three-phase workflow (analyze and draft, verify and ground, uniformize and deliver) before evaluating the result against `BENCHMARK.md` and promoting it to `3-output/`. The Verify & Ground phase invokes the `grounding` skill.

## How it works

The plugin operates over a fixed project layout: `1-input/` holds read-only source material, `2-wip/<task-name>/` holds per-task drafts and reports, `3-output/` holds final delivered documents, and `4-references/` holds examples and verified facts used as grounding anchors. Every intermediate artifact stays in WIP until all rules pass. See `skills/process/references/FOLDER-STRUCTURE.md` for the full convention.

Grounding is the single verification flow. The `grounding` skill runs the deterministic three-layer CLI (regex exact + Levenshtein fuzzy + BM25, plus optional semantic), reads the per-claim verdicts, applies three core rules (agreement beats magnitude; a numeric/entity contradiction is the final word; re-recommend semantic on struggle), handles the scanned-PDF OCR fallback chain, and writes a grounding report plus an intra-document self-consistency report. The `validate` skill wraps it and layers compliance on top; the `process` skill calls it from its verify phase; the `update` skill calls it as a mandatory closing step. The claim-classification methodology for the synthesis workflow (DIRECT QUOTE / PARAPHRASE / INFERENCE / INTERPRETATION / UNSUPPORTED, with HIGH/MEDIUM/LOW severity) is in `skills/process/references/GROUNDING.md`.

Uniformization applies task-specific measurable rules (R1, R2, R3...) derived from stated quality criteria and project-level standards, executed in priority order until every rule passes. See `skills/process/references/UNIFORMIZATION.md` for rule categories, and `examples/` for real, in-use rule-sets (a full `INSTRUCTIONS.md` plus a worked uniformization checklist) to load when helping a user author their own.

The PDF toolkit (`pdf` skill) covers a library-focused guide (pypdf, pdfplumber, reportlab), pre-built scripts under `skills/pdf/scripts/`, CLI tools (pdftotext, qpdf, pdftk, pdfimages), production patterns (exit codes, batch processing), and topic guides: `skills/pdf/forms.md` and `skills/pdf/forms-production.md` for form processing, `skills/pdf/tables.md` for advanced table extraction, `skills/pdf/ocr.md` for scanned PDFs, `skills/pdf/reference.md` for advanced/JS libraries and troubleshooting.

## Documentation

- `skills/process/SKILL.md` - four-phase build flow (objective refinement, program generation, benchmark generation, scaffolding, execution) and phase gates
- `skills/process/references/FOLDER-STRUCTURE.md` - folder convention
- `skills/process/references/WORKFLOW.md` - three-phase execution detail
- `skills/process/references/GROUNDING.md` - claim classification and verification rules for the synthesis workflow
- `skills/process/references/UNIFORMIZATION.md` - rule categories and generation template
- `examples/` - real validation rule-sets (`INSTRUCTIONS-example-preschool-transcriptions.md`, `uniformization-checklist-example.md`)
- `skills/grounding/SKILL.md` - the canonical grounding flow: CLI usage (single / document / batch), semantic-consent gate, OCR fallback chain, core verdict rules, status mapping, self-consistency check
- `skills/validate/SKILL.md` - validation: criteria gathering, grounding (via the `grounding` skill), compliance checklist, summary, corrected copy
- `skills/update/SKILL.md` - updating an existing output with a mandatory CLI-grounding closing step
- `skills/pdf/SKILL.md` - PDF library reference, pre-built scripts, production patterns; topic guides `forms.md`, `forms-production.md`, `tables.md`, `ocr.md`, `reference.md`

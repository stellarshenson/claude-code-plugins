# document-processing

Structured document processing plugin for Claude Code. Turns raw source material in `1-input/` into verified, quality-controlled outputs in `3-output/` with full traceability from every claim back to its source.

- **Workflow** - three phases: analyze and draft, verify and ground, uniformize and deliver
- **Tailored program** - generates `INSTRUCTIONS.md` + `BENCHMARK.md` per objective, not ad-hoc summarization
- **Phase gates** - explicit gates enforced between phases
- **Single verification flow** - the `grounding` skill; the `validate` skill, the `process` verify phase, and the `update` closing step all call it rather than re-implementing
- **Tooling** - ships a deterministic grounding CLI plus a complete PDF toolkit

## Grounding CLI

Ships the `document-processing` command with a lexical-mode grounder (default, CPU-only, torch-free): a frozen-weight logistic over 13-18 signals per effort tier (low / medium / high; high is the default). Semantic retrieval + NLI entailment are opt-in via `--semantic` and the `[semantic]` extra.

- **Citations** - every hit returns line / column / paragraph / page / context snippet; the agent cites without rereading the source
- **Token saving** - measured 64-86% reduction vs batched generative grounding on real sources (SVG Medium article, Liu 2023 paper)
- **Performance** - ~165 ms/claim warm single-thread CPU (high tier); ~5.6s cold start (first run: loads SaT segmenter, first MT model, WordNet). Low/medium tiers faster (no MT)

### Effort tiers

The `lexical_effort` config key (or `--effort` CLI overlay) selects the signal set:

| Tier | Features | Cross-lingual | Notes |
|------|----------|---------------|-------|
| `low` | 13 | no | Fastest; English-only; no language detection |
| `medium` | 16 | no | Adds lingua language detection + WordNet antonym contradiction |
| `high` | 18 | yes | Adds argos-translate MT (CTranslate2 int8); default tier |

All three tiers are CPU-only with no extra install required (argos, SaT OpenVINO INT8, and WordNet ship in core).

Retrain a tier manifold on your own data:

```bash
document-processing train-lexical --effort {low,medium,high} --data PATH
```

`PATH` must be parquet or jsonl with `claim` / `source_text` / `label` columns, >= 200 rows, >= 40 per class.

### Data-science validated

The frozen-weight lexical manifold was validated on a held-out private RAG dataset (2752 gold labels) and VitaminC.

- **Macro-F1** - 0.817 on private RAG (2752 gold, joint logistic); 0.691 on VitaminC (hold-not-collapse: +0.136 vs base, -0.015 private RAG cost)
- **Zero-shot** - 0.808 on Liu 2023 / Han 2024 / Ye 2024 fixtures (same three academic papers as cascade archive)
- **Config** - `calibration.mode: lexical` in `config_document_processing.yaml`; override via `.stellars-plugins/config_document_processing.yaml` project-local

The six-iteration deterministic cascade archive (CV mean 1.0, three academic papers) exists under [`references/grounding-results/`](../references/grounding-results/) and is described in [`references/README.md`](../references/README.md). That engine is a back-compat fallback reachable via explicit `engine:` config override; it is not the current default.

### NLI / entailment grounding (the truth signal)

Lexical tests word presence, cosine tests topic, only entailment tests "does evidence support claim?". A cross-encoder reads `(evidence, claim)` -> entailment / neutral / contradiction = grounded / unconfirmed / contradicted.

- **Model** - `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli`, ONNX, torch-free, multilingual
- **Cross-lingual** - confirms claims (NB/FR vs EN source) that lexical + cosine cannot
- **Contradictions** - catches word-number + semantic contradictions the lexical guard misses
- **Public-data check** - `make grounding-validate ENGINE=nli` (VitaminC contradiction recall 0.81 vs lexical 0.05)

### Local domain calibration (Bayesian)

Calibrate per-corpus when default thresholds miss the domain. Bayesian logistic (bambi / PyMC) over the layer features (lexical + semantic + NLI); learned weights live in config, used with no fitting at run time.

```bash
# calibrate from labelled evidence, then transfer learned weights into config
document-processing calibrate --action update \
  --evidence evidence.json --profile .stellars-plugins/calibrator.json --semantic
document-processing config set-calibrator --profile .stellars-plugins/calibrator.json
```

- **Evidence** - JSON list `{claim, sources:[paths] (or source_text), label:0|1, lang?, weight?}`; LLM-eval prob works as a soft label
- **set-calibrator** - writes a `calibration:` block (engine, threshold, weights) into `.stellars-plugins/config_document_processing.yaml`
- **Incremental** - `--from <profile>` seeds the next fit from the posterior, feedback accumulates
- **Prior** - lives in config (`calibration.prior`), not code
- **Docs** - [`docs/grounding_calibration.md`](../docs/grounding_calibration.md); demo [`notebooks/01-kj-calibration-demo.ipynb`](../notebooks/01-kj-calibration-demo.ipynb)

| Layer | What it catches | Dep | In lexical mode |
|-------|-----------------|-----|-----------------|
| Exact (regex) | verbatim quotes | core | feeds logistic[^1] |
| Fuzzy (Levenshtein) | near-verbatim paraphrase | core | feeds logistic[^1] |
| BM25 (IDF recall) | distinctive claim tokens present | core | feeds logistic[^1] |
| Semantic (e5 + FAISS) | same meaning, different words | opt-in | opt-in unchanged |
| NLI (cross-encoder) | entailment / contradiction - true grounding, multilingual | opt-in | opt-in unchanged |

[^1]: In lexical mode (default), the Exact/Fuzzy/BM25 features plus 10-15 additional signals feed a frozen-weight logistic (LexicalVerdict). Individual threshold flags (`--threshold`, `--bm25-threshold`) apply to the cascade fallback path only.

- **Opt-in deps** - `[semantic]` extra: `onnxruntime`, `transformers`, `faiss-cpu`, `pyarrow`; calibration core deps `pymc`/`bambi`/`arviz`/`pandas`
- **Core package** - uses OpenVINO INT8 (SaT segmenter, high tier); `onnxruntime` is a `[semantic]` extra dependency only, not in core
- **Torch-free** - models are ONNX, downloaded on first use (e5 ~120 MB, NLI ~560 MB)
- **Default** - bare install = lexical high-tier; the `grounding` skill recommends enabling semantic/NLI at `document-processing setup`

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

- **Settings** - `./.stellars-plugins/settings.json` (project-local, sibling to `.claude/`)
- **Default model** - `intfloat/multilingual-e5-small` (118M params, multilingual, trained for retrieval)

### Enable OCR (optional, opt-in)

```bash
pip install 'stellars-claude-code-plugins[ocr]'
# plus a system tesseract install:
apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-deu  # etc per language
# brew install tesseract tesseract-lang                         # macOS
```

Enables auto-OCR fallback for scanned PDFs that have no sibling text file.

- **Language** - agent supplies `--ocr-lang <code>` per run (`eng`, `deu`, `fra`, `chi_sim`, etc); the tool never auto-detects
- **Cache** - auto-OCR results written as `<stem>.ocr.txt` next to the source with a header carrying quality stats (mean confidence, page count, language, timestamp)
- **Fallback** - without `[ocr]` extras the tool uses vision-OCR: the agent reads the PDF via the Read tool, transcribes pages, saves to `<stem>.ocr.txt`, reruns
- **Convention** - both paths produce the same sibling-file convention so subsequent grounding runs use the cached candidate without re-OCR

Native source formats (no extras required): `.txt`, `.md`, `.rst`, `.pdf` (text), `.docx`, `.odt`, `.rtf`, `.html` - extracted directly.

- **Warning-ack gate** - the stop-and-think gate surfaces per-source warnings (`OCR-FALLBACK`, `OCR-CANDIDATE`, `OCR-FAILED`, `OCR-LANG-NEEDED`, `OCR-MISSING`, `SOURCE-SKIPPED`) the agent must ack with terse reasoning before grounding consumes the result

### Usage

```bash
# Single claim, three-layer default
document-processing ground \
  --claim "Kubernetes runs on 12 nodes" \
  --source docs/source.md \
  --threshold 0.85 --bm25-threshold 0.5

# One document: extract claims, then ground them all
document-processing extract-claims --document docs/brief.md --output validation/claims.json
document-processing ground \
  --manifest validation/claims.json \
  --source docs/source.md \
  --output validation/grounding-report.md \
  --semantic --semantic-threshold 0.85

# Many documents via manifest
document-processing validate --manifest source_map.yaml --output-dir validation/

# Intra-document self-consistency
document-processing check-consistency --document docs/brief.md --output validation/consistency-report.md
```

- **ground** - `--claim TEXT` XOR `--manifest FILE`, plus `--source` (repeatable)
- **validate** - `--document FILE` (repeatable) + `--source` XOR `--manifest source_map.yaml`
- **--semantic** - boolean flag, default off; enables e5 embedding + NLI + calibrated verdict
- **Output** - all layer scores per claim, the winning passage, and location metadata
- **Reading** - see `skills/grounding/SKILL.md` for how the agent reads output (including "never blindly trust scores — verify via the pointer", the three core verdict rules, the OCR fallback chain)

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
| `grounding` | Grounding claims against source(s) via the CLI - "ground", "grounding", "check grounding", "run ground", "verify claims against a source". Pure grounding, no compliance. The canonical verification flow; `validate`, `process`, and `update` all call it |
| `validate` | Validating a document against rules and against its source - "validate document", "validate against rules", "check compliance and grounding", "audit document against source". Runs the `grounding` skill, then adds the compliance layer |
| `update` | Updating an existing `3-output/` document - "update the document", "add a new source to the timeline", "re-verify after sources changed", "apply corrections to the output". Ends with a mandatory CLI-grounding pass |
| `pdf` | PDF work - fill a form, extract text/tables, create/merge/split PDFs, OCR a scanned PDF, batch-process. Library reference + pre-built scripts + topic guides for forms, tables, OCR |

## Example usage

```
/document-processing:process synthesize expert opinions into unified position paper
```

The `process` skill walks through objective refinement, generates `INSTRUCTIONS.md` and `BENCHMARK.md` for user approval, scaffolds a WIP folder under `2-wip/<task-name>/`, then executes the three-phase workflow (analyze and draft, verify and ground, uniformize and deliver) before evaluating the result against `BENCHMARK.md` and promoting it to `3-output/`. The Verify & Ground phase invokes the `grounding` skill.

## How it works

The plugin operates over a fixed project layout with grounding as the single verification flow across all skills.

- **Layout** - `1-input/` read-only source material, `2-wip/<task-name>/` per-task drafts and reports, `3-output/` final delivered documents, `4-references/` examples and verified facts used as grounding anchors
- **WIP discipline** - every intermediate artifact stays in WIP until all rules pass; full convention in `skills/process/references/FOLDER-STRUCTURE.md`

Grounding is the single verification flow. The `grounding` skill runs the lexical-mode CLI (frozen-weight logistic over 13-18 signals per effort tier; semantic + NLI opt-in via `--semantic`), reads the per-claim verdicts, applies three core rules (agreement beats magnitude; a numeric/entity contradiction is the final word; re-recommend semantic on struggle), handles the scanned-PDF OCR fallback chain, and writes a grounding report plus an intra-document self-consistency report. The `validate` skill wraps it and layers compliance on top; the `process` skill calls it from its verify phase; the `update` skill calls it as a mandatory closing step. The claim-classification methodology for the synthesis workflow (DIRECT QUOTE / PARAPHRASE / INFERENCE / INTERPRETATION / UNSUPPORTED, with HIGH/MEDIUM/LOW severity) is in `skills/process/references/GROUNDING.md`.

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

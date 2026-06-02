---
name: grounding
description: Ground claims against source material with the deterministic grounding CLI - single claim, a whole document's claims, or a batch of documents via source_map.yaml. Pure grounding, no tone/style/format compliance (that is the `validate` skill). Use when asked to ground, do grounding, check grounding, run ground, or verify claims against a source / sources.
---

# Grounding Skill

Grounding a document is a **three-step chain**, not just step 2:

1. **`extract-claims`** — enumerate the load-bearing claims from the document into `claims.json` (heuristic, lossy — review it before grounding).
2. **`ground`** — score every claim against the source(s) with the deterministic CLI (regex exact + Levenshtein fuzzy + BM25, + optional semantic); read the verdicts, apply the verdict rules; write `grounding-report.md`.
3. **`check-consistency`** — check the document against *itself* for divergences grounding structurally can't see (`42 users` here vs `50 users` there; `dev/test/staging` vs `dev/staging/prod`); write `consistency-report.md`.

A document-grounding run produces **both** `grounding-report.md` and `consistency-report.md`. For a *single claim* (no document), run only step 2's single-claim form (`document-processing ground`). For *many documents*, `validate` runs the whole chain per client. **Always runs the CLI** - it is the canonical operational grounder; generative interpretation is only an on-top layer for semantic claims after the CLI ran.

The `validate` skill wraps this whole chain and adds a tone/style/length/format compliance layer on top; the `process` skill invokes this skill from its Verify & Ground phase; the `update` skill calls it as its mandatory closing step.

## Output style (MANDATORY for all generated artefacts)

Every file this skill writes (`grounding-report.md`, `consistency-report.md`, `claims.json` review notes) uses telegram-style: short clauses, drop articles/copulas where meaning stays clear, one fact per line, bullets not paragraphs, concrete numbers over adjectives, no hedging ("may"/"might"), imperative actions. Reviewers skim for verdicts - prose costs attention.

## Pre-flight install (MANDATORY - run every session, no asking)

Always run this single line BEFORE invoking `document-processing`. No-op when the package is already importable; auto-installs when missing OR when a stale shim is on PATH but the package is uninstalled in the active Python:

```bash
python3 -c "import stellars_claude_code_plugins" 2>/dev/null || python3 -m pip install --user --upgrade stellars-claude-code-plugins
```

Ships the `document-processing` CLI with deterministic three-layer grounding (regex exact + Levenshtein fuzzy + BM25 passage ranking). All three scores reported every call + line/column/paragraph/page/context per hit. Verify: `document-processing --help`. Never ask the user whether to install - just run the line. **The CLI is mandatory.** Generative interpretation is only an on-top layer for semantic claims after the CLI ran - never a substitute for it. If the package genuinely cannot be installed, say so and stop; do not silently degrade to manual search.

## Semantic grounding (+ NLI): opt-in per call via `--semantic` (recommend it by default)

**Posture: recommend semantic, enable it per call.** There is no persisted `semantic_enabled` setting anymore — semantic is a flag on the grounder. Pass `--semantic` to bring two layers online together:

- **Retrieval embedder + FAISS** (default `intfloat/multilingual-e5-small`, set via `semantic_model` in settings) — catches meaning-match when wording AND terms diverge
- **NLI entailment cross-encoder** (rides with semantic, no separate flag) — the truth signal: does the evidence *entail* the claim? Catches contradictions and cross-lingual matches the lexical layers structurally cannot reach. With NLI on, the verdict runs through the calibrated engine so entailment is weighed against the other layers, not a hard override

Decision each run:

- **Default → recommend `--semantic`.** Phrase it as the default: "Semantic + NLI grounding is the recommended default — the only layers that catch a passage that *means* the claim (or *contradicts* it) while sharing no wording. One-time cost: `pip install 'stellars-claude-code-plugins[semantic]'` plus model downloads on first use (~120 MB embedder + ~560 MB NLI). Use it?"
- **User declines → lexical-only for this session.** Three lexical layers, no persistence. Don't re-ask (the re-recommend-on-struggle rule below still applies).

Never pass `--semantic` while the `[semantic]` extra is uninstalled — the CLI hard-fails (exit 2) on that explicit contract. Install first, then `--semantic`.

### Never blindly trust scores. Verify generatively when in doubt

Scores = signals, not truth. Every layer can be fooled:

- exact: hits unrelated substring with same word order
- fuzzy: high on character overlap with opposite meaning ("3-6 hours" vs "36 hours")
- bm25: high on shared terms with no logical link
- semantic: high on topically-similar passage that doesn't support the claim

Tool ALWAYS gives a pointer (line/column/paragraph/page/context) even on UNCONFIRMED. Use it. Jump → read → judge. No full rescan needed — that's the point, saves tokens.

Verify generatively when ANY of:

- Borderline: winning layer within 0.05 of threshold (fuzzy 0.85-0.90, bm25 0.40-0.50, semantic 0.85-0.90) — close calls are the failure zone
- Layer disagreement: semantic ≥0.85 but fuzzy <0.6 AND bm25 <0.3 → topical similarity without real support, often noise
- Location off: pointer nowhere near where the claim should live → wrong chunk won
- Numeric / named-entity claims: models blur "3 seconds" vs "3 minutes"; always read
- Medium score on fake-sounding claim: reject unless named entity appears in the quoted passage — fake-entity detection is the whole point

Verdict output: quote the passage + state supports / contradicts / topical-only. Never override CONFIRMED without evidence, never accept CONFIRMED without reading.

### When to RE-RECOMMEND semantic to the user

The user declined semantic for this session, but the lexical-only pass is struggling — >25% UNCONFIRMED OR any claim in the fuzzy 0.5-0.85 AND bm25 0.2-0.5 "almost grounded" zone that semantic usually rescues → stop and re-offer (the situation has changed; this isn't nagging):

> Three-layer grounding left N/M UNCONFIRMED and K in the almost-grounded zone. Semantic + NLI grounding (requires the `[semantic]` extra, model downloads first time) usually resolves these. Use it for this document?
>
> 1. `pip install 'stellars-claude-code-plugins[semantic]'`
> 2. re-run with `--semantic`

Never silently flip a deliberate opt-out — offer, wait for consent, proceed.

## Source format support

Grounding tools accept these formats directly via `--source`:

- `.txt` / `.md` / `.rst` - read as UTF-8
- `.pdf` (text) - extracted via pypdf
- `.pdf` (scanned/image-only) - falls back through the chain below
- `.docx` - extracted via python-docx
- `.odt` - extracted via odfpy
- `.rtf` - extracted via striprtf
- `.html` / `.htm` - stripped via stdlib `html.parser`

**Scanned-PDF fallback chain** (when text extraction yields < 100 chars/page):

1. **Sibling lookup** (same stem, same directory). Priority order:
   `.ocr.txt` → `.txt` → `.docx` → `.doc` → `.odt` → `.md` → `.rst`
   → `.html` → `.htm` → `.rtf`. Image extensions (`.png` / `.jpg` /
   `.tiff` etc) and the original `.pdf` are excluded. First match
   wins; the tool fires `OCR-FALLBACK` warning.
2. **Auto-OCR** (when `[ocr]` extras installed: `pip install
   stellars-claude-code-plugins[ocr]` + system tesseract). Caller
   MUST supply `--ocr-lang <code>` (e.g. `eng`, `deu`, `fra`,
   `chi_sim`). Tool runs pytesseract with the supplied language,
   caches result as `<stem>.ocr.txt` next to the source.
3. **Vision-OCR by Claude** (when extras missing OR OCR fails).
   Use the Read tool on the PDF with `pages=N` per page,
   transcribe each page in source language, save as
   `<stem>.ocr.txt` next to source, rerun.

**Gate warnings the agent will see and how to respond**:

| Warning | Trigger | Response |
|---|---|---|
| `OCR-FALLBACK` | Sibling text file found OR auto-OCR succeeded with mean confidence ≥80% AND ≥100 chars | Optional review. Ack `'sibling-text-accepted'` or `'good-quality-OCR-accepted'` |
| `OCR-CANDIDATE` | Auto-OCR mid-confidence (60-80%) OR sibling `.ocr.txt` still has the tool-generated header (unreviewed) | Open `<stem>.ocr.txt`, scan for transcription errors (numbers, names, technical terms), edit corrections in place, delete the header block to mark reviewed. Then ack `'candidate-reviewed'` (or `'candidate-accepted-as-is'` after a quick scan) |
| `OCR-FAILED` | Auto-OCR mean confidence < 60% OR < 20 chars extracted | Either correct the cached `<stem>.ocr.txt` candidate manually, OR delete it and run vision-OCR via Read tool on the PDF, save corrected transcript as `<stem>.ocr.txt`, rerun. Source is SKIPPED until the candidate is replaced |
| `OCR-LANG-NEEDED` | Scanned PDF, no sibling, `--ocr-lang` not supplied | Inspect the document (filename tokens, visible page text via Read tool), pick the right Tesseract code (the gate suggests one from sparse extraction). Rerun with `--ocr-lang <code>` |
| `OCR-MISSING` | Scanned PDF, no sibling, OCR extras missing | Either install `[ocr]` extras + system tesseract, OR vision-OCR via Read tool, save as `<stem>.ocr.txt`, rerun |
| `SOURCE-MISSING` / `SOURCE-SKIPPED` | File not found / unsupported format / decode error | Fix the path / convert format upstream / accept the skip with `'skip-acceptable'` |

**Candidate-file convention**: `<stem>.ocr.txt` is the highest-priority sibling. Tool-generated candidates open with a `# OCR candidate for ...` header carrying quality stats, language, timestamp. Editing the candidate replaces the auto-OCR text. **Deleting the header block marks the candidate as human-reviewed and silences `OCR-CANDIDATE` on the next run** (otherwise the warning re-fires - a never-reviewed candidate cannot graduate silently to ground truth).

## Core rules

Three rules override default per-claim behaviour. Apply in order: rule 2 trumps 1, rule 3 fires after 1-2 decided.

**Rule 1: agreement beats magnitude.** Confidence = how many layers agree, NOT a single layer's peak. Claim with sem=0.90, fuzzy=0, bm25=0 is LESS confirmed than sem=0.75, fuzzy=0.65, bm25=0.45 — multi-layer agreement rules out topical-noise false positives. Prefer `agreement_score` over individual scores. Semantic-only hit = read the pointer before accepting; lone layer at threshold is usually topical similarity, not grounding.

**Rule 2: contradiction flag is the final word.** `numeric_mismatches` OR `entity_mismatches` non-empty → verdict CONTRADICTED, overrides every other score. Example: claim "Kubernetes runs on 42 nodes" vs source "12 nodes" → `numeric_mismatches=[("42", "12")]` → CONTRADICTED even with `exact_score=1.0` on surrounding wording. Never promote CONTRADICTED to CONFIRMED, never suppress — the numeric/entity disagreement IS the finding.

**Rule 3: re-recommend semantic on struggle.** >25% UNCONFIRMED OR any claim in `fuzzy_score` [0.5, 0.85] AND `bm25_score` [0.2, 0.5] almost-grounded zone → ask user ONCE. Never silent auto-enable — user consent was explicit, one-way. Template:

```
Three-layer grounding left N/M claims UNCONFIRMED and K in the
almost-grounded zone. Semantic grounding (4th layer, +150MB model
first time, requires `[semantic]` extra) often resolves these. Enable?
  - yes: re-run with --semantic
  - no: keep current verdicts
```

Record answer in `./.stellars-plugins/settings.json` — avoids re-asking same session.

## Per-claim workflow

**What counts as a claim.** Claims are the load-bearing statements - the assertions and assumptions a document rests on that need validation, plus every quote that needs validation. Concretely: factual statements, attributions ("X said Y"), numbers, dates, named entities, direct quotes, and inferences presented as established. Not claims: structural/editorial sentences, transitions, formatting-level text, the document's own headings - skip those.

Extract every claim in that sense.

**Step 0 (document / batch runs): extract-claims.** Let the heuristic extractor build the claims list instead of typing 30+ claims by hand - shrinks manual work from ~30 min to ~5 min plus review. Lossy: markdown headers, bullet stubs, and short sentences get dropped. Always review the generated `claims.json` before grounding. Reason: enumeration is the one step where manual work scales badly; grounding + attribute sidecar does the judgement.

```bash
document-processing extract-claims \
  --document clients/actone/opportunity_brief.md \
  --output validation/claims.json
```

Per claim:

1. **State claim** exactly as in document
2. **Run grounding tool FIRST.** Use `document-processing ground` for single claims, `document-processing ground` for a claims.json. Three layers run independently (regex + Levenshtein + BM25), all three scores + line/column/paragraph/page/context per hit — no rereading source, huge token saving. Secondary: disciplined generative interpretation ONLY when all three lexical layers fail AND claim is semantic (summary / synthesis / cross-passage inference). Never skip the tool; run first, add generative on top when lexical signal absent.
3. **Mark status** from tool output:
   - CONFIRMED — `match_type=exact` → quote `exact_matched_text` at `exact_location`
   - CONFIRMED (fuzzy) — `match_type=fuzzy` → quote `fuzzy_matched_text` at `fuzzy_location`, note paraphrase tolerance
   - CONFIRMED (topical / bm25) — `match_type=bm25` → quote `bm25_matched_text` at `bm25_location`, note wording differs but terms align
   - UNCONFIRMED — `match_type=none` → no lexical evidence; generative only for semantic claims, else remove/rephrase
   - CONTRADICTED — source directly contradicts (manual call; re-run with contradicting phrase for location)
   - INFERRED — reasonable inference not directly stated; explain, tool confirms absence of verbatim
   - NOT APPLICABLE — structural/editorial, not fact-based; skip tool

## Using the grounding CLI

Subcommands and how they fit together:

| Subcommand | Input → output | Notes |
|---|---|---|
| `ground --claim TEXT --source FILE…` | one claim → match (stdout, `--json` for full object) | no `--output`; exit 0 grounded / 1 unconfirmed |
| `extract-claims --document FILE [--output claims.json]` | a document → `claims.json` | heuristic, lossy — review before grounding |
| `ground --manifest claims.json --source FILE… [--output report.md]` | claims.json → `grounding-report.md` (or `--json`) | `--primary-source FILE` flags cross-source pollution; exit 0 all grounded / 1 some unconfirmed; exit 2 if a source is binary/unextractable |
| `check-consistency --document FILE [--output report.md]` | a document → `consistency-report.md` | markdown only (no `--json`); exit 0 clean / 1 findings exist |
| `validate --manifest source_map.yaml --output-dir DIR` | manifest → `DIR/<client>/{claims.json,grounding-report.md,consistency-report.md}` | runs extract-claims+ground+check-consistency per client; `--stop-on-error` aborts on first failure; exit 0 all clean / 1 any issue / 2 malformed yaml |
| `setup [--force]` | writes `./.stellars-plugins/settings.json` | model/cache config; semantic is opt-in per call via `--semantic`, not a setting |

Shared optional flags on `ground` / `validate`: `--threshold 0.85` (fuzzy), `--bm25-threshold 0.5`, `--semantic` (boolean; enables the embedding + NLI + calibrated-verdict bundle, default off), `--semantic-threshold` / `--semantic-threshold-percentile`. `ground` also takes `--ocr-lang CODE` (scanned PDFs), `--scanned-threshold`, `--ack-warning TOKEN=reason` (the stop-and-think gate).

### Mode A: single-claim probe — on-demand checks during review

```bash
document-processing ground \
  --claim "Kubernetes runs on 12 nodes" \
  --source docs/architecture.md \
  --json
```

All three scores always return, even when only one fires — layered signal distinguishes verbatim / paraphrase / topical / fabrication.

### Mode B: one document — the full grounding chain (extract → ground → consistency)

This is the default flow when you have a document to ground. Run all three steps; do not stop after step 2.

```bash
# Step 1 — enumerate claims (heuristic, lossy). REVIEW claims.json before step 2:
# reword ambiguous claims, split compound ones, add anything the heuristic dropped.
document-processing extract-claims --document docs/brief.md --output validation/claims.json

# Step 2 — ground every claim against the source(s).
# claims.json: list of strings or [{"claim": "...", "id": "..."}]
# Pass --semantic to enable the semantic + NLI layers (opt-in per call)
# Pass --primary-source to flag cross-source pollution when multiple --source flags are present
document-processing ground \
  --manifest validation/claims.json \
  --source docs/source.md \
  --source docs/research.md \
  --primary-source docs/source.md \
  --output validation/grounding-report.md \
  --threshold 0.85 \
  --bm25-threshold 0.5 \
  --semantic     # add to enable the bundle; omit for lexical-only

# Step 3 — check the document against itself (always; this is part of grounding a document).
document-processing check-consistency --document docs/brief.md --output validation/consistency-report.md
```

Outputs: `validation/grounding-report.md` (per-claim verdicts) **and** `validation/consistency-report.md` (intra-document divergences). Apply the Core rules to step 2's output; resolve every consistency finding before declaring the document grounded. Binary sources (PDF / PNG / JPG / DOCX / XLSX / ZIP that fail extraction) fail loud with exit code 2 and a suggested extractor (`pdftotext`, `docx2txt`, `pandoc`). See "Self-consistency check" below for what step 3's findings look like.

### Mode C: many documents — batch via source_map.yaml

`source_map.yaml` shape:

```yaml
clients:
  actone:
    sources:
      - clients/actone/transcript.md
      - clients/actone/research_doc.md
    document: clients/actone/opportunity_brief.md
    primary_source: clients/actone/transcript.md   # optional; flags cross-source pollution
  arelion:
    sources: [clients/arelion/transcript.md]
    document: clients/arelion/opportunity_brief.md
```

Invoke:

```bash
document-processing validate \
  --manifest source_map.yaml \
  --output-dir validation/
```

For every client entry it runs the full Mode B chain — `extract-claims` -> `ground` (with cross-source provenance) -> `check-consistency` — writing `validation/<client>/claims.json`, `validation/<client>/grounding-report.md`, and `validation/<client>/consistency-report.md`. A per-client error is logged to `validation/<client>/error.log` and the batch continues unless `--stop-on-error` is passed.

Exit codes:
- `0` every client succeeded with no unconfirmed claims and no consistency findings
- `1` at least one client has unconfirmed claims, consistency findings, or an error
- `2` the `source_map.yaml` itself was malformed

### verification_needed: second-guess this CONFIRMED verdict

`GroundingMatch.verification_needed=true` fires whenever the tool thinks a CONFIRMED verdict deserves a human/agent re-check before trust. Reasons fill `grounding-report.md` inline so reviewers don't have to guess which signal tripped:

- semantic hit without lexical co-support (topical noise risk) — `lexical_co_support=false`
- grounded on non-primary source when `--primary-source` was supplied (cross-source pollution)
- winning-layer score within 0.05 of its threshold (borderline)
- claim has numbers, passage has numbers on the same unit/context key, but `numeric_mismatches` is empty (deterministic check silent but co-presence heuristic fires — possible multi-value range collision the specificity gate suppressed)

`claim_attributes` sidecar lists numbers + entities for both claim and winning passage side-by-side, so the second-guess pass can compare without rereading source. Never downgrade CONFIRMED to UNCONFIRMED on `verification_needed=true` without reading - the flag is a cue, not a verdict.

`grounded_source` names the path where the winning-layer hit was found. Always check it before citing: a claim grounded on the wrong file in a multi-source batch is a silent failure mode the earlier tool couldn't catch.

### Tool output maps to status

| Tool output | Status |
|-------------|--------|
| `exact_score=1.0` | CONFIRMED |
| `fuzzy_score ≥ threshold`, `exact_score=0` | CONFIRMED (fuzzy) — paraphrase |
| `bm25_score ≥ bm25_threshold`, `exact=0`, `fuzzy<threshold` | CONFIRMED (topical) — wording differs, same terms |
| `semantic_score ≥ semantic_threshold`, lexical all below | CONFIRMED (semantic) — meaning matches, wording+terms diverge. Only with `--semantic` |
| all layers below thresholds | UNCONFIRMED — quote best available for diagnostics |

Priority when multiple fire: exact > fuzzy > bm25 > semantic.

Tool returns `exact_location` / `fuzzy_location` / `bm25_location` with `line_start`, `column_start`, `paragraph`, `page`, `context_before`, `context_after` — cite directly, don't reread source. Saves tokens, keeps citations precise.

### When to reach for generative (secondary) grounding

Only when all three lexical layers return `none` AND claim is semantic (summary / synthesis / cross-passage inference). Disciplined: still cite WHICH passages contributed + acknowledge absence of verbatim/paraphrase/term match. Never let generative override lexical UNCONFIRMED for factual claims — that's fabrication territory.

## NLI / entailment grounding (optional, strongest)

Lexical = word presence. cosine = topic. neither = truth. NLI = truth: does evidence support claim?

- cross-encoder reads `(evidence, claim)` -> entailment / neutral / contradiction = grounded / unconfirmed / contradicted
- model `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli`, ONNX, torch-free, multilingual, ~560 MB first use
- **multilingual** - confirms cross-lingual claim (NB/FR vs EN source); lexical+cosine cannot
- catches word-number + semantic contradictions lexical guard misses (VitaminC contradiction recall 0.81 vs lexical 0.05)
- in `ground()`: NLI argmax = first-class verdict; contradiction folds into guard, entailment counts as signal
- NLI verdict drives grounding when its grounder is active; default lexical path unchanged
- residual: NLI calls unsupported-addition "contradiction" (NEI<->contra) - calibrator tempers once trained

## Local domain calibration (optional)

Default thresholds miss your domain? calibrate per-corpus. Bayesian logistic (bambi/PyMC) over the layer features (lexical + semantic + NLI).

- **evidence** - JSON list `{claim, sources:[paths] (or source_text), label:0|1, lang?, weight?}`; label = gold (1 grounded, 0 not); LLM-eval prob works as soft label
- **calibrate** - `document-processing calibrate --action update --evidence evidence.json --profile .stellars-plugins/calibrator.json --semantic`; grounds each record, fits posterior, saves
- **inspect** - `calibrate --action show --profile ...` prints coefficient mean +/- sd
- **transfer to config** - `config set-calibrator --profile ...` writes `calibration:` block (engine, threshold, weights) into `.stellars-plugins/config_document_processing.yaml`; grounding uses weights, no fitting at run time
- **incremental** - `--from <profile>` seeds new fit from prior posterior; feedback accumulates
- **public-data check** - `make grounding-validate ENGINE=nli` runs VitaminC; reproducible, no private corpus
- prior lives in config (`calibration.prior`), not code
- never calibrate without user's own labelled evidence - do not invent labels to "improve" scores
- demo: `notebooks/calibration_demo.ipynb`; full doc: `docs/grounding_calibration.md`

## Output: grounding-report.md

Telegram-style template:

```markdown
# Source Grounding Report

- document: <path>
- sources: <path(s)>
- date: <date>

## Claims

### 1. <id>
- claim: "<exact text>"
- status: CONFIRMED
- scores: exact 1.00 / fuzzy 1.00 / bm25 1.00
- source: "<supporting fragment>" @ `docs/source.md:L42:C5 ¶3 pg2`

### 2. <id>
- claim: "<exact text>"
- status: CONFIRMED (topical)
- scores: exact 0.00 / fuzzy 0.52 / bm25 0.88
- source: "<winning passage>" @ `docs/source.md:L88 ¶5`
- note: wording differs, terms match

### 3. <id>
- claim: "<exact text>"
- status: UNCONFIRMED
- scores: exact 0.00 / fuzzy 0.62 / bm25 0.20
- best fuzzy: "<fragment>" @ `docs/source.md:L88 ¶5` (ratio 0.62 < 0.85)
- best bm25: `¶12` (recall 0.20 < 0.5)
- action: remove or rephrase

### 4. <id>
- claim: "<exact text with number>"
- status: CONFIRMED (semantic) - VERIFY
- scores: exact 0.00 / fuzzy 0.22 / bm25 0.05 / semantic 0.84
- source file: `docs/research.md` [NON-PRIMARY]
- verification: no lexical co-support, grounded on non-primary source, numeric co-presence without clear mismatch
- claim numbers: [("42", "", "users")]  |  passage numbers: [("50", "", "users")]
- action: second-guess - passage says 50 users, claim says 42 users, may be a silent numeric slip

...

## Summary

- total: X
- confirmed: X
- unconfirmed: X
- contradicted: X
- inferred: X
- n/a: X
- grounding score: X/Y (confirmed / total factual)
```

UNCONFIRMED/CONTRADICTED: list concrete corrections.

When invoked standalone, write the report to `validation/grounding-report.md` (create `validation/` if absent). When invoked by `validate` / `process` / `update`, write wherever the caller specifies via `--output`.

## Self-consistency check (step 3 of grounding a document)

Step 3 of the Mode B chain — run it on every document-grounding run, not just when something looks off. Grounding (steps 1-2) catches claim-vs-source mismatch; it is structurally blind to the document contradicting *itself* - the brief that lists `dev/test/staging` on one page and `dev/staging/prod` on another, or "42 users" here and "50 users" there. `validate` runs this automatically per client; in Mode B you run it explicitly after `ground`:

```bash
document-processing check-consistency \
  --document path/to/document.md \
  --output validation/consistency-report.md
```

Findings come in two shapes:

- **numeric**: same `(unit, context_word)` key with different values across lines. Example: "42 users" on line 10 vs "50 users" on line 80.
- **entity_set**: token-sets with high Jaccard overlap (>= 0.5) but non-identical members. Catches the `dev/test/staging` vs `dev/staging/prod` case; also flags `Python 3.11` vs `Python 3.12` head-token variants with numeric tails.

Every finding lists line numbers. Resolve intrinsic inconsistencies before declaring the document grounded - the document claims X and not-X means one of them is wrong, grounding against external source won't disambiguate. Exit code 1 when findings exist (automation-friendly). Markdown only — no `--json`.

## Rules

- Never modify source document(s) — read-only; source integrity is the whole basis of grounding
- Run the CLI first, every time — generative grounding is only the on-top layer for semantic claims
- Quote evidence — actual text, not "confirmed"; verdict without quote is assertion
- Be specific — UNCONFIRMED / CONTRADICTED entries cite exact offending text + location + concrete fix
- This skill produces grounding + consistency reports only; tone/style/length/format compliance is the `validate` skill

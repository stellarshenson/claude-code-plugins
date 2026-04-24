---
name: validate-document
description: Validate a document against its source material for grounding, then check tone, style, length and format compliance. Use when asked to validate, verify, check grounding, or audit a document against a source.
---

# Document Validation Skill

Two phases: (1) source grounding - extract claims, verify each; (2) compliance - tone, style, length, format.

## Output style (MANDATORY for all generated artefacts)

Every file the skill writes (`grounding-report.md`, `compliance-checklist.md`, `validation-summary.md`, `criteria.md`) uses telegram-style: short clauses, drop articles/copulas where meaning stays clear, one fact per line, bullets not paragraphs, concrete numbers over adjectives, no hedging ("may"/"might"), imperative actions. Reviewers skim for verdicts - prose costs attention.

## Install (MANDATORY)

```bash
pip install stellars-claude-code-plugins
```

Ships `document-processing` CLI with deterministic three-layer grounding (regex exact + Levenshtein fuzzy + BM25 passage ranking). All three scores reported every call + line/column/paragraph/page/context per hit. Verify: `document-processing --help`. Without install → manual search only, no programmatic grounding.

## Check semantic-grounding consent (MANDATORY every run)

Read `./.stellars-plugins/settings.json` (project-local, sibling to `.claude/`) before grounding:

```bash
test -f .stellars-plugins/settings.json && cat .stellars-plugins/settings.json
```

Missing file → run `document-processing setup` once (writes answer, never re-prompts). Never auto-enable semantic — needs optional deps (`pip install 'stellars-claude-code-plugins[semantic]'`) + 150MB model download on first use; surprise installs waste user bandwidth.

Read `semantic_enabled`:

- `true` → pass `--semantic on` to every `ground` / `ground-many` call. 4th layer (ModernBERT + FAISS) catches meaning-match when wording AND terms diverge. Useful for long/abstract sources.
- `false` (default) → pass `--semantic off` or omit. Three lexical layers only.
- Missing file → run `document-processing setup` and proceed per answer.

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
- Medium score on fake-sounding claim: reject unless named entity appears in the quoted passage — fake-entity detection is the whole point of H2

Verdict output: quote the passage + state supports / contradicts / topical-only. Never override CONFIRMED without evidence, never accept CONFIRMED without reading.

### When to RE-RECOMMEND semantic to the user

`semantic_enabled=false` AND three-layer pass leaves many UNCONFIRMED (>25% OR any claim fuzzy 0.5-0.85 AND bm25 0.2-0.5 — the "almost grounded" zone that semantic usually rescues) → stop and ask:

> Three-layer grounding left N/M UNCONFIRMED and K in the almost-grounded zone. Semantic grounding (4th layer, +150MB model first time, requires `[semantic]` extra) often resolves these. Enable?
>
> 1. `pip install 'stellars-claude-code-plugins[semantic]'`
> 2. `document-processing setup --force` and answer yes
> 3. re-run with `--semantic on`

Never silently enable — user already declined once. Offer, wait for consent, proceed.

## Phase 0: Gather Criteria

Ask if not provided.

**Required:**
- **Document to validate**: path
- **Source document(s)**: path(s) for grounding

**Optional (offer defaults):**
- **Word count range**: min-max (default: no constraint)
- **Tone**: first-person / formal / technical / conversational (default: infer)
- **Style rules**: patterns to enforce or prohibit (default: none)
- **Target audience**: default general
- **Section format rules**: bullets, section lengths, heading structure (default: none)
- **Focus rules**: excluded or prioritised content (default: none)
- **Format rules**: encoding, spacing, links (default: UTF-8, single spacing, no links)
- **Custom rules**: key-value pairs

Store all criteria.

## Phase 1: Setup

Create `validation/` in project root. All artifacts here — single directory = one place to delete, diff, archive.

```
validation/
├── criteria.md              <- collected criteria summary
├── grounding-report.md      <- Phase 2 output
├── compliance-checklist.md  <- Phase 3 output
├── validation-summary.md    <- Phase 4 output
└── <filename>_corrected.<ext> <- Phase 5 output (best-effort corrected copy)
```

Write `criteria.md`.

## Phase 2: Source Grounding Check

### Core rules

Three rules override default per-claim behaviour. Apply in order: rule 2 trumps 1, rule 3 fires after 1-2 decided.

**Rule 1: agreement beats magnitude.** Confidence = how many layers agree, NOT a single layer's peak. Claim with sem=0.90, fuzzy=0, bm25=0 is LESS confirmed than sem=0.75, fuzzy=0.65, bm25=0.45 — multi-layer agreement rules out topical-noise false positives. Prefer `agreement_score` over individual scores. Semantic-only hit = read the pointer before accepting; lone layer at threshold is usually topical similarity, not grounding.

**Rule 2: contradiction flag is the final word.** `numeric_mismatches` OR `entity_mismatches` non-empty → verdict CONTRADICTED, overrides every other score. Example: claim "Kubernetes runs on 42 nodes" vs source "12 nodes" → `numeric_mismatches=[("42", "12")]` → CONTRADICTED even with `exact_score=1.0` on surrounding wording. Never promote CONTRADICTED to CONFIRMED, never suppress — the numeric/entity disagreement IS the finding.

**Rule 3: re-recommend semantic on struggle.** >25% UNCONFIRMED OR any claim in `fuzzy_score` [0.5, 0.85] AND `bm25_score` [0.2, 0.5] almost-grounded zone → ask user ONCE. Never silent auto-enable — user consent was explicit, one-way. Template:

```
Three-layer grounding left N/M claims UNCONFIRMED and K in the
almost-grounded zone. Semantic grounding (4th layer, +150MB model
first time, requires `[semantic]` extra) often resolves these. Enable?
  - yes: re-run with --semantic on
  - no: keep current verdicts
```

Record answer in `./.stellars-plugins/settings.json` — avoids re-asking same session.

### Per-claim workflow

Extract every factual claim, assertion, attribution, number, date, quote.

**Step 0 (batch runs): extract-claims.** Let the heuristic extractor build the claims list instead of typing 30+ claims by hand - shrinks manual work from ~30 min to ~5 min plus review. Lossy: markdown headers, bullet stubs, and short sentences get dropped. Always review the generated `claims.json` before grounding. Reason: enumeration is the one step where manual work scales badly; grounding + attribute sidecar does the judgement.

```bash
document-processing extract-claims \
  --document clients/actone/opportunity_brief.md \
  --output validation/claims.json
```

Per claim:

1. **State claim** exactly as in document
2. **Run grounding tool FIRST.** Use `document-processing ground` for single claims, `ground-many` for batches. Three layers run independently (regex + Levenshtein + BM25), all three scores + line/column/paragraph/page/context per hit — no rereading source, huge token saving. Secondary: disciplined generative interpretation ONLY when all three lexical layers fail AND claim is semantic (summary / synthesis / cross-passage inference). Never skip the tool; run first, add generative on top when lexical signal absent.
3. **Mark status** from tool output:
   - CONFIRMED — `match_type=exact` → quote `exact_matched_text` at `exact_location`
   - CONFIRMED (fuzzy) — `match_type=fuzzy` → quote `fuzzy_matched_text` at `fuzzy_location`, note paraphrase tolerance
   - CONFIRMED (topical / bm25) — `match_type=bm25` → quote `bm25_matched_text` at `bm25_location`, note wording differs but terms align
   - UNCONFIRMED — `match_type=none` → no lexical evidence; generative only for semantic claims, else remove/rephrase
   - CONTRADICTED — source directly contradicts (manual call; re-run with contradicting phrase for location)
   - INFERRED — reasonable inference not directly stated; explain, tool confirms absence of verbatim
   - NOT APPLICABLE — structural/editorial, not fact-based; skip tool

### Using the grounding CLI

Batch — builds `grounding-report.md` in one shot:

```bash
# claims.json: list of strings or [{"claim": "...", "id": "..."}]
# Pass --semantic on if settings.semantic_enabled == true
# Pass --primary-source to flag cross-source pollution when multiple --source flags are present
document-processing ground-many \
  --claims validation/claims.json \
  --source docs/source.md \
  --source docs/research.md \
  --primary-source docs/source.md \
  --output validation/grounding-report.md \
  --threshold 0.85 \
  --bm25-threshold 0.5 \
  --semantic on     # omit or 'off' when settings disables it
```

Binary sources (PDF / PNG / JPG / DOCX / XLSX / ZIP) now fail loud with exit code 2 and a suggested extractor (`pdftotext`, `docx2txt`, `pandoc`). Previous silent U+FFFD decode masked this as a grounding miss.

Single-claim probe — on-demand checks during review:

```bash
document-processing ground \
  --claim "Kubernetes runs on 12 nodes" \
  --source docs/architecture.md \
  --json
```

All three scores always return, even when only one fires — layered signal distinguishes verbatim / paraphrase / topical / fabrication.

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
| `semantic_score ≥ semantic_threshold`, lexical all below | CONFIRMED (semantic) — meaning matches, wording+terms diverge. Only with `--semantic on` |
| all layers below thresholds | UNCONFIRMED — quote best available for diagnostics |

Priority when multiple fire: exact > fuzzy > bm25 > semantic.

Tool returns `exact_location` / `fuzzy_location` / `bm25_location` with `line_start`, `column_start`, `paragraph`, `page`, `context_before`, `context_after` — cite directly, don't reread source. Saves tokens, keeps citations precise.

### When to reach for generative (secondary) grounding

Only when all three lexical layers return `none` AND claim is semantic (summary / synthesis / cross-passage inference). Disciplined: still cite WHICH passages contributed + acknowledge absence of verbatim/paraphrase/term match. Never let generative override lexical UNCONFIRMED for factual claims — that's fabrication territory.

**Output** (`grounding-report.md`) — telegram-style template:

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

## Phase 2.5: Self-Consistency

Grounding catches claim-vs-source mismatch. It cannot catch same-document internal inconsistencies - the brief that lists `dev/test/staging` on one page and `dev/staging/prod` on another. Run the intra-document checker after grounding, before compliance:

```bash
document-processing check-consistency \
  --document path/to/document.md \
  --output validation/consistency-report.md
```

Findings come in two shapes:

- **numeric**: same `(unit, context_word)` key with different values across lines. Example: "42 users" on line 10 vs "50 users" on line 80.
- **entity_set**: token-sets with high Jaccard overlap (>= 0.5) but non-identical members. Catches the `dev/test/staging` vs `dev/staging/prod` case; also flags `Python 3.11` vs `Python 3.12` head-token variants with numeric tails.

Every finding lists line numbers. Resolve intrinsic inconsistencies before shipping - the document claims X and not-X means one of them is wrong, grounding against external source won't disambiguate. Exit code 1 when findings exist (automation-friendly).

## Phase 3: Compliance Checklist

Check against all criteria. Generate `compliance-checklist.md` — telegram-style template:

```markdown
# Compliance Checklist

- document: <path>
- date: <date>

## word_count
- count: XXX
- range: [min, max]
- pass: yes/no
- action: trim N / expand N / ok

## tone
- expected: <tone>
- violations: [quotes] / none
- action: rephrase N passages / ok

## style_rules
(per rule)
- rule: <desc>
- status: pass/fail
- violations: [quotes] / none
- action: fix / ok

## focus_rules
- prohibited found: [quotes] / none
- required present: [list] / yes/no
- action: remove N / add N / ok

## format
- encoding: UTF-8 yes/no
- spacing: correct yes/no
- links: N / none
- action: fix / ok

## section_format
(per rule)
- rule: <desc>
- status: pass/fail
- details: [measurements]
- action: fix / ok

## custom_rules
(per rule)
- rule: <desc>
- status: pass/fail
- evidence: [details]
- action: fix / ok
```

Python scripts for measurable checks (word count, point length, links) — never eyeball; human counting on long docs is unreliable, off-by-N errors cascade into wrong verdicts.

## Phase 4: Validation Summary

Generate `validation-summary.md` — telegram-style template:

```markdown
# Validation Summary

- document: <path>
- sources: <path(s)>
- date: <date>

## grounding
- claims: X
- score: X/Y (Z%)
- issues: [list] / none

## compliance
- rules: X
- passed: X
- failed: X
- issues: [list] / none

## verdict
PASS / PASS WITH WARNINGS / FAIL

## required_actions
1. <fix>
2. <fix>
...
(or "none - document passes all checks")
```

## Phase 5: Apply Corrections (best effort)

Always produce corrected copy — separate file so original stays reviewable:

1. Copy original → `validation/<filename>_corrected.<ext>`
2. Apply corrections:
   - UNCONFIRMED: rephrase to align with source or remove
   - CONTRADICTED: fix to match source
   - Compliance failures: fix formatting, trim, adjust tone
3. Re-run both checks against corrected version
4. Update `validation-summary.md` with post-correction status
5. Present diff to user

## Important Notes

- Never modify source document(s) — read-only; source integrity is the whole basis of grounding
- All artifacts in `validation/` — single cleanup point
- Python for measurements — never manual; eyeballing corrupts verdicts
- Quote evidence — actual text, not "confirmed"; verdict without quote is assertion
- Be specific — violations cite exact offending text + location
- Preserve originals — corrected version separate file with `_corrected` suffix; overwrite only on explicit request

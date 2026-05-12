---
name: validate
description: Validate a finished document against rules AND against its source - first grounds every claim via the grounding CLI, then checks tone, style, length, format, focus and custom rules. Produces a validation/ folder with grounding report, compliance checklist, summary, and a best-effort corrected copy. Use when asked to validate a document, validate against rules, check compliance and grounding, or audit a document against a source.
---

# Validate Skill

Two layers: (1) **grounding** - every factual claim verified against source material; (2) **compliance** - tone, style, length, format, focus, custom rules. The grounding layer is delegated to the **`grounding`** skill; this skill gathers criteria, runs grounding through it, then adds the compliance layer and produces the verdict.

## Output style (MANDATORY for all generated artefacts)

Every file this skill writes (`grounding-report.md`, `consistency-report.md`, `compliance-checklist.md`, `validation-summary.md`, `criteria.md`) uses telegram-style: short clauses, drop articles/copulas where meaning stays clear, one fact per line, bullets not paragraphs, concrete numbers over adjectives, no hedging ("may"/"might"), imperative actions. Reviewers skim for verdicts - prose costs attention.

## Pre-flight install (MANDATORY - run every session, no asking)

```bash
python3 -c "import stellars_claude_code_plugins" 2>/dev/null || python3 -m pip install --user --upgrade stellars-claude-code-plugins
```

No-op when the package is importable; auto-installs when missing OR when a stale shim is on PATH but the package is uninstalled in the active Python. Never ask - just run the line. The CLI is mandatory for the grounding layer; without it, say so and stop rather than degrade to manual search.

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

If the user is unsure how to phrase rules, load the real rule-set examples in `${CLAUDE_PLUGIN_ROOT}/examples/` (a full `INSTRUCTIONS.md` with measurable uniformization rules R0-R4, plus a worked uniformization checklist) and use them to draft concrete, measurable criteria - word ranges with a preferred band, exclusion lists with example quotes, a falsifiable "does this sentence change what the reader knows" test. Adapt the shape, not the content.

Store all criteria.

## Phase 1: Setup

Create `validation/` in project root. All artifacts here — single directory = one place to delete, diff, archive.

```
validation/
├── criteria.md              <- collected criteria summary
├── claims.json              <- extracted claims (grounding layer)
├── grounding-report.md      <- grounding layer output
├── consistency-report.md    <- self-consistency check output
├── compliance-checklist.md  <- compliance layer output
├── validation-summary.md    <- final verdict
└── <filename>_corrected.<ext> <- best-effort corrected copy
```

Write `criteria.md`.

## Phase 2: Grounding layer (delegate to the `grounding` skill)

Run the grounding flow per the **`grounding`** skill (`${CLAUDE_PLUGIN_ROOT}/skills/grounding/SKILL.md`) - it carries the canonical procedure: pre-flight install, semantic-consent gate, source-format + OCR fallback chain, the three core rules (agreement-beats-magnitude / contradiction-is-final / re-recommend-semantic), the per-claim workflow, `extract-claims`, the `ground` / `ground-many` CLI, `verification_needed` second-guessing, status mapping, and the self-consistency check.

Concretely, in single-document mode:

```bash
document-processing extract-claims --document <doc> --output validation/claims.json
# review validation/claims.json, then:
document-processing ground-many \
  --claims validation/claims.json \
  --source <source> [--source <other>] [--primary-source <source>] \
  --output validation/grounding-report.md \
  --threshold 0.85 --bm25-threshold 0.5 \
  --semantic on   # only if settings.semantic_enabled == true

document-processing check-consistency --document <doc> --output validation/consistency-report.md
```

Outputs: `validation/grounding-report.md` (claim verdicts: CONFIRMED / CONFIRMED-fuzzy / CONFIRMED-topical / CONFIRMED-semantic-VERIFY / UNCONFIRMED / CONTRADICTED / INFERRED / N-A, with quoted evidence + location) and `validation/consistency-report.md` (intra-document numeric / entity-set conflicts). For a batch of documents, run the `grounding` skill's `source_map.yaml` mode instead.

Apply the `grounding` skill's verdict rules verbatim - do not invent a parallel ruleset here. Carry the grounding-score and the list of UNCONFIRMED / CONTRADICTED items forward into Phases 3-5.

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

## consistency
- findings: X / none
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
   - Consistency findings: reconcile the conflicting values
   - Compliance failures: fix formatting, trim, adjust tone
3. Re-run grounding + compliance against the corrected version
4. Update `validation-summary.md` with post-correction status
5. Present diff to user

## Important Notes

- Never modify source document(s) — read-only; source integrity is the whole basis of grounding
- All artifacts in `validation/` — single cleanup point
- Python for measurements — never manual; eyeballing corrupts verdicts
- Quote evidence — actual text, not "confirmed"; verdict without quote is assertion
- Be specific — violations cite exact offending text + location
- Preserve originals — corrected version separate file with `_corrected` suffix; overwrite only on explicit request
- The grounding mechanics live in the `grounding` skill - this skill never re-implements them, it calls them

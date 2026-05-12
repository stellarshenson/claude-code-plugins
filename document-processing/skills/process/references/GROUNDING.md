# Grounding Methodology

Every factual claim in a produced document must be traceable to a specific passage in a source document. This prevents hallucination, ensures legal defensibility, and enables quality auditing.

## Assumption Extraction Process

Read the draft document and for each factual statement determine its relationship to source material:

1. **DIRECT QUOTE** - verbatim text from a source document
2. **PARAPHRASE** - restated content preserving original meaning
3. **INFERENCE** - conclusion drawn from source material but not explicitly stated
4. **INTERPRETATION** - author's assessment or analysis of source material
5. **UNSUPPORTED** - claim with no identifiable source

## Standardized Assumption Format

For each claim extracted from the draft, record:

```markdown
### [ID]: [Claim Title]
- **Claim**: [Statement as it appears in the draft]
- **Type**: [DIRECT QUOTE / PARAPHRASE / INFERENCE / INTERPRETATION]
- **Source**: [Document name, page/section/paragraph]
- **Source Text**: [Verbatim relevant passage from source]
- **Impact**: [HIGH/MEDIUM/LOW] - [Why accuracy matters here]
- **Status**: [VERIFIED / PARTIALLY VERIFIED / UNVERIFIED / CONTRADICTED]
- **Action**: [Keep as-is / Revise to... / Remove / Add source qualifier]
```

## Verification Rules by Type

**DIRECT QUOTE**: Verify verbatim accuracy against source. Check spelling, numbers, dates, names. Any deviation is a failure.

**PARAPHRASE**: Verify semantic accuracy. The paraphrase must not distort meaning, omit critical qualifiers, or add implications not present in the source. Compare side by side.

**INFERENCE**: Verify that the source material actually supports the inference. If the logical connection is weak or requires assumptions not stated, either remove the claim or qualify it with "This suggests..." / "This may indicate...".

**INTERPRETATION**: Must be explicitly flagged as interpretation in the output document, not presented as fact. Acceptable phrasing: "This indicates...", "In context, this suggests...", "The pattern of... points to...".

**UNSUPPORTED**: Must be removed from the final document or qualified as author's assessment with clear language: "It appears that..." with acknowledgment that no source confirms this.

## Legal-Domain Grounding Requirements

For legal documents, grounding requirements are stricter:

- **Court findings**: Must cite specific ruling (sygn. akt), date, and quote or close paraphrase
- **Legal provisions**: Must cite article number and statute (e.g., art. 113 par. 1 KRO)
- **Expert opinions**: Must name the source and context
- **Factual claims about events**: Must reference source document with date
- **Dates and numbers**: Must be verified against source - no rounding, no approximation

## Universal Facts (4-references/facts/)

The `4-references/facts/` folder contains verified universal facts that serve as grounding anchors. These do not require per-document verification because they are established independently:

- Legal provisions (statutory articles with exact wording)
- Court precedent summaries (established case law)
- Scientific consensus statements (peer-reviewed findings)
- Institutional standards and definitions

When a claim in the draft matches a universal fact from `4-references/facts/`, it can be grounded against that reference instead of a source document from `1-input/`. The assumption register should note `Source: 4-references/facts/<filename>` for such claims.

## Output Artifacts

The grounding process produces two artifacts in the WIP folder:

**`<task-name>-assumptions.md`** - the full register of extracted claims with verification status

**`<task-name>-grounding-report.md`** - summary containing:
- Total claims extracted and verified
- Count by type and status
- List of corrections made
- Remaining unverified items with risk assessment
- Contradictions found between sources (if any)

## Severity-Based Filtering

Not every sentence needs a grounding entry. Focus on:

- **HIGH**: Dates, numbers, court findings, legal references, attributed statements
- **MEDIUM**: Characterizations of behavior, descriptions of patterns, causal claims
- **LOW**: Structural statements, transitions, formatting-level content

For HIGH impact claims, verification is mandatory. For MEDIUM, verification is recommended. LOW impact items can be skipped unless they contain implicit factual claims.

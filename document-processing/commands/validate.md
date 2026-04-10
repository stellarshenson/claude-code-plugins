---
description: Validate a document against source material for grounding and compliance
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Skill, AskUserQuestion]
argument-hint: "path to document to validate, and source material to check against"
---

# Validate Document

Invoke the `document-processing:validate-document` skill to run full validation: source grounding (extract claims, verify against source) then compliance checking (tone, style, length, format).

Produces artifacts in `validation/` directory: grounding report, compliance checklist, validation summary, and corrected copy.

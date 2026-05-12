---
description: Ground claims against source material with the grounding CLI - single claim, one document, or many via source_map.yaml
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Skill, AskUserQuestion]
argument-hint: "a claim + source, OR a document + source(s), OR a path to source_map.yaml"
---

# Grounding

Invoke the `document-processing:grounding` skill. Pure grounding - no tone/style/format compliance (that is `/document-processing:validate`). The skill always runs the `document-processing` CLI; generative interpretation is only an on-top layer for semantic claims.

Three modes (the skill picks based on the argument):

- **Single claim** - `document-processing ground --claim "..." --source <file> --json`
- **One document** - `extract-claims` -> review `claims.json` -> `ground-many --claims ... --source <each source> --output validation/grounding-report.md`, then `check-consistency`
- **Many documents** - a `source_map.yaml` declaring `clients[].sources` + `document` (+ optional `primary_source`) -> `document-processing validate-many --source-map source_map.yaml --output-dir validation/`, producing `validation/<client>/{claims.json,grounding-report.md,consistency-report.md}` per client

## Pre-flight install (MANDATORY, no asking)

Before invoking `document-processing`, always run:

```bash
python3 -c "import stellars_claude_code_plugins" 2>/dev/null || python3 -m pip install --user --upgrade stellars-claude-code-plugins
```

No-op when the package is importable; auto-installs when missing or when a stale shim is on PATH but the package is uninstalled in the active Python.

## `source_map.yaml` shape

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

A per-client error is logged to `validation/<client>/error.log` and the batch continues unless `--stop-on-error` is passed.

Exit codes:
- `0` every client succeeded with no unconfirmed claims and no consistency findings
- `1` at least one client has unconfirmed claims, consistency findings, or an error
- `2` the `source_map.yaml` itself was malformed

## When NOT to use this

- You also need tone/style/length/format compliance checks -> use `/document-processing:validate`
- You are building a new deliverable from sources -> use `/document-processing:process`
- You are updating an existing output -> use `/document-processing:update`

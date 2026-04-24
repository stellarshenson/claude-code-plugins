---
description: Batch validate many documents against their sources via source_map.yaml
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Skill, AskUserQuestion]
argument-hint: "path to source_map.yaml (declares clients[].sources + document)"
---

# Validate Many

Batch-validate a set of client documents declared in a `source_map.yaml` manifest. Runs extract-claims, ground-many (with cross-source provenance), and check-consistency for every client entry, writing per-client reports under a single output root.

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

Invoke via:

```bash
document-processing validate-many \
  --source-map source_map.yaml \
  --output-dir validation/
```

Produces `validation/<client>/claims.json`, `validation/<client>/grounding-report.md`, and `validation/<client>/consistency-report.md` per client. A per-client error is logged to `validation/<client>/error.log` and the batch continues unless `--stop-on-error` is passed.

Exit codes:
- `0` every client succeeded with no unconfirmed claims and no consistency findings
- `1` at least one client has unconfirmed claims, consistency findings, or an error
- `2` the `source_map.yaml` itself was malformed

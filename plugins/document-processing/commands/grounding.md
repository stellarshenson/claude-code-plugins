---
description: Ground claims against source material with the grounding CLI - single claim, one document, or many via source_map.yaml
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Skill, AskUserQuestion]
argument-hint: "a claim + source, OR a document + source(s), OR a path to source_map.yaml"
---

# Grounding

Invoke `document-processing:grounding` skill. Pure grounding - no tone/style/format compliance (that = `/document-processing:validate`). Skill always runs `document-processing` CLI; generative interpretation only on-top layer for semantic claims.

Three modes (skill picks from argument):

- **Single claim** - `document-processing ground --claim "..." --source <file> --json`
- **One document — full grounding chain (extract → ground → consistency)** - `document-processing extract-claims --document <doc> --output validation/claims.json` -> review `claims.json` -> `document-processing ground --manifest validation/claims.json --source <src1> --source <src2> --output validation/grounding-report.md` -> `document-processing check-consistency --document <doc> --output validation/consistency-report.md`. All three steps run; run produces both `grounding-report.md` and `consistency-report.md`.
- **Many documents** - `source_map.yaml` declaring `clients[].sources` + `document` (+ optional `primary_source`) -> `document-processing validate --manifest source_map.yaml --output-dir validation/`, runs same chain per client, producing `validation/<client>/{claims.json,grounding-report.md,consistency-report.md}`

## Default engine

Lexical mode is the default: a frozen-weight logistic over 13-18 signals selected by `lexical_effort` (low / medium / high, default high). All lexical tiers are CPU-only with no extra install required. Use `--effort` CLI overlay or set `lexical_effort` in config to switch tiers.

## Optional layers (opt-in)

- **semantic** - `--semantic` adds bge-m3 retrieval + reranker (OpenVINO int8, torch-free)
- **NLI / entailment** - the truth signal: cross-encoder reads `(evidence, claim)` -> grounded / unconfirmed / contradicted; multilingual, catches contradictions + cross-lingual matches lexical misses
- **calibration** - tune the verdict to your corpus from labelled evidence: `calibrate --action update --evidence f.json` then `config set-calibrator`; learned weights live in config. Public-data check: `make grounding-validate ENGINE=nli`. Full doc: `docs/grounding_calibration.md`

## Pre-flight install (MANDATORY, no asking)

Before invoking `document-processing`, always run:

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
OLDER=$(printf '%s\n%s\n' "$LIB" "$PLUG" | sort -V | head -1)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && [ "$OLDER" = "$LIB" ] && { echo "STALE: library $LIB older than plugin $PLUG - refusing to run on an outdated CLI; re-run the upgrade"; exit 1; }
echo "toolkit $LIB"
```

**Run the CLI without touching the caller's project.** The gate above puts it on PATH, so the bare command name is the whole invocation. `uv run` instead resolves whatever project the working directory sits in and writes `uv.lock` and `.venv` into it, so if you reach for uv pass `--no-project` (`uv run --no-project <cli> ...`) - it skips project discovery, leaves the tree untouched and still finds the same PATH binary. `--no-sync` and `--frozen` are not substitutes; both still create `.venv`.

The upgrade always runs - a stale-but-importable install is exactly the failure this gate prevents, and the reinstall also repairs a stale shim on PATH whose package is uninstalled in the active Python.

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

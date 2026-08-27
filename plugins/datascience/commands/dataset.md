---
description: Acquire a dataset into the project's external data directory - gitignored archive plus tracked licence sidecar generated from one spec - or audit the corpora a project already holds
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, WebFetch, Skill]
argument-hint: "the corpus to acquire or audit, e.g. 'fetch ragtruth for the grounding task' or 'what datasets does this project hold, under which licences'"
---

# Dataset

Read the `datascience:dataset` skill first - it is the single source of truth for the two-artifact layout, the admission gate, the sidecar shape, and the fetcher contract. Do NOT duplicate its content here. The `examples/` sidecars and fetcher skeleton win on any conflict.

## What to do

1. Read the `datascience:dataset` skill, then the closest `examples/` artifact - `dataset-ragtruth.md` for a public corpus, `dataset-edgar-restricted.md` for a restricted one, `fetch_datasets.py` for the fetcher skeleton
2. **Location gate (before creating anything)** - propose `data/external/<task>-datasets/` plus the alternatives visible on disk; WAIT for the answer, then reuse the confirmed location for the rest of that task without asking again
3. **Admission gate before any download** - licence permits the intended use (commercial, training and redistribution are three separate permissions), the corpus carries what the task consumes, the task-shape mapping writes as a one-line rewrite, no provenance overlap with the evaluation set. Name which filter a rejected corpus failed
4. **Sidecar first** - the spec dict in `scripts/fetch_<task>_datasets.py` is the single source of truth; `--dry-run` renders every sidecar and fetches nothing, so licences and sizes are read before a byte costs bandwidth. Never hand-write or hand-edit a sidecar
5. **Fetch** - named args fetch one corpus, no args fetch all; a failed corpus prints `SKIP <id>: <error>` and continues; stage, archive, remove staging; the archive contains its own sidecar
6. **Gitignore** - whitelist the sidecars, ignore everything else under the folder; verify with `git check-ignore -v` on one archive and one sidecar before the first commit
7. **Restricted corpus** - the three extra sidecar bullets (restriction clauses, reason, exclusion mechanism); no archive at all where redistribution is forbidden; credentials come from the environment or the vault at fetch time - never the spec, the sidecar, or the repo

## Audit mode

When asked what a project holds: list the tracked `dataset-*.md` sidecars under `data/external/`, report each corpus's licence, size and restrictions from its sidecar, and flag any archive or extracted tree present WITHOUT a sidecar - that is a defect, per the skill's first rule.

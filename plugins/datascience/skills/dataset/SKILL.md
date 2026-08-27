---
name: dataset
description: Acquire public and private datasets into a task folder under the project's external data directory - each corpus lands as a gitignored `dataset-<name>.zip` archive plus a tracked `dataset-<name>.md` sidecar recording licence, size, provenance, restrictions and the mapping onto the task, generated from one spec and re-rendered from the observed download so its row counts cannot drift. Use when fetching, downloading, adding, vendoring or documenting a corpus, benchmark or training set, when auditing what data a project holds and under what licence, or when a dataset arrives under access restrictions. Triggers - "download this dataset", "fetch the corpus", "add a dataset", "get the benchmark", "vendor this data", "what licence is this data", "document the dataset", "dataset sidecar", "external data".
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebFetch
---

# Dataset acquisition

Every dataset a project acquires gets TWO artifacts in a task folder under the external data directory. A corpus present without its sidecar is a defect - nobody downstream can tell what it is, where it came from, or whether it may be used.

- `dataset-<name>.zip` - the archive, **gitignored**
- `dataset-<name>.md` - the sidecar, **tracked**

Sidecar survives the archive. Archives are large, rebuildable and machine-local; the sidecar is the only record that reaches another machine, another repo, or a reader six months on.

## Ask where it goes (MANDATORY - before creating anything)

Propose a location and WAIT for the answer. Not before the first byte is fetched - before the directory is created, because the sidecar is written and tracked before any download happens. Projects differ on where external data lives, and a corpus written to the wrong tree is a large file to move and a gitignore rule to redo.

- Suggest `data/external/<task>-datasets/`, naming the task you inferred from the request
- Offer the alternatives you can see on disk - an existing `data/external/*` sibling, a `datasets/` root, a path already in `.gitignore`
- Wait for the answer, then reuse the confirmed location for the rest of that task without asking again

## Layout

```
data/external/<task>-datasets/
├── dataset-ragtruth.zip          # gitignored
├── dataset-ragtruth.md           # tracked
├── dataset-edgar-restricted.md   # tracked - describes the tree below, no archive
└── edgar-restricted/             # gitignored
```

- **Task folder, not a flat dump** - one folder per task (`grounding-datasets/`, `ner-datasets/`, `forecasting-datasets/`), so a project running three tasks does not have to reason about which corpus belongs to which
- **Archive per corpus** where the corpus fits an archive; an extracted tree beside the sidecar where it does not (multi-GB, incremental, or fetched file-by-file)
- **`<name>`** - lowercase-hyphen, matches the spec key, identical across `.zip` and `.md`
- Scaffolding a project that will hold data → create `data/external/<task>-datasets/` with the gitignore rules below before the first fetch

## Admission gate

Decide admission BEFORE downloading, and say which filter a rejected corpus failed. Discovering after the fetch that the licence forbids the use means the data is already on disk and in someone's pipeline.

- **Licence permits the intended use** - the gating filter, and the one that is checked first. Commercial use, training and redistribution are three separate permissions; verify each. A CC-BY-NC or "no training" card fails a commercial project regardless of how good the corpus is
- **The corpus carries what the task consumes** - claims without their source documents cannot be grounded; text without labels cannot be supervised. Name what the task needs and confirm it ships
- **Task shape maps** - write the mapping as a one-line rewrite (`response span → claim; retrieved passage → evidence`). If it cannot be written, the corpus does not fit
- **Provenance overlap** - a corpus drawn from the same document population as the evaluation set contaminates it. Either exclude, or admit as a restricted slice with the disjointness clause spelled out

## The sidecar

**Generated from the spec, never hand-written.** A hand-written sidecar drifts from what the fetcher actually downloaded; a generated one cannot.

**Licence is the load-bearing field.** It is why the sidecar is tracked while the archive is not - months later the archive says nothing about what may be done with it, and a corpus whose terms nobody can state is a corpus nobody can ship. Record the identifier exactly (`MIT`, `CC-BY-4.0`, `Apache-2.0`), not a paraphrase, plus the underlying works' status when it differs from the packaging - a public-domain government document redistributed under an Apache-2.0 dataset card is two different permissions and both matter. Where the terms restrict use (non-commercial, no-training, attribution-required, share-alike), that restriction goes in the bullet, not in a caveat.

Fixed shape - title, why-this-corpus paragraph, fact bullets, `## Caveats`, `## Provenance`:

| Field | Carries |
|---|---|
| Source | HuggingFace id, GitHub repo, or the URL pattern fetched - one `Source` line whatever the kind |
| Licence | the identifier, plus the underlying works' status when it differs |
| Size | rows and splits, or documents and pages - a number, not "large" |
| Languages | enumerated |
| How negatives were made | perturbation, natural, or none-ship-with-the-corpus |
| How labels were made | human, LLM-judged, or unlabeled |
| Mapping onto our task | the one-line rewrite from the admission gate |

- **Why-this-corpus first** - one paragraph naming what this corpus does that the others do not. Without it the next reader cannot tell whether it can be dropped
- **Caveats are mandatory and specific** - register mismatch, machine translation, unverified labels, low document diversity, a host that 403s an unrecognised user agent. "Some limitations apply" is not a caveat
- **Provenance names the decision** - who admitted this corpus, when, and the script that fetched it. Close with the tracked-vs-gitignored line so a reader who sees only the sidecar knows the archive is absent by design

Mirror `examples/dataset-ragtruth.md` verbatim for shape.

## Private and restricted datasets

Same two artifacts, three extra bullets. A restriction that lives only in the fetch code is a restriction that gets relaxed by the next person to touch it.

- **Restriction** - the filter clauses, stated as clauses, with `both clauses, no relaxation` where they are conjunctive
- **Reason for the restriction** - what admitting the unrestricted corpus would break
- **The exclusion mechanism** - the list, its source, and how identifiers were resolved, with the count that survived and the count that did not

Credentials never enter the sidecar, the spec, or the repo. Read them from the environment or the vault at fetch time; the sidecar records that access is gated and how it is obtained, never the token.

Where restricted access forbids redistribution, the archive is not built at all - only the sidecar is, and it says so. Mirror `examples/dataset-edgar-restricted.md`.

## The fetcher

One script per task folder, `scripts/fetch_<task>_datasets.py`. Skeleton to mirror: `examples/fetch_datasets.py`.

- **One spec dict is the source of truth** - the sidecar is rendered from it, then re-rendered after the fetch with the row counts the download actually produced. A hand-typed `size` that a Hub dataset has since outgrown is the drift this closes; `licence` is still asserted, so verify it against the card
- **Sidecar first, then download** - `--dry-run` writes every sidecar and fetches nothing, so the licences and sizes can be read before a byte costs bandwidth
- **Stage, then archive** - splits land in `_staging_<name>/` as parquet, get zipped, staging is removed. A partial download never masquerades as a complete archive
- **The archive contains its own sidecar** - a `.zip` copied to another machine explains itself
- **A failed corpus is a result, not a crash** - print `SKIP <id>: <error>` and continue; one dead Hub id must not abort a nine-corpus fetch
- **Named args fetch one corpus**, no args fetch all
- Re-running is idempotent - staging is cleared on entry, the archive is overwritten

## Gitignore

Whitelist the sidecars, ignore everything else under the folder - so a new corpus is ignored by default and a new sidecar is tracked by default:

```gitignore
!/data/external/
/data/external/*
!/data/external/.gitkeep
# Sidecars are tracked. The archives and extracted trees they describe are not.
!/data/external/<task>-datasets/
/data/external/<task>-datasets/*
!/data/external/<task>-datasets/*.md
```

Verify with `git check-ignore -v <path>` on one archive and one sidecar before the first commit. An archive committed by accident is expensive to remove from history.

## Rules

- No corpus without a sidecar, and no sidecar without the admission gate having been answered
- Never hand-edit a generated sidecar - change the spec and re-render
- Never commit an archive or an extracted tree
- Never put a credential in the spec, the sidecar, or the script
- A restriction is recorded in the sidecar, not only in the code that applies it
- State the licence exactly; "open" and "free" are not licences

<!-- improved 2026-08-12 | body authored at 1301w / 121L (within the 1500-2000w budget for a skill of this scope) | quality n/a (eval skipped at author request) | trigger n/a (eval skipped at author request) | via improve-skill -->

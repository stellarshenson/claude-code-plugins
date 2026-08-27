"""Fetch the admitted corpora into data/external/<task>-datasets/.

Every corpus here passed the admission gate - LICENCE permits the intended use
(checked first, and the only filter that can make the data unusable after it is
downloaded), the corpus carries what the task consumes, and the task shape maps.

For each corpus this writes a sidecar `dataset-<name>.md` from the spec below,
then downloads and archives it as `dataset-<name>.zip`. The sidecars are tracked
in git; the archives are not.

Run:  uv run python scripts/fetch_datasets.py             # all
      uv run python scripts/fetch_datasets.py ragtruth    # one
      uv run python scripts/fetch_datasets.py --dry-run   # sidecars only
"""

from pathlib import Path
import shutil
import sys
import zipfile

TASK = "grounding"
OUT = Path(__file__).resolve().parent.parent / "data" / "external" / f"{TASK}-datasets"

# ONE source of truth: sidecars are rendered from this, so a description can
# never drift from what was actually downloaded.
DATASETS = {
    "ragtruth": {
        "title": "RAGTruth",
        "source": "`wandb/RAGTruth-processed` on HuggingFace",
        "hf": ["wandb/RAGTruth-processed"],
        "licence": "MIT",
        "size": "17,790 responses - 15,090 train / 2,700 test",
        "languages": "English",
        "negatives": "Naturally occurring LLM hallucinations - 6 models answering real "
        "retrieval prompts; no perturbation",
        "labels": "Human expert span annotation",
        "why": "The only corpus where domain, negative construction and licence are all "
        "correct at once. Negatives are the error distribution a production system "
        "actually meets, not a synthetic approximation of it.",
        "caveats": "English only. Retrieval contexts derive from MS MARCO / CNN-DM / Yelp, "
        "so the documents are public-web register rather than business documents.",
        "mapping": "response span -> claim; retrieved passage -> evidence; "
        "any hallucinated span in a sentence -> that claim is unsupported",
    },
}

SIDECAR = """# {title}

{why}

- **Source** - {source}
- **Licence** - {licence}
- **Size** - {size}
- **Languages** - {languages}
- **How negatives were made** - {negatives}
- **How labels were made** - {labels}
- **Mapping onto our task** - {mapping}

## Caveats

{caveats}

## Provenance

Admitted against the licence / contents / task-shape gate; see the Licence bullet
above for the terms this corpus may be used under.

Fetched by `scripts/{script}`. The archive `dataset-{name}.zip` is
gitignored; this sidecar is tracked.
"""

FIELDS = (
    "title",
    "why",
    "licence",
    "size",
    "languages",
    "negatives",
    "labels",
    "mapping",
    "caveats",
)


def write_sidecar(name, spec):
    body = SIDECAR.format(
        name=name,
        task=TASK,
        source=spec.get("source") or ", ".join(f"`{h}`" for h in spec.get("hf", [])),
        script=Path(__file__).name,
        **{k: spec.get(k, "-") for k in FIELDS},
    )
    if spec.get("subsets"):
        body += "\n## Subsets fetched\n\n" + "\n".join(f"- `{s}`" for s in spec["subsets"]) + "\n"
    path = OUT / f"dataset-{name}.md"
    path.write_text(body)
    return path


def fetch(name, spec):
    """Stage every split as parquet, archive, drop staging. A partial download
    never masquerades as a complete archive."""
    from datasets import load_dataset

    staging = OUT / f"_staging_{name}"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    written = 0
    observed: list[str] = []
    for hf_id in spec.get("hf", []):
        for sub in spec.get("subsets") or [None]:
            tag = f"{hf_id.replace('/', '__')}{'__' + sub if sub else ''}"
            try:
                ds = load_dataset(hf_id, sub) if sub else load_dataset(hf_id)
            except Exception as e:  # noqa: BLE001 - a failed corpus is a result, not a crash
                print(f"    SKIP {tag}: {type(e).__name__}: {str(e)[:110]}", flush=True)
                continue
            for split, d in ds.items():
                f = staging / f"{tag}__{split}.parquet"
                d.to_parquet(f)
                written += 1
                observed.append(f"{split} {len(d):,}")
                print(f"    {tag}/{split}: {len(d)} rows -> {f.name}", flush=True)

    if not written:
        shutil.rmtree(staging)
        return None

    # Re-render from what the download ACTUALLY produced, so the sidecar's row
    # counts are observed rather than asserted. Written once before the fetch so
    # `--dry-run` has something to review; rewritten here with the real numbers.
    write_sidecar(name, {**spec, "size": " / ".join(observed) or spec.get("size", "-")})

    archive = OUT / f"dataset-{name}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(staging.iterdir()):
            z.write(f, f.name)
        # The archive carries its own sidecar - a .zip copied to another machine
        # explains itself.
        z.write(OUT / f"dataset-{name}.md", f"dataset-{name}.md")
    shutil.rmtree(staging)
    return archive


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    dry = "--dry-run" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)

    for name in args or list(DATASETS):
        if name not in DATASETS:
            print(f"unknown dataset {name!r}; known: {', '.join(DATASETS)}")
            continue
        spec = DATASETS[name]
        print(f"\n=== {name} - {spec['title']}", flush=True)
        print(f"  sidecar -> {write_sidecar(name, spec).name}", flush=True)
        if dry:
            continue
        archive = fetch(name, spec)
        if archive:
            print(
                f"  archive -> {archive.name} ({archive.stat().st_size / 1e6:.1f} MB)", flush=True
            )
        else:
            print("  archive -> NONE (every split failed; see SKIP lines)", flush=True)

    print(f"\nsidecars and archives in {OUT}")
    print("archives are gitignored; sidecars are tracked")


if __name__ == "__main__":
    main()
